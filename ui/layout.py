# specdiggeranalyse/ui/layout.py
# -*- coding: utf-8 -*-

"""
UI layout builder for SpecDiggerAnalyse.

Goal:
- Centralize widget construction + geometry (grid/pack)
- Keep event wiring / callbacks out of here as much as possible
- Return a dict of references so app.py can bind commands/events later

This is a "best-effort" layout that matches the structure of your current monolith:
- top control bar (load, export, options)
- left tables (main + combined)
- right plots (main + combined)
- status bar

You can adapt labels/buttons as you migrate more of the original UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import tkinter as tk
from tkinter import ttk

from .widgets import EditableTreeview


@dataclass(slots=True)
class UILayout:
    """Convenience container for UI element references."""
    root: tk.Tk

    # top controls
    btn_load: ttk.Button
    btn_export_csv: ttk.Button
    btn_export_xlsx: ttk.Button
    btn_aliases: ttk.Button
    btn_species_table: ttk.Button
    btn_plot_cfg: ttk.Button
    btn_recompute: ttk.Button
    btn_export_plots: ttk.Button

    # normalization selection
    lbl_norm: ttk.Label
    lst_norm: tk.Listbox
    btn_norm_add_from_table: ttk.Button
    btn_norm_clear: ttk.Button
    btn_norm_all: ttk.Button

    # tables
    tree_main: EditableTreeview
    tree_combined: EditableTreeview

    # plot containers (frames where app.py will embed FigureCanvasTkAgg)
    plot_frame_main: ttk.Widget
    plot_frame_combined: ttk.Widget

    # status
    status_var: tk.StringVar
    status_label: ttk.Label

    # other useful frames
    frame_tables: ttk.Frame
    frame_plots: ttk.Frame


def _make_tree(parent: ttk.Frame, columns: tuple[str, ...]) -> EditableTreeview:
    tree = EditableTreeview(parent, columns=columns, show="headings", selectmode="browse")
    for c in columns:
        tree.heading(c, text=c)
        # default widths; app.py can refine later
        w = 160
        if c.lower() in ("species", "base", "group"):
            w = 240
        if "mean" in c.lower() or c.lower() in ("sd", "n"):
            w = 110
        tree.column(c, width=w, anchor="w", stretch=True)
    return tree


def build_ui(root: tk.Tk) -> UILayout:
    """
    Construct the GUI layout and return references to key widgets.

    App wiring happens in app.py (commands, bindings, plot embedding).
    """
    root.title("SpecDiggerAnalyse")
    root.minsize(1180, 720)

    # Use ttk theme defaults
    style = ttk.Style(root)
    try:
        style.theme_use(style.theme_use())
    except Exception:
        pass

    # Root grid: top bar, main content, status bar
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # -------------------------------------------------------------------------
    # Top control bar
    # -------------------------------------------------------------------------
    top = ttk.Frame(root, padding=(8, 8, 8, 4))
    top.grid(row=0, column=0, sticky="ew")
    top.grid_columnconfigure(20, weight=1)  # spacer stretch

    btn_load = ttk.Button(top, text="Load Excel files…")
    btn_recompute = ttk.Button(top, text="Recompute")
    btn_export_csv = ttk.Button(top, text="Export CSV…")
    btn_export_xlsx = ttk.Button(top, text="Export XLSX…")
    btn_aliases = ttk.Button(top, text="Aliases…")
    btn_species_table = ttk.Button(top, text="Species table…")
    btn_plot_cfg = ttk.Button(top, text="Plot settings…")
    btn_export_plots = ttk.Button(top, text="Export plots…")
    btn_load.grid(row=0, column=0, padx=(0, 6))
    btn_recompute.grid(row=0, column=1, padx=(0, 14))
    btn_export_csv.grid(row=0, column=2, padx=(0, 6))
    btn_export_xlsx.grid(row=0, column=3, padx=(0, 14))
    btn_aliases.grid(row=0, column=4, padx=(0, 6))
    btn_species_table.grid(row=0, column=5, padx=(0, 6))
    btn_plot_cfg.grid(row=0, column=6, padx=(0, 6))
    btn_export_plots.grid(row=0, column=7, padx=(0, 6))

    # -------------------------------------------------------------------------
    # Main content: horizontal PanedWindow (left=tables, right=plots)
    # -------------------------------------------------------------------------
    main = ttk.PanedWindow(root, orient="horizontal")
    main.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 4))

    frame_tables = ttk.Frame(main, padding=(0, 0, 6, 0))
    frame_plots = ttk.Frame(main, padding=(6, 0, 0, 0))
    main.add(frame_tables, weight=1)
    main.add(frame_plots, weight=2)

    # -------------------------------------------------------------------------
    # Left side: normalization selection + two tables (main, combined)
    # -------------------------------------------------------------------------
    frame_tables.grid_rowconfigure(2, weight=1)
    frame_tables.grid_rowconfigure(4, weight=1)
    frame_tables.grid_columnconfigure(0, weight=1)

    # Normalization selection box
    norm_box = ttk.Labelframe(frame_tables, text="Normalization (Unbound selection)", padding=8)
    norm_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    norm_box.grid_columnconfigure(0, weight=1)
    norm_box.grid_rowconfigure(1, weight=1)

    lbl_norm = ttk.Label(norm_box, text="Select one or more species used as denominator (sum A(real)).")
    lbl_norm.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

    lst_norm = tk.Listbox(norm_box, height=5, selectmode=tk.EXTENDED)
    lst_norm.grid(row=1, column=0, sticky="ew", padx=(0, 8))

    btn_norm_add_from_table = ttk.Button(norm_box, text="Add from selected row")
    btn_norm_clear = ttk.Button(norm_box, text="Clear selection")
    btn_norm_add_from_table.grid(row=1, column=1, sticky="ew", padx=(0, 6))
    btn_norm_clear.grid(row=1, column=2, sticky="ew")
    btn_norm_all = ttk.Button(norm_box, text="Normalize on all species")
    btn_norm_all.grid(row=2, column=0, columnspan=3, padx=(0, 6), pady=(6, 0), sticky="ew")

    # Main table
    lbl_main = ttk.Label(frame_tables, text="Separate species (main)")
    lbl_main.grid(row=1, column=0, sticky="w")

    table_main_box = ttk.Frame(frame_tables)
    table_main_box.grid(row=2, column=0, sticky="nsew", pady=(2, 10))
    table_main_box.grid_rowconfigure(0, weight=1)
    table_main_box.grid_columnconfigure(0, weight=1)

    tree_main = _make_tree(
        table_main_box,
        columns=("species", "mean_relative_%", "sd", "n"),
    )
    ysb1 = ttk.Scrollbar(table_main_box, orient="vertical", command=tree_main.yview)
    xsb1 = ttk.Scrollbar(table_main_box, orient="horizontal", command=tree_main.xview)
    tree_main.configure(yscrollcommand=ysb1.set, xscrollcommand=xsb1.set)

    tree_main.grid(row=0, column=0, sticky="nsew")
    ysb1.grid(row=0, column=1, sticky="ns")
    xsb1.grid(row=1, column=0, sticky="ew")

    # Combined table
    lbl_comb = ttk.Label(frame_tables, text="Combined Mg pairs (base species)")
    lbl_comb.grid(row=3, column=0, sticky="w")

    table_comb_box = ttk.Frame(frame_tables)
    table_comb_box.grid(row=4, column=0, sticky="nsew", pady=(2, 0))
    table_comb_box.grid_rowconfigure(0, weight=1)
    table_comb_box.grid_columnconfigure(0, weight=1)

    tree_combined = _make_tree(
        table_comb_box,
        columns=("species", "mean_relative_%", "sd", "n"),
    )
    ysb2 = ttk.Scrollbar(table_comb_box, orient="vertical", command=tree_combined.yview)
    xsb2 = ttk.Scrollbar(table_comb_box, orient="horizontal", command=tree_combined.xview)
    tree_combined.configure(yscrollcommand=ysb2.set, xscrollcommand=xsb2.set)

    tree_combined.grid(row=0, column=0, sticky="nsew")
    ysb2.grid(row=0, column=1, sticky="ns")
    xsb2.grid(row=1, column=0, sticky="ew")

    # -------------------------------------------------------------------------
    # Right side: two plot frames stacked vertically
    # -------------------------------------------------------------------------
    frame_plots.grid_rowconfigure(0, weight=1)
    frame_plots.grid_rowconfigure(1, weight=1)
    frame_plots.grid_columnconfigure(0, weight=1)

    plot_frame_main = ttk.Labelframe(frame_plots, text="Plot: Separate species", padding=6)
    plot_frame_combined = ttk.Labelframe(frame_plots, text="Plot: Combined Mg pairs", padding=6)
    plot_frame_main.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    plot_frame_combined.grid(row=1, column=0, sticky="nsew")

    # Add placeholder labels; app.py will replace with matplotlib canvases
    ttk.Label(plot_frame_main, text="(Plot canvas will be embedded here)").pack(anchor="center", expand=True)
    ttk.Label(plot_frame_combined, text="(Plot canvas will be embedded here)").pack(anchor="center", expand=True)

    # -------------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------------
    status = ttk.Frame(root, padding=(8, 4))
    status.grid(row=2, column=0, sticky="ew")
    status.grid_columnconfigure(0, weight=1)

    status_var = tk.StringVar(value="Ready.")
    status_label = ttk.Label(status, textvariable=status_var, anchor="w")
    status_label.grid(row=0, column=0, sticky="ew")

    return UILayout(
        root=root,
        btn_load=btn_load,
        btn_export_csv=btn_export_csv,
        btn_export_xlsx=btn_export_xlsx,
        btn_export_plots=btn_export_plots,
        btn_aliases=btn_aliases,
        btn_species_table=btn_species_table,
        btn_plot_cfg=btn_plot_cfg,
        btn_recompute=btn_recompute,
        lbl_norm=lbl_norm,
        lst_norm=lst_norm,
        btn_norm_add_from_table=btn_norm_add_from_table,
        btn_norm_all=btn_norm_all,
        btn_norm_clear=btn_norm_clear,
        tree_main=tree_main,
        tree_combined=tree_combined,
        plot_frame_main=plot_frame_main,
        plot_frame_combined=plot_frame_combined,
        status_var=status_var,
        status_label=status_label,
        frame_tables=frame_tables,
        frame_plots=frame_plots,
    )


__all__ = ["UILayout", "build_ui"]
