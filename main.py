import gc
import asyncio
from ble_server import BLEServer

print("main.py: starting application")

# ---------------------------------------------------------------
# Hardware init -- each peripheral is optional; failures are caught
# so the BLE server always starts.
# ---------------------------------------------------------------

# Display
display = None
try:
    from display_manager import DisplayManager
    display = DisplayManager()
    display.show_startup()
    display.log("Display initialized")
    gc.collect()
    print("main.py: display initialized OK")
except Exception as e:
    print("main.py: display init FAILED:", e)
    import sys
    sys.print_exception(e)

# NeoPixel LED
led = None
try:
    from led_manager import LEDManager
    led = LEDManager(pin=38, brightness=0.3)
    led.status_startup()
    gc.collect()
    print("main.py: LED initialized OK")
except Exception as e:
    print("main.py: LED init FAILED:", e)

# SD card
sd = None
try:
    from sd_manager import SDManager
    sd = SDManager(sck=14, mosi=15, miso=16, cs=21, spi_id=1)
    if sd.mount():
        info = sd.free_space()
        if info:
            free_mb = info[0] / 1_048_576
            total_mb = info[1] / 1_048_576
            print("main.py: SD card {:.1f}/{:.1f} MB free".format(free_mb, total_mb))
            if display:
                display.log("SD: {:.0f}/{:.0f}MB".format(free_mb, total_mb))
        files = sd.list_files()
        print("main.py: SD files:", files)
    else:
        sd = None  # mount failed, treat as unavailable
    gc.collect()
except Exception as e:
    print("main.py: SD init FAILED:", e)
    sd = None

# BOOT button
button = None
try:
    from button import ButtonManager
    button = ButtonManager(
        pin=0,
        on_press=lambda dur: _on_button_press(dur),
        on_long_press=lambda dur: _on_button_long_press(dur),
    )
    gc.collect()
    print("main.py: button initialized OK")
except Exception as e:
    print("main.py: button init FAILED:", e)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _log(msg):
    """Log to display if available, always print to serial."""
    if display:
        display.log(msg)


def _on_button_press(duration_ms):
    """Short press handler -- show device info."""
    print("Button short press: {}ms".format(duration_ms))
    _log("BTN: short {}ms".format(duration_ms))
    if sd and sd.is_mounted:
        _log("SD: mounted")
    else:
        _log("SD: not available")


def _on_button_long_press(duration_ms):
    """Long press handler -- placeholder for future functionality."""
    print("Button long press: {}ms".format(duration_ms))
    _log("BTN: long {}ms".format(duration_ms))


# ---------------------------------------------------------------
# BLE callbacks
# ---------------------------------------------------------------

def on_receive(server, message, connection):
    """Called when the phone sends data. Echoes it back for testing."""
    print("Received from phone:", message)
    _log("RX: " + message)
    if led:
        led.status_rx()
    server.send("Echo: " + message)
    _log("TX: Echo: " + message)


def on_status(event, detail=""):
    """Called on BLE state transitions. Updates display and LED."""
    if display:
        if event == "advertising":
            display.show_advertising()
        elif event == "connected":
            display.show_connected(detail)
        elif event == "disconnected":
            display.show_disconnected()
        elif event == "error":
            display.log("ERR: " + detail)
        # "rx" events are handled in on_receive for more context

    if led:
        if event == "advertising":
            led.status_advertising()
        elif event == "connected":
            led.status_connected()
        elif event == "disconnected":
            led.status_disconnected()
        elif event == "error":
            led.status_error()


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

async def main():
    print("=" * 40)
    print("  KeyMaster BLE Server")
    print("=" * 40)
    print()
    print("To test:")
    print("  1. Open nRF Connect on your phone")
    print("  2. Scan and connect to 'KeyMaster'")
    print("  3. Subscribe to notifications on TX (..4e51)")
    print("  4. Write text to RX (..4e52)")
    print("  5. You should see your text echoed back")
    print()
    if sd and sd.is_mounted:
        print("  SD card: mounted at", sd.mount_point)
    else:
        print("  SD card: not available")
    if led:
        print("  NeoPixel LED: active")
    if button:
        print("  BOOT button: monitored")
    print()

    _log("Starting BLE...")

    server = BLEServer(
        device_name="KeyMaster",
        on_receive=on_receive,
        on_status=on_status,
    )
    _log("BLE server created")

    # Gather all async tasks -- BLE server + button monitor
    tasks = [server.run()]
    if button:
        tasks.append(button.monitor())

    await asyncio.gather(*tasks)


asyncio.run(main())
