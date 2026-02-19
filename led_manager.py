"""
NeoPixel (WS2812B) LED manager for Waveshare ESP32-S3-LCD-1.47.

Single RGB LED on GPIO 38.  Provides named colour presets for BLE
status events plus direct colour control.
"""

from machine import Pin
from neopixel import NeoPixel


class LEDManager:
    def __init__(self, pin=38, n=1, brightness=0.3):
        """Initialise the NeoPixel strip.

        Args:
            pin: GPIO number (default 38 for Waveshare board).
            n: Number of LEDs (1 for built-in).
            brightness: 0.0 - 1.0 master brightness scaler.
        """
        self._np = NeoPixel(Pin(pin, Pin.OUT), n)
        self._n = n
        self._brightness = max(0.0, min(1.0, brightness))
        self.off()
        print("LED: NeoPixel initialized on GPIO", pin)

    # ------------------------------------------------------------------
    # Low-level
    # ------------------------------------------------------------------

    def set_color(self, r, g, b):
        """Set all LEDs to the given RGB colour (0-255 per channel).
        Brightness scaling is applied automatically."""
        br = self._brightness
        r = int(r * br)
        g = int(g * br)
        b = int(b * br)
        for i in range(self._n):
            self._np[i] = (r, g, b)
        self._np.write()

    def off(self):
        """Turn off all LEDs."""
        for i in range(self._n):
            self._np[i] = (0, 0, 0)
        self._np.write()

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        self._brightness = max(0.0, min(1.0, value))

    # ------------------------------------------------------------------
    # Named status presets (match BLE events)
    # ------------------------------------------------------------------

    def status_startup(self):
        """White -- device is booting."""
        self.set_color(255, 255, 255)

    def status_advertising(self):
        """Blue -- BLE is advertising, waiting for connection."""
        self.set_color(0, 0, 255)

    def status_connected(self):
        """Green -- BLE device connected."""
        self.set_color(0, 255, 0)

    def status_disconnected(self):
        """Red -- BLE device disconnected."""
        self.set_color(255, 0, 0)

    def status_error(self):
        """Bright red -- an error occurred."""
        self.set_color(255, 0, 0)

    def status_sd_activity(self):
        """Yellow -- SD card read/write in progress."""
        self.set_color(255, 200, 0)

    def status_rx(self):
        """Cyan -- data received over BLE."""
        self.set_color(0, 255, 255)
