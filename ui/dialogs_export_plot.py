# specdiggeranalyse/ui/dialogs_export_plot.py
# -*- coding: utf-8 -*-

"""
Plot export dialog for SpecDiggerAnalyse (v2.5.6 compatible).

Exports main and/or combined plots to PNG/SVG/PDF.
Key requirement: exported plots match the GUI sizing (axes_w_in/axes_h_in/margins_in).

Design:
- Create a fresh Figure for export (avoid mutating embedded Tk figures)
- Apply sizing helper based on plot cfg
- Call plotting.draw_main / draw_combined to render
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from matplotlib.figure import Figure

from ..plotting import draw_main, draw_combined


@dataclass(slots=True)
class ExportPlotRequest:
    target: str  # "main" | "combined" | "both"
    fmt: str     # "png" | "svg" | "pdf"
    dpi: int
    transparent: bool
    tight: bool


def apply_fig_sizing(fig: Figure, cfg: Dict[str, Any]) -> None:
    """
    Same logic as app.py _apply_fig_sizing, but standalone for export.
    """
    axes_w = cfg.get("axes_w_in", None)
    axes_h = cfg.get("axes_h_in", None)
    margins = cfg.get("margins_in", (0.8, 0.25, 0.35, 0.8))

    if axes_w is None or axes_h is None:
        return

    try:
        axes_w = float(axes_w)
        axes_h = float(axes_h)
    except Exception:
        return

    try:
        L, R, T, B = margins
        L = float(L); R = float(R); T = float(T); B = float(B)
    except Exception:
        L, R, T, B = 0.8, 0.25, 0.35, 0.8

    axes_w = max(0.1, axes_w)
    axes_h = max(0.1, axes_h)
    L = max(0.0, L); R = max(0.0, R); T = max(0.0, T); B = max(0.0, B)

    fig_w = L + axes_w + R
    fig_h = B + axes_h + T
    if fig_w <= 0 or fig_h <= 0:
        return

    fig.set_size_inches(fig_w, fig_h, forward=True)

    left = L / fig_w
    right = 1.0 - (R / fig_w)
    bottom = B / fig_h
    top = 1.0 - (T / fig_h)

    left = min(max(left, 0.0), 0.95)
    right = min(max(right, left + 0.01), 1.0)
    bottom = min(max(bottom, 0.0), 0.95)
    top = min(max(top, bottom + 0.01), 1.0)

    fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)


class ExportPlotDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk | tk.Toplevel):
        super().__init__(parent)
        self.title("Export plot(s)")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[ExportPlotRequest] = None

        self.var_target = tk.StringVar(value="main")
        self.var_fmt = tk.StringVar(value="png")
        self.var_dpi = tk.StringVar(value="300")
        self.var_transparent = tk.BooleanVar(value=False)
        self.var_tight = tk.BooleanVar(value=True)

        pad = 10
        frm = ttk.Frame(self, padding=pad)
        frm.grid(row=0, column=0, sticky="nsew")

        frm.grid_columnconfigure(1, weight=1)

        r = 0
        ttk.Label(frm, text="Target").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frm,
            textvariable=self.var_target,
            values=["main", "combined", "both"],
            state="readonly",
            width=18,
        ).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(frm, text="Format").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frm,
            textvariable=self.var_fmt,
            values=["png", "svg", "pdf"],
            state="readonly",
            width=18,
        ).grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        ttk.Label(frm, text="DPI (PNG)").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.var_dpi, width=10).grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Checkbutton(frm, text="Transparent background", variable=self.var_transparent).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(6, 2)
        )
        r += 1

        ttk.Checkbutton(frm, text="Tight bounding box", variable=self.var_tight).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(2, 8)
        )
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        btns.grid_columnconfigure(0, weight=1)

        ttk.Button(btns, text="Cancel", command=self._on_cancel).grid(row=0, column=1, sticky="e", padx=(0, 6))
        ttk.Button(btns, text="OK", command=self._on_ok).grid(row=0, column=2, sticky="e")

        self.bind("<Escape>", lambda e: self._on_cancel(), add=True)
        self.bind("<Control-Return>", lambda e: self._on_ok(), add=True)

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    def _on_ok(self) -> None:
        fmt = self.var_fmt.get().strip().lower()
        if fmt not in ("png", "svg", "pdf"):
            messagebox.showerror("Export plot", "Invalid format.", parent=self)
            return

        try:
            dpi = int(float(self.var_dpi.get().strip()))
            dpi = max(72, min(1200, dpi))
        except Exception:
            dpi = 300

        self.result = ExportPlotRequest(
            target=self.var_target.get().strip().lower(),
            fmt=fmt,
            dpi=dpi,
            transparent=bool(self.var_transparent.get()),
            tight=bool(self.var_tight.get()),
        )
        self.destroy()


def ask_export_plot(parent: tk.Tk | tk.Toplevel) -> Optional[ExportPlotRequest]:
    dlg = ExportPlotDialog(parent)
    parent.wait_window(dlg)
    return dlg.result


def export_plot_files(
    *,
    out_base: Path,
    req: ExportPlotRequest,
    df_main,
    per_file_matrix_main,
    cfg_main: Dict[str, Any],
    df_combined,
    per_file_matrix_combined,
    cfg_combined: Dict[str, Any],
    sig_pairs: Sequence[Tuple[str, str, float]] = (),
) -> list[Path]:
    """
    Render and save plot(s) according to request.
    Returns list of written paths.
    """
    out_base = Path(out_base)
    fmt = req.fmt

    written: list[Path] = []

    def save_one(kind: str) -> Path:
        # Build a fresh figure
        fig = Figure(figsize=(6.5, 4.0), dpi=100)
        ax = fig.add_subplot(111)

        if kind == "main":
            apply_fig_sizing(fig, cfg_main)
            draw_main(
                ax=ax,
                df_main=df_main,
                per_file_matrix_main=per_file_matrix_main,
                plot_cfg_main=cfg_main,
                title="Separate species",
                ylabel="relative (%)",
            )
        else:
            apply_fig_sizing(fig, cfg_combined)
            draw_combined(
                ax=ax,
                df_combined=df_combined,
                per_file_matrix_combined=per_file_matrix_combined,
                plot_cfg_combined=cfg_combined,
                sig_pairs=list(sig_pairs) if sig_pairs else None,
                title="Combined Mg pairs",
                ylabel="relative (%)",
            )

        suffix = f"_{kind}.{fmt}"
        out = out_base.with_suffix("")  # drop any existing suffix
        out = out.with_name(out.name + suffix)

        save_kwargs = {}
        if fmt == "png":
            save_kwargs["dpi"] = req.dpi
        save_kwargs["transparent"] = req.transparent
        if req.tight:
            save_kwargs["bbox_inches"] = "tight"

        fig.savefig(str(out), format=fmt, **save_kwargs)
        return out

    if req.target in ("main", "both"):
        written.append(save_one("main"))
    if req.target in ("combined", "both"):
        written.append(save_one("combined"))

    return written


__all__ = [
    "ExportPlotRequest",
    "ask_export_plot",
    "export_plot_files",
    "apply_fig_sizing",
]