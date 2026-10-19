#include "lis2dh12.h"
#include "hal.h"

bool lis2dh12_init(void)
{
    uint8_t id = 0, v;
    if (!hal_i2c_read(LIS2DH12_ADDR, LIS2DH12_WHO_AM_I, &id, 1) || id != 0x33u) return false;
    v = 0x47; hal_i2c_write(LIS2DH12_ADDR, LIS2DH12_CTRL_REG1, &v, 1);  /* 50 Hz, XYZ ligados */
    v = 0xA8; hal_i2c_write(LIS2DH12_ADDR, LIS2DH12_CTRL_REG4, &v, 1);  /* BDU, ±8 g, HR      */
    return true;
}

bool lis2dh12_read_g(float *ax, float *ay, float *az)
{
    uint8_t b[6];
    /* bit 7 do registrador = auto-incremento */
    if (!hal_i2c_read(LIS2DH12_ADDR, LIS2DH12_OUT_X_L | 0x80u, b, 6)) return false;
    /* alta resolução: 12 bits alinhados à esquerda, 4 mg/LSB em ±8 g */
    *ax = (float)((int16_t)(b[0] | (b[1] << 8)) >> 4) * 0.004f;
    *ay = (float)((int16_t)(b[2] | (b[3] << 8)) >> 4) * 0.004f;
    *az = (float)((int16_t)(b[4] | (b[5] << 8)) >> 4) * 0.004f;
    return true;
}
