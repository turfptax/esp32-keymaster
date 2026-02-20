"""
Interactive menu UI for Waveshare ESP32-S3-LCD-1.47.

Single-button navigation: short press = next item, long press = select.
Renders directly to the ST7789 display via display_manager.
"""

import gc
import st7789py as st7789
import vga1_8x16 as font

# --- Layout constants ---
_CHAR_W = 8
_CHAR_H = 16
_WIDTH = 172
_HEIGHT = 320
_CHARS_PER_LINE = _WIDTH // _CHAR_W  # 21

_TITLE_H = 32  # 2 text lines
_SEP1_Y = _TITLE_H  # 32
_ITEMS_Y = _SEP1_Y + 1  # 33
_VISIBLE_ITEMS = 15
_ITEMS_ZONE_H = _VISIBLE_ITEMS * _CHAR_H  # 240
_SEP2_Y = _ITEMS_Y + _ITEMS_ZONE_H  # 273
_FOOTER_Y = _SEP2_Y + 2  # 275

# --- Menu colors (RGB565) ---
_BG = st7789.BLACK
_FG = st7789.WHITE
_SEL_BG = st7789.color565(0, 0, 120)  # Medium blue highlight
_SEL_FG = st7789.WHITE
_TITLE_BG = st7789.color565(0, 0, 80)  # Dark blue (matches status title)
_TITLE_FG = st7789.WHITE
_HINT_FG = st7789.color565(128, 128, 128)  # Gray footer
_SEP_COLOR = st7789.color565(60, 60, 60)
_BACK_FG = st7789.YELLOW  # "< Back" stands out
_VAL_FG = st7789.CYAN  # Value suffix color
_INFO_FG = st7789.color565(100, 100, 100)  # Dim for non-selectable info


class MenuItem:
    """Lightweight menu item.

    Kinds:
        "sub"   - data is callable() -> (title, [MenuItem, ...])
        "cb"    - data is callable() or None (None = go back)
        "cycle" - data is {"values": [...], "idx": int, "cb": fn_or_None}
        "info"  - data is callable() -> str (display-only, not selectable)
    """
    __slots__ = ('label', 'kind', 'data')

    def __init__(self, label, kind, data=None):
        self.label = label
        self.kind = kind
        self.data = data


class MenuManager:
    """Manages menu navigation, state stack, and rendering."""

    def __init__(self, display_manager):
        self._dm = display_manager
        self._tft = display_manager.tft
        self._stack = []  # [(title, items, sel_idx, scroll_off), ...]
        self._active = False
        self._prev_sel = -1
        self._prev_scroll = -1

    @property
    def is_active(self):
        return self._active

    # ------------------------------------------------------------------
    # Public navigation API
    # ------------------------------------------------------------------

    def open(self, title, items):
        """Open the menu system with the given root menu."""
        self._stack = []
        self._push(title, items)
        self._active = True
        self._dm.menu_active = True
        self._render_full()

    def close(self):
        """Close the menu system."""
        self._stack = []
        self._active = False
        self._dm.menu_active = False

    def on_short_press(self):
        """Move selection to the next item (wraps around)."""
        if not self._active or not self._stack:
            return
        title, items, sel, scroll = self._stack[-1]
        sel = (sel + 1) % len(items)
        scroll = self._adjust_scroll(sel, scroll, len(items))
        self._stack[-1] = (title, items, sel, scroll)
        self._render_diff()

    def on_long_press(self):
        """Select / enter the highlighted item."""
        if not self._active or not self._stack:
            return
        title, items, sel, scroll = self._stack[-1]
        item = items[sel]

        if item.kind == "sub":
            try:
                sub_title, sub_items = item.data()
                self._push(sub_title, sub_items)
                self._render_full()
            except Exception as e:
                print("Menu: submenu error:", e)
        elif item.kind == "cb":
            if item.data is None:
                self._pop()
            else:
                try:
                    item.data()
                except Exception as e:
                    print("Menu: callback error:", e)
                # Refresh current menu in case callback changed state
                if self._active and self._stack:
                    self._render_full()
        elif item.kind == "cycle":
            d = item.data
            d["idx"] = (d["idx"] + 1) % len(d["values"])
            if d.get("cb"):
                try:
                    d["cb"](d["values"][d["idx"]])
                except Exception as e:
                    print("Menu: cycle cb error:", e)
            self._render_item_at(sel)
        # "info" items: long press is a no-op

    # ------------------------------------------------------------------
    # Stack management
    # ------------------------------------------------------------------

    def _push(self, title, items):
        self._stack.append((title, items, 0, 0))
        self._prev_sel = -1
        self._prev_scroll = -1

    def _pop(self):
        if len(self._stack) > 1:
            self._stack.pop()
            self._prev_sel = -1
            self._prev_scroll = -1
            self._render_full()
        else:
            # At root -- close menu entirely
            self.close()

    # ------------------------------------------------------------------
    # Scroll logic
    # ------------------------------------------------------------------

    def _adjust_scroll(self, sel, scroll, total):
        if total <= _VISIBLE_ITEMS:
            return 0
        if sel < scroll:
            scroll = sel
        elif sel >= scroll + _VISIBLE_ITEMS:
            scroll = sel - _VISIBLE_ITEMS + 1
        return scroll

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_full(self):
        """Complete redraw of the menu screen."""
        if not self._stack:
            return
        title, items, sel, scroll = self._stack[-1]
        tft = self._tft

        # Title bar
        tft.fill_rect(0, 0, _WIDTH, _TITLE_H, _TITLE_BG)
        self._center_text(title, 8, _TITLE_FG, _TITLE_BG)

        # Separator 1
        tft.hline(0, _SEP1_Y, _WIDTH, _SEP_COLOR)

        # Clear items zone
        tft.fill_rect(0, _ITEMS_Y, _WIDTH, _ITEMS_ZONE_H, _BG)

        # Draw visible items
        end = min(scroll + _VISIBLE_ITEMS, len(items))
        for i in range(scroll, end):
            vis = i - scroll
            self._draw_item(vis, items[i], i == sel)

        # Scroll indicators
        if scroll > 0:
            tft.text(font, "^", _WIDTH - _CHAR_W, _ITEMS_Y, _HINT_FG, _BG)
        if scroll + _VISIBLE_ITEMS < len(items):
            y_last = _ITEMS_Y + (_VISIBLE_ITEMS - 1) * _CHAR_H
            tft.text(font, "v", _WIDTH - _CHAR_W, y_last, _HINT_FG, _BG)

        # Separator 2
        tft.hline(0, _SEP2_Y, _WIDTH, _SEP_COLOR)

        # Footer
        tft.fill_rect(0, _FOOTER_Y, _WIDTH, _CHAR_H, _BG)
        tft.text(font, "Tap=Next  Hold=OK", 0, _FOOTER_Y, _HINT_FG, _BG)

        self._prev_sel = sel
        self._prev_scroll = scroll
        gc.collect()

    def _render_diff(self):
        """Redraw only the changed items (fast highlight move)."""
        if not self._stack:
            return
        title, items, sel, scroll = self._stack[-1]

        if scroll != self._prev_scroll:
            # Scroll offset changed -- full redraw needed
            self._render_full()
            return

        # Unhighlight old selection
        if self._prev_sel >= 0:
            vis_prev = self._prev_sel - scroll
            if 0 <= vis_prev < _VISIBLE_ITEMS:
                self._draw_item(vis_prev, items[self._prev_sel], False)

        # Highlight new selection
        vis_cur = sel - scroll
        if 0 <= vis_cur < _VISIBLE_ITEMS:
            self._draw_item(vis_cur, items[sel], True)

        self._prev_sel = sel
        self._prev_scroll = scroll

    def _render_item_at(self, abs_idx):
        """Redraw a single item by its absolute index (for cycle updates)."""
        if not self._stack:
            return
        title, items, sel, scroll = self._stack[-1]
        vis = abs_idx - scroll
        if 0 <= vis < _VISIBLE_ITEMS:
            self._draw_item(vis, items[abs_idx], abs_idx == sel)

    def _draw_item(self, vis_index, item, selected):
        """Render one menu item at the given visual row."""
        y = _ITEMS_Y + vis_index * _CHAR_H

        if selected:
            bg, fg = _SEL_BG, _SEL_FG
        else:
            bg, fg = _BG, _FG

        # Clear line
        self._tft.fill_rect(0, y, _WIDTH, _CHAR_H, bg)

        # Prefix
        prefix = "> " if selected else "  "

        # Build suffix for cycle and info items
        suffix = ""
        if item.kind == "cycle" and item.data:
            val = item.data["values"][item.data["idx"]]
            suffix = " [" + val + "]"
        elif item.kind == "info" and item.data:
            try:
                suffix = " " + item.data()
            except Exception:
                suffix = " ?"

        # Color overrides
        if item.kind == "cb" and item.data is None and not selected:
            fg = _BACK_FG  # "< Back" in yellow when not highlighted

        # Assemble text
        label = item.label
        max_chars = _CHARS_PER_LINE
        if suffix:
            avail = max_chars - len(prefix) - len(suffix)
            if avail < 0:
                avail = 0
            if len(label) > avail:
                label = label[:avail]
            text = prefix + label + suffix
        else:
            text = prefix + label

        text = text[:max_chars]
        self._tft.text(font, text, 0, y, fg, bg)

    def _center_text(self, string, y, fg, bg):
        """Draw text horizontally centered."""
        x = (_WIDTH - len(string) * _CHAR_W) // 2
        self._tft.text(font, string, x, y, fg, bg)
