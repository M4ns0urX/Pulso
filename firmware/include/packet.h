/**
 * packet.h — Formato do pacote LoRa da Pulso (20 bytes, little-endian).
 *
 *  byte  campo        tipo    observação
 *  0     ver|tipo     u8      versão (4 bits altos) | tipo (4 bits baixos)
 *  1-2   device_id    u16
 *  3-6   timestamp    u32     segundos (Unix)
 *  7     bpm          u8      0 = inválido
 *  8     spo2         u8      %, 0 = inválido
 *  9-10  x            i16     decímetros
 *  11-12 y            i16     decímetros
 *  13-14 z            i16     decímetros (negativo = abaixo da superfície)
 *  15    bateria      u8      %
 *  16    flags        u8      ver PKT_FLAG_*
 *  17    seq          u8      contador de pacotes
 *  18-19 crc16        u16     CRC-16/CCITT-FALSE dos bytes 0..17
 *
 * O mesmo formato é implementado em Python em digital-twin/pulso_twin/packet.py.
 */
#ifndef PULSO_PACKET_H
#define PULSO_PACKET_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define PKT_SIZE          20u
#define PKT_VERSION       1u

typedef enum {
    PKT_TYPE_PERIODIC = 0,
    PKT_TYPE_SOS      = 1,
    PKT_TYPE_EVENT    = 2,   /* queda, bateria crítica etc. */
} pkt_type_t;

#define PKT_FLAG_SOS         0x01u
#define PKT_FLAG_FALL        0x02u
#define PKT_FLAG_CHARGING    0x04u
#define PKT_FLAG_LOW_BATT    0x08u
#define PKT_FLAG_NO_CONTACT  0x10u   /* sensor óptico sem contato com a pele */
#define PKT_FLAG_SOS_ACKED   0x20u

typedef struct {
    uint8_t  type;
    uint16_t device_id;
    uint32_t timestamp;
    uint8_t  bpm;
    uint8_t  spo2;
    int16_t  x_dm, y_dm, z_dm;
    uint8_t  battery;
    uint8_t  flags;
    uint8_t  seq;
} pulso_packet_t;

uint16_t pkt_crc16(const uint8_t *data, size_t len);
void     pkt_encode(const pulso_packet_t *p, uint8_t out[PKT_SIZE]);
/** Retorna false se o CRC ou a versão não conferem. */
bool     pkt_decode(const uint8_t in[PKT_SIZE], pulso_packet_t *p);

#endif /* PULSO_PACKET_H */
