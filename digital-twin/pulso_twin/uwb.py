"""Simulação do UWB: ranging com ruído e trilateração (espelho de firmware/src/uwb_pos.c)."""
from __future__ import annotations

import math
import random

ALCANCE_M = 45.0          # alcance útil do UWB numa galeria
RUIDO_M = 0.05            # desvio padrão da medida de distância
ALTURA_TAG_M = 1.2
ALTURA_TETO_M = 3.0


def medir(ancoras, x: float, y: float, z_piso: float, rng: random.Random):
    """Distâncias medidas da braçadeira até as âncoras ao alcance (até 6)."""
    tz = z_piso + ALTURA_TAG_M
    med = []
    for a in ancoras:
        d = math.sqrt((a.x - x) ** 2 + (a.y - y) ** 2 + (a.z - tz) ** 2)
        if d <= ALCANCE_M:
            med.append((a, d + rng.gauss(0, RUIDO_M)))
    med.sort(key=lambda m: m[1])
    return med[:6]


def resolver(medidas, z_piso: float, inicial: tuple[float, float] | None):
    """Gauss-Newton 2D com amortecimento. Retorna (x, y, rms) ou None."""
    if len(medidas) < 2:
        return None
    tz = z_piso + ALTURA_TAG_M
    if inicial:
        x, y = inicial
    else:
        x = sum(a.x for a, _ in medidas) / len(medidas)
        y = sum(a.y for a, _ in medidas) / len(medidas) + 0.5
    rms = 0.0
    for _ in range(15):
        a11 = a12 = a22 = b1 = b2 = sse = 0.0
        for a, d in medidas:
            dz = a.z - tz
            dh = math.sqrt(max(d * d - dz * dz, 0.0))
            ex, ey = x - a.x, y - a.y
            est = max(math.hypot(ex, ey), 1e-3)
            r = est - dh
            jx, jy = ex / est, ey / est
            a11 += jx * jx; a12 += jx * jy; a22 += jy * jy
            b1 += jx * r; b2 += jy * r; sse += r * r
        rms = math.sqrt(sse / len(medidas))
        a11 += 1e-3; a22 += 1e-3
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-9:
            return None
        dx = (a22 * b1 - a12 * b2) / det
        dy = (-a12 * b1 + a11 * b2) / det
        x -= dx; y -= dy
        if abs(dx) < 1e-4 and abs(dy) < 1e-4:
            break
    return x, y, rms
