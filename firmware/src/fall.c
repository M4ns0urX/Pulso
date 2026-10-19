#include "fall.h"
#include "pulso_config.h"
#include <math.h>

void fall_init(fall_t *f) { f->state = FALL_NORMAL; f->t_mark = 0; f->still_ms = 0; }

bool fall_update(fall_t *f, float ax, float ay, float az, uint32_t now, uint32_t dt)
{
    float g = sqrtf(ax * ax + ay * ay + az * az);

    switch (f->state) {
    case FALL_NORMAL:
        if (g < CFG_FALL_FREEFALL_G) { f->state = FALL_FREEFALL; f->t_mark = now; }
        break;
    case FALL_FREEFALL:
        if (g >= CFG_FALL_FREEFALL_G) {
            f->state = (now - f->t_mark >= CFG_FALL_FREEFALL_MS) ? FALL_WAIT_IMPACT : FALL_NORMAL;
            f->t_mark = now;
            if (f->state == FALL_WAIT_IMPACT && g > CFG_FALL_IMPACT_G) { f->state = FALL_WAIT_STILL; f->still_ms = 0; }
        }
        break;
    case FALL_WAIT_IMPACT:
        if (g > CFG_FALL_IMPACT_G) { f->state = FALL_WAIT_STILL; f->t_mark = now; f->still_ms = 0; }
        else if (now - f->t_mark > CFG_FALL_IMPACT_WINDOW_MS) f->state = FALL_NORMAL;
        break;
    case FALL_WAIT_STILL:
        if (g > 0.8f && g < 1.2f) f->still_ms += dt;
        else if (now - f->t_mark > 300u) {            /* ignora o "quique" logo após o impacto */
            f->state = FALL_NORMAL;                   /* voltou a se mexer: não foi queda */
            break;
        }
        if (f->still_ms >= CFG_FALL_STILL_MS) { f->state = FALL_NORMAL; return true; }
        break;
    }
    return false;
}
