/**
 * fall.h — Detecção de queda com o acelerômetro.
 *
 * Padrão procurado: queda livre (|a| < 0,4 g por 80 ms) → impacto (> 2,5 g
 * em até 1 s) → imobilidade (|a| perto de 1 g por 2 s).
 */
#ifndef PULSO_FALL_H
#define PULSO_FALL_H

#include <stdint.h>
#include <stdbool.h>

typedef enum { FALL_NORMAL, FALL_FREEFALL, FALL_WAIT_IMPACT, FALL_WAIT_STILL } fall_state_t;

typedef struct {
    fall_state_t state;
    uint32_t     t_mark;
    uint32_t     still_ms;
} fall_t;

void fall_init(fall_t *f);
/** ax, ay, az em g. Retorna true no instante em que a queda é confirmada. */
bool fall_update(fall_t *f, float ax, float ay, float az, uint32_t now_ms, uint32_t dt_ms);

#endif
