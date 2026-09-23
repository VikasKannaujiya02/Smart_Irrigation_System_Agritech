from drivers.sx1278 import SX1278

radio = SX1278()

try:
    radio.open()

    print("SPI Opened")

    radio.reset()

    version = radio.read_version()

    print(f"Version Register = 0x{version:02X}")

finally:
    radio.close()
