<<<<<<< HEAD
# Firmware da braçadeira Pulso

Firmware em C para o **RAK3172** (STM32WLE5 + rádio LoRa). Ele lê os sensores, calcula BPM, SpO2 e a posição, trata o botão SOS e a detecção de queda, e envia um pacote de 20 bytes pela LoRaWAN a cada 5 segundos.

## Estrutura

```
firmware/
├── include/            interfaces (.h)
│   ├── pulso_config.h  tempos e limites (SOS 2 s, envio 5 s, SpO2 < 90 % …)
│   ├── packet.h        formato do pacote LoRa (20 bytes)
│   ├── hal.h           abstração do hardware
│   └── …
├── src/
│   ├── app.c           lógica principal (ciclo de 5 s, SOS, queda, downlink)
│   ├── packet.c        codificação/decodificação + CRC-16
│   ├── sos.c           máquina de estados do botão SOS
│   ├── ppg.c           cálculo de BPM e SpO2 (ratio of ratios)
│   ├── uwb_pos.c       trilateração UWB (Gauss-Newton)
│   └── fall.c          detecção de queda (queda livre → impacto → imobilidade)
├── drivers/            MAX30102, LIS2DH12, MAX17048 (registradores reais)
├── platform/
│   ├── rak3172/        HAL da placa real (STM32CubeWL)
│   └── host/           HAL simulada para rodar no PC
└── tests/              testes unitários
```

## Rodar no PC (sem hardware)

Precisa só de `gcc` e `make`.

```bash
cd firmware
make test     # 21 testes: pacote, SOS, BPM/SpO2, UWB, queda
make sim      # simula 30 s da braçadeira: envio periódico, SOS aos 12 s, ACK aos 20 s
```

Exemplo de saída da simulação:

```
[  5.00 s] LoRa               1042010578e7684861e9015f0254f457000033b1
           tipo=0 id=0x0142 BPM=72 SpO2=97% pos=(48.9, 60.7, -298.8) m bat=87% flags=0x00 seq=0
[ 14.00 s] LED VERMELHO aceso
[ 14.00 s] LoRa (confirmado)  1142010e78e768486131025e0254f45701026f7c
           tipo=1 id=0x0142 BPM=72 SpO2=97% pos=(56.1, 60.6, -298.8) m bat=87% flags=0x01 seq=2
[ 20.00 s] downlink recebido: SOS RECEBIDO pelo operador
[ 20.00 s] LED VERDE aceso
```

Para mandar os pacotes do firmware simulado direto para o servidor:

```bash
./build/pulso_sim --hex 30 | python3 ../servidor/ingest_stdin.py
```

## Gravar na placa real

1. No **STM32CubeIDE**, abra o exemplo `LoRaWAN_End_Node` do pacote **STM32CubeWL**.
2. Configure a região **AU915** (Brasil) e as chaves OTAA (DevEUI, AppEUI e AppKey) do servidor LoRaWAN.
3. Copie `include/`, `src/`, `drivers/` e `platform/rak3172/hal_rak3172.c` para o projeto.
4. No CubeMX, configure os pinos conforme o cabeçalho de `hal_rak3172.c`: I2C2 em PA11/PA12, SPI1 em PA4–PA7 e GPIOs.
5. Adicione o driver oficial do **DW3000** (Qorvo) e implemente `uwb_ds_twr()` a partir do exemplo de DS-TWR.
6. Registre `pulso_on_rx` como callback de recepção do `LmHandler`.
7. No `main.c`, troque o loop do exemplo por:
   ```c
   app_init();
   while (1) { MX_LoRaWAN_Process(); app_tick(); }
   ```
8. Grave pelo conector SWD (Tag-Connect J3) com um ST-Link.

## Pacote LoRa (20 bytes)

| Bytes | Campo | Tipo |
|---|---|---|
| 0 | versão (4 bits) + tipo (4 bits: 0 periódico, 1 SOS, 2 evento) | u8 |
| 1–2 | ID da braçadeira | u16 |
| 3–6 | horário (Unix) | u32 |
| 7 | BPM (0 = inválido) | u8 |
| 8 | SpO2 % (0 = inválido) | u8 |
| 9–14 | posição x, y, z em decímetros | 3 × i16 |
| 15 | bateria % | u8 |
| 16 | flags: SOS, queda, carregando, bateria baixa, sem contato, SOS confirmado | u8 |
| 17 | sequência | u8 |
| 18–19 | CRC-16/CCITT | u16 |

**Downlinks (porta 2):** `0x01` = SOS recebido (LED verde), `0x02` = caso encerrado, `0x03` = vibrar.
**Porta 3:** tabela de âncoras UWB da zona atual.

## Consumo de energia

O MCU fica em Stop2 entre os eventos. O MAX30102 amostra continuamente com os LEDs em cerca de 7 mA e baixo ciclo de trabalho. O UWB liga só durante o ranging, cerca de 10 ms a cada 5 s. A LoRa transmite cerca de 50 ms a cada 5 s. A estimativa de consumo médio é de 2 a 4 mA, o que dá vários dias com a bateria de 1200 mAh. **Esse valor precisa ser confirmado em bancada.**
=======
# Firmware

Código da braçadeira (RAK3172 / STM32WLE5): leitura do MAX30102, ranging UWB com DWM3000, envio LoRaWAN a cada 5 s, botão SOS e modo de baixo consumo.

*A desenvolver.*
>>>>>>> ac7e550b7831f00c5ccce98272034df7b2f66950
