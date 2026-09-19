"""Tkinter canvas that displays the composited image, scaled to fit, and lets
the user draw a freehand (lasso) selection for the manual segmentation flow.
"""
from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageTk


class CanvasView(tk.Canvas):
    def __init__(self, parent, on_polygon_complete=None, **kwargs):
        kwargs.setdefault("bg", "#2b2b2b")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)
        self.on_polygon_complete = on_polygon_complete

        self.image: Image.Image | None = None
        self._tk_image = None
        self.scale = 1.0
        self.offset = (0, 0)

        self.selecting_enabled = False
        self._points: list[tuple[int, int]] = []

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _e: self._redraw())

    # -- rendering ---------------------------------------------------------
    def set_image(self, pil_image: Image.Image) -> None:
        self.image = pil_image.convert("RGBA")
        self._redraw()

    def _redraw(self) -> None:
        self.delete("image")
        if self.image is None:
            return

        cw = max(self.winfo_width(), 1)
        ch = max(self.winfo_height(), 1)
        iw, ih = self.image.size
        scale = min(cw / iw, ch / ih)
        scale = max(scale, 0.01)
        self.scale = scale

        disp_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
        disp = self.image.resize(disp_size, Image.LANCZOS)

        backdrop = self._checkerboard(disp_size)
        backdrop.paste(disp, (0, 0), disp)

        self._tk_image = ImageTk.PhotoImage(backdrop)
        ox = (cw - disp_size[0]) // 2
        oy = (ch - disp_size[1]) // 2
        self.offset = (ox, oy)
        self.create_image(ox, oy, anchor="nw", image=self._tk_image, tags="image")
        self.tag_lower("image")

    @staticmethod
    def _checkerboard(size: tuple[int, int], cell: int = 10) -> Image.Image:
        w, h = size
        board = Image.new("RGB", size, (200, 200, 200))
        pixels = board.load()
        for y in range(h):
            for x in range(0, w):
                if ((x // cell) + (y // cell)) % 2 == 0:
                    pixels[x, y] = (170, 170, 170)
        return board

    # -- selection (manual mode) -------------------------------------------
    def clear_selection(self) -> None:
        self._points = []
        self.delete("selection")

    def _on_press(self, event: tk.Event) -> None:
        if not self.selecting_enabled:
            return
        self._points = [(event.x, event.y)]
        self.delete("selection")

    def _on_drag(self, event: tk.Event) -> None:
        if not self.selecting_enabled:
            return
        self._points.append((event.x, event.y))
        self.delete("selection")
        if len(self._points) > 1:
            flat = [coord for point in self._points for coord in point]
            self.create_line(*flat, fill="#00e08a", width=2, tags="selection")

    def _on_release(self, _event: tk.Event) -> None:
        if not self.selecting_enabled:
            return
        if len(self._points) < 3:
            self._points = []
            return
        flat = [coord for point in self._points for coord in point]
        self.create_polygon(*flat, outline="#00e08a", fill="", width=2, tags="selection")
        image_points = [self._to_image_coords(p) for p in self._points]
        if self.on_polygon_complete:
            self.on_polygon_complete(image_points)

    def _to_image_coords(self, point: tuple[int, int]) -> tuple[float, float]:
        x, y = point
        ox, oy = self.offset
        return ((x - ox) / self.scale, (y - oy) / self.scale)
