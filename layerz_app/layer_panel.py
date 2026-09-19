"""Right-hand panel listing every layer with its level, visibility and delete controls."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .layer_model import Layer


class LayerPanel(ttk.Frame):
    def __init__(self, parent, on_change=None, **kwargs):
        kwargs.setdefault("width", 320)
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self._thumb_refs: list[ImageTk.PhotoImage] = []

        ttk.Label(self, text="Layers (top to bottom)", font=("", 11, "bold")).pack(
            anchor="w", pady=(0, 6)
        )
        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="both", expand=True)

    def set_layers(self, ordered_layers: list[Layer]) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self._thumb_refs.clear()

        # Layers are given bottom-to-top; show top-to-bottom, matching how
        # most image editors list their stacks.
        for layer in reversed(ordered_layers):
            self._add_row(layer)

    def _add_row(self, layer: Layer) -> None:
        row = ttk.Frame(self.rows_frame, relief="groove", borderwidth=1, padding=4)
        row.pack(fill="x", pady=2)

        thumb_img = ImageTk.PhotoImage(layer.thumbnail((48, 48)))
        self._thumb_refs.append(thumb_img)
        ttk.Label(row, image=thumb_img).grid(row=0, column=0, rowspan=2, padx=(0, 6))

        ttk.Label(row, text=layer.name, font=("", 10, "bold")).grid(
            row=0, column=1, columnspan=3, sticky="w"
        )

        ttk.Label(row, text="Level:").grid(row=1, column=1, sticky="w")
        level_var = tk.IntVar(value=layer.level)
        spin = ttk.Spinbox(
            row,
            from_=-50,
            to=50,
            textvariable=level_var,
            width=4,
            command=lambda lid=layer.id, v=level_var: self._emit(lid, level=v.get()),
        )
        spin.grid(row=1, column=2, sticky="w")
        spin.bind("<Return>", lambda e, lid=layer.id, v=level_var: self._emit(lid, level=v.get()))
        spin.bind("<FocusOut>", lambda e, lid=layer.id, v=level_var: self._emit(lid, level=v.get()))

        visible_var = tk.BooleanVar(value=layer.visible)
        ttk.Checkbutton(
            row,
            text="Visible",
            variable=visible_var,
            command=lambda lid=layer.id, v=visible_var: self._emit(lid, visible=v.get()),
        ).grid(row=1, column=3, padx=6)

        ttk.Button(
            row,
            text="Delete",
            width=7,
            command=lambda lid=layer.id: self._emit(lid, delete=True),
        ).grid(row=0, column=4, rowspan=2, padx=(6, 0))

    def _emit(self, layer_id: int, **kwargs) -> None:
        if self.on_change:
            self.on_change(layer_id, **kwargs)
