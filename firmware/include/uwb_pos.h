/**
 * uwb_pos.h — Cálculo da posição a partir das distâncias UWB (trilateração).
 *
 * As âncoras ficam no teto das galerias, alternadas entre as paredes
 * (zigue-zague) para evitar que fiquem todas alinhadas.
 * Resolve em 2D por mínimos quadrados (Gauss-Newton), usando a altura
 * conhecida da braçadeira para converter distância 3D em distância horizontal.
 */
#ifndef PULSO_UWB_POS_H
#define PULSO_UWB_POS_H

#include <stdint.h>
#include <stdbool.h>

typedef struct { float x, y, z; } vec3_t;
typedef struct { uint16_t id; vec3_t pos; } uwb_anchor_t;

/**
 * anchors/dist: n âncoras e as distâncias medidas (m).
 * io_pos: entra com a estimativa anterior, sai com a nova posição.
 * Retorna false se houver menos de 2 âncoras ou se não convergir.
 */
bool uwb_solve(const uwb_anchor_t *anchors, const float *dist, uint8_t n,
               float tag_z, vec3_t *io_pos, float *out_rms_m);

#endif
