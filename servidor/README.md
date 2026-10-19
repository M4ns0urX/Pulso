# Servidor

Recebe os pacotes LoRa, trata os dados, aplica as regras de alerta, grava no banco e serve a API e o dashboard. Usa só a biblioteca padrão do Python 3.10+.

## Pipeline de tratamento

Cada pacote passa pelas 6 etapas descritas em [banco-de-dados.md](../docs/textos/banco-de-dados.md):

1. **Receber:** decodifica os 20 bytes e confere o CRC (`packet.py`).
2. **Validar:** descarta valores impossíveis e pacotes duplicados, já que o mesmo pacote chega por vários gateways.
3. **Filtrar:** aplica média móvel de 3 leituras em BPM e SpO2.
4. **Enriquecer:** identifica o nível pela altura, encaixa a posição na galeria (map-matching), descobre a zona e o trabalhador do turno (`mapa.py`).
5. **Regras:** abre, normaliza e escalona alertas (`regras.py`).
6. **Armazenar:** grava a leitura e o resumo por minuto (`db.py`).

## Regras de alerta

| Alerta | Condição | Nível | Quem encerra |
|---|---|---|---|
| SOS | botão SOS | crítico | operador |
| Queda | acelerômetro | crítico | operador |
| Oxigenação baixa | SpO2 < 90 % (normaliza com ≥ 93 %) | crítico | automático |
| BPM alto / baixo | > 150 ou < 40 por 30 s | alto | automático |
| Sem sinal | nenhum pacote por 30 s | alto | automático |
| Bateria fraca | < 15 % | aviso | automático |
| Sensor sem contato | braçadeira mal posicionada | aviso | automático |

**Escalonamento:** se o alerta não for confirmado em 30 s, o supervisor do turno é avisado. Em 2 minutos, a brigada de emergência e o gerente de HSE são acionados.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `pulso_server/packet.py` | Formato do pacote, igual ao do firmware |
| `pulso_server/mapa.py` | Mapa da mina, zonas, âncoras UWB (zigue-zague) e map-matching |
| `pulso_server/servidor.py` | Pipeline, alertas, confirmação e encerramento, downlink |
| `pulso_server/regras.py` | Limites e regras |
| `pulso_server/db.py` | Banco SQLite (demonstração) |
| `pulso_server/api.py` | API HTTP e Server-Sent Events |
| `schema_timescale.sql` | Esquema de produção (PostgreSQL + TimescaleDB, com retenção de 90 dias e 5 anos) |
| `config/mina_exemplo.json` | Mapa e trabalhadores da mina de exemplo |
| `ingest_stdin.py` | Recebe pacotes em hexadecimal, por exemplo do firmware simulado |

## API

| Rota | Função |
|---|---|
| `GET /api/mapa` | Níveis, galerias, âncoras e gateways |
| `GET /api/estado` | Trabalhadores, alertas, indicadores e eventos |
| `GET /api/stream` | O estado a cada 1 s (SSE) |
| `GET /api/historico?dispositivo=321&minutos=5` | Série de BPM e SpO2 |
| `GET /api/relatorio` | Alertas por tipo e tempo médio de resposta (NR-22) |
| `POST /api/alertas/{id}/recebido` | Operador assume o alerta |
| `POST /api/alertas/{id}/encerrar` | Encerra o alerta (`{"falso_alarme": true}` opcional) |

## Firmware → servidor

```bash
cd firmware && make
./build/pulso_sim --hex 30 | python3 ../servidor/ingest_stdin.py
```
