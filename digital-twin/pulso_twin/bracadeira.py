"""Braçadeira virtual: reproduz o comportamento do firmware (firmware/src/app.c)."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "servidor"))
from pulso_server.packet import (DL_SOS_ACK, DL_SOS_CLOSE, FLAG_FALL,  # noqa: E402
                                 FLAG_LOW_BATT, FLAG_SOS, FLAG_SOS_ACKED, TYPE_EVENT,
                                 TYPE_PERIODIC, TYPE_SOS, Packet)

from . import uwb  # noqa: E402

PERIODO_S = 5.0
SOS_SEGURAR_S = 2.0
SOS_REENVIO_S = 3.0


class Bracadeira:
    def __init__(self, trabalhador, rede, rng: random.Random, bateria: float | None = None):
        self.trab = trabalhador
        self.rede = rede
        self.rng = rng
        self.id = trabalhador.id
        self.bateria = bateria if bateria is not None else rng.uniform(55, 98)
        self.proximo_envio = rng.uniform(0, PERIODO_S)     # desencontra os envios
        self.seq = 0
        self.ligada = True
        self.pos_estimada: tuple[float, float] | None = None
        # SOS (mesma máquina de estados de firmware/src/sos.c)
        self.sos_estado = "ocioso"        # ocioso, pressionando, enviado, confirmado
        self.sos_t = 0.0
        self.queda_pendente = False
        self.led = None                   # None, "vermelho", "verde"

    # -------------------------------------------------------------- ciclo
    def passo(self, agora: float, dt: float) -> None:
        if not self.ligada:
            return
        if self.proximo_envio < 1e9:                 # primeiro passo: converte para horário absoluto
            self.proximo_envio += agora
        self.bateria = max(0.0, self.bateria - dt * 0.0006)     # ~2 %/h
        # botão SOS
        pressionado = self.trab.segurando_sos > 0
        if self.sos_estado == "ocioso" and pressionado:
            self.sos_estado, self.sos_t = "pressionando", agora
        elif self.sos_estado == "pressionando":
            if not pressionado:
                self.sos_estado = "ocioso"
            elif agora - self.sos_t >= SOS_SEGURAR_S:
                self.sos_estado, self.sos_t, self.led = "enviado", agora, "vermelho"
                self.enviar(agora, TYPE_SOS)
        elif self.sos_estado == "enviado" and agora - self.sos_t >= SOS_REENVIO_S:
            self.sos_t = agora
            self.enviar(agora, TYPE_SOS)
        if self.queda_pendente:
            self.enviar(agora, TYPE_EVENT)
            self.queda_pendente = False
        if agora >= self.proximo_envio:
            self.proximo_envio += PERIODO_S
            self.enviar(agora, TYPE_PERIODIC)

    # -------------------------------------------------------------- envio
    def _localizar(self) -> tuple[float, float]:
        x, y = self.trab.xy
        nivel = self.trab.nivel
        med = uwb.medir(nivel.ancoras, x, y, nivel.z, self.rng)
        sol = uwb.resolver(med, nivel.z, self.pos_estimada)
        if sol and sol[2] < 1.0:
            self.pos_estimada = (sol[0], sol[1])
        return self.pos_estimada or (x, y)

    def enviar(self, agora: float, tipo: int) -> None:
        x, y = self._localizar()
        flags = 0
        if self.sos_estado in ("enviado", "confirmado"):
            flags |= FLAG_SOS
        if self.sos_estado == "confirmado":
            flags |= FLAG_SOS_ACKED
        if tipo == TYPE_EVENT:
            flags |= FLAG_FALL
        if self.bateria < 15:
            flags |= FLAG_LOW_BATT
        p = Packet(tipo, self.id, int(agora), self.trab.bpm + self.rng.gauss(0, 1.2),
                   self.trab.spo2 + self.rng.gauss(0, 0.4), x, y,
                   self.trab.nivel.z + uwb.ALTURA_TAG_M, self.bateria, flags, self.seq)
        self.seq = (self.seq + 1) & 0xFF
        for dl in self.rede.enviar(p.encode(), self.trab.nivel.id, *self.trab.xy):
            self.receber_downlink(dl)

    def receber_downlink(self, dl: bytes) -> None:
        if dl[:1] == bytes([DL_SOS_ACK]) and self.sos_estado == "enviado":
            self.sos_estado, self.led = "confirmado", "verde"
        elif dl[:1] == bytes([DL_SOS_CLOSE]):
            self.sos_estado, self.led = "ocioso", None
