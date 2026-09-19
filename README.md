# LayerZ

LayerZ is a local desktop tool for turning flat images into editable image
layers. Load a JPEG, PNG, or PSD, separate regions automatically or with a
lasso selection, adjust the stacking order, and export the result as either
transparent PNG layers or a layered PSD.

No terminal commands are required to use the app day-to-day: double-click
**`Run LayerZ.command`** in Finder. The first run creates a local virtual
environment and installs dependencies; every run after that just opens the
app window.

## What it does

- **Open**: `.jpg` / `.jpeg` / `.png` load as a single background layer.
  `.psd` files load with their existing layers already separated out.
- **Automatic mode**: color-based clustering (K-means, fully offline, no
  downloaded models) splits the image into N candidate regions, each
  becoming its own transparent-background layer.
- **Manual mode**: draw a lasso selection directly on the canvas, pick which
  existing layer it should be cut from, choose the level for the new layer,
  then click "Create Layer from Selection". The selected pixels move into
  the new layer and become transparent in the source layer.
- **Levels**: every layer has an integer level in the right-hand panel.
  Lower numbers render at the bottom, higher numbers render on top. Editing
  the level immediately re-stacks the preview.
- **Export**: writes one PNG per visible layer (named by level order), a
  flattened composite PNG, and a `_manifest.json` describing each layer's
  name, level, and file — everything needed to reconstruct the stack.
- **Export as PSD**: writes a single, real layered `.psd` file (layer names,
  order, and visibility all preserved) that opens directly in Photoshop or
  any PSD-compatible editor.

## Quick start

1. Double-click **`Run LayerZ.command`** in Finder.
2. Click **Open...** and choose a `.jpg`, `.jpeg`, `.png`, or `.psd` file.
3. Choose **Automatic** to create color-based regions, or **Manual** to draw
  a selection and lift it into a new layer.
4. Adjust layer levels and visibility in the layer panel.
5. Export with **Export PNGs...** or **Export PSD...**.

The launcher creates a local virtual environment and installs dependencies on
the first run. It does not upload images or require an online service.

## Manual setup (optional)

If you'd rather not use the `.command` launcher:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

## Project layout

```
layerz_app/
  layer_model.py   Layer + LayerStack (ordering, compositing)
  io_utils.py       load JPEG/PNG/PSD, export layers + manifest
  segmentation.py   K-means auto-segmentation, lasso mask cutting
  canvas_view.py    Tkinter canvas: scaled preview + lasso drawing
  layer_panel.py    Tkinter layer list: level, visibility, delete
  gui.py            wires everything into the main window
run.py              entry point (python3 run.py)
Run LayerZ.command  double-click launcher (macOS)
```

## Notes & limitations

- PNG has no native concept of layers, so "layered PNG" is produced as a set
  of individually-exported, correctly ordered transparent PNGs plus a
  manifest — the same approach most image editors use for "export layers".
- Automatic segmentation groups pixels by color similarity; it works best on
  images with reasonably distinct color regions. For fine-grained control,
  use manual mode after (or instead of) auto-segmenting.
- PSD export writes flat pixel layers (name, order, visibility, transparency)
  — no smart objects, adjustment layers, or effects, since those aren't
  produced by this app in the first place.

## Development

Run the application directly from an activated virtual environment:

```bash
python3 run.py
```

The core image operations can be smoke-tested without opening the GUI. The
project currently targets macOS and requires Python 3.10 or newer.
