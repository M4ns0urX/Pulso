#include "sos.h"
#include "pulso_config.h"

void sos_init(sos_t *s)
{
    s->state = SOS_IDLE;
    s->press_start_ms = 0;
    s->last_tx_ms = 0;
    s->retries = 0;
}

uint8_t sos_update(sos_t *s, bool pressed, uint32_t now_ms)
{
    switch (s->state) {
    case SOS_IDLE:
        if (pressed) { s->state = SOS_PRESSING; s->press_start_ms = now_ms; }
        return 0;

    case SOS_PRESSING:
        if (!pressed) { s->state = SOS_IDLE; return 0; }       /* toque acidental */
        if (now_ms - s->press_start_ms >= CFG_SOS_HOLD_MS) {
            s->state = SOS_SENT;
            s->last_tx_ms = now_ms;
            s->retries = 0;
            return SOS_ACT_SEND | SOS_ACT_LED_RED | SOS_ACT_VIBRATE;
        }
        return 0;

    case SOS_SENT:
        if (now_ms - s->last_tx_ms >= CFG_SOS_RETRY_MS && s->retries < CFG_SOS_MAX_RETRIES) {
            s->last_tx_ms = now_ms;
            s->retries++;
            return SOS_ACT_SEND | SOS_ACT_LED_RED;
        }
        return 0;

    case SOS_ACKED:
    default:
        return 0;
    }
}

uint8_t sos_on_ack(sos_t *s)
{
    if (s->state != SOS_SENT) return 0;
    s->state = SOS_ACKED;
    return SOS_ACT_LED_GREEN | SOS_ACT_VIBRATE;       /* "ajuda a caminho" */
}

uint8_t sos_on_close(sos_t *s)
{
    if (s->state == SOS_IDLE) return 0;
    sos_init(s);
    return SOS_ACT_LEDS_OFF;
}

bool sos_active(const sos_t *s) { return s->state == SOS_SENT || s->state == SOS_ACKED; }
