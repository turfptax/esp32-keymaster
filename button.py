"""
BOOT button handler for Waveshare ESP32-S3-LCD-1.47.

GPIO 0 -- active LOW with internal pull-up.
Provides async monitoring with debounce and short/long press detection.
"""

import asyncio
import time
from machine import Pin


class ButtonManager:
    def __init__(self, pin=0, on_press=None, on_long_press=None,
                 on_very_long_press=None):
        """
        Args:
            pin: GPIO number (default 0 = BOOT button).
            on_press: callback(duration_ms) for short presses (<1 s).
            on_long_press: callback(duration_ms) for long presses (1-3 s).
            on_very_long_press: callback(duration_ms) for very long presses (>=3 s).
        """
        self._pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self._on_press = on_press
        self._on_long_press = on_long_press
        self._on_very_long_press = on_very_long_press
        self._debounce_ms = 50
        self._long_press_ms = 1000
        self._very_long_press_ms = 3000
        print("Button: initialized on GPIO", pin)

    @property
    def is_pressed(self):
        """True when the button is currently held down (active LOW)."""
        return self._pin.value() == 0

    @property
    def on_press(self):
        return self._on_press

    @on_press.setter
    def on_press(self, callback):
        self._on_press = callback

    @property
    def on_long_press(self):
        return self._on_long_press

    @on_long_press.setter
    def on_long_press(self, callback):
        self._on_long_press = callback

    @property
    def on_very_long_press(self):
        return self._on_very_long_press

    @on_very_long_press.setter
    def on_very_long_press(self, callback):
        self._on_very_long_press = callback

    async def monitor(self):
        """Run forever, detecting button presses.

        Designed to be added to asyncio.gather() alongside other tasks.
        """
        print("Button: monitor started")
        while True:
            try:
                # Wait for button press (active LOW)
                if self._pin.value() == 0:
                    # Debounce -- wait and re-check
                    await asyncio.sleep_ms(self._debounce_ms)
                    if self._pin.value() != 0:
                        # False trigger
                        continue

                    # Button is genuinely pressed -- time the hold
                    press_start = time.ticks_ms()

                    # Wait for release
                    while self._pin.value() == 0:
                        await asyncio.sleep_ms(20)

                    duration = time.ticks_diff(time.ticks_ms(), press_start)
                    print("Button: press {}ms".format(duration))

                    if duration >= self._very_long_press_ms:
                        if self._on_very_long_press:
                            self._on_very_long_press(duration)
                    elif duration >= self._long_press_ms:
                        if self._on_long_press:
                            self._on_long_press(duration)
                    else:
                        if self._on_press:
                            self._on_press(duration)

            except Exception as e:
                print("Button: monitor error:", e)

            await asyncio.sleep_ms(50)
