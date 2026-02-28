"""
tool_icons.py - Cortex tool activity icons for the bottom display panel.

Shows 6 grouped icons (24x24) in a 3x2 grid at the bottom of the screen.
Icons flash bright when their associated MCP tool is called, then fade
to a "recently used" mid-brightness, and finally back to dim.
"""

import time
import st7789py as st7789

# --- Layout constants ---
_ICON_W = 24
_ICON_H = 24
_X_POS = (25, 74, 123)      # 3 columns, centered in 172px
_ROW1_Y = 228               # Row 1 icons top
_ROW2_Y = 272               # Row 2 icons top
_LBL1_Y = 253               # Row 1 labels
_LBL2_Y = 297               # Row 2 labels
_PANEL_Y = 224               # Separator line y
_CHAR_W = 8

# --- Timing ---
_ACTIVE_MS = 1500            # Bright flash duration
_RECENT_MS = 30000           # "Recently used" duration

# --- Colors ---
_BG = st7789.BLACK
_DIM = st7789.color565(35, 35, 35)
_LBL_DIM = st7789.color565(50, 50, 50)

# Bright accent per group
_BRIGHT = {
    'conn': st7789.GREEN,
    'ctx':  st7789.CYAN,
    'data': st7789.YELLOW,
    'logs': st7789.MAGENTA,
    'sess': st7789.color565(255, 140, 0),   # Orange
    'link': st7789.WHITE,
}

# Mid-brightness per group
_MID = {
    'conn': st7789.color565(0, 90, 0),
    'ctx':  st7789.color565(0, 90, 90),
    'data': st7789.color565(90, 90, 0),
    'logs': st7789.color565(90, 0, 90),
    'sess': st7789.color565(120, 60, 0),
    'link': st7789.color565(70, 70, 70),
}

# Group definitions: (key, label, x, y)
_GROUPS = (
    ('conn', 'CONN', _X_POS[0], _ROW1_Y),
    ('ctx',  'CTX',  _X_POS[1], _ROW1_Y),
    ('data', 'DATA', _X_POS[2], _ROW1_Y),
    ('logs', 'LOGS', _X_POS[0], _ROW2_Y),
    ('sess', 'SESS', _X_POS[1], _ROW2_Y),
    ('link', 'LINK', _X_POS[2], _ROW2_Y),
)

# Command name -> group mapping
_CMD_MAP = {
    'ping':          'conn',
    'status':        'conn',
    'computer_reg':  'conn',
    'get_context':   'ctx',
    'note':          'data',
    'query':         'data',
    'activity':      'logs',
    'search':        'logs',
    'session_start': 'sess',
    'session_end':   'sess',
}


# ---------------------------------------------------------------
# Icon drawing functions
# Each draws a 24x24 icon at (x, y) using ST7789 primitives.
# ---------------------------------------------------------------

def _draw_conn(tft, x, y, c):
    """Signal tower with radiating bars."""
    # Tower body
    tft.fill_rect(x + 10, y + 8, 4, 14, c)
    # Base
    tft.fill_rect(x + 7, y + 20, 10, 3, c)
    # Signal arcs (horizontal bars, left side)
    tft.hline(x + 2, y + 2, 6, c)
    tft.hline(x + 4, y + 5, 4, c)
    tft.hline(x + 6, y + 8, 3, c)
    # Signal arcs (right side)
    tft.hline(x + 16, y + 2, 6, c)
    tft.hline(x + 16, y + 5, 4, c)
    tft.hline(x + 15, y + 8, 3, c)
    # Antenna tip
    tft.fill_rect(x + 11, y + 4, 2, 4, c)


def _draw_ctx(tft, x, y, c):
    """Lightbulb shape."""
    # Bulb body
    tft.fill_rect(x + 7, y + 3, 10, 11, c)
    tft.fill_rect(x + 5, y + 5, 14, 7, c)
    # Round top corners (clear)
    tft.fill_rect(x + 5, y + 3, 2, 2, _BG)
    tft.fill_rect(x + 17, y + 3, 2, 2, _BG)
    # Round bottom corners (clear)
    tft.fill_rect(x + 5, y + 12, 2, 2, _BG)
    tft.fill_rect(x + 17, y + 12, 2, 2, _BG)
    # Filament (dark center dot)
    tft.fill_rect(x + 11, y + 7, 2, 3, _BG)
    # Neck
    tft.fill_rect(x + 9, y + 15, 6, 2, c)
    # Base stripes
    tft.fill_rect(x + 8, y + 18, 8, 2, c)
    tft.fill_rect(x + 9, y + 21, 6, 2, c)


def _draw_data(tft, x, y, c):
    """Document with folded corner and text lines."""
    # Page outline
    tft.rect(x + 4, y + 1, 14, 22, c)
    tft.rect(x + 5, y + 2, 12, 20, c)
    # Folded corner
    tft.fill_rect(x + 14, y + 1, 4, 4, _BG)
    tft.hline(x + 14, y + 5, 4, c)
    tft.vline(x + 14, y + 1, 5, c)
    tft.line(x + 14, y + 1, x + 18, y + 5, c)
    # Text lines
    tft.hline(x + 7, y + 8, 8, c)
    tft.hline(x + 7, y + 11, 8, c)
    tft.hline(x + 7, y + 14, 6, c)
    tft.hline(x + 7, y + 17, 8, c)


def _draw_logs(tft, x, y, c):
    """Magnifying glass over lines."""
    # Lens circle (square approximation)
    tft.rect(x + 3, y + 2, 14, 14, c)
    tft.rect(x + 4, y + 3, 12, 12, c)
    # Round corners
    tft.fill_rect(x + 3, y + 2, 2, 2, _BG)
    tft.fill_rect(x + 15, y + 2, 2, 2, _BG)
    tft.fill_rect(x + 3, y + 14, 2, 2, _BG)
    tft.fill_rect(x + 15, y + 14, 2, 2, _BG)
    # Handle (diagonal, approximated)
    tft.fill_rect(x + 15, y + 14, 3, 3, c)
    tft.fill_rect(x + 17, y + 16, 3, 3, c)
    tft.fill_rect(x + 19, y + 18, 3, 3, c)
    # Search lines inside lens
    tft.hline(x + 6, y + 7, 7, c)
    tft.hline(x + 6, y + 10, 5, c)


def _draw_sess(tft, x, y, c):
    """Clock face with hands."""
    # Clock body (rounded square)
    tft.rect(x + 3, y + 1, 18, 22, c)
    tft.rect(x + 4, y + 2, 16, 20, c)
    # Round corners
    tft.fill_rect(x + 3, y + 1, 2, 2, _BG)
    tft.fill_rect(x + 19, y + 1, 2, 2, _BG)
    tft.fill_rect(x + 3, y + 21, 2, 2, _BG)
    tft.fill_rect(x + 19, y + 21, 2, 2, _BG)
    # Hour markers (12, 3, 6, 9 o'clock)
    tft.fill_rect(x + 11, y + 4, 2, 2, c)
    tft.fill_rect(x + 17, y + 10, 2, 2, c)
    tft.fill_rect(x + 11, y + 18, 2, 2, c)
    tft.fill_rect(x + 5, y + 10, 2, 2, c)
    # Center dot
    tft.fill_rect(x + 11, y + 10, 2, 4, c)
    # Hour hand (up)
    tft.vline(x + 11, y + 6, 4, c)
    tft.vline(x + 12, y + 6, 4, c)
    # Minute hand (right)
    tft.hline(x + 13, y + 11, 4, c)
    tft.hline(x + 13, y + 12, 4, c)


def _draw_link(tft, x, y, c):
    """Bidirectional arrows (data bridge)."""
    # Right arrow (top)
    tft.hline(x + 3, y + 6, 14, c)
    tft.hline(x + 3, y + 7, 14, c)
    # Arrowhead right
    tft.vline(x + 15, y + 4, 3, c)
    tft.vline(x + 16, y + 5, 3, c)
    tft.vline(x + 17, y + 4, 6, c)
    tft.vline(x + 18, y + 5, 4, c)
    tft.vline(x + 19, y + 6, 2, c)
    # Left arrow (bottom)
    tft.hline(x + 7, y + 16, 14, c)
    tft.hline(x + 7, y + 17, 14, c)
    # Arrowhead left
    tft.vline(x + 8, y + 14, 3, c)
    tft.vline(x + 7, y + 15, 3, c)
    tft.vline(x + 6, y + 14, 6, c)
    tft.vline(x + 5, y + 15, 4, c)
    tft.vline(x + 4, y + 16, 2, c)
    # Center dot (BLE indicator)
    tft.fill_rect(x + 10, y + 10, 4, 4, c)


# Dispatch table
_DRAW_FNS = {
    'conn': _draw_conn,
    'ctx':  _draw_ctx,
    'data': _draw_data,
    'logs': _draw_logs,
    'sess': _draw_sess,
    'link': _draw_link,
}


# ---------------------------------------------------------------
# ToolPanel — state manager and renderer
# ---------------------------------------------------------------

class ToolPanel:
    """Manages 6 tool-group icons with flash/fade behavior."""

    def __init__(self, font):
        self._font = font
        self._states = {}
        for g, _, _, _ in _GROUPS:
            self._states[g] = {'ts': 0, 'phase': 'dim'}

    def trigger(self, cmd_name):
        """Mark a tool group as active based on the CMD: command name.

        Returns the group key, or None if no mapping found.
        """
        group = _CMD_MAP.get(cmd_name)
        if group is None:
            return None
        self._states[group]['ts'] = time.ticks_ms()
        self._states[group]['phase'] = 'active'
        return group

    def trigger_link(self):
        """Mark the bridge/link icon as active (any serial traffic)."""
        self._states['link']['ts'] = time.ticks_ms()
        self._states['link']['phase'] = 'active'

    def draw_all(self, tft):
        """Full panel redraw: separator + all 6 icons + labels."""
        # Separator line
        tft.hline(0, _PANEL_Y, 172, st7789.color565(60, 60, 60))
        # Clear icon area
        tft.fill_rect(0, _PANEL_Y + 1, 172, 320 - _PANEL_Y - 1, _BG)
        # Draw each icon
        for g, label, x, y in _GROUPS:
            self._draw_one(tft, g, label, x, y)

    def draw_group(self, tft, group):
        """Redraw a single group icon (after state change)."""
        for g, label, x, y in _GROUPS:
            if g == group:
                self._draw_one(tft, g, label, x, y)
                return

    def update(self, tft):
        """Transition active->recent->dim based on timestamps.

        Call periodically (~500ms). Only redraws icons that changed phase.
        """
        now = time.ticks_ms()
        for g, label, x, y in _GROUPS:
            st = self._states[g]
            old = st['phase']
            if old == 'active':
                if time.ticks_diff(now, st['ts']) > _ACTIVE_MS:
                    st['phase'] = 'recent'
                    self._draw_one(tft, g, label, x, y)
            elif old == 'recent':
                if time.ticks_diff(now, st['ts']) > _RECENT_MS:
                    st['phase'] = 'dim'
                    self._draw_one(tft, g, label, x, y)

    def _draw_one(self, tft, group, label, x, y):
        """Draw one icon + label at the correct brightness."""
        phase = self._states[group]['phase']
        if phase == 'active':
            color = _BRIGHT[group]
            lbl_c = color
        elif phase == 'recent':
            color = _MID[group]
            lbl_c = color
        else:
            color = _DIM
            lbl_c = _LBL_DIM

        # Clear icon area
        tft.fill_rect(x, y, _ICON_W, _ICON_H, _BG)
        # Draw icon shape
        _DRAW_FNS[group](tft, x, y, color)
        # Label centered below icon
        lbl_y = _LBL1_Y if y == _ROW1_Y else _LBL2_Y
        lbl_x = x + (_ICON_W - len(label) * _CHAR_W) // 2
        tft.text(self._font, label, lbl_x, lbl_y, lbl_c, _BG)
