"""
SD card manager for Waveshare ESP32-S3-LCD-1.47.

Handles SPI(1) init, mount/unmount, and basic file operations.
Pin mapping from Waveshare schematic:
    CLK  = GPIO 14
    MOSI = GPIO 15  (CMD)
    MISO = GPIO 16  (D0)
    CS   = GPIO 21  (D3)
"""

import os
import gc
from machine import Pin, SPI
from sdcard import SDCard


class SDManager:
    def __init__(self, sck=14, mosi=15, miso=16, cs=21, spi_id=1,
                 mount_point="/sd"):
        self._sck = sck
        self._mosi = mosi
        self._miso = miso
        self._cs_pin = cs
        self._spi_id = spi_id
        self._mount_point = mount_point
        self._spi = None
        self._sd = None
        self._mounted = False

    # ------------------------------------------------------------------
    # Mount / unmount
    # ------------------------------------------------------------------

    def mount(self):
        """Initialise SPI, create SDCard, and mount the filesystem.
        Returns True on success, False on failure (no card, etc.)."""
        try:
            self._spi = SPI(
                self._spi_id,
                baudrate=1_000_000,  # low speed for init
                sck=Pin(self._sck),
                mosi=Pin(self._mosi),
                miso=Pin(self._miso),
            )
            cs = Pin(self._cs_pin, Pin.OUT, value=1)
            self._sd = SDCard(self._spi, cs, baudrate=10_000_000)

            # Create mount point directory if needed
            try:
                os.mkdir(self._mount_point)
            except OSError:
                pass  # already exists

            os.mount(self._sd, self._mount_point)
            self._mounted = True
            print("SD: mounted at", self._mount_point)
            gc.collect()
            return True
        except OSError as e:
            print("SD: mount failed:", e)
            self._cleanup()
            return False
        except Exception as e:
            print("SD: unexpected error:", e)
            self._cleanup()
            return False

    def unmount(self):
        """Unmount the filesystem and release SPI."""
        if self._mounted:
            try:
                os.umount(self._mount_point)
                print("SD: unmounted")
            except OSError as e:
                print("SD: unmount error:", e)
            self._mounted = False
        self._cleanup()

    def _cleanup(self):
        """Release SPI resources."""
        if self._spi:
            try:
                self._spi.deinit()
            except Exception:
                pass
            self._spi = None
        self._sd = None
        self._mounted = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_mounted(self):
        return self._mounted

    @property
    def mount_point(self):
        return self._mount_point

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def list_files(self, path=None):
        """List files at the given path (defaults to mount point)."""
        if not self._mounted:
            print("SD: not mounted")
            return []
        if path is None:
            path = self._mount_point
        try:
            return os.listdir(path)
        except OSError as e:
            print("SD: list error:", e)
            return []

    def file_exists(self, path):
        """Check whether a file exists on the SD card."""
        if not self._mounted:
            return False
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def read_file(self, path):
        """Read an entire file and return its contents as a string."""
        if not self._mounted:
            print("SD: not mounted")
            return None
        try:
            with open(path, "r") as f:
                return f.read()
        except OSError as e:
            print("SD: read error:", e)
            return None

    def write_file(self, path, data):
        """Write a string to a file (overwrites if exists).
        Returns True on success."""
        if not self._mounted:
            print("SD: not mounted")
            return False
        try:
            with open(path, "w") as f:
                f.write(data)
            return True
        except OSError as e:
            print("SD: write error:", e)
            return False

    def append_file(self, path, data):
        """Append a string to a file. Returns True on success."""
        if not self._mounted:
            print("SD: not mounted")
            return False
        try:
            with open(path, "a") as f:
                f.write(data)
            return True
        except OSError as e:
            print("SD: append error:", e)
            return False

    def free_space(self):
        """Return (free_bytes, total_bytes) for the SD card, or None."""
        if not self._mounted:
            return None
        try:
            stat = os.statvfs(self._mount_point)
            block_size = stat[0]
            total_blocks = stat[2]
            free_blocks = stat[3]
            return (free_blocks * block_size, total_blocks * block_size)
        except OSError as e:
            print("SD: statvfs error:", e)
            return None
