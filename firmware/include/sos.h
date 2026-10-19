/**
 * sos.h — Máquina de estados do botão SOS.
 *
 *  IDLE --(aperta)--> PRESSING --(2 s)--> SENT --(ACK do operador)--> ACKED
 *                         |                 | reenvia a cada 3 s         |
 *                    (solta antes)          |                       (operador encerra)
 *                         v                 v                            v
 *                       IDLE           (sem ACK: continua)             IDLE
 */
#ifndef PULSO_SOS_H
#define PULSO_SOS_H

#include <stdint.h>
#include <stdbool.h>

typedef enum { SOS_IDLE, SOS_PRESSING, SOS_SENT, SOS_ACKED } sos_state_t;

/* Ações que a aplicação deve executar (bitmask) */
#define SOS_ACT_SEND        0x01u   /* enviar pacote de SOS agora   */
#define SOS_ACT_LED_RED     0x02u
#define SOS_ACT_LED_GREEN   0x04u
#define SOS_ACT_VIBRATE     0x08u
#define SOS_ACT_LEDS_OFF    0x10u

typedef struct {
    sos_state_t state;
    uint32_t    press_start_ms;
    uint32_t    last_tx_ms;
    uint16_t    retries;
} sos_t;

void    sos_init(sos_t *s);
uint8_t sos_update(sos_t *s, bool pressed, uint32_t now_ms);
uint8_t sos_on_ack(sos_t *s);    /* downlink CFG_DL_CMD_SOS_ACK   */
uint8_t sos_on_close(sos_t *s);  /* downlink CFG_DL_CMD_SOS_CLOSE */
bool    sos_active(const sos_t *s);

#endif
