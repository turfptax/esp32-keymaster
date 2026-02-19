"""
display_manager.py - BLE status display for Waveshare ESP32-S3-LCD-1.47
172x320 ST7789 SPI display in portrait mode.
"""

import gc
from machine import Pin, SPI
import st7789py as st7789
import vga1_8x16 as font


# --- Pin Configuration (Waveshare ESP32-S3-LCD-1.47) ---
_SPI_ID   = 2
_BAUDRATE = 40_000_000
_SCK      = 40
_MOSI     = 45
_CS       = 42
_DC       = 41
_RST      = 39
_BL       = 48

# --- Display Geometry ---
_WIDTH  = 172
_HEIGHT = 320

# Custom rotation table for 172x320
# Format: (madctl, width, height, xstart, ystart, needs_swap)
# X-offset = (240 - 172) / 2 = 34
_CUSTOM_ROTATIONS = (
    (0x00, 172, 320, 34, 0, False),   # Portrait
    (0x60, 320, 172, 0, 34, False),   # Landscape
    (0xC0, 172, 320, 34, 0, False),   # Portrait inverted
    (0xA0, 320, 172, 0, 34, False),   # Landscape inverted
)

# --- Layout Constants ---
_CHAR_W         = font.WIDTH                          # 8
_CHAR_H         = font.HEIGHT                         # 16
_CHARS_PER_LINE = _WIDTH // _CHAR_W                   # 21
_TITLE_H        = 2 * _CHAR_H                        # 32px (2 lines)
_SEP1_Y         = _TITLE_H                            # 32
_STATUS_Y       = _SEP1_Y + _CHAR_H                   # 48
_SEP2_Y         = _STATUS_Y + 2 * _CHAR_H             # 80
_LOG_Y          = _SEP2_Y + _CHAR_H                    # 96
_MAX_LOG_LINES  = (_HEIGHT - _LOG_Y) // _CHAR_H       # 14

# --- Colors (RGB565) ---
_TITLE_BG  = st7789.color565(0, 0, 80)                # Dark blue
_TITLE_FG  = st7789.WHITE
_SEP_COLOR = st7789.color565(60, 60, 60)               # Dark gray
_ADV_COLOR = st7789.YELLOW
_CONN_COLOR = st7789.GREEN
_DISC_COLOR = st7789.RED
_LOG_FG    = st7789.CYAN
_BG        = st7789.BLACK
_LABEL_FG  = st7789.WHITE


class DisplayManager:
    """High-level display wrapper for BLE status debugging."""

    def __init__(self):
        spi = SPI(
            _SPI_ID,
            baudrate=_BAUDRATE,
            sck=Pin(_SCK),
            mosi=Pin(_MOSI),
            miso=None,
        )
        self._tft = st7789.ST7789(
            spi,
            _WIDTH,
            _HEIGHT,
            cs=Pin(_CS, Pin.OUT),
            dc=Pin(_DC, Pin.OUT),
            reset=Pin(_RST, Pin.OUT),
            backlight=Pin(_BL, Pin.OUT),
            custom_rotations=_CUSTOM_ROTATIONS,
            rotation=0,
            color_order=st7789.BGR,
        )
        self._log_buf = []
        gc.collect()

    # --- Public API ---

    def show_startup(self):
        """Draw the initial screen with title, separators, and init status."""
        self._tft.fill(_BG)
        self._draw_title()
        self._draw_separator(_SEP1_Y)
        self._draw_status("Initializing...", _ADV_COLOR)
        self._draw_separator(_SEP2_Y)

    def show_advertising(self):
        """Update status zone to show advertising state."""
        self._draw_status("Advertising...", _ADV_COLOR)
        self.log("Advertising...")

    def show_connected(self, device_info=""):
        """Update status zone to show connected state."""
        self._draw_status("Connected", _CONN_COLOR)
        msg = "Connected"
        if device_info:
            msg += ": " + device_info[:10]
        self.log(msg)

    def show_disconnected(self):
        """Update status zone to show disconnected state."""
        self._draw_status("Disconnected", _DISC_COLOR)
        self.log("Disconnected")

    def log(self, message):
        """Add a message to the scrolling event log."""
        max_msg = _CHARS_PER_LINE - 2  # Room for "> " prefix
        if len(message) > max_msg:
            message = message[:max_msg]
        self._log_buf.append(message)
        if len(self._log_buf) > _MAX_LOG_LINES:
            self._log_buf.pop(0)
        self._draw_log()

    # --- Internal rendering ---

    def _draw_title(self):
        """Render the title zone (dark blue background, white text)."""
        self._tft.fill_rect(0, 0, _WIDTH, _TITLE_H, _TITLE_BG)
        self._center_text("KeyMaster", 0, _TITLE_FG, _TITLE_BG)
        self._center_text("BLE Server", _CHAR_H, _TITLE_FG, _TITLE_BG)

    def _draw_separator(self, y):
        """Draw a 1px horizontal separator line."""
        self._tft.hline(0, y, _WIDTH, _SEP_COLOR)

    def _draw_status(self, text, color):
        """Clear and redraw the status zone between the two separators."""
        # Clear the zone (between sep1 and sep2, excluding separator pixels)
        self._tft.fill_rect(0, _SEP1_Y + 1, _WIDTH, _SEP2_Y - _SEP1_Y - 1, _BG)
        # Draw "Status: " label in white
        label = "Status: "
        self._tft.text(font, label, 0, _STATUS_Y, _LABEL_FG, _BG)
        # Draw the status text in the appropriate color
        x_offset = len(label) * _CHAR_W
        self._tft.text(font, text, x_offset, _STATUS_Y, color, _BG)

    def _draw_log(self):
        """Redraw the entire log zone from the ring buffer."""
        # Clear log zone
        self._tft.fill_rect(0, _LOG_Y, _WIDTH, _HEIGHT - _LOG_Y, _BG)
        # Draw each entry
        for i, msg in enumerate(self._log_buf):
            y = _LOG_Y + i * _CHAR_H
            self._tft.text(font, "> " + msg, 0, y, _LOG_FG, _BG)

    def _center_text(self, string, y, fg, bg):
        """Draw text horizontally centered on the given y line."""
        x = (_WIDTH - len(string) * _CHAR_W) // 2
        self._tft.text(font, string, x, y, fg, bg)
