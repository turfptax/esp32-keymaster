"""
USB Serial <-> BLE transparent bridge.

Reads newline-delimited lines from USB-CDC (sys.stdin) via select.poll()
and forwards them as BLE TX notifications. Receives BLE RX writes and
writes them to USB-CDC (sys.stdout).

Protocol: transparent passthrough of UTF-8 newline-delimited messages.
Max 512 bytes per message. MTU-aware chunking on TX.
"""

import sys
import select
import asyncio

_MAX_MSG = 512           # Maximum message length in bytes
_CHUNK_SIZE = 200        # Safe BLE notification chunk size
_POLL_TIMEOUT_MS = 100   # select.poll() timeout
_BUF_OVERFLOW = 1024     # Clear buffer if this big without \n


class SerialBridge:
    def __init__(self, ble_server, on_activity=None):
        """
        Args:
            ble_server: BLEServer instance for BLE TX.
            on_activity: Optional callback(direction, message) for display/LED.
                         direction is "serial_in" or "ble_in".
        """
        self._ble = ble_server
        self._on_activity = on_activity
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)
        self._buf = bytearray()
        print("Bridge: initialized")

    def on_ble_receive(self, server, message, connection):
        """BLE RX -> USB Serial. Wired as BLEServer's on_receive callback."""
        line = message if message.endswith("\n") else message + "\n"
        sys.stdout.write(line)
        if self._on_activity:
            try:
                self._on_activity("ble_in", message.rstrip("\n"))
            except Exception:
                pass

    async def run(self):
        """USB Serial -> BLE TX async loop. Add to asyncio.gather()."""
        print("Bridge: serial reader started")
        while True:
            events = self._poll.poll(_POLL_TIMEOUT_MS)
            if events:
                self._read_available()
            self._process_buffer()
            await asyncio.sleep_ms(0)  # Yield to event loop

    def _read_available(self):
        """Read all available bytes from stdin into the buffer."""
        while True:
            try:
                ch = sys.stdin.read(1)
                if ch:
                    if isinstance(ch, str):
                        self._buf.extend(ch.encode("utf-8"))
                    else:
                        self._buf.extend(ch)
                else:
                    break
            except Exception:
                break
            # Check if more data waiting
            if not self._poll.poll(0):
                break

    def _process_buffer(self):
        """Extract complete newline-delimited lines and send via BLE."""
        # Safety: prevent runaway buffer
        if len(self._buf) > _BUF_OVERFLOW and b"\n" not in self._buf:
            print("Bridge: buffer overflow, clearing")
            self._buf = bytearray()
            return

        while b"\n" in self._buf:
            idx = self._buf.index(b"\n")
            line_bytes = bytes(self._buf[:idx + 1])  # Include \n
            self._buf = self._buf[idx + 1:]

            if len(line_bytes) > _MAX_MSG:
                line_bytes = line_bytes[:_MAX_MSG - 1] + b"\n"

            self._send_ble(line_bytes)

    def _send_ble(self, data_bytes):
        """Send bytes via BLE TX with MTU-aware chunking."""
        if not self._ble.connected:
            return

        if self._on_activity:
            try:
                preview = data_bytes[:40].decode("utf-8", "replace").rstrip("\n")
                self._on_activity("serial_in", preview)
            except Exception:
                pass

        if len(data_bytes) <= _CHUNK_SIZE:
            self._ble.send_raw(data_bytes)
        else:
            offset = 0
            while offset < len(data_bytes):
                end = min(offset + _CHUNK_SIZE, len(data_bytes))
                self._ble.send_raw(data_bytes[offset:end])
                offset = end
