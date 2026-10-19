/**
 * hal.h — Camada de abstração de hardware.
 *
 * A aplicação (app.c) só conversa com o hardware por estas funções.
 * Implementações:
 *   platform/rak3172/hal_rak3172.c  → placa real (STM32WLE5 / STM32CubeWL)
 *   platform/host/hal_host.c        → simulação no PC (testes e demonstração)
 */
#ifndef PULSO_HAL_H
#define PULSO_HAL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "uwb_pos.h"

typedef enum { LED_RED, LED_GREEN } hal_led_t;

/* Tempo */
uint32_t hal_millis(void);
uint32_t hal_unix_time(void);
void     hal_sleep_until(uint32_t wake_ms);       /* modo Stop2 até o próximo evento */

/* Identificação */
uint16_t hal_device_id(void);

/* GPIO */
bool hal_sos_pressed(void);                        /* PA0, ativo em nível baixo */
void hal_led(hal_led_t led, bool on);              /* PB5 vermelho, PB6 verde   */
void hal_vibrate(uint16_t ms);                     /* PB7 → MOSFET Q2           */
bool hal_is_charging(void);                        /* PA9 ← CHG do BQ24075      */

/* I²C2 (PA11 SDA / PA12 SCL) — MAX30102, LIS2DH12, MAX17048 */
bool hal_i2c_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, size_t len);
bool hal_i2c_read (uint8_t addr7, uint8_t reg, uint8_t *buf, size_t len);

/* UWB (DWM3000 via SPI1). Faz uma rodada de ranging DS-TWR com as âncoras
 * ao alcance e devolve quantas responderam. */
uint8_t hal_uwb_ranging(uwb_anchor_t *anchors, float *dist_m, uint8_t max);

/* LoRaWAN */
bool   hal_lora_send(uint8_t port, const uint8_t *buf, size_t len, bool confirmed);
/** Retorna o tamanho do downlink recebido (0 se não houver). */
size_t hal_lora_poll_downlink(uint8_t *buf, size_t max);

#endif
