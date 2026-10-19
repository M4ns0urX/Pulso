# Digital twin

Simulação completa do sistema Pulso. Ela reproduz a mina, os trabalhadores, as braçadeiras e a rede LoRa, e é a prova de conceito do projeto.

## O que é simulado

| Módulo | O que faz |
|---|---|
| `trabalhador.py` | Trabalhadores andando pelas galerias, parando para trabalhar, com BPM e SpO2 realistas (sobem ao andar e reagem a gás, queda e estresse) |
| `bracadeira.py` | Braçadeira virtual com o mesmo comportamento do firmware: envio a cada 5 s, SOS com 2 s de pressão, reenvio até o ACK, LED verde ao confirmar |
| `uwb.py` | Ranging UWB com ruído de 5 cm e trilateração por Gauss-Newton, o mesmo algoritmo de `firmware/src/uwb_pos.c` |
| `rede.py` | Gateways LoRa nas galerias, com perda de pacotes pela distância, recepção duplicada por vários gateways e downlink classe A |
| `simulacao.py` | Junta tudo, roda em tempo real ou acelerado e executa um roteiro de eventos |

A mina simulada vem de `servidor/config/mina_exemplo.json`: 2 níveis, 9 zonas, 41 âncoras UWB, 10 gateways e 12 trabalhadores.

## Roteiro da demonstração

| Tempo | Evento |
|---|---|
| início | Rita começa com a bateria em 14 % → aviso de bateria fraca |
| 40 s | Marcos entra numa área com gás → SpO2 cai abaixo de 90 % → alerta crítico |
| 75 s | Carlos aperta o SOS → alerta crítico em menos de 3 s |
| 130 s | Diego sofre uma queda → alerta de queda |
| 170 s | A braçadeira do Sérgio para de transmitir → alerta "sem sinal" após 30 s |
| 200 s | Marcos sai da área com gás → o alerta se normaliza sozinho |

Sem resposta do operador, os alertas escalam: o supervisor é avisado com 30 s e a brigada com 2 min.

## Como rodar

Na raiz do repositório:

```bash
python3 run_demo.py                  # http://localhost:8080
python3 run_demo.py --velocidade 4   # 4x mais rápido
```

No dashboard, selecione um trabalhador e use os botões **SOS**, **Gás**, **Queda**, **Sem sinal** e **Normalizar** para criar eventos na hora, o que é útil na apresentação para a banca.
