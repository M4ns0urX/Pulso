/** max17048.h — Medidor de bateria MAX17048. Endereço I²C 0x36. */
#ifndef MAX17048_H
#define MAX17048_H

#include <stdint.h>
#include <stdbool.h>

#define MAX17048_ADDR      0x36u
#define MAX17048_VCELL     0x02u
#define MAX17048_SOC       0x04u
#define MAX17048_VERSION   0x08u
#define MAX17048_CONFIG    0x0Cu

bool    max17048_init(void);
uint8_t max17048_soc_pct(void);      /* carga em % */
float   max17048_vcell(void);        /* tensão da célula em V */

#endif
