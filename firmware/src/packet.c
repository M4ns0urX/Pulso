#include "packet.h"

uint16_t pkt_crc16(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000u) ? (uint16_t)((crc << 1) ^ 0x1021u) : (uint16_t)(crc << 1);
    }
    return crc;
}

static void put16(uint8_t *b, uint16_t v) { b[0] = (uint8_t)v; b[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *b, uint32_t v) { put16(b, (uint16_t)v); put16(b + 2, (uint16_t)(v >> 16)); }
static uint16_t get16(const uint8_t *b) { return (uint16_t)(b[0] | (b[1] << 8)); }
static uint32_t get32(const uint8_t *b) { return (uint32_t)get16(b) | ((uint32_t)get16(b + 2) << 16); }

void pkt_encode(const pulso_packet_t *p, uint8_t out[PKT_SIZE])
{
    out[0] = (uint8_t)((PKT_VERSION << 4) | (p->type & 0x0Fu));
    put16(&out[1], p->device_id);
    put32(&out[3], p->timestamp);
    out[7] = p->bpm;
    out[8] = p->spo2;
    put16(&out[9],  (uint16_t)p->x_dm);
    put16(&out[11], (uint16_t)p->y_dm);
    put16(&out[13], (uint16_t)p->z_dm);
    out[15] = p->battery;
    out[16] = p->flags;
    out[17] = p->seq;
    put16(&out[18], pkt_crc16(out, 18));
}

bool pkt_decode(const uint8_t in[PKT_SIZE], pulso_packet_t *p)
{
    if ((in[0] >> 4) != PKT_VERSION) return false;
    if (get16(&in[18]) != pkt_crc16(in, 18)) return false;
    p->type      = in[0] & 0x0Fu;
    p->device_id = get16(&in[1]);
    p->timestamp = get32(&in[3]);
    p->bpm       = in[7];
    p->spo2      = in[8];
    p->x_dm      = (int16_t)get16(&in[9]);
    p->y_dm      = (int16_t)get16(&in[11]);
    p->z_dm      = (int16_t)get16(&in[13]);
    p->battery   = in[15];
    p->flags     = in[16];
    p->seq       = in[17];
    return true;
}
