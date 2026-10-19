/** lis2dh12.h — Driver do acelerômetro LIS2DH12. Endereço I²C 0x19. */
#ifndef LIS2DH12_H
#define LIS2DH12_H

#include <stdbool.h>

#define LIS2DH12_ADDR       0x19u
#define LIS2DH12_WHO_AM_I   0x0Fu   /* deve ler 0x33 */
#define LIS2DH12_CTRL_REG1  0x20u
#define LIS2DH12_CTRL_REG4  0x23u
#define LIS2DH12_OUT_X_L    0x28u

bool lis2dh12_init(void);                         /* 50 Hz, ±8 g, alta resolução */
bool lis2dh12_read_g(float *ax, float *ay, float *az);

#endif
