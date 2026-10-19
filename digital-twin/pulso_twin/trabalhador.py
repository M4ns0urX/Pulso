"""Trabalhador virtual: anda pelas galerias e tem sinais vitais realistas."""
from __future__ import annotations

import math
import random


class Trabalhador:
    def __init__(self, cfg: dict, nivel, rng: random.Random):
        self.id = cfg["id"]
        self.nome = cfg["nome"]
        self.nivel = nivel
        self.rng = rng
        # começa num ponto aleatório de uma galeria da zona inicial
        gals = [g for g in nivel.galerias if g.zona == cfg.get("zona_inicial")] or nivel.galerias
        self.galeria = rng.choice(gals)
        self.t = rng.random()
        self.sentido = rng.choice((-1, 1))
        self.velocidade = rng.uniform(0.6, 1.1)          # m/s
        self.parado_ate = 0.0
        # fisiologia
        self.bpm_base = rng.uniform(64, 82)
        self.spo2_base = rng.uniform(96.5, 98.5)
        self.bpm = self.bpm_base
        self.spo2 = self.spo2_base
        # eventos
        self.gas = False            # bolsão de gás / baixa oxigenação
        self.estresse = 0.0         # 0 a 1
        self.caido = False
        self.segurando_sos = 0.0    # segundos restantes segurando o botão
        self.aguardando_resgate = False

    @property
    def xy(self) -> tuple[float, float]:
        return self.galeria.ponto(self.t)

    @property
    def andando(self) -> bool:
        return not self.caido and self.parado_ate <= 0

    # ---------------- movimento ----------------
    def _proxima_galeria(self, ponta):
        vizinhas = [g for g in self.nivel.galerias if g is not self.galeria and
                    (math.dist(g.a, ponta) < 1 or math.dist(g.b, ponta) < 1 or g.projetar(ponta)[0] < 1)]
        if not vizinhas:
            self.sentido *= -1
            return
        g = self.rng.choice(vizinhas)
        _, _, t = g.projetar(ponta)
        self.galeria, self.t = g, t
        self.sentido = 1 if t < 0.5 else -1

    def mover(self, dt: float) -> None:
        if self.caido or self.aguardando_resgate or self.segurando_sos > 0:
            return
        if self.parado_ate > 0:
            self.parado_ate -= dt
            return
        L = self.galeria.comprimento or 1
        self.t += self.sentido * self.velocidade * dt / L
        if self.t >= 1 or self.t <= 0:
            ponta = self.galeria.b if self.t >= 1 else self.galeria.a
            self.t = min(max(self.t, 0), 1)
            self._proxima_galeria(ponta)
        if self.rng.random() < dt / 40:                  # para para trabalhar de vez em quando
            self.parado_ate = self.rng.uniform(15, 70)

    # ---------------- fisiologia ----------------
    def atualizar_vitais(self, dt: float) -> None:
        atividade = 1.0 if self.andando else 0.2
        alvo_bpm = self.bpm_base + 18 * atividade + 70 * self.estresse
        alvo_spo2 = self.spo2_base
        if self.gas:
            alvo_spo2 = 83.0
            alvo_bpm += 25
        if self.caido:
            alvo_bpm = self.bpm_base + 35
        k_bpm = 1 - math.exp(-dt / 15)
        k_spo2 = 1 - math.exp(-dt / (25 if self.gas else 40))
        self.bpm += (alvo_bpm - self.bpm) * k_bpm + self.rng.gauss(0, 0.6)
        self.spo2 += (alvo_spo2 - self.spo2) * k_spo2 + self.rng.gauss(0, 0.08)
        self.spo2 = min(self.spo2, 100.0)
        self.estresse = max(0.0, self.estresse - dt / 400)
        if self.segurando_sos > 0:
            self.segurando_sos -= dt
