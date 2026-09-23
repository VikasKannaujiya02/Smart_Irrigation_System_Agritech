"""
Hardware test: SX1278 transmit path.

Sends a single test packet and reports success/failure based on TxDone.
Run on the transmitting Raspberry Pi.

Usage:
    python3 drivers/test_sx1278_tx.py "hello field sensor"
"""

import sys

from sx1278 import SX1278, SX1278Error


def main() -> int:
    message = sys.argv[1] if len(sys.argv) > 1 else "SX1278 TX test packet"
    payload = message.encode("utf-8")

    radio = SX1278(bus=0, device=0, reset_pin=25, dio0_pin=24)
    try:
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
            tx_power_dbm=17,
        )

        radio.begin_packet()
        radio.write(payload)
        radio.end_packet(timeout=5.0)

        print(f"PASS: transmitted {len(payload)} bytes: {message!r}")
        return 0

    except SX1278Error as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        radio.close()


if __name__ == "__main__":
    sys.exit(main())
