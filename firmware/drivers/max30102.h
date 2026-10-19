/** max30102.h — Driver do sensor óptico MAX30102 (BPM / SpO2). Endereço I²C 0x57. */
#ifndef MAX30102_H
#define MAX30102_H

#include <stdint.h>
#include <stdbool.h>

#define MAX30102_ADDR          0x57u
#define MAX30102_REG_INTR1     0x00u
#define MAX30102_REG_INTR_EN1  0x02u
#define MAX30102_REG_FIFO_WR   0x04u
#define MAX30102_REG_FIFO_OVF  0x05u
#define MAX30102_REG_FIFO_RD   0x06u
#define MAX30102_REG_FIFO_DATA 0x07u
#define MAX30102_REG_FIFO_CFG  0x08u
#define MAX30102_REG_MODE      0x09u
#define MAX30102_REG_SPO2_CFG  0x0Au
#define MAX30102_REG_LED1_PA   0x0Cu   /* LED vermelho     */
#define MAX30102_REG_LED2_PA   0x0Du   /* LED infravermelho */
#define MAX30102_REG_PART_ID   0xFFu   /* deve ler 0x15    */

bool    max30102_init(void);
/** Lê até max amostras da FIFO. Retorna quantas foram lidas. */
uint8_t max30102_read_fifo(uint32_t *red, uint32_t *ir, uint8_t max);
void    max30102_shutdown(bool off);

#endif
