#include "ppg.h"
#include <math.h>

#define PPG_MAX_N 512u

static float mean_u32(const uint32_t *v, uint16_t n)
{
    double s = 0;
    for (uint16_t i = 0; i < n; i++) s += v[i];
    return (float)(s / n);
}

/* RMS do componente AC (sinal menos a média) */
static float ac_rms(const uint32_t *v, uint16_t n, float dc)
{
    double s = 0;
    for (uint16_t i = 0; i < n; i++) { double d = (double)v[i] - dc; s += d * d; }
    return (float)sqrt(s / n);
}

ppg_result_t ppg_compute(const uint32_t *red, const uint32_t *ir, uint16_t n, uint16_t fs_hz)
{
    ppg_result_t r = { false, false, 0, 0, 0.0f };
    if (n < fs_hz * 2u || n > PPG_MAX_N) return r;

    float dc_ir = mean_u32(ir, n), dc_red = mean_u32(red, n);
    if (dc_ir < PPG_MIN_DC_CONTACT) { r.no_contact = true; return r; }

    /* --- BPM: suaviza o IR (média móvel de 4) e procura picos --- */
    static float s[PPG_MAX_N];
    float maxv = -1e30f;
    for (uint16_t i = 0; i < n; i++) {
        float acc = 0; uint16_t k = 0;
        for (int j = (int)i - 3; j <= (int)i; j++) if (j >= 0) { acc += (float)ir[j] - dc_ir; k++; }
        s[i] = acc / (float)k;
        if (s[i] > maxv) maxv = s[i];
    }
    float thr = 0.3f * maxv;
    uint16_t min_dist = (uint16_t)(fs_hz * 0.3f);          /* no máximo 200 BPM */
    int last_peak = -1, n_int = 0; long sum_int = 0;
    for (uint16_t i = 1; i + 1 < n; i++) {
        if (s[i] > thr && s[i] >= s[i - 1] && s[i] > s[i + 1]) {
            if (last_peak < 0 || (i - last_peak) >= min_dist) {
                if (last_peak >= 0) { sum_int += i - last_peak; n_int++; }
                last_peak = i;
            }
        }
    }
    if (n_int < 2) return r;
    float bpm = 60.0f * (float)fs_hz * (float)n_int / (float)sum_int;

    /* --- SpO2: ratio of ratios --- */
    float rr = (ac_rms(red, n, dc_red) / dc_red) / (ac_rms(ir, n, dc_ir) / dc_ir);
    float spo2 = 110.0f - 25.0f * rr;
    if (spo2 > 100.0f) spo2 = 100.0f;
    if (spo2 < 0.0f) spo2 = 0.0f;

    r.valid = (bpm >= 30.0f && bpm <= 220.0f);
    r.bpm = (uint8_t)(bpm + 0.5f);
    r.spo2 = (uint8_t)(spo2 + 0.5f);
    r.ratio_r = rr;
    return r;
}
