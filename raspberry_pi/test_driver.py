from drivers.sx1278 import SX1278

radio = SX1278()

try:
    print("=" * 50)
    print("SX1278 DRIVER TEST")
    print("=" * 50)

    radio.open()
    print("[PASS] SPI Open")

    radio.begin()
    print("[PASS] Radio Begin")

    radio.set_frequency(433000000)
    print("[PASS] Frequency")

    radio.set_tx_power(17)
    print("[PASS] TX Power")

    radio.set_spreading_factor(7)
    print("[PASS] Spreading Factor")

    radio.set_bandwidth(125000)
    print("[PASS] Bandwidth")

    radio.set_coding_rate(5)
    print("[PASS] Coding Rate")

    radio.set_sync_word(0x12)
    print("[PASS] Sync Word")

    radio.set_crc(True)
    print("[PASS] CRC")

    radio.standby()
    print("[PASS] Standby")

    radio.sleep()
    print("[PASS] Sleep")

    print("\nALL CONFIGURATION TESTS PASSED")

except Exception as e:
    print("\nTEST FAILED")
    print(type(e).__name__)
    print(e)

finally:
    try:
        radio.close()
        print("[PASS] Driver Closed")
    except Exception:
        pass