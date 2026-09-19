"""Image loading (JPEG/PNG/PSD) and layered-export helpers."""
from __future__ import annotations

import json
import os

from PIL import Image

from .layer_model import Layer, LayerStack

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".psd")


def load_document(path: str) -> LayerStack:
    """Load a JPEG/PNG as a single base layer, or a PSD as its native layers."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".psd":
        return _load_psd(path)
    return _load_flat_image(path)


def _load_flat_image(path: str) -> LayerStack:
    image = Image.open(path).convert("RGBA")
    stack = LayerStack(canvas_size=image.size)
    stack.add(Layer(name="Background", image=image, level=0))
    return stack


def _load_psd(path: str) -> LayerStack:
    from psd_tools import PSDImage  # imported lazily: heaviest optional dep

    psd = PSDImage.open(path)
    canvas_size = (psd.width, psd.height)
    stack = LayerStack(canvas_size=canvas_size)

    flat_layers = list(_iter_psd_layers(psd))
    if not flat_layers:
        composite = psd.composite()
        if composite is None:
            composite = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        stack.add(Layer(name="Background", image=composite.convert("RGBA"), level=0))
        return stack

    for level, psd_layer in enumerate(flat_layers):
        layer_image = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        try:
            rendered = psd_layer.composite()
        except Exception:
            rendered = None
        if rendered is not None:
            box = (
                psd_layer.left,
                psd_layer.top,
                psd_layer.left + rendered.width,
                psd_layer.top + rendered.height,
            )
            layer_image.paste(rendered.convert("RGBA"), box, rendered.convert("RGBA"))
        stack.add(
            Layer(
                name=psd_layer.name or f"Layer {level}",
                image=layer_image,
                level=level,
                visible=bool(psd_layer.visible),
            )
        )
    return stack


def _iter_psd_layers(psd) -> list:
    """Return PSD layers in bottom-to-top order, skipping non-image groups."""
    layers = []
    for layer in psd:
        if layer.is_group():
            continue
        if layer.kind in ("pixel", "smartobject", "type", "shape"):
            layers.append(layer)
    return layers


def export_layers(stack: LayerStack, output_dir: str, base_name: str = "layer") -> list[str]:
    """Write each visible layer to its own PNG, ordered by level, plus a
    flattened composite and a JSON manifest describing the stack.

    Returns the list of written file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    written: list[str] = []
    manifest = {"canvas_size": list(stack.canvas_size), "layers": []}

    for index, layer in enumerate(stack.ordered()):
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in layer.name).strip() or "layer"
        filename = f"{index:02d}_{base_name}_{safe_name}.png"
        out_path = os.path.join(output_dir, filename)
        layer.image.save(out_path)
        written.append(out_path)
        manifest["layers"].append(
            {
                "file": filename,
                "name": layer.name,
                "level": layer.level,
                "visible": layer.visible,
            }
        )

    composite_path = os.path.join(output_dir, f"{base_name}_composite.png")
    stack.composite().save(composite_path)
    written.append(composite_path)

    manifest_path = os.path.join(output_dir, f"{base_name}_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    written.append(manifest_path)

    return written


def export_psd(stack: LayerStack, path: str) -> None:
    """Write the layer stack out as a single, real layered .psd file."""
    from psd_tools import PSDImage  # imported lazily: heaviest optional dep

    psd = PSDImage.new(mode="RGBA", size=stack.canvas_size, color=0)
    for layer in stack.ordered():
        pixel_layer = psd.create_pixel_layer(layer.image, name=layer.name, top=0, left=0)
        pixel_layer.visible = layer.visible
    psd.save(path)
