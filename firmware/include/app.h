/** app.h — Aplicação principal da braçadeira (independente do hardware). */
#ifndef PULSO_APP_H
#define PULSO_APP_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    bool     sensors_ok;
    uint8_t  last_bpm, last_spo2, battery;
    float    x, y, z;
    uint32_t packets_sent;
} app_status_t;

void app_init(void);
/** Chamar em laço. Faz a amostragem, o SOS, a queda e o envio a cada 5 s. */
void app_tick(void);
const app_status_t *app_status(void);

/** Usado pela HAL do PC para injetar amostras simuladas do sensor. */
void app_push_ppg(const uint32_t *red, const uint32_t *ir, uint16_t n);
void app_push_accel(float ax, float ay, float az);

#endif
