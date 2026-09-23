"""
Hardware test: SX1278 receive path.

Listens continuously and prints each received packet along with RSSI/SNR.
Run on the receiving Raspberry Pi. Stop with Ctrl+C.

Usage:
    python3 drivers/test_sx1278_rx.py
"""

import sys

from sx1278 import SX1278, SX1278Error


def main() -> int:
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
        )
        radio.receive()

        print("Listening for packets (Ctrl+C to stop)...")
        while True:
            try:
                payload = radio.read(timeout=10.0)
            except SX1278Error as exc:
                # Timeout is expected periodically while idle; keep listening.
                print(f"  ... {exc}")
                continue

            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                text = repr(payload)

            print(
                f"RX: {text!r} | RSSI={radio.packet_rssi()} dBm | "
                f"SNR={radio.packet_snr():.2f} dB"
            )

    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 0
    except SX1278Error as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        radio.close()


if __name__ == "__main__":
    sys.exit(main())
