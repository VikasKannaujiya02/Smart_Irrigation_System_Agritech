"""
SX1278 LoRa Driver
AI Smart Irrigation Digital Twin

Production-grade, dependency-minimal SX1278 (RFM95/96/97/98-class) driver
for Raspberry Pi. Communicates directly over SPI using ``spidev`` and
controls the RESET / DIO0 lines using ``RPi.GPIO``. No third-party LoRa
library (LoRaRF, gpiod, gpiozero, pyLoRa, etc.) is used or required.

Hardware wiring assumed by the defaults (overridable in the constructor):
    SPI bus   : 0
    SPI CS    : 0   (CE0)
    RESET     : GPIO25 (BCM numbering)
    DIO0      : GPIO24 (BCM numbering)

All register addresses and bit-field values are taken from the
Semtech SX1276/77/78/79 datasheet (Rev. 7, DS_SX1276-7-8-9_W_APP V7).

This module intentionally exposes the same construction signature as the
original bootstrap driver (``bus``, ``device``, ``reset_pin``) so it is a
drop-in replacement; DIO0 support and all LoRa functionality are additive.
"""

from __future__ import annotations

import time
from enum import IntEnum
from typing import List, Optional

try:
    import spidev
    import RPi.GPIO as GPIO
except ImportError:
    spidev = None
    GPIO = None



# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #

class SX1278Error(Exception):
    """Base exception for all SX1278 driver errors."""


class SX1278NotFoundError(SX1278Error):
    """Raised when the chip version register does not match the expected ID."""


class SX1278TimeoutError(SX1278Error):
    """Raised when a TX or RX operation exceeds its allotted timeout."""


class SX1278StateError(SX1278Error):
    """Raised when an operation is attempted in an invalid driver state."""


# --------------------------------------------------------------------------- #
# Register map (SX1276/77/78/79 datasheet)
# --------------------------------------------------------------------------- #

class Register(IntEnum):
    FIFO = 0x00
    OP_MODE = 0x01
    FRF_MSB = 0x06
    FRF_MID = 0x07
    FRF_LSB = 0x08
    PA_CONFIG = 0x09
    PA_RAMP = 0x0A
    OCP = 0x0B
    LNA = 0x0C
    FIFO_ADDR_PTR = 0x0D
    FIFO_TX_BASE_ADDR = 0x0E
    FIFO_RX_BASE_ADDR = 0x0F
    FIFO_RX_CURRENT_ADDR = 0x10
    IRQ_FLAGS_MASK = 0x11
    IRQ_FLAGS = 0x12
    RX_NB_BYTES = 0x13
    PKT_SNR_VALUE = 0x19
    PKT_RSSI_VALUE = 0x1A
    RSSI_VALUE = 0x1B
    MODEM_CONFIG_1 = 0x1D
    MODEM_CONFIG_2 = 0x1E
    SYMB_TIMEOUT_LSB = 0x1F
    PREAMBLE_MSB = 0x20
    PREAMBLE_LSB = 0x21
    PAYLOAD_LENGTH = 0x22
    MAX_PAYLOAD_LENGTH = 0x23
    HOP_PERIOD = 0x24
    MODEM_CONFIG_3 = 0x26
    FREQ_ERROR_MSB = 0x28
    DETECT_OPTIMIZE = 0x31
    INVERT_IQ = 0x33
    DETECTION_THRESHOLD = 0x37
    SYNC_WORD = 0x39
    INVERT_IQ2 = 0x3B
    DIO_MAPPING_1 = 0x40
    VERSION = 0x42
    PA_DAC = 0x4D


class OpMode(IntEnum):
    """RegOpMode (0x01) mode bits, LongRangeMode bit (bit 7) always set to 1."""
    SLEEP = 0x00
    STANDBY = 0x01
    FSTX = 0x02
    TX = 0x03
    FSRX = 0x04
    RXCONTINUOUS = 0x05
    RXSINGLE = 0x06
    CAD = 0x07


LONG_RANGE_MODE = 0x80  # Bit 7 of RegOpMode: 1 = LoRa mode

# RegIrqFlags (0x12) bit masks
IRQ_RX_TIMEOUT = 0x80
IRQ_RX_DONE = 0x40
IRQ_PAYLOAD_CRC_ERROR = 0x20
IRQ_VALID_HEADER = 0x10
IRQ_TX_DONE = 0x08
IRQ_CAD_DONE = 0x04
IRQ_FHSS_CHANGE_CHANNEL = 0x02
IRQ_CAD_DETECTED = 0x01

FXOSC = 32_000_000.0          # SX1278 crystal frequency (Hz)
FSTEP = FXOSC / (2 ** 19)      # Frequency synthesizer step size (Hz)

# Valid LoRa bandwidths in kHz -> RegModemConfig1 Bw[3:0] value
_BANDWIDTH_MAP = {
    7_800: 0x00,
    10_400: 0x01,
    15_600: 0x02,
    20_800: 0x03,
    31_250: 0x04,
    41_700: 0x05,
    62_500: 0x06,
    125_000: 0x07,
    250_000: 0x08,
    500_000: 0x09,
}

_EXPECTED_VERSION = 0x12  # SX1276/77/78/79 silicon revision reported by RegVersion


class SX1278:
    """
    Driver for the SX1278 LoRa transceiver on Raspberry Pi.

    Example:
        radio = SX1278(bus=0, device=0, reset_pin=25, dio0_pin=24)
        radio.open()
        radio.begin()
        radio.configure(
            frequency=433_000_000,
            bandwidth=125_000,
            spreading_factor=7,
            coding_rate=5,
            preamble_length=8,
            sync_word=0x12,
            crc=True,
        )
        radio.begin_packet()
        radio.write(b"hello")
        radio.end_packet()

        radio.receive()
        if radio.available():
            payload = radio.read()

        radio.close()
    """

    REG_VERSION = Register.VERSION  # kept for backward compatibility

    def __init__(
        self,
        bus: int = 0,
        device: int = 0,
        reset_pin: int = 25,
        dio0_pin: int = 24,
        spi_speed_hz: int = 5_000_000,
    ) -> None:
        self.bus = bus
        self.device = device
        self.reset_pin = reset_pin
        self.dio0_pin = dio0_pin
        self.spi_speed_hz = spi_speed_hz

        self._is_open = False
        self._mode: OpMode = OpMode.SLEEP
        self._implicit_header = False
        self._tx_payload_length = 0

        if GPIO is not None:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.reset_pin, GPIO.OUT)
            GPIO.setup(self.dio0_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        if spidev is not None:
            self.spi = spidev.SpiDev()
        else:
            # Mock for Windows
            class MockSPI:
                def open(self, *args): pass
                def close(self): pass
                def xfer2(self, *args): return [0, 0]
            self.spi = MockSPI()

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "SX1278":
        self.open()
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Low-level SPI / GPIO
    # ------------------------------------------------------------------ #

    def open(self) -> None:
        """Open the SPI device and configure bus parameters."""
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.spi_speed_hz
        self.spi.mode = 0
        self._is_open = True

    def close(self) -> None:
        """Put the radio to sleep, release SPI, and clean up GPIO."""
        try:
            if self._is_open:
                self.sleep()
        except SX1278Error:
            pass
        finally:
            if self._is_open:
                self.spi.close()
                self._is_open = False
            if GPIO is not None:
                GPIO.cleanup((self.reset_pin, self.dio0_pin))

    def reset(self) -> None:
        """Hardware reset per datasheet section 7.2.2 (>=100 us low pulse)."""
        if GPIO is not None:
            GPIO.output(self.reset_pin, GPIO.LOW)
            time.sleep(0.001)
            GPIO.output(self.reset_pin, GPIO.HIGH)
            time.sleep(0.01)

    def _require_open(self) -> None:
        if not self._is_open:
            raise SX1278StateError("SPI bus is not open; call open() first.")

    def read_register(self, address: int) -> int:
        """Read a single 8-bit register."""
        self._require_open()
        response = self.spi.xfer2([address & 0x7F, 0x00])
        return response[1]

    def write_register(self, address: int, value: int) -> None:
        """Write a single 8-bit register."""
        self._require_open()
        self.spi.xfer2([address | 0x80, value & 0xFF])

    def _read_fifo(self, length: int) -> List[int]:
        self._require_open()
        buf = [Register.FIFO & 0x7F] + [0x00] * length
        response = self.spi.xfer2(buf)
        return response[1:]

    def _write_fifo(self, data: bytes) -> None:
        self._require_open()
        buf = [Register.FIFO | 0x80] + list(data)
        self.spi.xfer2(buf)

    def read_version(self) -> int:
        """Read RegVersion (0x42); returns 0x12 on genuine SX1276/77/78/79 silicon."""
        return self.read_register(Register.VERSION)

    # ------------------------------------------------------------------ #
    # Radio initialization / mode control
    # ------------------------------------------------------------------ #

    def begin(self) -> None:
        """
        Reset the chip, verify its identity, and switch it into LoRa
        Sleep mode, then Standby mode, ready for configuration.
        """
        self._require_open()
        self.reset()

        version = self.read_version()
        if version != _EXPECTED_VERSION:
            raise SX1278NotFoundError(
                f"Unexpected RegVersion 0x{version:02X}, expected "
                f"0x{_EXPECTED_VERSION:02X}. Check wiring/SPI bus/device."
            )

        # Must be in Sleep mode to switch LongRangeMode bit.
        self.write_register(Register.OP_MODE, LONG_RANGE_MODE | OpMode.SLEEP)
        time.sleep(0.01)
        self._mode = OpMode.SLEEP

        # Default FIFO base addresses: TX and RX each own the full 256-byte
        # FIFO for simplicity (non-overlapping single-packet operation).
        self.write_register(Register.FIFO_TX_BASE_ADDR, 0x00)
        self.write_register(Register.FIFO_RX_BASE_ADDR, 0x00)

        # Map DIO0 -> RxDone in RX modes / TxDone in TX mode (00 in both cases).
        self.write_register(Register.DIO_MAPPING_1, 0x00)

        # RegLna: default LNA gain (max gain, boost off).
        self.write_register(Register.LNA, 0x23)

        self.standby()

    def sleep(self) -> None:
        """Enter LoRa Sleep mode (lowest power)."""
        self._set_mode(OpMode.SLEEP)

    def standby(self) -> None:
        """Enter LoRa Standby mode."""
        self._set_mode(OpMode.STANDBY)

    def _set_mode(self, mode: OpMode) -> None:
        self.write_register(Register.OP_MODE, LONG_RANGE_MODE | mode)
        self._mode = mode

    # ------------------------------------------------------------------ #
    # LoRa modem configuration
    # ------------------------------------------------------------------ #

    def set_frequency(self, frequency_hz: float) -> None:
        """Set the carrier frequency in Hz (e.g. 433_000_000 for 433 MHz)."""
        frf = int(round(frequency_hz / FSTEP))
        self.write_register(Register.FRF_MSB, (frf >> 16) & 0xFF)
        self.write_register(Register.FRF_MID, (frf >> 8) & 0xFF)
        self.write_register(Register.FRF_LSB, frf & 0xFF)

    def set_bandwidth(self, bandwidth_hz: int) -> None:
        """Set the LoRa signal bandwidth in Hz. Must be one of the datasheet values."""
        if bandwidth_hz not in _BANDWIDTH_MAP:
            valid = ", ".join(str(b) for b in sorted(_BANDWIDTH_MAP))
            raise ValueError(f"Invalid bandwidth {bandwidth_hz}. Valid values (Hz): {valid}")

        bw_bits = _BANDWIDTH_MAP[bandwidth_hz]
        config1 = self.read_register(Register.MODEM_CONFIG_1)
        config1 = (config1 & 0x0F) | (bw_bits << 4)
        self.write_register(Register.MODEM_CONFIG_1, config1)

    def set_coding_rate(self, denominator: int) -> None:
        """Set the LoRa coding rate 4/denominator, denominator in [5..8]."""
        if denominator not in (5, 6, 7, 8):
            raise ValueError("Coding rate denominator must be 5, 6, 7 or 8 (i.e. 4/5..4/8).")

        cr_bits = denominator - 4
        config1 = self.read_register(Register.MODEM_CONFIG_1)
        config1 = (config1 & 0xF1) | (cr_bits << 1)
        self.write_register(Register.MODEM_CONFIG_1, config1)

    def set_spreading_factor(self, spreading_factor: int) -> None:
        """Set the LoRa spreading factor, valid range 6..12."""
        if not 6 <= spreading_factor <= 12:
            raise ValueError("Spreading factor must be between 6 and 12.")

        if spreading_factor == 6:
            # SF6 requires implicit header mode and special detection settings.
            self.write_register(Register.DETECTION_THRESHOLD, 0x0C)
            self.write_register(Register.DETECT_OPTIMIZE, 0x05)
        else:
            self.write_register(Register.DETECTION_THRESHOLD, 0x0A)
            self.write_register(Register.DETECT_OPTIMIZE, 0x03)

        config2 = self.read_register(Register.MODEM_CONFIG_2)
        config2 = (config2 & 0x0F) | (spreading_factor << 4)
        self.write_register(Register.MODEM_CONFIG_2, config2)

    def set_preamble_length(self, length: int) -> None:
        """Set the LoRa preamble length in symbols (datasheet default 8)."""
        if not 6 <= length <= 65535:
            raise ValueError("Preamble length must be between 6 and 65535 symbols.")
        self.write_register(Register.PREAMBLE_MSB, (length >> 8) & 0xFF)
        self.write_register(Register.PREAMBLE_LSB, length & 0xFF)

    def set_sync_word(self, sync_word: int) -> None:
        """Set the LoRa sync word (0x34 = LoRaWAN public, 0x12 = private/default)."""
        if not 0 <= sync_word <= 0xFF:
            raise ValueError("Sync word must be a single byte (0-255).")
        self.write_register(Register.SYNC_WORD, sync_word)

    def set_crc(self, enabled: bool) -> None:
        """Enable or disable the payload CRC."""
        config2 = self.read_register(Register.MODEM_CONFIG_2)
        if enabled:
            config2 |= 0x04
        else:
            config2 &= ~0x04
        self.write_register(Register.MODEM_CONFIG_2, config2)

    def set_implicit_header(self, enabled: bool) -> None:
        """Enable (True) or disable (False, default explicit header) header mode."""
        config1 = self.read_register(Register.MODEM_CONFIG_1)
        if enabled:
            config1 |= 0x01
        else:
            config1 &= ~0x01
        self.write_register(Register.MODEM_CONFIG_1, config1)
        self._implicit_header = enabled

    def configure(
        self,
        frequency: float = 433_000_000,
        bandwidth: int = 125_000,
        spreading_factor: int = 7,
        coding_rate: int = 5,
        preamble_length: int = 8,
        sync_word: int = 0x12,
        crc: bool = True,
        tx_power_dbm: int = 17,
    ) -> None:
        """
        Convenience method applying a full LoRa modem configuration.
        Must be called after begin() and while the radio is in Standby mode.
        """
        self.standby()
        self.set_frequency(frequency)
        self.set_bandwidth(bandwidth)
        self.set_spreading_factor(spreading_factor)
        self.set_coding_rate(coding_rate)
        self.set_preamble_length(preamble_length)
        self.set_sync_word(sync_word)
        self.set_crc(crc)
        self.set_tx_power(tx_power_dbm)

        # RegModemConfig3: AGC auto-on (bit 2), LowDataRateOptimize off by default.
        self.write_register(Register.MODEM_CONFIG_3, 0x04)

    def set_tx_power(self, dbm: int) -> None:
        """
        Set TX output power in dBm using the PA_BOOST pin path
        (RFM95/96/97/98 modules route the PA output through PA_BOOST).
        Valid range: 2..20 dBm.
        """
        if not 2 <= dbm <= 20:
            raise ValueError("TX power must be between 2 and 20 dBm (PA_BOOST path).")

        if dbm > 17:
            # High power +20 dBm settings require PaDac boost and OCP raise.
            self.write_register(Register.PA_DAC, 0x87)
            self.write_register(Register.OCP, 0x3F)  # OCP trim ~240 mA
            output_power = dbm - 5
        else:
            self.write_register(Register.PA_DAC, 0x84)
            output_power = dbm - 2

        output_power = max(0, min(15, output_power))
        # PA_BOOST enabled (bit 7), max power (bits 6-4)=0x7, OutputPower bits 3-0.
        self.write_register(Register.PA_CONFIG, 0x80 | 0x70 | output_power)

    # ------------------------------------------------------------------ #
    # IRQ helpers
    # ------------------------------------------------------------------ #

    def _read_irq_flags(self) -> int:
        return self.read_register(Register.IRQ_FLAGS)

    def _clear_irq_flags(self, mask: int = 0xFF) -> None:
        self.write_register(Register.IRQ_FLAGS, mask)

    # ------------------------------------------------------------------ #
    # Transmit path
    # ------------------------------------------------------------------ #

    def begin_packet(self) -> None:
        """
        Prepare the radio to accept payload bytes for transmission.
        Must be followed by one or more write() calls and end_packet().
        """
        self.standby()
        self.write_register(Register.FIFO_ADDR_PTR, 0x00)
        self.write_register(Register.PAYLOAD_LENGTH, 0x00)
        self._tx_payload_length = 0

    def write(self, data: bytes) -> int:
        """
        Append bytes to the TX FIFO started by begin_packet().
        Returns the number of bytes written. Raises if payload would exceed
        the 255-byte SX1278 FIFO packet limit.
        """
        if self._tx_payload_length + len(data) > 255:
            raise ValueError("LoRa payload cannot exceed 255 bytes total.")

        self._write_fifo(data)
        self._tx_payload_length += len(data)
        self.write_register(Register.PAYLOAD_LENGTH, self._tx_payload_length)
        return len(data)

    def end_packet(self, timeout: float = 5.0) -> None:
        """
        Trigger transmission of the FIFO contents and block until TxDone
        or the timeout (seconds) elapses.
        """
        if self._tx_payload_length == 0:
            raise SX1278StateError("No payload written; call write() before end_packet().")

        self._clear_irq_flags()
        self.write_register(Register.DIO_MAPPING_1, 0x40)  # Map DIO0 to TxDone
        self._set_mode(OpMode.TX)

        deadline = time.monotonic() + timeout
        while True:
            if GPIO.input(self.dio0_pin) == GPIO.HIGH:
                break
            if (self._read_irq_flags() & IRQ_TX_DONE) != 0:
                break
            if time.monotonic() > deadline:
                self.standby()
                raise SX1278TimeoutError("Timed out waiting for TxDone.")
            time.sleep(0.001)

        self._clear_irq_flags(IRQ_TX_DONE)
        self.standby()

    # ------------------------------------------------------------------ #
    # Receive path
    # ------------------------------------------------------------------ #

    def receive(self, implicit_header_length: Optional[int] = None) -> None:
        """
        Put the radio into continuous receive mode.
        Pass implicit_header_length to switch into implicit-header mode
        (fixed-length packets, e.g. required for SF6); omit for explicit
        header mode (default, variable-length packets).
        """
        if implicit_header_length is not None:
            self.set_implicit_header(True)
            self.write_register(Register.PAYLOAD_LENGTH, implicit_header_length & 0xFF)
        else:
            self.set_implicit_header(False)

        self.write_register(Register.FIFO_RX_BASE_ADDR, 0x00)
        self._clear_irq_flags()
        self.write_register(Register.DIO_MAPPING_1, 0x00)  # Map DIO0 to RxDone
        self._set_mode(OpMode.RXCONTINUOUS)

    def available(self) -> bool:
        """
        Return True if a complete, CRC-valid packet is waiting to be read.
        A CRC-failed packet is discarded (flags cleared) and reported as
        not available.
        """
        flags = self._read_irq_flags()

        if (flags & IRQ_RX_DONE) == 0:
            return False

        if (flags & IRQ_PAYLOAD_CRC_ERROR) != 0:
            self._clear_irq_flags(IRQ_RX_DONE | IRQ_PAYLOAD_CRC_ERROR)
            return False

        return True

    def read(self, timeout: float = 0.0) -> bytes:
        """
        Read the received packet payload.

        If timeout > 0, blocks polling available() up to that many seconds
        and raises SX1278TimeoutError if no packet arrives in time. With
        timeout == 0 (default) it reads immediately, raising SX1278StateError
        if no packet is currently available (check available() first).
        """
        if timeout > 0:
            deadline = time.monotonic() + timeout
            while not self.available():
                if time.monotonic() > deadline:
                    raise SX1278TimeoutError("Timed out waiting for an incoming packet.")
                time.sleep(0.001)
        elif not self.available():
            raise SX1278StateError("No packet available; call available() first or pass timeout>0.")

        if self._implicit_header:
            length = self.read_register(Register.PAYLOAD_LENGTH)
        else:
            length = self.read_register(Register.RX_NB_BYTES)

        current_addr = self.read_register(Register.FIFO_RX_CURRENT_ADDR)
        self.write_register(Register.FIFO_ADDR_PTR, current_addr)

        payload = bytes(self._read_fifo(length))
        self._clear_irq_flags(IRQ_RX_DONE)
        return payload

    # ------------------------------------------------------------------ #
    # Monitoring
    # ------------------------------------------------------------------ #

    def rssi(self) -> int:
        """
        Return the current (instantaneous) RSSI in dBm.
        Uses RegRssiValue with the standard -164 dBm offset for the
        HF port (>= 779 MHz split point is handled by callers via
        packet_rssi() for the last-received-packet variant).
        """
        raw = self.read_register(Register.RSSI_VALUE)
        return raw - 157

    def packet_rssi(self) -> int:
        """Return the RSSI in dBm of the last received packet."""
        raw = self.read_register(Register.PKT_RSSI_VALUE)
        return raw - 157

    def packet_snr(self) -> float:
        """Return the SNR in dB of the last received packet."""
        raw = self.read_register(Register.PKT_SNR_VALUE)
        # RegPktSnrValue is signed, in steps of 0.25 dB (datasheet 5.5.5).
        if raw > 127:
            raw -= 256
        return raw / 4.0

    def irq_status(self) -> int:
        """Return the raw contents of RegIrqFlags (0x12)."""
        return self._read_irq_flags()

    @property
    def mode(self) -> OpMode:
        """Current operating mode as last set by this driver instance."""
        return self._mode
