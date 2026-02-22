"""
KeyMaster MCP Bridge Server

Connects to the ESP32 KeyMaster via USB serial and provides MCP tools
for AI agents to communicate with the Pi Zero 2 W through the BLE bridge.

Data flow:
    AI Agent -> MCP Server -> USB Serial -> ESP32 -> BLE -> Pi Zero 2 W

Configuration (environment variables):
    KEYMASTER_PORT    Serial port (e.g. COM4, /dev/ttyACM0). Auto-detects if unset.
    KEYMASTER_BAUD    Baud rate (default: 115200)
    KEYMASTER_TIMEOUT Response timeout in seconds (default: 5)
"""

import os
import sys
import json
import time
import threading
from collections import deque

import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PORT = os.environ.get("KEYMASTER_PORT", "")
_BAUD = int(os.environ.get("KEYMASTER_BAUD", "115200"))
_TIMEOUT = float(os.environ.get("KEYMASTER_TIMEOUT", "5"))

# ESP32-S3 USB-CDC vendor ID
_ESP32_S3_VID = 0x303A

# ---------------------------------------------------------------------------
# Serial bridge (computer <-> ESP32 USB)
# ---------------------------------------------------------------------------


class _SerialBridge:
    """Manages the serial connection to the ESP32 and background reading."""

    def __init__(self):
        self._ser = None
        self._lock = threading.Lock()
        self._rx_queue = deque(maxlen=500)
        self._reader_thread = None

    @property
    def is_connected(self):
        return self._ser is not None and self._ser.is_open

    def connect(self, port=None, baud=None):
        """Open the serial port. Auto-detects ESP32 if port is None."""
        if self.is_connected:
            return

        port = port or _PORT or self._find_port()
        baud = baud or _BAUD
        if not port:
            raise ConnectionError(
                "ESP32 not found. Set KEYMASTER_PORT env var "
                "(e.g. COM4 or /dev/ttyACM0) or plug in the device."
            )

        self._ser = serial.Serial(port, baud, timeout=0.1)
        # Give ESP32 bridge a moment to settle after port open
        time.sleep(0.5)
        self._ser.reset_input_buffer()

        # Start background reader
        if self._reader_thread is None or not self._reader_thread.is_alive():
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True
            )
            self._reader_thread.start()

    def disconnect(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def send(self, message):
        """Send a newline-delimited message."""
        self._ensure_connected()
        if not message.endswith("\n"):
            message += "\n"
        encoded = message.encode("utf-8")
        if len(encoded) > 512:
            raise ValueError("Message too long (max 512 bytes)")
        with self._lock:
            self._ser.write(encoded)

    def send_and_wait(self, message, timeout=None, settle=0.4):
        """Send a message and collect response lines.

        After the first response line arrives, waits an additional `settle`
        seconds for more lines before returning.
        """
        timeout = timeout or _TIMEOUT
        t0 = time.time()

        # Drain stale messages
        self._rx_queue.clear()

        self.send(message)

        lines = []
        deadline = t0 + timeout
        first_at = None

        while time.time() < deadline:
            # Collect new messages
            while self._rx_queue:
                ts, text = self._rx_queue.popleft()
                if ts >= t0:
                    lines.append(text)
                    if first_at is None:
                        first_at = time.time()

            # If we have responses and settle window elapsed, done
            if first_at is not None and (time.time() - first_at) >= settle:
                # Final drain
                while self._rx_queue:
                    ts, text = self._rx_queue.popleft()
                    if ts >= t0:
                        lines.append(text)
                break

            time.sleep(0.05)

        return lines

    def read_pending(self):
        """Return all buffered messages without sending anything."""
        lines = []
        while self._rx_queue:
            _ts, text = self._rx_queue.popleft()
            lines.append(text)
        return lines

    @property
    def port_name(self):
        if self._ser:
            return self._ser.port
        return None

    @property
    def buffered_count(self):
        return len(self._rx_queue)

    # -- internals --

    def _ensure_connected(self):
        if not self.is_connected:
            self.connect()

    def _find_port(self):
        """Auto-detect an ESP32-S3 USB-CDC port."""
        for p in serial.tools.list_ports.comports():
            if p.vid == _ESP32_S3_VID:
                return p.device
            if p.description and "ESP32" in p.description.upper():
                return p.device
        return None

    def _reader_loop(self):
        """Background thread: read serial lines into the queue."""
        buf = b""
        while True:
            try:
                if self._ser and self._ser.is_open:
                    chunk = self._ser.read(512)
                    if chunk:
                        buf += chunk
                        while b"\n" in buf:
                            idx = buf.index(b"\n")
                            line = buf[:idx].decode("utf-8", errors="replace").strip()
                            buf = buf[idx + 1:]
                            if line:
                                self._rx_queue.append((time.time(), line))
                else:
                    time.sleep(0.2)
            except serial.SerialException:
                # Port disconnected
                time.sleep(1.0)
            except Exception:
                time.sleep(0.5)


# Singleton bridge instance
_bridge = _SerialBridge()

# ---------------------------------------------------------------------------
# MCP server and tools
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "KeyMaster Bridge",
    instructions=(
        "Bridge to a Pi Zero 2 W wearable via ESP32 BLE. "
        "Use these tools to log activities, notes, and searches "
        "to the Pi for future analysis. The Pi stores all data locally."
    ),
)


@mcp.tool()
def ping() -> str:
    """Ping the Pi Zero to test round-trip connectivity.

    Sends CMD:ping through the ESP32 BLE bridge and waits for CMD:pong.
    Use this to verify the full chain: Computer -> ESP32 -> BLE -> Pi.
    """
    try:
        lines = _bridge.send_and_wait("CMD:ping", timeout=5)
        if lines:
            return "Response: " + " | ".join(lines)
        return "No response (timeout). Check ESP32 and Pi are connected."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def get_status() -> str:
    """Get the Pi Zero's current status.

    Returns uptime, connection info, storage stats, and recording state.
    """
    try:
        lines = _bridge.send_and_wait("CMD:status", timeout=5)
        if lines:
            return "\n".join(lines)
        return "No response (timeout)."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def send_note(content: str, tags: str = "") -> str:
    """Send a text note to the Pi Zero for storage.

    Notes are timestamped and stored on the Pi's SD card for future analysis.

    Args:
        content: The note text to store.
        tags: Optional comma-separated tags for categorization
              (e.g. "idea,project,urgent").
    """
    try:
        msg = {
            "type": "note",
            "content": content,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if tags:
            msg["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        lines = _bridge.send_and_wait(json.dumps(msg), timeout=5)
        if lines:
            return "\n".join(lines)
        return "Sent (no acknowledgment)."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def log_activity(program: str, details: str = "", file_path: str = "") -> str:
    """Log what the user is currently working on.

    Records the program, optional file path, and details to the Pi for
    building an activity timeline.

    Args:
        program: Program name (e.g. "VS Code", "Chrome", "Terminal").
        details: Optional description of the activity.
        file_path: Optional file path being worked on.
    """
    try:
        msg = {
            "type": "activity",
            "program": program,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if details:
            msg["details"] = details
        if file_path:
            msg["file_path"] = file_path
        lines = _bridge.send_and_wait(json.dumps(msg), timeout=5)
        if lines:
            return "\n".join(lines)
        return "Sent (no acknowledgment)."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def log_search(query: str, url: str = "", source: str = "web") -> str:
    """Log a web search or research query.

    Records searches for building a research history on the Pi.

    Args:
        query: The search query text.
        url: Optional URL of the search or result page.
        source: Search engine or source (e.g. "google", "github", "stackoverflow").
    """
    try:
        msg = {
            "type": "search",
            "query": query,
            "source": source,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if url:
            msg["url"] = url
        lines = _bridge.send_and_wait(json.dumps(msg), timeout=5)
        if lines:
            return "\n".join(lines)
        return "Sent (no acknowledgment)."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def send_message(message: str) -> str:
    """Send an arbitrary message to the Pi Zero through the bridge.

    Use for custom commands or data not covered by other tools.
    Messages are newline-delimited UTF-8, max 512 bytes.

    Args:
        message: The message to send.
    """
    try:
        if len(message.encode("utf-8")) > 500:
            return "Error: message too long (max ~500 bytes)."
        lines = _bridge.send_and_wait(message, timeout=5)
        if lines:
            return "\n".join(lines)
        return "Sent (no response)."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def read_responses() -> str:
    """Read any pending messages from the Pi Zero.

    Returns buffered messages that arrived without a preceding request.
    Useful for checking unsolicited data or async responses.
    """
    try:
        _bridge._ensure_connected()
        lines = _bridge.read_pending()
        if lines:
            return "\n".join(lines)
        return "No pending messages."
    except Exception as e:
        return "Error: {}".format(e)


@mcp.tool()
def connection_info() -> str:
    """Show current serial connection status and available ports.

    Lists detected serial ports and the active connection details.
    """
    try:
        # List available ports
        ports = serial.tools.list_ports.comports()
        port_list = []
        for p in ports:
            desc = p.description or "unknown"
            vid = "VID={:04X}".format(p.vid) if p.vid else ""
            port_list.append("{} - {} {}".format(p.device, desc, vid).strip())

        info = "Available ports:\n"
        if port_list:
            info += "\n".join("  " + p for p in port_list)
        else:
            info += "  (none detected)"

        info += "\n\n"

        if _bridge.is_connected:
            info += "Connected: {}\n".format(_bridge.port_name)
            info += "Baud: {}\n".format(_BAUD)
            info += "Buffered messages: {}".format(_bridge.buffered_count)
        else:
            info += "Status: Not connected"
            auto = _bridge._find_port()
            if auto:
                info += "\nAuto-detected ESP32: {}".format(auto)

        return info
    except Exception as e:
        return "Error: {}".format(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
