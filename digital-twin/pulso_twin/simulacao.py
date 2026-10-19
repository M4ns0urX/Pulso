"""Digital twin da Pulso: mina, trabalhadores, braçadeiras e rede LoRa.

Roda em tempo real (ou acelerado) numa thread. A cada passo:
  trabalhadores andam e têm os sinais vitais atualizados →
  braçadeiras fazem o ranging UWB, montam o pacote e enviam pela rede LoRa →
  a rede entrega os pacotes ao servidor (callback) e devolve os downlinks.
"""
from __future__ import annotations

import random
import threading
import time

from .bracadeira import Bracadeira
from .rede import RedeLoRa
from .trabalhador import Trabalhador

# Roteiro da demonstração: (segundo, ação, id do trabalhador)
ROTEIRO_PADRAO = [
    (40,  "gas",       324),   # bolsão de gás: SpO2 do Marcos cai
    (75,  "sos",       321),   # Carlos aperta o SOS na S-2
    (130, "queda",     330),   # Diego cai na N-2
    (170, "sem_sinal", 332),   # braçadeira do Sérgio para de transmitir
    (200, "normalizar", 324),  # Marcos sai da área com gás
]


class Simulacao:
    PASSO_S = 0.25

    def __init__(self, mina, velocidade: float = 1.0, semente: int = 7, roteiro=None):
        self.mina = mina
        self.velocidade = velocidade
        self.rng = random.Random(semente)
        self.inicio_real = time.time()
        self.t = 0.0                              # segundos simulados desde o início
        self.rede = RedeLoRa(mina, self.rng)
        self.roteiro = sorted(ROTEIRO_PADRAO if roteiro is None else roteiro)
        self.trabalhadores: dict[int, Trabalhador] = {}
        self.bracadeiras: dict[int, Bracadeira] = {}
        for cfg in mina.trabalhadores:
            tr = Trabalhador(cfg, mina.niveis[cfg["nivel"]], self.rng)
            self.trabalhadores[tr.id] = tr
            bat = 14.0 if cfg["nome"].startswith("Rita") else None   # Rita começa com bateria fraca
            self.bracadeiras[tr.id] = Bracadeira(tr, self.rede, self.rng, bat)
        self._lock = threading.Lock()
        self._rodando = False

    # ------------------------------------------------------------------ relógio
    def agora(self) -> float:
        """Horário simulado (Unix). O servidor usa o mesmo relógio."""
        return self.inicio_real + self.t

    # ------------------------------------------------------------------ ações
    def acao(self, nome: str, dev: int) -> bool:
        with self._lock:
            tr, br = self.trabalhadores.get(dev), self.bracadeiras.get(dev)
            if not tr:
                return False
            if nome == "sos":
                tr.segurando_sos = 2.6                # segura o botão por 2,6 s
                tr.estresse = 1.0
                tr.aguardando_resgate = True          # fica no local esperando a equipe
            elif nome == "gas":
                tr.gas = True
            elif nome == "queda":
                tr.caido = True
                br.queda_pendente = True
            elif nome == "sem_sinal":
                br.ligada = False
            elif nome == "normalizar":
                tr.gas = tr.caido = tr.aguardando_resgate = False
                tr.estresse = 0.0
                if not br.ligada:
                    br.ligada = True
                    br.proximo_envio = self.agora()
            else:
                return False
            return True

    # ------------------------------------------------------------------ passo
    def passo(self, dt: float) -> None:
        with self._lock:
            self.t += dt
            while self.roteiro and self.roteiro[0][0] <= self.t:
                _, nome, dev = self.roteiro.pop(0)
                self._lock.release()
                try:
                    self.acao(nome, dev)
                finally:
                    self._lock.acquire()
            agora = self.agora()
            for tr in self.trabalhadores.values():
                tr.mover(dt)
                tr.atualizar_vitais(dt)
            for br in self.bracadeiras.values():
                br.passo(agora, dt)

    def rodar(self, segundos: float) -> None:
        """Avança a simulação o mais rápido possível (usado nos testes)."""
        n = int(segundos / self.PASSO_S)
        for _ in range(n):
            self.passo(self.PASSO_S)

    def iniciar(self) -> threading.Thread:
        """Roda em tempo real (multiplicado pela velocidade) numa thread."""
        self._rodando = True

        def loop():
            prox = time.time()
            while self._rodando:
                self.passo(self.PASSO_S)
                prox += self.PASSO_S / self.velocidade
                time.sleep(max(0.0, prox - time.time()))

        th = threading.Thread(target=loop, daemon=True, name="digital-twin")
        th.start()
        return th

    def parar(self) -> None:
        self._rodando = False

    def resumo(self) -> dict:
        return {
            "tempo_simulado_s": round(self.t),
            "rede": dict(self.rede.stats),
            "bracadeiras": {d: {"led": b.led, "sos": b.sos_estado, "ligada": b.ligada,
                                "bateria": round(b.bateria, 1)} for d, b in self.bracadeiras.items()},
        }
