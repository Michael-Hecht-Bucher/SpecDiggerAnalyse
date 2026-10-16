# specdiggeranalyse/ui/dialogs_customize_plot.py
# -*- coding: utf-8 -*-

"""
Plot customization dialog (v2.5.6 compatible).

Edits the dict-based plot config in AppState.plots.{main,combined}.
Keys supported (from constants DEFAULT_PLOT_CFG_*):
- bar_width
- bar_color
- bars_alpha
- edgecolor
- edgewidth
- show_points
- point_color (optional; None means default matplotlib)
- jitter_width
- jitter_seed
- show_errorbars
- xtick_rotation
- xtick_ha
- grid
- spacing
- y_headroom
- axes_w_in / axes_h_in (inches) + margins_in (L, R, T, B inches)
- (legacy) fig_w / fig_h remain but are not necessary if axes sizes are used

This dialog:
- does NOT redraw plots; app.py should do that after Apply/OK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox


@dataclass(slots=True)
class PlotDialogResult:
    applied: bool
    which: str  # "main" or "combined"
    cfg: Dict[str, Any]


# -----------------------------
# Helpers
# -----------------------------
from typing import overload, Literal, Optional

@overload
def _to_float(x: str, *, allow_empty: Literal[False] = False) -> float: ...
@overload
def _to_float(x: str, *, allow_empty: Literal[True]) -> Optional[float]: ...

def _to_float(x: str, *, allow_empty: bool = False) -> Optional[float]:
    s = str(x).strip()
    if not s:
        return None if allow_empty else 0.0
    s = s.replace(",", ".")
    return float(s)


@overload
def _to_int(x: str, *, allow_empty: Literal[False] = False) -> int: ...
@overload
def _to_int(x: str, *, allow_empty: Literal[True]) -> Optional[int]: ...

def _to_int(x: str, *, allow_empty: bool = False) -> Optional[int]:
    s = str(x).strip()
    if not s:
        return None if allow_empty else 0
    return int(float(s.replace(",", ".")))


def _to_tuple4_in(x: str) -> Tuple[float, float, float, float]:
    """
    Parse "L,R,T,B" inches.
    Accept separators comma or semicolon; allow whitespace.
    """
    s = str(x).strip()
    if not s:
        raise ValueError("margins_in is empty. Provide four values: L,R,T,B (in inches).")
    s = s.replace(";", ",")
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    if len(parts) != 4:
        raise ValueError("margins_in must have four numbers: L,R,T,B (in inches).")
    vals = tuple(float(p.replace(",", ".")) for p in parts)
    return vals  # type: ignore[return-value]


def _as_str4(t: Tuple[float, float, float, float]) -> str:
    return f"{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}, {t[3]:.2f}"


# -----------------------------
# Dialog
# -----------------------------
class CustomizePlotDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        *,
        cfg_main: Dict[str, Any],
        cfg_combined: Dict[str, Any],
        title: str = "Plot settings",
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._cfg_main = cfg_main
        self._cfg_combined = cfg_combined
        self.result: Optional[PlotDialogResult] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ttk.Frame(self, padding=(10, 10, 10, 6))
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        ttk.Label(hdr, text="Plot customization", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.var_which = tk.StringVar(value="main")
        ttk.Label(hdr, text="Target:").grid(row=0, column=1, sticky="e", padx=(0, 6))
        self.cmb_which = ttk.Combobox(
            hdr, textvariable=self.var_which, values=["main", "combined"], state="readonly", width=12
        )
        self.cmb_which.grid(row=0, column=2, sticky="e")

        # Body with notebook tabs
        body = ttk.Frame(self, padding=(10, 0, 10, 10))
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        nb = ttk.Notebook(body)
        nb.grid(row=0, column=0, sticky="nsew")
        self.nb = nb

        self._frm_general = ttk.Frame(nb, padding=10)
        self._frm_axes = ttk.Frame(nb, padding=10)
        nb.add(self._frm_general, text="General")
        nb.add(self._frm_axes, text="Axes size & margins")

        # Button row
        btns = ttk.Frame(body)
        btns.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        btns.grid_columnconfigure(0, weight=1)

        self.btn_reset = ttk.Button(btns, text="Reset tab", command=self._on_reset_tab)
        self.btn_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        self.btn_apply = ttk.Button(btns, text="Apply", command=self._on_apply)
        self.btn_ok = ttk.Button(btns, text="OK", command=self._on_ok)

        self.btn_reset.grid(row=0, column=0, sticky="w")
        self.btn_cancel.grid(row=0, column=1, sticky="e", padx=(0, 6))
        self.btn_apply.grid(row=0, column=2, sticky="e", padx=(0, 6))
        self.btn_ok.grid(row=0, column=3, sticky="e")

        # Build forms
        self._build_general_form(self._frm_general)
        self._build_axes_form(self._frm_axes)

        # Initial fill
        self._load_cfg_into_form(self._current_cfg())

        # Events
        self.bind("<Escape>", lambda e: self._on_cancel(), add=True)
        self.bind("<Control-Return>", lambda e: self._on_ok(), add=True)
        self.cmb_which.bind("<<ComboboxSelected>>", lambda e: self._on_switch_target(), add=True)

        self.geometry("760x560")

    # -----------------------------
    # Form construction
    # -----------------------------
    def _build_general_form(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(1, weight=1)

        r = 0
        ttk.Label(parent, text="Bars").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        self.ent_bar_width = self._row_entry(parent, r, "Bar width", "0.65"); r += 1
        self.ent_bars_alpha = self._row_entry(parent, r, "Bar alpha", "1.0"); r += 1
        self.ent_bar_color = self._row_entry(parent, r, "Bar color (hex)", "#FFFFFF"); r += 1
        self.ent_edgecolor = self._row_entry(parent, r, "Edge color (hex)", "#000000"); r += 1
        self.ent_edgewidth = self._row_entry(parent, r, "Edge width", "1.0"); r += 1

        ttk.Separator(parent).grid(row=r, column=0, columnspan=2, sticky="ew", pady=10); r += 1

        ttk.Label(parent, text="Points & error bars").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        self.var_show_points = tk.BooleanVar(value=True)
        self.chk_show_points = ttk.Checkbutton(parent, text="Show per-file points", variable=self.var_show_points)
        self.chk_show_points.grid(row=r, column=0, columnspan=2, sticky="w"); r += 1

        self.ent_point_color = self._row_entry(parent, r, "Point color (optional hex)", ""); r += 1
        self.ent_jitter_width = self._row_entry(parent, r, "Jitter width", "0.12"); r += 1
        self.ent_jitter_seed = self._row_entry(parent, r, "Jitter seed (int)", "0"); r += 1

        self.var_show_errorbars = tk.BooleanVar(value=True)
        self.chk_show_errorbars = ttk.Checkbutton(parent, text="Show error bars (SD)", variable=self.var_show_errorbars)
        self.chk_show_errorbars.grid(row=r, column=0, columnspan=2, sticky="w"); r += 1

        ttk.Separator(parent).grid(row=r, column=0, columnspan=2, sticky="ew", pady=10); r += 1

        ttk.Label(parent, text="Axes / ticks").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        self.var_grid = tk.BooleanVar(value=False)
        self.chk_grid = ttk.Checkbutton(parent, text="Show horizontal grid", variable=self.var_grid)
        self.chk_grid.grid(row=r, column=0, columnspan=2, sticky="w"); r += 1

        self.ent_spacing = self._row_entry(parent, r, "Category spacing", "1.0"); r += 1
        self.ent_y_headroom = self._row_entry(parent, r, "Y headroom", "10.0"); r += 1
        self.ent_ylim_min = self._row_entry(parent, r, "Y min (optional)", ""); r += 1
        self.ent_ylim_max = self._row_entry(parent, r, "Y max (optional)", ""); r += 1
        self.ent_xtick_rotation = self._row_entry(parent, r, "X tick rotation", "45"); r += 1

        # tick horizontal alignment as combobox
        ttk.Label(parent, text="X tick alignment").grid(row=r, column=0, sticky="w", pady=2)
        self.var_xtick_ha = tk.StringVar(value="right")
        self.cmb_xtick_ha = ttk.Combobox(parent, textvariable=self.var_xtick_ha,
                                         values=["left", "center", "right"], state="readonly", width=10)
        self.cmb_xtick_ha.grid(row=r, column=1, sticky="ew", pady=2)
        r += 1

    def _build_axes_form(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(1, weight=1)
        r = 0
        ttk.Label(parent, text="Axes sizing (inches)").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        self.ent_axes_w_in = self._row_entry(parent, r, "Axes width (in)", ""); r += 1
        self.ent_axes_h_in = self._row_entry(parent, r, "Axes height (in)", ""); r += 1

        ttk.Separator(parent).grid(row=r, column=0, columnspan=2, sticky="ew", pady=10); r += 1

        ttk.Label(parent, text="Margins (inches)").grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1
        self.ent_margins_in = self._row_entry(parent, r, "Margins L,R,T,B (in)", "0.80, 0.25, 0.35, 0.80"); r += 1

        ttk.Label(
            parent,
            text="Tip: Leave axes width/height empty to use legacy fig_h/fig_w behavior.",
            foreground="#444444",
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 0))
        r += 1

    def _row_entry(self, parent: ttk.Frame, row: int, label: str, default: str) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        e = ttk.Entry(parent)
        e.grid(row=row, column=1, sticky="ew", pady=2)
        e.insert(0, default)
        return e

    # -----------------------------
    # Config selection and load/save
    # -----------------------------
    def _current_cfg(self) -> Dict[str, Any]:
        return self._cfg_main if self.var_which.get() == "main" else self._cfg_combined

    def _on_switch_target(self) -> None:
        self._load_cfg_into_form(self._current_cfg())

    def _load_cfg_into_form(self, cfg: Dict[str, Any]) -> None:
        # Bars
        self._set_entry(self.ent_bar_width, cfg.get("bar_width", ""))
        self._set_entry(self.ent_bars_alpha, cfg.get("bars_alpha", ""))
        self._set_entry(self.ent_bar_color, cfg.get("bar_color", ""))
        self._set_entry(self.ent_edgecolor, cfg.get("edgecolor", ""))
        self._set_entry(self.ent_edgewidth, cfg.get("edgewidth", ""))

        # Points
        self.var_show_points.set(bool(cfg.get("show_points", True)))
        pc = cfg.get("point_color", None)
        self._set_entry(self.ent_point_color, "" if pc is None else str(pc))
        self._set_entry(self.ent_jitter_width, cfg.get("jitter_width", ""))
        self._set_entry(self.ent_jitter_seed, cfg.get("jitter_seed", ""))

        # Error bars
        self.var_show_errorbars.set(bool(cfg.get("show_errorbars", True)))

        # Axis/ticks
        self.var_grid.set(bool(cfg.get("grid", False)))
        self._set_entry(self.ent_spacing, cfg.get("spacing", ""))
        self._set_entry(self.ent_y_headroom, cfg.get("y_headroom", ""))
        self._set_entry(self.ent_ylim_min, cfg.get("ylim_min", ""))
        self._set_entry(self.ent_ylim_max, cfg.get("ylim_max", ""))
        self._set_entry(self.ent_xtick_rotation, cfg.get("xtick_rotation", ""))
        self.var_xtick_ha.set(str(cfg.get("xtick_ha", "right")))

        # Axes sizing
        self._set_entry(self.ent_axes_w_in, cfg.get("axes_w_in", ""))
        self._set_entry(self.ent_axes_h_in, cfg.get("axes_h_in", ""))

        margins = cfg.get("margins_in", (0.8, 0.25, 0.35, 0.8))
        try:
            self._set_entry(self.ent_margins_in, _as_str4(tuple(margins)))  # type: ignore[arg-type]
        except Exception:
            self._set_entry(self.ent_margins_in, "0.80, 0.25, 0.35, 0.80")

    def _read_form_into_cfg(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}

        # Bars
        cfg["bar_width"] = _to_float(self.ent_bar_width.get())
        cfg["bars_alpha"] = _to_float(self.ent_bars_alpha.get())
        cfg["bar_color"] = self.ent_bar_color.get().strip() or "#FFFFFF"
        cfg["edgecolor"] = self.ent_edgecolor.get().strip() or "#000000"
        cfg["edgewidth"] = _to_float(self.ent_edgewidth.get())

        # Points
        cfg["show_points"] = bool(self.var_show_points.get())
        pc = self.ent_point_color.get().strip()
        cfg["point_color"] = pc if pc else None
        cfg["jitter_width"] = _to_float(self.ent_jitter_width.get())
        cfg["jitter_seed"] = _to_int(self.ent_jitter_seed.get())

        # Error bars
        cfg["show_errorbars"] = bool(self.var_show_errorbars.get())

        # Axis/ticks
        cfg["grid"] = bool(self.var_grid.get())
        cfg["spacing"] = _to_float(self.ent_spacing.get())
        cfg["y_headroom"] = _to_float(self.ent_y_headroom.get())
        cfg["ylim_min"] = _to_float(self.ent_ylim_min.get(), allow_empty=True)
        cfg["ylim_max"] = _to_float(self.ent_ylim_max.get(), allow_empty=True)
        cfg["xtick_rotation"] = _to_int(self.ent_xtick_rotation.get())
        cfg["xtick_ha"] = self.var_xtick_ha.get().strip() or "right"

        # Axes sizing
        cfg["axes_w_in"] = _to_float(self.ent_axes_w_in.get(), allow_empty=True)
        cfg["axes_h_in"] = _to_float(self.ent_axes_h_in.get(), allow_empty=True)
        cfg["margins_in"] = _to_tuple4_in(self.ent_margins_in.get())

        return cfg

    @staticmethod
    def _set_entry(ent: ttk.Entry, value: Any) -> None:
        ent.delete(0, tk.END)
        if value is None:
            return
        ent.insert(0, str(value))

    # -----------------------------
    # Buttons
    # -----------------------------
    def _on_reset_tab(self) -> None:
        # Reset just the current tab to a safe baseline (does not touch stored cfg)
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            # General tab reset values
            self.ent_bar_width.delete(0, tk.END); self.ent_bar_width.insert(0, "0.65")
            self.ent_bars_alpha.delete(0, tk.END); self.ent_bars_alpha.insert(0, "1.0")
            self.ent_bar_color.delete(0, tk.END); self.ent_bar_color.insert(0, "#FFFFFF")
            self.ent_edgecolor.delete(0, tk.END); self.ent_edgecolor.insert(0, "#000000")
            self.ent_edgewidth.delete(0, tk.END); self.ent_edgewidth.insert(0, "1.0")

            self.var_show_points.set(True)
            self.ent_point_color.delete(0, tk.END)
            self.ent_jitter_width.delete(0, tk.END); self.ent_jitter_width.insert(0, "0.12")
            self.ent_jitter_seed.delete(0, tk.END); self.ent_jitter_seed.insert(0, "0")

            self.var_show_errorbars.set(True)

            self.var_grid.set(False)
            self.ent_spacing.delete(0, tk.END); self.ent_spacing.insert(0, "1.0")
            self.ent_y_headroom.delete(0, tk.END); self.ent_y_headroom.insert(0, "10.0")
            self.ent_ylim_min.delete(0, tk.END)
            self.ent_ylim_max.delete(0, tk.END)
            self.ent_xtick_rotation.delete(0, tk.END); self.ent_xtick_rotation.insert(0, "45")
            self.var_xtick_ha.set("right")
        else:
            # Axes tab reset values
            self.ent_axes_w_in.delete(0, tk.END)
            self.ent_axes_h_in.delete(0, tk.END)
            self.ent_margins_in.delete(0, tk.END); self.ent_margins_in.insert(0, "0.80, 0.25, 0.35, 0.80")

    def _apply(self) -> bool:
        try:
            cfg_new = self._read_form_into_cfg()
        except Exception as e:
            messagebox.showerror("Invalid plot settings", str(e), parent=self)
            return False

        target = self.var_which.get()
        if target == "main":
            self._cfg_main.update(cfg_new)
            self.result = PlotDialogResult(applied=True, which="main", cfg=dict(self._cfg_main))
        else:
            self._cfg_combined.update(cfg_new)
            self.result = PlotDialogResult(applied=True, which="combined", cfg=dict(self._cfg_combined))
        return True

    def _on_apply(self) -> None:
        self._apply()

    def _on_ok(self) -> None:
        if self._apply():
            self.destroy()

    def _on_cancel(self) -> None:
        self.result = PlotDialogResult(applied=False, which=self.var_which.get(), cfg={})
        self.destroy()


def open_customize_plot_dialog(
    parent: tk.Tk | tk.Toplevel,
    *,
    cfg_main: Dict[str, Any],
    cfg_combined: Dict[str, Any],
) -> bool:
    """
    Open the dialog modally. Returns True if the user applied changes.
    """
    dlg = CustomizePlotDialog(parent, cfg_main=cfg_main, cfg_combined=cfg_combined)
    parent.wait_window(dlg)
    return bool(dlg.result and dlg.result.applied)


__all__ = ["open_customize_plot_dialog", "CustomizePlotDialog", "PlotDialogResult"]