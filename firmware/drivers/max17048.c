#include "max17048.h"
#include "hal.h"

bool max17048_init(void)
{
    uint8_t v[2];
    if (!hal_i2c_read(MAX17048_ADDR, MAX17048_VERSION, v, 2)) return false;
    /* alerta (pino ALRT → PA10) quando a carga cair abaixo de 15 %: ATHD = 32 − 15 = 17 */
    uint8_t cfg[2] = { 0x97, 0x00 | (32 - 15) };
    return hal_i2c_write(MAX17048_ADDR, MAX17048_CONFIG, cfg, 2);
}

uint8_t max17048_soc_pct(void)
{
    uint8_t v[2] = { 0, 0 };
    hal_i2c_read(MAX17048_ADDR, MAX17048_SOC, v, 2);
    return v[0] > 100 ? 100 : v[0];                 /* byte alto = % inteiro */
}

float max17048_vcell(void)
{
    uint8_t v[2] = { 0, 0 };
    hal_i2c_read(MAX17048_ADDR, MAX17048_VCELL, v, 2);
    return (float)((v[0] << 8) | v[1]) * 78.125e-6f;  /* 78,125 µV/LSB */
}
