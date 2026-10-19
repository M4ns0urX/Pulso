/** test_main.c — Testes unitários do firmware (rodam no PC: `make test`). */
#include "packet.h"
#include "sos.h"
#include "ppg.h"
#include "uwb_pos.h"
#include "fall.h"
#include "pulso_config.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

static int fails, total;
#define CHECK(cond, msg) do { total++; if (!(cond)) { fails++; printf("  FALHOU: %s (linha %d)\n", msg, __LINE__); } } while (0)

/* Vetor de referência compartilhado com o Python (digital-twin/tests) */
static const char *VECTOR_HEX = "1142010078e768805fd204c8ff48f447010728e2";

static void test_packet(void)
{
    printf("[pacote]\n");
    pulso_packet_t p = { PKT_TYPE_SOS, 0x0142, 1760000000u, 128, 95, 1234, -56, -3000, 71, PKT_FLAG_SOS, 7 };
    uint8_t b[PKT_SIZE]; char hex[41];
    pkt_encode(&p, b);
    for (int i = 0; i < 20; i++) sprintf(&hex[i * 2], "%02x", b[i]);
    CHECK(strcmp(hex, VECTOR_HEX) == 0, "codificação igual ao vetor de referência");

    pulso_packet_t q;
    CHECK(pkt_decode(b, &q), "decodifica pacote válido");
    CHECK(q.device_id == 0x0142 && q.bpm == 128 && q.spo2 == 95 && q.y_dm == -56 && q.z_dm == -3000, "campos preservados");
    b[7] ^= 0x01;
    CHECK(!pkt_decode(b, &q), "rejeita pacote corrompido (CRC)");
}

static void test_sos(void)
{
    printf("[botão SOS]\n");
    sos_t s; sos_init(&s);
    uint8_t a;
    sos_update(&s, true, 0);
    a = sos_update(&s, false, 800);
    CHECK(a == 0 && s.state == SOS_IDLE, "toque curto não aciona");

    sos_update(&s, true, 1000);
    a = sos_update(&s, true, 2500);
    CHECK(a == 0, "ainda não completou 2 s");
    a = sos_update(&s, true, 3000);
    CHECK((a & SOS_ACT_SEND) && (a & SOS_ACT_LED_RED) && s.state == SOS_SENT, "aciona após 2 s");
    a = sos_update(&s, false, 5000);
    CHECK(a == 0, "não reenvia antes de 3 s");
    a = sos_update(&s, false, 6000);
    CHECK(a & SOS_ACT_SEND, "reenvia após 3 s sem confirmação");
    a = sos_on_ack(&s);
    CHECK((a & SOS_ACT_LED_GREEN) && s.state == SOS_ACKED, "ACK acende LED verde");
    a = sos_update(&s, false, 20000);
    CHECK(a == 0, "não reenvia depois do ACK");
    a = sos_on_close(&s);
    CHECK((a & SOS_ACT_LEDS_OFF) && s.state == SOS_IDLE, "operador encerra o caso");
}

static void make_ppg(uint32_t *red, uint32_t *ir, int n, double bpm, double spo2, double dc_ir)
{
    double R = (110.0 - spo2) / 25.0, dc_red = 90000.0, ac_ir = 1500.0;
    for (int i = 0; i < n; i++) {
        double ph = fmod(i / 100.0 * bpm / 60.0, 1.0);
        double w = exp(-pow((ph - 0.15) / 0.06, 2)) + 0.35 * exp(-pow((ph - 0.45) / 0.08, 2));
        ir[i]  = (uint32_t)(dc_ir + ac_ir * w);
        red[i] = (uint32_t)(dc_red + ac_ir * R * dc_red / dc_ir * w);
    }
}

static void test_ppg(void)
{
    printf("[BPM e SpO2]\n");
    static uint32_t red[400], ir[400];
    make_ppg(red, ir, 400, 72, 97, 120000);
    ppg_result_t r = ppg_compute(red, ir, 400, 100);
    CHECK(r.valid, "medição válida");
    CHECK(abs((int)r.bpm - 72) <= 3, "BPM ≈ 72");
    CHECK(abs((int)r.spo2 - 97) <= 1, "SpO2 ≈ 97 %");

    make_ppg(red, ir, 400, 130, 86, 120000);
    r = ppg_compute(red, ir, 400, 100);
    CHECK(abs((int)r.bpm - 130) <= 4 && abs((int)r.spo2 - 86) <= 1, "BPM ≈ 130 e SpO2 ≈ 86 % (hipóxia)");
    printf("    medido: %u BPM, %u %%\n", r.bpm, r.spo2);

    make_ppg(red, ir, 400, 72, 97, 3000);
    r = ppg_compute(red, ir, 400, 100);
    CHECK(!r.valid && r.no_contact, "detecta sensor sem contato com a pele");
}

static void test_uwb(void)
{
    printf("[localização UWB]\n");
    uwb_anchor_t a[] = { {1, {0, -2, 3}}, {2, {20, 2, 3}}, {3, {40, -2, 3}}, {4, {60, 2, 3}} };
    const float tx = 27.3f, ty = 0.8f, tz = 1.2f;
    float d[4];
    srand(7);
    for (int i = 0; i < 4; i++) {
        float dx = a[i].pos.x - tx, dy = a[i].pos.y - ty, dz = a[i].pos.z - tz;
        d[i] = sqrtf(dx * dx + dy * dy + dz * dz) + ((rand() % 101) - 50) / 1000.0f;  /* ruído ±5 cm */
    }
    vec3_t p = { 25.0f, 0.0f, 0.0f };
    float rms;
    bool ok = uwb_solve(a, d, 4, tz, &p, &rms);
    float err = sqrtf((p.x - tx) * (p.x - tx) + (p.y - ty) * (p.y - ty));
    printf("    posição (%.2f, %.2f), erro %.1f cm\n", p.x, p.y, err * 100);
    CHECK(ok, "converge");
    CHECK(err < 0.15f, "erro menor que 15 cm");
}

static void test_fall(void)
{
    printf("[detecção de queda]\n");
    fall_t f; fall_init(&f);
    uint32_t t = 0; bool det = false;
    for (int i = 0; i < 50; i++, t += 20) det |= fall_update(&f, 0, 0, 1.0f, t, 20);   /* parado     */
    for (int i = 0; i < 8;  i++, t += 20) det |= fall_update(&f, 0, 0, 0.1f, t, 20);   /* queda livre */
    det |= fall_update(&f, 1.5f, 2.0f, 2.0f, t, 20); t += 20;                          /* impacto 3,2 g */
    for (int i = 0; i < 120; i++, t += 20) det |= fall_update(&f, 0, 1.0f, 0.05f, t, 20); /* imóvel no chão */
    CHECK(det, "queda detectada");

    fall_init(&f); det = false; t = 0;
    for (int i = 0; i < 200; i++, t += 20) {                                           /* caminhada  */
        float z = 1.0f + 0.3f * sinf(i * 0.6f);
        det |= fall_update(&f, 0.1f, 0, z, t, 20);
    }
    CHECK(!det, "caminhada não gera falso alarme");
}

int main(void)
{
    printf("Testes do firmware Pulso\n========================\n");
    test_packet(); test_sos(); test_ppg(); test_uwb(); test_fall();
    printf("------------------------\n%d/%d testes passaram\n", total - fails, total);
    return fails ? 1 : 0;
}
