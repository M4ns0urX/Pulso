"""Banco de dados da Pulso.

Para a demonstração usamos SQLite (não precisa instalar nada). Em produção
o mesmo esquema roda em PostgreSQL + TimescaleDB (ver schema_timescale.sql).
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS trabalhador (
    id         INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    matricula  TEXT,
    funcao     TEXT,
    empresa    TEXT
);
CREATE TABLE IF NOT EXISTS bracadeira (
    id              INTEGER PRIMARY KEY,
    numero_serie    TEXT,
    trabalhador_id  INTEGER REFERENCES trabalhador(id),
    firmware        TEXT,
    status          TEXT DEFAULT 'ativa'
);
CREATE TABLE IF NOT EXISTS zona (
    id              TEXT PRIMARY KEY,      -- nivel:zona, ex. N300:S-2
    nome            TEXT,
    nivel           TEXT,
    profundidade_m  REAL,
    risco           TEXT DEFAULT 'normal'
);
CREATE TABLE IF NOT EXISTS turno (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trabalhador_id  INTEGER REFERENCES trabalhador(id),
    bracadeira_id   INTEGER REFERENCES bracadeira(id),
    entrada         REAL,
    saida           REAL
);
-- série temporal: uma linha a cada 5 s por trabalhador
CREATE TABLE IF NOT EXISTS leitura (
    horario        REAL NOT NULL,
    bracadeira_id  INTEGER NOT NULL REFERENCES bracadeira(id),
    bpm            INTEGER,
    spo2           INTEGER,
    x REAL, y REAL, z REAL,
    zona_id        TEXT REFERENCES zona(id),
    bateria        INTEGER,
    flags          INTEGER
);
CREATE INDEX IF NOT EXISTS idx_leitura ON leitura(bracadeira_id, horario);
CREATE TABLE IF NOT EXISTS alerta (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    horario        REAL NOT NULL,
    bracadeira_id  INTEGER REFERENCES bracadeira(id),
    tipo           TEXT NOT NULL,          -- SOS, SPO2_BAIXO, QUEDA, BPM_ALTO, BPM_BAIXO, SEM_SINAL, BATERIA_BAIXA, SEM_CONTATO
    nivel          TEXT NOT NULL,          -- critico, alto, aviso
    x REAL, y REAL,
    zona_id        TEXT,
    status         TEXT NOT NULL DEFAULT 'aberto',   -- aberto, recebido, encerrado, normalizado
    escalonamento  INTEGER NOT NULL DEFAULT 0,       -- 0 sala de controle, 1 supervisor, 2 brigada
    atendido_por   TEXT,
    atendido_em    REAL,
    encerrado_em   REAL,
    falso_alarme   INTEGER DEFAULT 0,
    detalhe        TEXT
);
-- resumo por minuto (mantido por 5 anos; as leituras detalhadas por 90 dias)
CREATE TABLE IF NOT EXISTS resumo_minuto (
    minuto         INTEGER NOT NULL,
    bracadeira_id  INTEGER NOT NULL,
    bpm_medio REAL, bpm_max INTEGER, spo2_min INTEGER, n INTEGER,
    PRIMARY KEY (minuto, bracadeira_id)
);
"""


class Banco:
    def __init__(self, caminho: str | Path = ":memory:"):
        self.con = sqlite3.connect(str(caminho), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.con.executescript(SCHEMA)

    def executar(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self.con.execute(sql, params)
            self.con.commit()
            return cur

    def consultar(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.con.execute(sql, params).fetchall()]

    # ---------- operações usadas pelo pipeline ----------
    def gravar_leitura(self, l: dict) -> None:
        minuto = int(l["horario"] // 60)
        with self.lock:
            self.con.execute(
                "INSERT INTO leitura VALUES (?,?,?,?,?,?,?,?,?,?)",
                (l["horario"], l["bracadeira_id"], l["bpm"], l["spo2"], l["x"], l["y"], l["z"],
                 l["zona_id"], l["bateria"], l["flags"]),
            )
            if l["bpm"]:
                self.con.execute(
                    """INSERT INTO resumo_minuto VALUES (?,?,?,?,?,1)
                       ON CONFLICT(minuto, bracadeira_id) DO UPDATE SET
                         bpm_medio = (bpm_medio * n + excluded.bpm_medio) / (n + 1),
                         bpm_max   = MAX(bpm_max, excluded.bpm_max),
                         spo2_min  = MIN(spo2_min, excluded.spo2_min),
                         n = n + 1""",
                    (minuto, l["bracadeira_id"], l["bpm"], l["bpm"], l["spo2"] or 100),
                )
            self.con.commit()
