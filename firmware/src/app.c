/**
 * app.c — Lógica principal da braçadeira Pulso.
 *
 * Fluxo a cada 5 s:
 *   1. calcula BPM e SpO2 com a janela de amostras do MAX30102
 *   2. faz o ranging UWB e calcula a posição
 *   3. lê a bateria
 *   4. monta o pacote de 20 bytes e envia pela LoRaWAN
 * Em paralelo, o botão SOS e a detecção de queda geram envios imediatos.
 */
#include "app.h"
#include "hal.h"
#include "packet.h"
#include "sos.h"
#include "ppg.h"
#include "fall.h"
#include "uwb_pos.h"
#include "pulso_config.h"
#include "max30102.h"
#include "lis2dh12.h"
#include "max17048.h"
#include <string.h>

#define PPG_N (CFG_PPG_SAMPLE_HZ * CFG_PPG_WINDOW_S)

static app_status_t st;
static sos_t   sos;
static fall_t  fall;
static uint8_t seq;
static uint32_t next_tx_ms, last_acc_ms;
static bool    fall_pending;
static vec3_t  pos;

/* buffer circular da janela PPG */
static uint32_t ppg_red[PPG_N], ppg_ir[PPG_N];
static uint16_t ppg_head, ppg_count;

void app_push_ppg(const uint32_t *red, const uint32_t *ir, uint16_t n)
{
    for (uint16_t i = 0; i < n; i++) {
        ppg_red[ppg_head] = red[i]; ppg_ir[ppg_head] = ir[i];
        ppg_head = (uint16_t)((ppg_head + 1) % PPG_N);
        if (ppg_count < PPG_N) ppg_count++;
    }
}

void app_push_accel(float ax, float ay, float az)
{
    uint32_t now = hal_millis();
    uint32_t dt = last_acc_ms ? now - last_acc_ms : 1000u / CFG_ACC_SAMPLE_HZ;
    last_acc_ms = now;
    if (fall_update(&fall, ax, ay, az, now, dt)) fall_pending = true;
}

static void apply(uint8_t act)
{
    if (act & SOS_ACT_LEDS_OFF)  { hal_led(LED_RED, false); hal_led(LED_GREEN, false); }
    if (act & SOS_ACT_LED_RED)   { hal_led(LED_GREEN, false); hal_led(LED_RED, true); }
    if (act & SOS_ACT_LED_GREEN) { hal_led(LED_RED, false); hal_led(LED_GREEN, true); }
    if (act & SOS_ACT_VIBRATE)   hal_vibrate(400);
}

static void send_packet(pkt_type_t type)
{
    /* janela PPG em ordem cronológica */
    static uint32_t r[PPG_N], ir[PPG_N];
    uint16_t start = (uint16_t)((ppg_head + PPG_N - ppg_count) % PPG_N);
    for (uint16_t i = 0; i < ppg_count; i++) {
        r[i] = ppg_red[(start + i) % PPG_N]; ir[i] = ppg_ir[(start + i) % PPG_N];
    }
    ppg_result_t v = ppg_compute(r, ir, ppg_count, CFG_PPG_SAMPLE_HZ);

    uwb_anchor_t an[CFG_UWB_MAX_ANCHORS]; float d[CFG_UWB_MAX_ANCHORS];
    uint8_t n = hal_uwb_ranging(an, d, CFG_UWB_MAX_ANCHORS);
    if (n >= 2) {
        vec3_t p = pos;
        float rms;
        float tag_z = an[0].pos.z - CFG_UWB_ANCHOR_HEIGHT_M + CFG_UWB_TAG_HEIGHT_M;
        if (uwb_solve(an, d, n, tag_z, &p, &rms)) pos = p;
    }

    st.battery = max17048_soc_pct();
    pulso_packet_t pk = {
        .type = (uint8_t)type, .device_id = hal_device_id(), .timestamp = hal_unix_time(),
        .bpm = v.valid ? v.bpm : 0, .spo2 = v.valid ? v.spo2 : 0,
        .x_dm = (int16_t)(pos.x * 10.0f), .y_dm = (int16_t)(pos.y * 10.0f), .z_dm = (int16_t)(pos.z * 10.0f),
        .battery = st.battery, .flags = 0, .seq = seq++,
    };
    if (sos_active(&sos))            pk.flags |= PKT_FLAG_SOS;
    if (sos.state == SOS_ACKED)      pk.flags |= PKT_FLAG_SOS_ACKED;
    if (fall_pending)                pk.flags |= PKT_FLAG_FALL;
    if (v.no_contact)                pk.flags |= PKT_FLAG_NO_CONTACT;
    if (hal_is_charging())           pk.flags |= PKT_FLAG_CHARGING;
    if (st.battery < CFG_BATT_LOW_PCT) pk.flags |= PKT_FLAG_LOW_BATT;

    uint8_t buf[PKT_SIZE];
    pkt_encode(&pk, buf);
    /* SOS e eventos vão com confirmação; periódicos sem, para economizar bateria */
    hal_lora_send(CFG_LORA_PORT_UPLINK, buf, PKT_SIZE, type != PKT_TYPE_PERIODIC);

    if (type == PKT_TYPE_EVENT) fall_pending = false;
    st.last_bpm = pk.bpm; st.last_spo2 = pk.spo2;
    st.x = pos.x; st.y = pos.y; st.z = pos.z;
    st.packets_sent++;
}

static void handle_downlink(void)
{
    uint8_t dl[8];
    size_t n = hal_lora_poll_downlink(dl, sizeof dl);
    if (n == 0) return;
    switch (dl[0]) {
    case CFG_DL_CMD_SOS_ACK:   apply(sos_on_ack(&sos));   break;
    case CFG_DL_CMD_SOS_CLOSE: apply(sos_on_close(&sos)); break;
    case CFG_DL_CMD_VIBRATE:   hal_vibrate(1000);         break;
    default: break;
    }
}

void app_init(void)
{
    memset(&st, 0, sizeof st);
    sos_init(&sos);
    fall_init(&fall);
    st.sensors_ok = max30102_init() & lis2dh12_init() & max17048_init();
    hal_led(LED_RED, false); hal_led(LED_GREEN, false);
    next_tx_ms = hal_millis() + CFG_TX_PERIOD_MS;
}

void app_tick(void)
{
    uint32_t now = hal_millis();

    /* sensores: no hardware real os dados chegam pela interrupção do MAX30102 (PB12) */
    uint32_t r[32], ir[32];
    uint8_t n = max30102_read_fifo(r, ir, 32);
    if (n) app_push_ppg(r, ir, n);
    float ax, ay, az;
    if (lis2dh12_read_g(&ax, &ay, &az)) app_push_accel(ax, ay, az);

    /* botão SOS */
    uint8_t act = sos_update(&sos, hal_sos_pressed(), now);
    apply(act);
    if (act & SOS_ACT_SEND) send_packet(PKT_TYPE_SOS);

    /* queda detectada: envia na hora */
    if (fall_pending) send_packet(PKT_TYPE_EVENT);

    handle_downlink();

    /* envio periódico */
    if ((int32_t)(now - next_tx_ms) >= 0) {
        next_tx_ms += CFG_TX_PERIOD_MS;
        send_packet(PKT_TYPE_PERIODIC);
    }

    hal_sleep_until(now + 10u);
}

const app_status_t *app_status(void) { return &st; }
