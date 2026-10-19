"""Regras de alerta da Pulso (valores iniciais, a calibrar no piloto)."""
from __future__ import annotations

from dataclasses import dataclass, field

SPO2_CRITICO = 90          # %
HISTERESE_SPO2 = 3         # só normaliza com SpO2 >= 93 %
BPM_BAIXO = 40
BPM_ALTO = 150
BPM_DURACAO_S = 30         # BPM fora da faixa por 30 s
SEM_SINAL_S = 30           # 6 pacotes perdidos
BATERIA_BAIXA = 15         # %
ESCALONAR_SUPERVISOR_S = 30
ESCALONAR_BRIGADA_S = 120

NIVEL = {
    "SOS": "critico", "SPO2_BAIXO": "critico", "QUEDA": "critico",
    "BPM_ALTO": "alto", "BPM_BAIXO": "alto", "SEM_SINAL": "alto",
    "BATERIA_BAIXA": "aviso", "SEM_CONTATO": "aviso",
}
TITULO = {
    "SOS": "SOS acionado", "SPO2_BAIXO": "Oxigenação baixa", "QUEDA": "Queda detectada",
    "BPM_ALTO": "Frequência cardíaca alta", "BPM_BAIXO": "Frequência cardíaca baixa",
    "SEM_SINAL": "Sem sinal", "BATERIA_BAIXA": "Bateria fraca", "SEM_CONTATO": "Sensor sem contato",
}
# Alertas que só o operador pode encerrar (os outros se normalizam sozinhos)
SO_OPERADOR = {"SOS", "QUEDA"}


@dataclass
class Contexto:
    """Memória curta por braçadeira, usada pelas regras."""
    bpm_fora_desde: float | None = None
    ultimo_pacote: float = 0.0
    bpm_hist: list[int] = field(default_factory=list)
    spo2_hist: list[int] = field(default_factory=list)


def avaliar(leitura: dict, ctx: Contexto) -> tuple[set[str], set[str]]:
    """Retorna (condições ativas, condições normalizadas) para esta leitura."""
    ativas, normais = set(), set()
    t, bpm, spo2, flags = leitura["horario"], leitura["bpm"], leitura["spo2"], leitura["flags"]

    if flags & 0x01:
        ativas.add("SOS")
    if flags & 0x02:
        ativas.add("QUEDA")

    if spo2:
        if spo2 < SPO2_CRITICO:
            ativas.add("SPO2_BAIXO")
        elif spo2 >= SPO2_CRITICO + HISTERESE_SPO2:      # evita abrir/fechar perto do limite
            normais.add("SPO2_BAIXO")

    if bpm:
        fora = bpm < BPM_BAIXO or bpm > BPM_ALTO
        if fora:
            ctx.bpm_fora_desde = ctx.bpm_fora_desde or t
            if t - ctx.bpm_fora_desde >= BPM_DURACAO_S:
                ativas.add("BPM_ALTO" if bpm > BPM_ALTO else "BPM_BAIXO")
        else:
            ctx.bpm_fora_desde = None
            normais.update({"BPM_ALTO", "BPM_BAIXO"})

    (ativas if flags & 0x10 else normais).add("SEM_CONTATO")
    (ativas if leitura["bateria"] < BATERIA_BAIXA and not flags & 0x04 else normais).add("BATERIA_BAIXA")
    normais.add("SEM_SINAL")
    return ativas, normais
