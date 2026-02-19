# ESP32 KeyMaster

BLE server for the Waveshare ESP32-S3-LCD-1.47 development board. Provides a secure Bluetooth Low Energy interface for sharing API keys and sensitive data between devices. Includes a 172x320 ST7789 display for real-time status monitoring and OTA updates via WiFi using [ugit](https://github.com/turfptax/ugit).

## Hardware

- [Waveshare ESP32-S3-LCD-1.47](https://www.waveshare.com/esp32-s3-lcd-1.47.htm) (ESP32-S3, 8MB PSRAM, 16MB Flash, BLE 5, 172x320 ST7789 display)

## Features

- BLE GATT server with TX/RX characteristics (echo test)
- 172x320 color display showing connection status and event log
- OTA updates from this GitHub repo on every boot via ugit
- Graceful fallback -- works offline, works without display, works without ugit

## First-Time Setup

### 1. Flash MicroPython

```bash
pip install esptool mpremote
# Hold BOOT, press RESET, release both to enter boot mode
esptool.py --chip esp32s3 --port COM4 erase_flash
esptool.py --chip esp32s3 --port COM4 write_flash -z 0 ESP32_GENERIC_S3-SPIRAM_OCT-*.bin
```

Download firmware from: https://micropython.org/download/ESP32_GENERIC_S3/

### 2. Install Libraries

```bash
mpremote connect COM4 mip install aioble
mpremote connect COM4 mip install github:turfptax/ugit
```

### 3. Upload Project Files

```bash
mpremote connect COM4 cp boot.py :boot.py
mpremote connect COM4 cp main.py :main.py
mpremote connect COM4 cp ble_server.py :ble_server.py
mpremote connect COM4 cp display_manager.py :display_manager.py
mpremote connect COM4 cp st7789py.py :st7789py.py
mpremote connect COM4 cp vga1_8x16.py :vga1_8x16.py
```

### 4. Configure OTA Updates

Run once in the MicroPython REPL:

```python
import ugit
ugit.create_config(
    ssid='YourWiFiSSID',
    password='YourWiFiPassword',
    user='turfptax',
    repository='esp32-keymaster'
)
```

After this, the device auto-syncs with this repo on every boot.

### 5. Reset and Run

Press the RESET button. The device will:
1. Check for updates via WiFi (if ugit is configured)
2. Start the BLE server
3. Show status on the display
4. Advertise as "KeyMaster"

## Testing BLE

1. Install [nRF Connect](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp) on your phone
2. Scan and connect to "KeyMaster"
3. Expand the service (`a0e1b2c3-...4e50`)
4. Subscribe to notifications on TX characteristic (`...4e51`)
5. Write text to RX characteristic (`...4e52`)
6. You should see your message echoed back

## Project Structure

| File | Purpose |
|------|---------|
| `boot.py` | System init + OTA update check via ugit |
| `main.py` | Application entry point, wires display to BLE |
| `ble_server.py` | BLE GATT server using aioble |
| `display_manager.py` | ST7789 display wrapper with status zones |
| `st7789py.py` | ST7789 display driver (pure Python) |
| `vga1_8x16.py` | Bitmap font (8x16 pixels) |

## License

MIT
