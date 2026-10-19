"""Formato do pacote LoRa da Pulso (20 bytes). Espelho de firmware/src/packet.c."""
from __future__ import annotations

import struct
from dataclasses import dataclass

PKT_SIZE = 20
PKT_VERSION = 1

TYPE_PERIODIC, TYPE_SOS, TYPE_EVENT = 0, 1, 2

FLAG_SOS = 0x01
FLAG_FALL = 0x02
FLAG_CHARGING = 0x04
FLAG_LOW_BATT = 0x08
FLAG_NO_CONTACT = 0x10
FLAG_SOS_ACKED = 0x20

# Downlinks (porta 2)
DL_SOS_ACK = 0x01
DL_SOS_CLOSE = 0x02
DL_VIBRATE = 0x03

_FMT = "<BHIBBhhhBBB"  # 18 bytes + CRC


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (igual ao firmware)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


class PacketError(ValueError):
    pass


@dataclass
class Packet:
    type: int
    device_id: int
    timestamp: int
    bpm: int
    spo2: int
    x: float  # metros
    y: float
    z: float
    battery: int
    flags: int
    seq: int

    def encode(self) -> bytes:
        body = struct.pack(
            _FMT,
            (PKT_VERSION << 4) | (self.type & 0x0F),
            self.device_id & 0xFFFF,
            self.timestamp & 0xFFFFFFFF,
            max(0, min(255, int(round(self.bpm)))),
            max(0, min(255, int(round(self.spo2)))),
            int(round(self.x * 10)),
            int(round(self.y * 10)),
            int(round(self.z * 10)),
            max(0, min(100, int(round(self.battery)))),
            self.flags & 0xFF,
            self.seq & 0xFF,
        )
        return body + struct.pack("<H", crc16(body))

    @classmethod
    def decode(cls, raw: bytes) -> "Packet":
        if len(raw) != PKT_SIZE:
            raise PacketError(f"tamanho inválido: {len(raw)} bytes")
        if raw[0] >> 4 != PKT_VERSION:
            raise PacketError("versão desconhecida")
        (crc,) = struct.unpack("<H", raw[18:20])
        if crc != crc16(raw[:18]):
            raise PacketError("CRC não confere")
        v, dev, ts, bpm, spo2, x, y, z, bat, flags, seq = struct.unpack(_FMT, raw[:18])
        return cls(v & 0x0F, dev, ts, bpm, spo2, x / 10, y / 10, z / 10, bat, flags, seq)

    @property
    def sos(self) -> bool:
        return bool(self.flags & FLAG_SOS)

    @property
    def fall(self) -> bool:
        return bool(self.flags & FLAG_FALL)
