"""LoRa SX1278 gateway transport abstraction."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Protocol

from communication.protocol_constants import MAX_PACKET_BYTES


class LoRaTransport(Protocol):
    """Minimal byte transport required by the gateway LoRa interface."""

    def read(self, size: int) -> bytes:
        """Read bytes from the LoRa radio."""

    def write(self, data: bytes) -> int:
        """Write bytes to the LoRa radio."""

    def close(self) -> None:
        """Close the LoRa radio transport."""


class LoRaRFSX1278Transport:
    """LoRaRF-backed SPI transport for the SX1278 radio on Raspberry Pi."""

    def __init__(
        self,
        *,
        frequency_hz: int = 868_000_000,
        spi_bus: int = 0,
        spi_cs: int = 0,
        spi_speed_hz: int = 7_800_000,
        reset_pin: int = 22,
        dio0_pin: int = -1,
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
        try:
            from LoRaRF import SX127x, LoRaSpi, LoRaGpio  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Hardware Validation Required: LoRaRF is required for SX1278 SPI communication") from exc

        self._timeout = timeout

        # Build SPI and GPIO objects required by the constructor-injection API.
        spi = LoRaSpi(spi_bus, spi_cs, spi_speed_hz)
        cs = LoRaGpio(0, spi_cs)
        reset = LoRaGpio(0, reset_pin)
        irq = LoRaGpio(0, dio0_pin) if dio0_pin >= 0 else None
        txen = LoRaGpio(0, tx_enable_pin) if tx_enable_pin >= 0 else None
        rxen = LoRaGpio(0, rx_enable_pin) if rx_enable_pin >= 0 else None

        self._radio = SX127x(spi, cs, reset, irq, txen, rxen)
        self._begin_radio()
        self._configure_radio(
            frequency_hz=frequency_hz,
            tx_power=tx_power,
            spreading_factor=spreading_factor,
            bandwidth_hz=bandwidth_hz,
            coding_rate=coding_rate,
            preamble_length=preamble_length,
            sync_word=sync_word,
        )

    def _begin_radio(self) -> None:
        begin_result = self._radio.begin()
        if begin_result is False:
            raise RuntimeError("Hardware Validation Required: SX1278 SPI radio did not initialize")

    def _configure_radio(
        self,
        *,
        frequency_hz: int,
        tx_power: int,
        spreading_factor: int,
        bandwidth_hz: int,
        coding_rate: int,
        preamble_length: int,
        sync_word: int,
    ) -> None:
        self._call_if_available("setFrequency", frequency_hz)
        self._call_if_available("setTxPower", tx_power, getattr(self._radio, "TX_POWER_PA_BOOST", 1))
        self._call_if_available("setLoRaModulation", spreading_factor, bandwidth_hz, coding_rate, False)
        self._call_if_available(
            "setLoRaPacket",
            getattr(self._radio, "HEADER_EXPLICIT", 0),
            preamble_length,
            255,
            True,
            False,
        )
        self._call_if_available("setSyncWord", sync_word)
        self._call_if_available("request")

    def read(self, size: int = MAX_PACKET_BYTES) -> bytes:
        """
        Receive one complete LoRa packet.
        Reads available bytes instead of waiting for fixed packet size.
        """

        if size <= 0:
            raise ValueError("size must be greater than zero")

        deadline = time.monotonic() + self._timeout
        received = bytearray()

        # Put radio into receive mode
        self._call_if_available("request")

        while time.monotonic() < deadline:

            self._call_if_available("wait", 0)

            available = self._available_bytes()

            if available > 0:

                for _ in range(min(available, size)):

                    value = self._radio.read()

                    if isinstance(value, bytes):
                        received.extend(value)
                    else:
                        received.append(int(value) & 0xFF)

                break

            time.sleep(0.01)

        return bytes(received[:size])

    def write(self, data: bytes) -> int:
        if not data:
            raise ValueError("data must not be empty")

        self._radio.beginPacket()
        self._write_payload(data)
        self._radio.endPacket()
        self._call_if_available("wait")
        self._call_if_available("request")
        return len(data)

    def close(self) -> None:
        self._call_if_available("sleep")

    def _write_payload(self, data: bytes) -> None:
        try:
            self._radio.write(list(data), len(data))
        except TypeError:
            try:
                self._radio.write(list(data))
            except TypeError:
                for value in data:
                    self._radio.write(value)

    def _available_bytes(self) -> int:
        available = self._radio.available()
        if isinstance(available, bool):
            return 1 if available else 0
        return int(available)

    def _call_if_available(self, method_name: str, *args: Any) -> Any:
        method = getattr(self._radio, method_name, None)
        if method is None:
            return None
        try:
            return method(*args)
        except TypeError:
            if args:
                return method()
            raise


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
                spi_speed_hz=int(os.getenv("SX1278_SPI_SPEED_HZ", "7800000")),
                reset_pin=int(os.getenv("SX1278_RESET_PIN", "25")),
                dio0_pin=int(os.getenv("SX1278_DIO0_PIN", os.getenv("SX1278_IRQ_PIN", "24"))),
                tx_enable_pin=int(os.getenv("SX1278_TX_ENABLE_PIN", "-1")),
                rx_enable_pin=int(os.getenv("SX1278_RX_ENABLE_PIN", "-1")),
                tx_power=int(os.getenv("SX1278_TX_POWER", "17")),
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