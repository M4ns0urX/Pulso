-- Esquema de produção: PostgreSQL + TimescaleDB
-- (a demonstração usa o mesmo esquema em SQLite: pulso_server/db.py)

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE trabalhador (
    id         INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    matricula  TEXT UNIQUE,
    funcao     TEXT,
    empresa    TEXT
);

CREATE TABLE bracadeira (
    id              INTEGER PRIMARY KEY,
    numero_serie    TEXT UNIQUE,
    trabalhador_id  INTEGER REFERENCES trabalhador(id),
    firmware        TEXT,
    status          TEXT DEFAULT 'ativa'
);

CREATE TABLE zona (
    id              TEXT PRIMARY KEY,
    nome            TEXT,
    nivel           TEXT,
    profundidade_m  REAL,
    area            JSONB,           -- polígono no mapa
    risco           TEXT DEFAULT 'normal'
);

CREATE TABLE turno (
    id              BIGSERIAL PRIMARY KEY,
    trabalhador_id  INTEGER REFERENCES trabalhador(id),
    bracadeira_id   INTEGER REFERENCES bracadeira(id),
    entrada         TIMESTAMPTZ NOT NULL,
    saida           TIMESTAMPTZ
);

-- Série temporal: ~17 mil linhas por trabalhador por dia
CREATE TABLE leitura (
    horario        TIMESTAMPTZ NOT NULL,
    bracadeira_id  INTEGER NOT NULL REFERENCES bracadeira(id),
    bpm            SMALLINT,
    spo2           SMALLINT,
    x REAL, y REAL, z REAL,
    zona_id        TEXT REFERENCES zona(id),
    bateria        SMALLINT,
    flags          SMALLINT
);
SELECT create_hypertable('leitura', 'horario', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX ON leitura (bracadeira_id, horario DESC);

-- Compressão após 7 dias e retenção de 90 dias para o dado detalhado
ALTER TABLE leitura SET (timescaledb.compress, timescaledb.compress_segmentby = 'bracadeira_id');
SELECT add_compression_policy('leitura', INTERVAL '7 days');
SELECT add_retention_policy('leitura', INTERVAL '90 days');

-- Resumo por minuto (agregado contínuo), mantido por 5 anos
CREATE MATERIALIZED VIEW resumo_minuto WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', horario) AS minuto, bracadeira_id,
       AVG(bpm) AS bpm_medio, MAX(bpm) AS bpm_max, MIN(spo2) AS spo2_min, COUNT(*) AS n
FROM leitura GROUP BY 1, 2;
SELECT add_continuous_aggregate_policy('resumo_minuto',
       start_offset => INTERVAL '1 hour', end_offset => INTERVAL '1 minute', schedule_interval => INTERVAL '1 minute');
SELECT add_retention_policy('resumo_minuto', INTERVAL '5 years');

-- Alertas: guardados permanentemente (auditoria NR-22)
CREATE TABLE alerta (
    id             BIGSERIAL PRIMARY KEY,
    horario        TIMESTAMPTZ NOT NULL,
    bracadeira_id  INTEGER REFERENCES bracadeira(id),
    tipo           TEXT NOT NULL,
    nivel          TEXT NOT NULL,
    x REAL, y REAL,
    zona_id        TEXT,
    status         TEXT NOT NULL DEFAULT 'aberto',
    escalonamento  SMALLINT NOT NULL DEFAULT 0,
    atendido_por   TEXT,
    atendido_em    TIMESTAMPTZ,
    encerrado_em   TIMESTAMPTZ,
    falso_alarme   BOOLEAN DEFAULT FALSE,
    detalhe        TEXT
);
CREATE INDEX ON alerta (status, nivel);
