/**
 * hal_host.c — HAL simulada para rodar o firmware no PC.
 *
 * Simula: relógio, sensor óptico (BPM 72 / SpO2 97 %), acelerômetro,
 * bateria, âncoras UWB e a rede LoRa. Um roteiro aperta o botão SOS
 * aos 12 s e o operador confirma ("Recebido") aos 20 s.
 *
 * Saída: cada pacote enviado é impresso em hexadecimal + decodificado.
 * Use --hex para imprimir só o hexadecimal (um por linha), formato aceito
 * pelo servidor:  ./build/pulso_sim --hex | python3 -m pulso_server.ingest_stdin
 */
#include "hal.h"
#include "packet.h"
#include "pulso_config.h"
#include "max30102.h"
#include "lis2dh12.h"
#include "max17048.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

static uint32_t now_ms;
static uint32_t ppg_sample_idx;      /* próxima amostra a entregar */
static bool     hex_only;
static int      pending_ack;         /* 0 nada, 1 ack, 2 close */

void hal_host_set_hex_only(bool v) { hex_only = v; }
void hal_host_queue_downlink(int cmd) { pending_ack = cmd; }

uint32_t hal_millis(void)      { return now_ms; }
uint32_t hal_unix_time(void)   { return 1760000000u + now_ms / 1000u; }
void     hal_sleep_until(uint32_t t) { if (t > now_ms) now_ms = t; }
uint16_t hal_device_id(void)   { return 0x0142; }

bool hal_sos_pressed(void)     { return now_ms >= 12000 && now_ms < 14500; }  /* roteiro */
bool hal_is_charging(void)     { return false; }
void hal_led(hal_led_t led, bool on)
{
    if (!hex_only && on) printf("[%6.2f s] LED %s aceso\n", now_ms / 1000.0, led == LED_RED ? "VERMELHO" : "VERDE");
}
void hal_vibrate(uint16_t ms)
{
    if (!hex_only) printf("[%6.2f s] vibração %u ms\n", now_ms / 1000.0, ms);
}

/* ---------- sinal PPG sintético (forma de onda cardíaca simplificada) ---------- */
static void ppg_sample(uint32_t i, uint32_t *red, uint32_t *ir)
{
    const double bpm = 72.0, spo2 = 97.0;
    const double R = (110.0 - spo2) / 25.0;
    double t = i / (double)CFG_PPG_SAMPLE_HZ;
    double ph = fmod(t * bpm / 60.0, 1.0);
    double wave = exp(-pow((ph - 0.15) / 0.06, 2)) + 0.35 * exp(-pow((ph - 0.45) / 0.08, 2));
    double ir_dc = 120000.0, red_dc = 90000.0, ir_ac = 1500.0;
    double red_ac = ir_ac * R * red_dc / ir_dc;
    *ir  = (uint32_t)(ir_dc + ir_ac * wave + (rand() % 41 - 20));
    *red = (uint32_t)(red_dc + red_ac * wave + (rand() % 21 - 10));
}

/* ---------- I²C simulado ---------- */
bool hal_i2c_write(uint8_t addr, uint8_t reg, const uint8_t *buf, size_t len)
{ (void)addr; (void)reg; (void)buf; (void)len; return true; }

bool hal_i2c_read(uint8_t addr, uint8_t reg, uint8_t *buf, size_t len)
{
    memset(buf, 0, len);
    if (addr == MAX30102_ADDR) {
        uint32_t due = now_ms * CFG_PPG_SAMPLE_HZ / 1000u;
        if (reg == MAX30102_REG_PART_ID) buf[0] = 0x15;
        else if (reg == MAX30102_REG_FIFO_WR) buf[0] = (uint8_t)((due - ppg_sample_idx) > 31 ? 31 : (due - ppg_sample_idx));
        else if (reg == MAX30102_REG_FIFO_RD) buf[0] = 0;
        else if (reg == MAX30102_REG_FIFO_DATA && len == 6) {
            uint32_t r, ir; ppg_sample(ppg_sample_idx++, &r, &ir);
            buf[0] = (uint8_t)(r >> 16); buf[1] = (uint8_t)(r >> 8); buf[2] = (uint8_t)r;
            buf[3] = (uint8_t)(ir >> 16); buf[4] = (uint8_t)(ir >> 8); buf[5] = (uint8_t)ir;
        }
        return true;
    }
    if (addr == LIS2DH12_ADDR) {
        if (reg == LIS2DH12_WHO_AM_I) buf[0] = 0x33;
        else if (len == 6) { int16_t z = (int16_t)(250 << 4); buf[4] = (uint8_t)z; buf[5] = (uint8_t)(z >> 8); } /* 1 g em Z */
        return true;
    }
    if (addr == MAX17048_ADDR) {
        if (reg == MAX17048_SOC) buf[0] = (uint8_t)(87 - now_ms / 600000u);
        if (reg == MAX17048_VCELL) { buf[0] = 0xCC; buf[1] = 0x00; }
        return true;
    }
    return false;
}

/* ---------- UWB simulado: trabalhador andando na galeria ---------- */
uint8_t hal_uwb_ranging(uwb_anchor_t *a, float *d, uint8_t max)
{
    /* âncoras em zigue-zague no teto da galeria (Galeria Principal, nível −300 m, teto a −297 m) */
    static const uwb_anchor_t A[] = {
        {11, { 40.0f, 58.0f, -297.0f}}, {12, { 60.0f, 62.0f, -297.0f}},
        {13, { 80.0f, 58.0f, -297.0f}}, {14, {100.0f, 62.0f, -297.0f}},
        {15, {120.0f, 58.0f, -297.0f}},
    };
    /* anda a 0,8 m/s pela Galeria Principal (y = 60 m) do mapa de exemplo */
    float tx = 45.0f + 0.8f * (now_ms / 1000.0f);
    if (tx > 115.0f) tx = 115.0f;
    float ty = 60.5f, tz = -300.0f + CFG_UWB_TAG_HEIGHT_M;
    uint8_t n = 0;
    for (unsigned i = 0; i < sizeof A / sizeof A[0] && n < max; i++) {
        float dx = A[i].pos.x - tx, dy = A[i].pos.y - ty, dz = A[i].pos.z - tz;
        float dist = sqrtf(dx * dx + dy * dy + dz * dz);
        if (dist > 45.0f) continue;                           /* fora do alcance */
        a[n] = A[i];
        d[n] = dist + ((rand() % 201) - 100) / 1000.0f;       /* ruído ±10 cm */
        n++;
    }
    return n;
}

/* ---------- LoRa simulado ---------- */
bool hal_lora_send(uint8_t port, const uint8_t *buf, size_t len, bool confirmed)
{
    (void)port;
    if (hex_only) {
        for (size_t i = 0; i < len; i++) printf("%02x", buf[i]);
        printf("\n");
        fflush(stdout);
        return true;
    }
    pulso_packet_t p;
    pkt_decode(buf, &p);
    printf("[%6.2f s] LoRa %s  ", now_ms / 1000.0, confirmed ? "(confirmado)" : "            ");
    for (size_t i = 0; i < len; i++) printf("%02x", buf[i]);
    printf("\n           tipo=%u id=0x%04X BPM=%u SpO2=%u%% pos=(%.1f, %.1f, %.1f) m bat=%u%% flags=0x%02X seq=%u\n",
           p.type, p.device_id, p.bpm, p.spo2, p.x_dm / 10.0, p.y_dm / 10.0, p.z_dm / 10.0, p.battery, p.flags, p.seq);
    /* roteiro: o operador confirma o SOS aos 20 s */
    if ((p.flags & PKT_FLAG_SOS) && now_ms >= 20000 && !(p.flags & PKT_FLAG_SOS_ACKED)) pending_ack = 1;
    return true;
}

size_t hal_lora_poll_downlink(uint8_t *buf, size_t max)
{
    if (!pending_ack || max < 1) return 0;
    buf[0] = (uint8_t)(pending_ack == 1 ? CFG_DL_CMD_SOS_ACK : CFG_DL_CMD_SOS_CLOSE);
    if (!hex_only) printf("[%6.2f s] downlink recebido: %s\n", now_ms / 1000.0,
                          pending_ack == 1 ? "SOS RECEBIDO pelo operador" : "caso encerrado");
    pending_ack = 0;
    return 1;
}
