/**
 * hal_rak3172.c — HAL da placa real (RAK3172 / STM32WLE5CC).
 *
 * Para usar: crie um projeto no STM32CubeIDE a partir do exemplo
 * "LoRaWAN_End_Node" do pacote STM32CubeWL, copie as pastas include/,
 * src/ e drivers/ deste firmware e este arquivo, e chame app_init() /
 * app_tick() no lugar do loop do exemplo (ver README.md).
 *
 * Pinos (conforme o diagrama elétrico):
 *   PA0  SOS (entrada, pull-up, EXTI para acordar)   PB5  LED vermelho
 *   PB6  LED verde                                   PB7  motor (MOSFET Q2)
 *   PA9  CHG do BQ24075                              PA10 ALRT do MAX17048
 *   PA11/PA12 I2C2 (SDA/SCL)                         PA4-PA7 SPI1 (DWM3000)
 *   PB8  IRQ UWB   PB9 RST UWB   PB10 WAKE UWB       PB12 INT MAX30102  PB13 INT LIS2DH12
 */
#ifdef STM32WLxx

#include "hal.h"
#include "pulso_config.h"
#include "main.h"            /* gerado pelo CubeMX: handles hi2c2, hspi1, hrtc */
#include "LmHandler.h"       /* pilha LoRaWAN do STM32CubeWL                   */
#include "stm32_timer.h"
#include "deca_device_api.h" /* driver oficial Qorvo DW3000                    */
#include <string.h>

extern I2C_HandleTypeDef hi2c2;
extern RTC_HandleTypeDef hrtc;

/* ---------------- tempo ---------------- */
uint32_t hal_millis(void) { return HAL_GetTick(); }

uint32_t hal_unix_time(void)
{
    SysTime_t t = SysTimeGet();          /* sincronizado pela rede LoRaWAN (DeviceTimeReq) */
    return t.Seconds;
}

void hal_sleep_until(uint32_t wake_ms)
{
    uint32_t now = HAL_GetTick();
    if ((int32_t)(wake_ms - now) <= 1) return;
    /* entra em Stop2; o RTC (wakeup timer) ou um EXTI (SOS, sensores) acordam o MCU */
    HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, (wake_ms - now) * 2048u / 1000u, RTC_WAKEUPCLOCK_RTCCLK_DIV16, 0);
    HAL_SuspendTick();
    HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFI);
    SystemClock_Config();
    HAL_ResumeTick();
    HAL_RTCEx_DeactivateWakeUpTimer(&hrtc);
}

uint16_t hal_device_id(void) { return (uint16_t)(HAL_GetUIDw0() ^ HAL_GetUIDw1() ^ HAL_GetUIDw2()); }

/* ---------------- GPIO ---------------- */
bool hal_sos_pressed(void) { return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0) == GPIO_PIN_RESET; }
bool hal_is_charging(void) { return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET; }

void hal_led(hal_led_t led, bool on)
{
    HAL_GPIO_WritePin(GPIOB, led == LED_RED ? GPIO_PIN_5 : GPIO_PIN_6, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static UTIMER_Object_t vib_timer;
static void vib_off(void *ctx) { (void)ctx; HAL_GPIO_WritePin(GPIOB, GPIO_PIN_7, GPIO_PIN_RESET); }

void hal_vibrate(uint16_t ms)
{
    static bool init;
    if (!init) { UTIL_TIMER_Create(&vib_timer, 0, UTIL_TIMER_ONESHOT, vib_off, NULL); init = true; }
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_7, GPIO_PIN_SET);
    UTIL_TIMER_SetPeriod(&vib_timer, ms);
    UTIL_TIMER_Start(&vib_timer);
}

/* ---------------- I²C ---------------- */
bool hal_i2c_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, size_t len)
{
    return HAL_I2C_Mem_Write(&hi2c2, (uint16_t)(addr7 << 1), reg, I2C_MEMADD_SIZE_8BIT,
                             (uint8_t *)buf, (uint16_t)len, 10) == HAL_OK;
}

bool hal_i2c_read(uint8_t addr7, uint8_t reg, uint8_t *buf, size_t len)
{
    return HAL_I2C_Mem_Read(&hi2c2, (uint16_t)(addr7 << 1), reg, I2C_MEMADD_SIZE_8BIT,
                            buf, (uint16_t)len, 10) == HAL_OK;
}

/* ---------------- UWB (DWM3000) ---------------- */
/* Tabela de âncoras da zona atual, enviada pelo servidor por downlink (porta 3)
 * quando a braçadeira muda de zona. */
static uwb_anchor_t zone_anchors[CFG_UWB_MAX_ANCHORS];
static uint8_t      zone_anchor_count;

extern bool uwb_ds_twr(uint16_t anchor_id, float *dist_m);   /* uwb_twr.c, baseado nos exemplos Qorvo */

uint8_t hal_uwb_ranging(uwb_anchor_t *a, float *d, uint8_t max)
{
    uint8_t n = 0;
    for (uint8_t i = 0; i < zone_anchor_count && n < max; i++) {
        float dist;
        if (uwb_ds_twr(zone_anchors[i].id, &dist)) { a[n] = zone_anchors[i]; d[n] = dist; n++; }
    }
    dwt_entersleep(DWT_DW_IDLE);   /* desliga o rádio UWB até o próximo ciclo */
    return n;
}

/* ---------------- LoRaWAN ---------------- */
static uint8_t dl_buf[8];
static size_t  dl_len;

/* chamado pela pilha LmHandler ao receber um downlink */
void pulso_on_rx(LmHandlerAppData_t *data, LmHandlerRxParams_t *params)
{
    (void)params;
    if (data == NULL || data->BufferSize == 0) return;
    if (data->Port == CFG_LORA_PORT_DOWNLINK) {
        dl_len = data->BufferSize > sizeof dl_buf ? sizeof dl_buf : data->BufferSize;
        memcpy(dl_buf, data->Buffer, dl_len);
    } else if (data->Port == 3) {     /* tabela de âncoras: id(u16) x,y,z(i16 dm) = 8 bytes cada */
        zone_anchor_count = 0;
        for (uint8_t i = 0; i + 8 <= data->BufferSize && zone_anchor_count < CFG_UWB_MAX_ANCHORS; i += 8) {
            const uint8_t *b = &data->Buffer[i];
            uwb_anchor_t *an = &zone_anchors[zone_anchor_count++];
            an->id = (uint16_t)(b[0] | b[1] << 8);
            an->pos.x = (int16_t)(b[2] | b[3] << 8) / 10.0f;
            an->pos.y = (int16_t)(b[4] | b[5] << 8) / 10.0f;
            an->pos.z = (int16_t)(b[6] | b[7] << 8) / 10.0f;
        }
    }
}

bool hal_lora_send(uint8_t port, const uint8_t *buf, size_t len, bool confirmed)
{
    static uint8_t tx[32];
    memcpy(tx, buf, len);
    LmHandlerAppData_t app = { .Port = port, .BufferSize = (uint8_t)len, .Buffer = tx };
    return LmHandlerSend(&app, confirmed ? LORAMAC_HANDLER_CONFIRMED_MSG : LORAMAC_HANDLER_UNCONFIRMED_MSG,
                         false) == LORAMAC_HANDLER_SUCCESS;
}

size_t hal_lora_poll_downlink(uint8_t *buf, size_t max)
{
    if (!dl_len) return 0;
    size_t n = dl_len < max ? dl_len : max;
    memcpy(buf, dl_buf, n);
    dl_len = 0;
    return n;
}

#endif /* STM32WLxx */
