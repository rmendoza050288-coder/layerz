"""Core data model for LayerZ: a Layer and an ordered LayerStack."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from PIL import Image


_next_id = itertools.count(1)


@dataclass
class Layer:
    """A single image layer.

    `image` is always an RGBA Pillow Image the same size as the canvas, with
    fully transparent pixels wherever the layer has no content.
    `level` is the stacking order: lower values render first (bottom),
    higher values render last (top).
    """

    name: str
    image: Image.Image
    level: int = 0
    visible: bool = True
    id: int = field(default_factory=lambda: next(_next_id))

    def thumbnail(self, size=(64, 64)) -> Image.Image:
        thumb = self.image.copy()
        thumb.thumbnail(size)
        return thumb

    def is_empty(self) -> bool:
        alpha = np.array(self.image.split()[-1])
        return bool(np.all(alpha == 0))


class LayerStack:
    """Holds all layers for the current document and provides composition."""

    def __init__(self, canvas_size: tuple[int, int]):
        self.canvas_size = canvas_size
        self.layers: list[Layer] = []

    # -- basic list management -------------------------------------------------
    def add(self, layer: Layer) -> None:
        self.layers.append(layer)
        self.renumber_if_needed()

    def remove(self, layer_id: int) -> None:
        self.layers = [l for l in self.layers if l.id != layer_id]

    def get(self, layer_id: int) -> Layer | None:
        for l in self.layers:
            if l.id == layer_id:
                return l
        return None

    def clear(self) -> None:
        self.layers = []

    def ordered(self) -> list[Layer]:
        """Layers sorted bottom-to-top by level (stable for equal levels)."""
        return sorted(self.layers, key=lambda l: (l.level, l.id))

    def renumber_if_needed(self) -> None:
        """Ensure levels stay reasonably compact starting at 0 if unset."""
        if not self.layers:
            return

    def set_level(self, layer_id: int, level: int) -> None:
        layer = self.get(layer_id)
        if layer is not None:
            layer.level = level

    def move_level(self, layer_id: int, delta: int) -> None:
        layer = self.get(layer_id)
        if layer is not None:
            layer.level += delta

    # -- composition ------------------------------------------------------------
    def composite(self) -> Image.Image:
        """Flatten all visible layers, bottom to top, into one RGBA image."""
        result = Image.new("RGBA", self.canvas_size, (0, 0, 0, 0))
        for layer in self.ordered():
            if not layer.visible:
                continue
            result = Image.alpha_composite(result, layer.image)
        return result

    def next_default_level(self) -> int:
        if not self.layers:
            return 0
        return max(l.level for l in self.layers) + 1
