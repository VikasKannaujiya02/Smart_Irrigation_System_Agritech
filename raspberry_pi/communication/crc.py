"""CRC-16/CCITT-FALSE implementation for LoRa packets."""

from __future__ import annotations


CRC16_POLY = 0x1021
CRC16_INIT = 0xFFFF


def calculate_crc16(data: bytes) -> int:
    """Return CRC-16/CCITT-FALSE for packet bytes excluding the CRC field."""
    crc = CRC16_INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def verify_crc16(data: bytes, expected_crc: int) -> bool:
    """Return True when packet bytes match the expected CRC."""
    return calculate_crc16(data) == expected_crc

