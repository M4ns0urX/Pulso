/**
 * ppg.h — Cálculo de BPM e SpO2 a partir das amostras do MAX30102.
 *
 * BPM: detecção de picos no canal infravermelho (IR).
 * SpO2: método "ratio of ratios":  R = (AC_red/DC_red) / (AC_ir/DC_ir)
 *       SpO2 ≈ 110 − 25·R   (curva empírica; calibrar com oxímetro de referência)
 */
#ifndef PULSO_PPG_H
#define PULSO_PPG_H

#include <stdint.h>
#include <stdbool.h>

#define PPG_MIN_DC_CONTACT  50000u   /* abaixo disso o sensor está sem contato */

typedef struct {
    bool    valid;
    bool    no_contact;
    uint8_t bpm;
    uint8_t spo2;
    float   ratio_r;
} ppg_result_t;

/** red/ir: n amostras na taxa fs_hz (ex.: 400 amostras a 100 Hz = 4 s). */
ppg_result_t ppg_compute(const uint32_t *red, const uint32_t *ir, uint16_t n, uint16_t fs_hz);

#endif
