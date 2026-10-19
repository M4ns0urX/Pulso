"""Simulação da rede LoRa subterrânea (gateways nas galerias, classe A)."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Callable

ALCANCE_GATEWAY_M = 70.0   # dentro de galerias o sinal cai rápido nas curvas
PERDA_BASE = 0.02          # 2 % de perda mesmo perto do gateway


class RedeLoRa:
    def __init__(self, mina, rng: random.Random):
        self.mina = mina
        self.rng = rng
        self.entregar: Callable[[bytes, str, float], None] = lambda raw, gw, rssi: None
        self.fila_downlink: dict[int, list[bytes]] = defaultdict(list)
        self.stats = {"enviados": 0, "perdidos": 0, "entregas": 0, "downlinks": 0}

    def enviar(self, raw: bytes, nivel_id: str, x: float, y: float) -> list[bytes]:
        """Uplink da braçadeira. Retorna os downlinks entregues na janela RX (classe A)."""
        self.stats["enviados"] += 1
        nivel = self.mina.niveis[nivel_id]
        recebeu = False
        for i, (gx, gy) in enumerate(nivel.gateways):
            d = math.dist((x, y), (gx, gy))
            if d > ALCANCE_GATEWAY_M:
                continue
            p_perda = PERDA_BASE + 0.5 * (d / ALCANCE_GATEWAY_M) ** 4
            if self.rng.random() < p_perda:
                continue
            rssi = -60 - 35 * math.log10(max(d, 1))
            self.entregar(raw, f"{nivel_id}-GW{i + 1}", round(rssi, 1))   # pode chegar por vários gateways
            self.stats["entregas"] += 1
            recebeu = True
        if not recebeu:
            self.stats["perdidos"] += 1
            return []
        dev = int.from_bytes(raw[1:3], "little")
        dl, self.fila_downlink[dev] = self.fila_downlink[dev], []
        self.stats["downlinks"] += len(dl)
        return dl

    def agendar_downlink(self, dev: int, dados: bytes) -> None:
        """Chamado pelo servidor (ex.: operador clicou 'Recebido')."""
        self.fila_downlink[dev].append(dados)
