"""
Hardware test: SX1278 presence / SPI sanity check.

Run directly on a Raspberry Pi with the SX1278 module wired to:
    SPI bus 0, CS0, RESET=GPIO25, DIO0=GPIO24

Usage:
    python3 drivers/test_sx1278_detect.py
"""

import sys

from sx1278 import SX1278, SX1278NotFoundError


def main() -> int:
    radio = SX1278(bus=0, device=0, reset_pin=25, dio0_pin=24)
    try:
        radio.open()
        radio.reset()
        version = radio.read_version()
        print(f"RegVersion = 0x{version:02X}")

        if version != 0x12:
            print("FAIL: unexpected chip version, check wiring/SPI settings.")
            return 1

        print("PASS: SX1278 detected successfully.")
        return 0

    except SX1278NotFoundError as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        radio.close()


if __name__ == "__main__":
    sys.exit(main())
