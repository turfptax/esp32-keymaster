# boot.py -- runs once at power-on before main.py
#
# IMPORTANT: ESP32-S3 uses native USB-CDC. The time.sleep(2) below lets
# USB enumerate before anything can crash. Without it, a boot crash makes
# the device invisible (no COM port) and requires a full reflash.
#
# To update from GitHub, run manually in REPL:
#   import ugit; ugit.wificonnect(); ugit.pull_all()

import time
time.sleep(2)  # Let USB-CDC enumerate -- prevents bricking on crash

import gc
import esp
esp.osdebug(None)
gc.collect()

print("boot.py: system ready")
