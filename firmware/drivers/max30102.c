#include "max30102.h"
#include "hal.h"

static bool wr(uint8_t reg, uint8_t v) { return hal_i2c_write(MAX30102_ADDR, reg, &v, 1); }

bool max30102_init(void)
{
    uint8_t id = 0;
    if (!hal_i2c_read(MAX30102_ADDR, MAX30102_REG_PART_ID, &id, 1) || id != 0x15u) return false;

    wr(MAX30102_REG_MODE, 0x40);            /* reset                                     */
    wr(MAX30102_REG_FIFO_WR, 0); wr(MAX30102_REG_FIFO_OVF, 0); wr(MAX30102_REG_FIFO_RD, 0);
    wr(MAX30102_REG_FIFO_CFG, 0x5F);        /* média de 4 amostras, rollover, almost-full=15 */
    wr(MAX30102_REG_SPO2_CFG, 0x27);        /* faixa 4096 nA, 100 amostras/s, 18 bits    */
    wr(MAX30102_REG_LED1_PA, 0x24);         /* ~7 mA no LED vermelho                     */
    wr(MAX30102_REG_LED2_PA, 0x24);         /* ~7 mA no LED infravermelho                */
    wr(MAX30102_REG_INTR_EN1, 0x80);        /* interrupção "FIFO quase cheia" → PB12     */
    wr(MAX30102_REG_MODE, 0x03);            /* modo SpO2 (vermelho + IR)                 */
    return true;
}

uint8_t max30102_read_fifo(uint32_t *red, uint32_t *ir, uint8_t max)
{
    uint8_t wp = 0, rp = 0;
    hal_i2c_read(MAX30102_ADDR, MAX30102_REG_FIFO_WR, &wp, 1);
    hal_i2c_read(MAX30102_ADDR, MAX30102_REG_FIFO_RD, &rp, 1);
    uint8_t n = (uint8_t)((wp - rp) & 0x1Fu);
    if (n > max) n = max;
    for (uint8_t i = 0; i < n; i++) {
        uint8_t b[6];
        if (!hal_i2c_read(MAX30102_ADDR, MAX30102_REG_FIFO_DATA, b, 6)) return i;
        red[i] = (((uint32_t)b[0] << 16) | ((uint32_t)b[1] << 8) | b[2]) & 0x3FFFFu;
        ir[i]  = (((uint32_t)b[3] << 16) | ((uint32_t)b[4] << 8) | b[5]) & 0x3FFFFu;
    }
    return n;
}

void max30102_shutdown(bool off) { wr(MAX30102_REG_MODE, off ? 0x83 : 0x03); }
