"""Segmentation helpers.

`auto_segment` splits a flat image into several candidate layers using color
clustering (K-means) - no network access or pretrained model required, so it
works fully offline and deterministically.

`polygon_mask` / `cut_region` support the manual workflow: the user draws a
freehand or polygon selection on the canvas and that region is lifted out of
the source layer into a brand new layer.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw


def auto_segment(image: Image.Image, num_layers: int = 4, min_area_ratio: float = 0.01) -> list[Image.Image]:
    """Cluster the image by color into `num_layers` regions.

    Returns a list of RGBA images (same size as `image`), one per region,
    sorted largest-area first (a reasonable default for background-to-
    foreground ordering). Regions smaller than `min_area_ratio` of the
    canvas are dropped.
    """
    rgba = image.convert("RGBA")
    rgb = np.array(rgba.convert("RGB"))
    h, w = rgb.shape[:2]

    samples = rgb.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    k = max(1, min(num_layers, 12))
    _, labels, _ = cv2.kmeans(samples, k, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    labels = labels.reshape((h, w))

    alpha_full = np.array(rgba.split()[-1])
    layers: list[tuple[int, Image.Image]] = []
    min_pixels = int(min_area_ratio * h * w)

    for cluster_id in range(k):
        mask = (labels == cluster_id).astype(np.uint8) * 255
        # Clean up speckle noise so each layer is a coherent region.
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        area = int(np.count_nonzero(mask))
        if area < min_pixels:
            continue

        layer_alpha = np.minimum(mask, alpha_full)
        layer_rgba = np.dstack([rgb, layer_alpha]).astype(np.uint8)
        layers.append((area, Image.fromarray(layer_rgba, mode="RGBA")))

    layers.sort(key=lambda pair: pair[0], reverse=True)
    return [img for _area, img in layers]


def polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> Image.Image:
    """Build a single-channel (mode "L") mask from a closed polygon."""
    mask = Image.new("L", size, 0)
    if len(points) >= 3:
        ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def cut_region(source: Image.Image, mask: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Split `source` into (extracted_layer, remainder_layer) using `mask`.

    The extracted layer keeps the pixels inside the mask; the remainder
    keeps everything else transparent inside the masked area, so the two
    can be recombined without duplication.
    """
    source = source.convert("RGBA")
    src_arr = np.array(source)
    mask_arr = np.array(mask.convert("L"))

    extracted = src_arr.copy()
    extracted[..., 3] = np.minimum(extracted[..., 3], mask_arr)

    remainder = src_arr.copy()
    inverse = 255 - mask_arr
    remainder[..., 3] = np.minimum(remainder[..., 3], inverse)

    return (
        Image.fromarray(extracted, mode="RGBA"),
        Image.fromarray(remainder, mode="RGBA"),
    )
