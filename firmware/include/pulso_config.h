/**
 * pulso_config.h — Parâmetros gerais da braçadeira Pulso.
 *
 * Todos os tempos em milissegundos. Os limites de alerta aqui são os
 * mesmos usados pelo servidor (servidor/pulso_server/rules.py) e devem
 * ser calibrados no piloto.
 */
#ifndef PULSO_CONFIG_H
#define PULSO_CONFIG_H

/* ---------- Ciclo de envio ---------- */
#define CFG_TX_PERIOD_MS          5000u   /* pacote periódico a cada 5 s     */
#define CFG_PPG_SAMPLE_HZ         100u    /* taxa de amostragem do MAX30102   */
#define CFG_PPG_WINDOW_S          4u      /* janela usada no cálculo de BPM   */
#define CFG_ACC_SAMPLE_HZ         50u     /* taxa do acelerômetro LIS2DH12    */

/* ---------- Botão SOS ---------- */
#define CFG_SOS_HOLD_MS           2000u   /* segurar 2 s para acionar          */
#define CFG_SOS_RETRY_MS          3000u   /* reenvia o SOS até receber ACK     */
#define CFG_SOS_MAX_RETRIES       40u     /* ~2 min de tentativas              */

/* ---------- Limites locais (redundância do servidor) ---------- */
#define CFG_SPO2_CRITICAL         90u     /* % */
#define CFG_BPM_LOW               40u
#define CFG_BPM_HIGH              150u
#define CFG_BATT_LOW_PCT          15u
#define CFG_BATT_CRITICAL_PCT     5u      /* abaixo: só SOS + localização      */

/* ---------- UWB ---------- */
#define CFG_UWB_MAX_ANCHORS       8u
#define CFG_UWB_TAG_HEIGHT_M      1.2f    /* altura média da braçadeira (m)     */
#define CFG_UWB_ANCHOR_HEIGHT_M   3.0f    /* âncoras no teto da galeria (m)     */

/* ---------- Detecção de queda ---------- */
#define CFG_FALL_FREEFALL_G       0.40f
#define CFG_FALL_FREEFALL_MS      80u
#define CFG_FALL_IMPACT_G         2.50f
#define CFG_FALL_IMPACT_WINDOW_MS 1000u
#define CFG_FALL_STILL_MS         2000u

/* ---------- LoRaWAN ---------- */
#define CFG_LORA_PORT_UPLINK      1u
#define CFG_LORA_PORT_DOWNLINK    2u
#define CFG_DL_CMD_SOS_ACK        0x01u   /* operador clicou "Recebido"        */
#define CFG_DL_CMD_SOS_CLOSE      0x02u   /* operador encerrou o caso          */
#define CFG_DL_CMD_VIBRATE        0x03u   /* chamar atenção do trabalhador     */

#endif /* PULSO_CONFIG_H */
