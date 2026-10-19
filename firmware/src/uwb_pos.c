#include "uwb_pos.h"
#include <math.h>

bool uwb_solve(const uwb_anchor_t *a, const float *d, uint8_t n,
               float tag_z, vec3_t *io, float *out_rms)
{
    if (n < 2) return false;
    float x = io->x, y = io->y;

    /* chute inicial: se não houver posição anterior, usa o centro das âncoras */
    if (x == 0.0f && y == 0.0f) {
        for (uint8_t i = 0; i < n; i++) { x += a[i].pos.x; y += a[i].pos.y; }
        x /= n; y /= n; y += 0.5f;   /* desloca um pouco para fugir da linha das âncoras */
    }

    float rms = 0;
    for (int it = 0; it < 15; it++) {
        /* monta J^T J e J^T r (2x2) */
        float a11 = 0, a12 = 0, a22 = 0, b1 = 0, b2 = 0, sse = 0;
        for (uint8_t i = 0; i < n; i++) {
            float dz = a[i].pos.z - tag_z;
            float h2 = d[i] * d[i] - dz * dz;
            float dh = h2 > 0 ? sqrtf(h2) : 0.0f;          /* distância horizontal medida */
            float ex = x - a[i].pos.x, ey = y - a[i].pos.y;
            float est = sqrtf(ex * ex + ey * ey);
            if (est < 1e-3f) est = 1e-3f;
            float res = est - dh;
            float jx = ex / est, jy = ey / est;
            a11 += jx * jx; a12 += jx * jy; a22 += jy * jy;
            b1 += jx * res; b2 += jy * res;
            sse += res * res;
        }
        rms = sqrtf(sse / n);
        /* amortecimento (Levenberg) para o caso de âncoras quase alinhadas */
        a11 += 1e-3f; a22 += 1e-3f;
        float det = a11 * a22 - a12 * a12;
        if (fabsf(det) < 1e-9f) return false;
        float dx = ( a22 * b1 - a12 * b2) / det;
        float dy = (-a12 * b1 + a11 * b2) / det;
        x -= dx; y -= dy;
        if (fabsf(dx) < 1e-4f && fabsf(dy) < 1e-4f) break;
    }
    io->x = x; io->y = y; io->z = tag_z;
    if (out_rms) *out_rms = rms;
    return rms < 1.0f;
}
