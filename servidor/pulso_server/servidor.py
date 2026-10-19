"""Servidor de ingestão da Pulso.

Cada pacote recebido passa pelas 6 etapas do tratamento:
  1. Receber      decodifica e confere o CRC
  2. Validar      descarta valores impossíveis e pacotes repetidos
  3. Filtrar      média móvel de BPM e SpO2
  4. Enriquecer   nível, zona da mina e trabalhador do turno
  5. Regras       gera, normaliza e escalona alertas
  6. Armazenar    grava a leitura e o resumo por minuto
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from . import regras
from .db import Banco
from .mapa import Mina
from .packet import DL_SOS_ACK, DL_SOS_CLOSE, Packet, PacketError

ESCALONAMENTO_TXT = {
    1: "Supervisor do turno avisado por rádio e SMS",
    2: "Brigada de emergência e gerente de HSE acionados",
}


class Servidor:
    def __init__(self, mina: Mina, banco: Banco | None = None,
                 relogio: Callable[[], float] = time.time,
                 downlink: Callable[[int, bytes], None] | None = None):
        self.mina = mina
        self.banco = banco or Banco()
        self.agora = relogio
        self.downlink = downlink or (lambda dev, data: None)
        self.lock = threading.RLock()
        self.ctx: dict[int, regras.Contexto] = {}
        self.ao_vivo: dict[int, dict] = {}            # último estado de cada braçadeira
        self.vistos: deque[tuple[int, int, int]] = deque(maxlen=2000)
        self.ignorar_sos: set[int] = set()            # SOS encerrado, aguardando a braçadeira
        self.eventos: deque[dict] = deque(maxlen=60)  # linha do tempo para o dashboard
        self.stats = {"recebidos": 0, "duplicados": 0, "corrompidos": 0, "invalidos": 0, "processados": 0}
        self._cadastrar()

    # ------------------------------------------------------------------ cadastro
    def _cadastrar(self) -> None:
        agora = self.agora()
        for n in self.mina.niveis.values():
            for z in n.zonas:
                self.banco.executar("INSERT OR IGNORE INTO zona VALUES (?,?,?,?,?)",
                                    (f"{n.id}:{z}", z, n.id, n.z, "normal"))
        for i, t in enumerate(self.mina.trabalhadores):
            self.banco.executar("INSERT OR IGNORE INTO trabalhador VALUES (?,?,?,?,?)",
                                (t["id"], t["nome"], f"MAT-{1000 + i}", t.get("funcao"), "Mina exemplo"))
            self.banco.executar("INSERT OR IGNORE INTO bracadeira VALUES (?,?,?,?,?)",
                                (t["id"], f"PLS-{t['id']:05d}", t["id"], "1.0.0", "ativa"))
            self.banco.executar("INSERT INTO turno (trabalhador_id, bracadeira_id, entrada) VALUES (?,?,?)",
                                (t["id"], t["id"], agora))
        self.trab = {t["id"]: t for t in self.mina.trabalhadores}

    def _evento(self, texto: str, nivel: str = "info", dev: int | None = None) -> None:
        self.eventos.appendleft({"horario": self.agora(), "texto": texto, "nivel": nivel, "dispositivo": dev})

    # ------------------------------------------------------------------ ingestão
    def receber_uplink(self, raw: bytes, gateway: str = "?", rssi: float = 0.0) -> dict | None:
        with self.lock:
            self.stats["recebidos"] += 1
            # 1. Receber
            try:
                p = Packet.decode(raw)
            except PacketError:
                self.stats["corrompidos"] += 1
                return None
            # 2. Validar
            chave = (p.device_id, p.seq, p.timestamp)
            if chave in self.vistos:                      # o mesmo pacote chega por vários gateways
                self.stats["duplicados"] += 1
                return None
            self.vistos.append(chave)
            if p.device_id not in self.trab:
                self.stats["invalidos"] += 1
                return None
            bpm = p.bpm if 25 <= p.bpm <= 230 else None
            spo2 = p.spo2 if 50 <= p.spo2 <= 100 else None

            # 3. Filtrar (média móvel de 3 leituras)
            ctx = self.ctx.setdefault(p.device_id, regras.Contexto())
            if bpm:
                ctx.bpm_hist = (ctx.bpm_hist + [bpm])[-3:]
                bpm = round(sum(ctx.bpm_hist) / len(ctx.bpm_hist))
            if spo2:
                ctx.spo2_hist = (ctx.spo2_hist + [spo2])[-3:]
                spo2 = round(sum(ctx.spo2_hist) / len(ctx.spo2_hist))
            # alertas críticos usam o valor bruto para não atrasar
            spo2_regra = min(spo2, p.spo2) if spo2 and p.spo2 >= 50 else spo2

            # 4. Enriquecer
            nivel = self.mina.nivel_por_z(p.z)
            x, y = nivel.encaixar(p.x, p.y)
            zona, _ = nivel.zona_de(x, y)
            horario = self.agora()
            ctx.ultimo_pacote = horario
            leitura = {
                "horario": horario, "bracadeira_id": p.device_id, "bpm": bpm, "spo2": spo2,
                "x": round(x, 2), "y": round(y, 2), "z": p.z, "zona_id": f"{nivel.id}:{zona}",
                "bateria": p.battery, "flags": p.flags,
            }

            # 5. Regras
            if not p.sos:
                self.ignorar_sos.discard(p.device_id)
            flags_regra = p.flags & ~0x01 if p.device_id in self.ignorar_sos else p.flags
            ativas, normais = regras.avaliar({**leitura, "spo2": spo2_regra, "flags": flags_regra}, ctx)
            for tipo in ativas:
                self._abrir_alerta(p.device_id, tipo, {**leitura, "spo2": spo2_regra})
            for tipo in normais - ativas:
                self._normalizar(p.device_id, tipo)

            # 6. Armazenar
            self.banco.gravar_leitura(leitura)
            self.ao_vivo[p.device_id] = {
                **leitura, "nivel": nivel.id, "zona": zona, "tipo_pacote": p.type,
                "gateway": gateway, "rssi": rssi, "sos_confirmado": bool(p.flags & 0x20),
            }
            self.stats["processados"] += 1
            return leitura

    # ------------------------------------------------------------------ alertas
    def _alerta_aberto(self, dev: int, tipo: str) -> dict | None:
        r = self.banco.consultar(
            "SELECT * FROM alerta WHERE bracadeira_id=? AND tipo=? AND status IN ('aberto','recebido')",
            (dev, tipo))
        return r[0] if r else None

    def _abrir_alerta(self, dev: int, tipo: str, l: dict) -> None:
        if self._alerta_aberto(dev, tipo):
            return
        nome = self.trab[dev]["nome"]
        zona = l["zona_id"].split(":")[1] if l.get("zona_id") else "?"
        det = {"SPO2_BAIXO": f"SpO2 {l.get('spo2')} %", "BPM_ALTO": f"{l.get('bpm')} BPM",
               "BPM_BAIXO": f"{l.get('bpm')} BPM", "BATERIA_BAIXA": f"{l.get('bateria')} %"}.get(tipo, "")
        self.banco.executar(
            "INSERT INTO alerta (horario, bracadeira_id, tipo, nivel, x, y, zona_id, detalhe) VALUES (?,?,?,?,?,?,?,?)",
            (self.agora(), dev, tipo, regras.NIVEL[tipo], l.get("x"), l.get("y"), l.get("zona_id"), det))
        self._evento(f"{regras.TITULO[tipo]}: {nome} ({zona}) {det}".strip(), regras.NIVEL[tipo], dev)

    def _normalizar(self, dev: int, tipo: str) -> None:
        if tipo in regras.SO_OPERADOR:
            return
        a = self._alerta_aberto(dev, tipo)
        if a:
            self.banco.executar("UPDATE alerta SET status='normalizado', encerrado_em=? WHERE id=?",
                                (self.agora(), a["id"]))
            self._evento(f"{regras.TITULO[tipo]} normalizado: {self.trab[dev]['nome']}", "ok", dev)

    def reconhecer(self, alerta_id: int, operador: str = "Operador") -> bool:
        """Operador clicou em 'Recebido'."""
        with self.lock:
            a = self.banco.consultar("SELECT * FROM alerta WHERE id=?", (alerta_id,))
            if not a or a[0]["status"] != "aberto":
                return False
            a = a[0]
            self.banco.executar("UPDATE alerta SET status='recebido', atendido_por=?, atendido_em=? WHERE id=?",
                                (operador, self.agora(), alerta_id))
            if a["tipo"] == "SOS":
                self.downlink(a["bracadeira_id"], bytes([DL_SOS_ACK]))   # LED verde na braçadeira
            seg = self.agora() - a["horario"]
            self._evento(f"{operador} recebeu o alerta de {self.trab[a['bracadeira_id']]['nome']} "
                         f"em {seg:.0f} s e despachou o resgate", "ok", a["bracadeira_id"])
            return True

    def encerrar(self, alerta_id: int, operador: str = "Operador", falso_alarme: bool = False) -> bool:
        with self.lock:
            a = self.banco.consultar("SELECT * FROM alerta WHERE id=?", (alerta_id,))
            if not a or a[0]["status"] not in ("aberto", "recebido"):
                return False
            a = a[0]
            self.banco.executar(
                "UPDATE alerta SET status='encerrado', encerrado_em=?, falso_alarme=?, "
                "atendido_por=COALESCE(atendido_por, ?), atendido_em=COALESCE(atendido_em, ?) WHERE id=?",
                (self.agora(), int(falso_alarme), operador, self.agora(), alerta_id))
            if a["tipo"] == "SOS":
                self.ignorar_sos.add(a["bracadeira_id"])
                self.downlink(a["bracadeira_id"], bytes([DL_SOS_CLOSE]))
            self._evento(f"Caso de {self.trab[a['bracadeira_id']]['nome']} encerrado"
                         + (" (falso alarme)" if falso_alarme else ""), "ok", a["bracadeira_id"])
            return True

    # ------------------------------------------------------------------ rotina de 1 s
    def tick(self) -> None:
        with self.lock:
            agora = self.agora()
            for dev, ctx in self.ctx.items():                         # sem sinal
                if ctx.ultimo_pacote and agora - ctx.ultimo_pacote > regras.SEM_SINAL_S:
                    l = self.ao_vivo.get(dev, {})
                    self._abrir_alerta(dev, "SEM_SINAL", l)
            for a in self.banco.consultar("SELECT * FROM alerta WHERE status='aberto'"):   # escalonamento
                idade = agora - a["horario"]
                novo = 2 if idade >= regras.ESCALONAR_BRIGADA_S else 1 if idade >= regras.ESCALONAR_SUPERVISOR_S else 0
                if novo > a["escalonamento"] and a["nivel"] != "aviso":
                    self.banco.executar("UPDATE alerta SET escalonamento=? WHERE id=?", (novo, a["id"]))
                    self._evento(f"{ESCALONAMENTO_TXT[novo]} ({self.trab[a['bracadeira_id']]['nome']})",
                                 "alto", a["bracadeira_id"])

    # ------------------------------------------------------------------ consultas
    def estado(self) -> dict:
        with self.lock:
            agora = self.agora()
            alertas = self.banco.consultar(
                "SELECT * FROM alerta WHERE status IN ('aberto','recebido') ORDER BY "
                "CASE nivel WHEN 'critico' THEN 0 WHEN 'alto' THEN 1 ELSE 2 END, horario")
            por_dev: dict[int, str] = {}
            for a in alertas:
                por_dev.setdefault(a["bracadeira_id"], a["nivel"])
                a["titulo"] = regras.TITULO[a["tipo"]]
                a["nome"] = self.trab[a["bracadeira_id"]]["nome"]
                a["idade_s"] = round(agora - a["horario"])
            trabalhadores = []
            for dev, t in self.trab.items():
                v = self.ao_vivo.get(dev)
                if not v:
                    continue
                sem_sinal = agora - self.ctx[dev].ultimo_pacote > regras.SEM_SINAL_S
                trabalhadores.append({
                    "id": dev, "nome": t["nome"], "funcao": t.get("funcao"),
                    "nivel": v["nivel"], "zona": v["zona"], "x": v["x"], "y": v["y"],
                    "bpm": v["bpm"], "spo2": v["spo2"], "bateria": v["bateria"],
                    "status": por_dev.get(dev, "normal"), "sem_sinal": sem_sinal,
                    "atualizado_ha_s": round(agora - v["horario"]), "sos_confirmado": v["sos_confirmado"],
                })
            return {
                "horario": agora,
                "kpis": {
                    "no_subsolo": len(trabalhadores),
                    "alertas_criticos": sum(a["nivel"] == "critico" for a in alertas),
                    "alertas": len(alertas),
                    "sem_sinal": sum(t["sem_sinal"] for t in trabalhadores),
                },
                "trabalhadores": trabalhadores,
                "alertas": alertas,
                "eventos": list(self.eventos)[:25],
                "rede": dict(self.stats),
            }

    def historico(self, dev: int, minutos: float = 5) -> list[dict]:
        return self.banco.consultar(
            "SELECT horario, bpm, spo2, bateria FROM leitura WHERE bracadeira_id=? AND horario>=? ORDER BY horario",
            (dev, self.agora() - minutos * 60))

    def relatorio(self) -> dict:
        """Resumo para o relatório NR-22: alertas e tempos de resposta."""
        linhas = self.banco.consultar(
            "SELECT tipo, COUNT(*) n, AVG(atendido_em - horario) resp, SUM(falso_alarme) falsos "
            "FROM alerta GROUP BY tipo")
        return {"por_tipo": linhas, "leituras": self.banco.consultar("SELECT COUNT(*) n FROM leitura")[0]["n"]}
