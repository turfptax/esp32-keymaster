import gc
import asyncio
from ble_server import BLEServer

print("main.py: starting application")

# Try to initialize the display. If it fails (wrong driver, missing file, etc.)
# we still want BLE to work -- just without screen output.
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


def _log(msg):
    """Log to display if available, always print to serial."""
    if display:
        display.log(msg)


def on_receive(server, message, connection):
    """Called when the phone sends data. Echoes it back for testing."""
    print("Received from phone:", message)
    _log("RX: " + message)
    server.send("Echo: " + message)
    _log("TX: Echo: " + message)


def on_status(event, detail=""):
    """Called on BLE state transitions. Updates the display."""
    if not display:
        return
    if event == "advertising":
        display.show_advertising()
    elif event == "connected":
        display.show_connected(detail)
    elif event == "disconnected":
        display.show_disconnected()
    elif event == "error":
        display.log("ERR: " + detail)
    # "rx" events are handled in on_receive for more context


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

    _log("Starting BLE...")

    server = BLEServer(
        device_name="KeyMaster",
        on_receive=on_receive,
        on_status=on_status,
    )
    _log("BLE server created")

    await server.run()


asyncio.run(main())
