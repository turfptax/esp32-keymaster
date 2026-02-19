# boot.py -- runs once at power-on before main.py
#
# IMPORTANT: ESP32-S3 uses native USB-CDC. The time.sleep(2) below lets
# USB enumerate before anything can crash. Without it, a boot crash makes
# the device invisible (no COM port) and requires a full reflash.
#
# First-Time Setup Instructions:
#   1. pip install esptool mpremote
#   2. Download MicroPython ESP32-S3 SPIRAM_OCT firmware from:
#      https://micropython.org/download/ESP32_GENERIC_S3/
#   3. Enter boot mode: Hold BOOT, press RESET, release both
#   4. esptool.py --chip esp32s3 --port COM4 erase_flash
#   5. esptool.py --chip esp32s3 --port COM4 write_flash -z 0 <firmware.bin>
#   6. Install libraries:
#      mpremote connect COM4 mip install aioble
#      mpremote connect COM4 mip install github:turfptax/ugit
#   7. Configure ugit (run once in REPL):
#      import ugit
#      ugit.create_config(ssid='WiFiName', password='WiFiPass',
#                         user='turfptax', repository='esp32-keymaster',
#                         ignore=['/lib', '/ble_secrets.json'])
#   8. After ugit is configured, the device auto-updates from GitHub on boot.

import time
time.sleep(2)  # Let USB-CDC enumerate -- prevents bricking on crash

try:
    import gc
    import esp
    esp.osdebug(None)
    gc.collect()
    print("boot.py: system ready")

    # OTA update check -- sync with GitHub repo before starting app
    import ugit
    print("boot.py: checking for updates...")
    ugit.wificonnect()
    ugit.pull_all()
    # If files changed, ugit calls machine.reset() and we never reach here.
    # If no changes, we continue to main.py normally.
    print("boot.py: up to date")
except ImportError:
    print("boot.py: ugit not installed, skipping update check")
except Exception as e:
    print("boot.py: error:", e)
    # Continue anyway -- run with existing code on flash
