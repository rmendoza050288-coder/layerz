"""Main application window wiring the canvas, layer panel and toolbars together."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .canvas_view import CanvasView
from .io_utils import export_layers, export_psd, load_document
from .layer_model import Layer
from .layer_panel import LayerPanel
from .segmentation import auto_segment, cut_region, polygon_mask


class LayerZApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LayerZ - Layered PNG Generator")
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)

        self.stack = None
        self.current_path: str | None = None
        self._pending_polygon: list[tuple[float, float]] | None = None

        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self._on_mode_change()

    # -- layout --------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Image / PSD...", command=self.open_file)
        file_menu.add_command(label="Export Layers (PNGs)...", command=self.export_layers)
        file_menu.add_command(label="Export as PSD...", command=self.export_psd)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="Open...", command=self.open_file).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Export PNGs...", command=self.export_layers).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Export PSD...", command=self.export_psd).pack(
            side="left", padx=2
        )
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(toolbar, text="Mode:").pack(side="left")
        self.mode_var = tk.StringVar(value="automatic")
        ttk.Radiobutton(
            toolbar, text="Automatic", variable=self.mode_var, value="automatic",
            command=self._on_mode_change,
        ).pack(side="left")
        ttk.Radiobutton(
            toolbar, text="Manual", variable=self.mode_var, value="manual",
            command=self._on_mode_change,
        ).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        self.auto_frame = ttk.Frame(toolbar)
        ttk.Label(self.auto_frame, text="Layers:").pack(side="left")
        self.num_layers_var = tk.IntVar(value=4)
        ttk.Spinbox(
            self.auto_frame, from_=2, to=12, textvariable=self.num_layers_var, width=4
        ).pack(side="left", padx=4)
        ttk.Button(self.auto_frame, text="Auto-Segment", command=self.run_auto_segment).pack(
            side="left", padx=4
        )

        self.manual_frame = ttk.Frame(toolbar)
        ttk.Label(self.manual_frame, text="Source layer:").pack(side="left")
        self.source_layer_var = tk.StringVar()
        self.source_layer_combo = ttk.Combobox(
            self.manual_frame, textvariable=self.source_layer_var, state="readonly", width=18
        )
        self.source_layer_combo.pack(side="left", padx=4)
        ttk.Label(self.manual_frame, text="New layer level:").pack(side="left", padx=(8, 0))
        self.new_level_var = tk.IntVar(value=0)
        ttk.Spinbox(
            self.manual_frame, from_=-50, to=50, textvariable=self.new_level_var, width=4
        ).pack(side="left", padx=4)
        ttk.Button(
            self.manual_frame, text="Create Layer from Selection",
            command=self.create_layer_from_selection,
        ).pack(side="left", padx=(8, 4))
        ttk.Button(self.manual_frame, text="Clear Selection", command=self.clear_selection).pack(
            side="left", padx=4
        )

    def _build_body(self) -> None:
        body = ttk.Frame(self.root)
        body.pack(side="top", fill="both", expand=True)

        self.canvas_view = CanvasView(body, on_polygon_complete=self._on_polygon_complete)
        self.canvas_view.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self.layer_panel = LayerPanel(body, on_change=self._on_layer_panel_change)
        self.layer_panel.pack(side="right", fill="y", padx=6, pady=6)

    def _build_statusbar(self) -> None:
        self.status_var = tk.StringVar(value="Open a JPEG, PNG, or PSD file to begin.")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken").pack(
            side="bottom", fill="x"
        )

    def _on_mode_change(self) -> None:
        manual = self.mode_var.get() == "manual"
        if manual:
            self.auto_frame.pack_forget()
            self.manual_frame.pack(side="left")
        else:
            self.manual_frame.pack_forget()
            self.auto_frame.pack(side="left")
        self.canvas_view.selecting_enabled = manual
        if not manual:
            self.clear_selection()

    # -- file operations -------------------------------------------------------
    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.psd"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.stack = load_document(path)
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))
            return

        self.current_path = path
        w, h = self.stack.canvas_size
        self.status_var.set(
            f"Loaded {os.path.basename(path)} ({w}x{h}) - {len(self.stack.layers)} layer(s)."
        )
        self._refresh_all()

    def export_layers(self) -> None:
        if self.stack is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        out_dir = filedialog.askdirectory(title="Choose export folder")
        if not out_dir:
            return
        base_name = os.path.splitext(os.path.basename(self.current_path or "layerz"))[0]
        try:
            written = export_layers(self.stack, out_dir, base_name=base_name)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.status_var.set(f"Exported {len(written)} file(s) to {out_dir}")
        messagebox.showinfo("Export complete", f"Wrote {len(written)} file(s) to:\n{out_dir}")

    def export_psd(self) -> None:
        if self.stack is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        base_name = os.path.splitext(os.path.basename(self.current_path or "layerz"))[0]
        path = filedialog.asksaveasfilename(
            title="Export as PSD",
            defaultextension=".psd",
            initialfile=f"{base_name}.psd",
            filetypes=[("Photoshop document", "*.psd")],
        )
        if not path:
            return
        try:
            export_psd(self.stack, path)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.status_var.set(f"Exported layered PSD to {path}")
        messagebox.showinfo("Export complete", f"Wrote layered PSD to:\n{path}")

    # -- automatic segmentation -------------------------------------------------
    def run_auto_segment(self) -> None:
        if self.stack is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        base = self.stack.composite()
        k = self.num_layers_var.get()
        try:
            regions = auto_segment(base, num_layers=k)
        except Exception as exc:
            messagebox.showerror("Segmentation failed", str(exc))
            return
        if not regions:
            messagebox.showinfo("No regions", "No distinct regions were found; try more layers.")
            return

        self.stack.clear()
        for i, region_img in enumerate(regions):
            name = "Background" if i == 0 else f"Region {i}"
            self.stack.add(Layer(name=name, image=region_img, level=i))
        self.status_var.set(f"Auto-segmented into {len(regions)} layer(s).")
        self._refresh_all()

    # -- manual segmentation -----------------------------------------------------
    def _on_polygon_complete(self, image_points: list[tuple[float, float]]) -> None:
        self._pending_polygon = image_points
        self.status_var.set(
            f"Selection ready ({len(image_points)} points). Click 'Create Layer from Selection'."
        )

    def clear_selection(self) -> None:
        self._pending_polygon = None
        self.canvas_view.clear_selection()

    def create_layer_from_selection(self) -> None:
        if self.stack is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        points = self._pending_polygon
        if not points or len(points) < 3:
            messagebox.showwarning("No selection", "Draw a lasso selection on the image first.")
            return

        source_label = self.source_layer_var.get()
        if not source_label:
            messagebox.showwarning("No source layer", "Choose a source layer.")
            return
        source_id = int(source_label.split(":")[0])
        source_layer = self.stack.get(source_id)
        if source_layer is None:
            messagebox.showerror("Error", "Source layer no longer exists.")
            return

        mask = polygon_mask(self.stack.canvas_size, points)
        extracted, remainder = cut_region(source_layer.image, mask)
        source_layer.image = remainder

        level = self.new_level_var.get()
        new_layer = Layer(name=f"Selection {len(self.stack.layers) + 1}", image=extracted, level=level)
        self.stack.add(new_layer)

        self.clear_selection()
        self.status_var.set(f"Created layer '{new_layer.name}' at level {level}.")
        self._refresh_all()

    # -- layer panel callbacks ---------------------------------------------------
    def _on_layer_panel_change(self, layer_id: int, **kwargs) -> None:
        if self.stack is None:
            return
        if kwargs.get("delete"):
            self.stack.remove(layer_id)
            self._refresh_all()
            return
        layer = self.stack.get(layer_id)
        if layer is None:
            return
        if "level" in kwargs:
            layer.level = kwargs["level"]
        if "visible" in kwargs:
            layer.visible = kwargs["visible"]
        self._refresh_all()

    # -- shared refresh ---------------------------------------------------------
    def _refresh_all(self) -> None:
        if self.stack is None:
            return
        self.canvas_view.set_image(self.stack.composite())
        self.layer_panel.set_layers(self.stack.ordered())

        values = [f"{l.id}: {l.name}" for l in self.stack.layers]
        self.source_layer_combo["values"] = values
        if values and self.source_layer_var.get() not in values:
            self.source_layer_var.set(values[0])
        self.new_level_var.set(self.stack.next_default_level())


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    LayerZApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
