"""LoRa SX1278 gateway transport abstraction."""

from __future__ import annotations

import logging
import os
from typing import Protocol

from ..communication.protocol_constants import MAX_PACKET_BYTES


class LoRaTransport(Protocol):
    """Minimal byte transport required by the gateway LoRa interface."""

    def read(self, size: int) -> bytes:
        """Read bytes from the LoRa radio."""

    def write(self, data: bytes) -> int:
        """Write bytes to the LoRa radio."""

    def close(self) -> None:
        """Close the LoRa radio transport."""


class LoRaRFSX1278Transport:
    """SX1278 SPI transport for the Raspberry Pi, backed by drivers.sx1278.SX1278."""

    def __init__(
        self,
        *,
        frequency_hz: int = 868_000_000,
        spi_bus: int = 0,
        spi_cs: int = 0,
        spi_speed_hz: int = 7_800_000,
        reset_pin: int = 25,
        dio0_pin: int = 24,
        tx_enable_pin: int = -1,
        rx_enable_pin: int = -1,
        tx_power: int = 17,
        spreading_factor: int = 7,
        bandwidth_hz: int = 125_000,
        coding_rate: int = 5,
        preamble_length: int = 8,
        sync_word: int = 0x12,
        timeout: float = 2.0,
    ) -> None:
        from ..drivers.sx1278 import SX1278

        self._timeout = timeout

        self._radio = SX1278(
            bus=spi_bus,
            device=spi_cs,
            reset_pin=reset_pin,
            dio0_pin=dio0_pin,
            spi_speed_hz=spi_speed_hz,
        )

        self._radio.open()
        self._radio.begin()

        self._radio.configure(
            frequency=frequency_hz,
            bandwidth=bandwidth_hz,
            spreading_factor=spreading_factor,
            coding_rate=coding_rate,
            preamble_length=preamble_length,
            sync_word=sync_word,
            crc=True,
            tx_power_dbm=tx_power,
        )

        self._radio.receive()

    def read(self, size: int = MAX_PACKET_BYTES) -> bytes:
        """Receive one complete LoRa packet using the driver's own timeout."""
        if size <= 0:
            raise ValueError("size must be greater than zero")

        from ..drivers.sx1278 import SX1278TimeoutError

        try:
            payload = self._radio.read(timeout=self._timeout)
        except SX1278TimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

        return bytes(payload[:size])

    def write(self, data: bytes) -> int:
        if not data:
            raise ValueError("data must not be empty")

        self._radio.begin_packet()
        self._radio.write(data)
        self._radio.end_packet()
        self._radio.receive()
        return len(data)

    def close(self) -> None:
        self._radio.close()


class LoRaInterface:
    """Sends and receives framed packet bytes through the SX1278 LoRa gateway."""

    def __init__(
        self,
        serial_interface: LoRaTransport | None = None,
        logger: logging.Logger | None = None,
        port: str | None = None,
        baudrate: int | None = None,
        timeout: float = 2.0,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        if serial_interface is not None:
            self._transport = serial_interface
            self._hardware_ready = True
            return

        if port or baudrate:
            raise RuntimeError("Hardware Validation Required: SX1278 serial transport has been replaced by LoRaRF SPI")

        spi_enabled = os.getenv("SX1278_SPI_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
        if spi_enabled:
            self._transport = LoRaRFSX1278Transport(
                frequency_hz=int(os.getenv("SX1278_FREQUENCY_HZ", os.getenv("LORA_FREQUENCY_HZ", "868000000"))),
                spi_bus=int(os.getenv("SX1278_SPI_BUS", "0")),
                spi_cs=int(os.getenv("SX1278_SPI_CS", "0")),
                spi_speed_hz=int(os.getenv("SX1278_SPI_SPEED_HZ", "1000000")),
                reset_pin=int(os.getenv("SX1278_RESET_PIN", "25")),
                dio0_pin=int(os.getenv("SX1278_DIO0_PIN", os.getenv("SX1278_IRQ_PIN", "24"))),
                tx_enable_pin=int(os.getenv("SX1278_TX_ENABLE_PIN", "-1")),
                rx_enable_pin=int(os.getenv("SX1278_RX_ENABLE_PIN", "-1")),
                tx_power=int(os.getenv("SX1278_TX_POWER", "20")),
                spreading_factor=int(os.getenv("SX1278_SPREADING_FACTOR", "7")),
                bandwidth_hz=int(os.getenv("SX1278_BANDWIDTH_HZ", "125000")),
                coding_rate=int(os.getenv("SX1278_CODING_RATE", "5")),
                preamble_length=int(os.getenv("SX1278_PREAMBLE_LENGTH", "8")),
                sync_word=int(os.getenv("SX1278_SYNC_WORD", "18"), 0),
                timeout=timeout,
            )
            self._hardware_ready = True
        else:
            self._transport = None
            self._hardware_ready = False

    def send_packet(self, raw_packet: bytes) -> None:
        """Transmit a serialized protocol packet."""
        if self._transport is None:
            raise RuntimeError("Hardware Validation Required: enable SX1278 SPI transport before transmitting")
        written = self._transport.write(raw_packet)
        if written != len(raw_packet):
            raise IOError("LoRa transport did not accept the full packet")
        self._logger.info("LoRa packet transmitted bytes=%s", written)

    def receive_packet(self) -> bytes:
        """Receive a serialized LoRa packet."""
        if self._transport is None:
            raise RuntimeError(
                "Hardware Validation Required: enable SX1278 SPI transport before receiving"
            )

        raw_packet = self._transport.read(MAX_PACKET_BYTES)

        if not raw_packet:
            raise TimeoutError("No LoRa packet received before timeout")

        self._logger.info("LoRa packet received bytes=%s", len(raw_packet))
        return raw_packet

    @property
    def hardware_ready(self) -> bool:
        """Return whether a real SX1278 SPI transport is configured."""
        return self._hardware_ready

    def close(self) -> None:
        """Close the underlying transport."""
        if self._transport is not None:
            self._transport.close()
