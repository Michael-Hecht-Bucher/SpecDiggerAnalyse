# specdiggeranalyse/app.py
# -*- coding: utf-8 -*-

"""
SpecDiggerAnalyse v2.5.6-compatible app wiring (Tk + matplotlib + controllers).

This module:
- builds the UI layout (ui/layout.py)
- owns AppState
- binds UI events to controller recomputation
- renders tables and plots

Dialogs (aliases/species table/plot settings) can be plugged in later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Dict, Any, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd

import matplotlib
matplotlib.use("TkAgg")  # safe explicit backend for Tk embedding
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk

from .controllers import load_files_into_state, recompute_all, recompute_combined
from .io_export import export_csv_bundle, export_xlsx
from .models import AppState
from .plotting import draw_main, draw_combined
from .ui.layout import UILayout, build_ui

from .ui.dialogs_alias import open_aliases_dialog

from .ui.dialogs_customize_plot import open_customize_plot_dialog
from .ui.dialogs_export_plot import ask_export_plot, export_plot_files
from .ui.dialogs_per_file import open_per_file_dialog
from .ui.dialogs_species_table import ask_species_table_rows

if TYPE_CHECKING:
    import pandas as pd


@dataclass(slots=True)
class PlotHandles:
    fig: Figure
    ax: Axes
    canvas: FigureCanvasTkAgg
    toolbar: NavigationToolbar2Tk


class SpecDiggerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.state = AppState()
        self.ui: UILayout = build_ui(root)

        # Replace placeholder labels in plot frames with matplotlib canvases
        self.plot_main = self._embed_plot(self.ui.plot_frame_main)
        self.plot_combined = self._embed_plot(self.ui.plot_frame_combined)

        # Wire buttons / interactions
        self._bind_events()

        # Initial render
        self._render_all()

    # ---------------------------------------------------------------------
    # UI embedding
    # ---------------------------------------------------------------------
    def _embed_plot(self, frame: ttk.Widget) -> PlotHandles:
        # Remove placeholder children if any (layout.py adds labels)
        for child in frame.winfo_children():
            child.destroy()

        fig = Figure(figsize=(6.5, 4.0), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, frame)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        return PlotHandles(fig=fig, ax=ax, canvas=canvas, toolbar=toolbar)

    def _bind_events(self) -> None:
        self.ui.btn_load.configure(command=self.on_load_files)
        self.ui.btn_recompute.configure(command=self.on_recompute)

        self.ui.btn_export_csv.configure(command=self.on_export_csv)
        self.ui.btn_export_xlsx.configure(command=self.on_export_xlsx)
        self.ui.btn_export_plots.configure(command=self.on_export_plots)

        # Norm selection helpers
        self.ui.btn_norm_add_from_table.configure(command=self.on_norm_add_from_selected_row)
        self.ui.btn_norm_all.configure(command=self.on_norm_all_species)
        self.ui.btn_norm_clear.configure(command=self.on_norm_clear)

        # Minimal: double-click tree row to add to normalization too (optional)
        self.ui.tree_main.bind("<Double-1>", self.on_open_per_file_main, add=True)
        self.ui.tree_combined.bind("<Double-1>", self.on_open_per_file_combined, add=True)

        # Placeholder hooks for dialogs (to be implemented later)
        self.ui.btn_aliases.configure(command=self.on_aliases_dialog)
        self.ui.btn_species_table.configure(command=self.on_species_table_dialog)
        self.ui.btn_plot_cfg.configure(command=self.on_plot_settings_dialog)

        # Keyboard shortcut: Ctrl+R recompute
        self.root.bind("<Control-r>", lambda e: self.on_recompute(), add=True)

        # v2.5.6: AMP grouping toggle (no explicit button in layout yet)
        # We'll add a checkbox in the top bar dynamically to keep layout.py simple.
        self._add_amp_grouping_toggle()
        self._add_amp_sort_toggle()

    def _add_amp_grouping_toggle(self) -> None:
        # Add a checkbox to the top bar: place it to the right in the same row.
        # layout.py has no handle to 'top' frame; so we locate it by parent of btn_load.
        top = self.ui.btn_load.master
        self._var_group_amp = tk.BooleanVar(value=self.state.options.group_modified_unmodified)

        chk = ttk.Checkbutton(
            top,
            text="Group modified/unmodified (-AMP)",
            variable=self._var_group_amp,
            command=self.on_toggle_group_amp,
        )
        # Put it after plot settings button
        chk.grid(row=0, column=9, padx=(12, 0), sticky="w")
        self._chk_group_amp = chk

    def _add_amp_sort_toggle(self) -> None:
        top = self.ui.btn_load.master
        self._var_sort_amp_pairs = tk.BooleanVar(value=self.state.options.sort_plots_by_amp_pairs)

        chk = ttk.Checkbutton(
            top,
            text="Sort plots by AMP pairs",
            variable=self._var_sort_amp_pairs,
            command=self.on_toggle_sort_amp_pairs,
        )
        chk.grid(row=0, column=10, padx=(12, 0), sticky="w")
        self._chk_sort_amp_pairs = chk

    # ---------------------------------------------------------------------
    # Actions
    # ---------------------------------------------------------------------
    def on_load_files(self) -> None:
        filepaths = filedialog.askopenfilenames(
            parent=self.root,
            title="Select SpecDigger Excel files",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if not filepaths:
            return

        try:
            self.ui.status_var.set("Loading files…")
            self.root.update_idletasks()

            load_files_into_state(self.state, filepaths)
            recompute_all(self.state)
            self.ui.status_var.set(f"Loaded {len(self.state.data.per_file_raw)} file(s).")

            # refresh normalization listbox (keep user choices if possible)
            self._sync_norm_listbox()

            self._render_all()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Load error", f"{type(e).__name__}: {e}")
            self.ui.status_var.set("Load failed.")

    def on_recompute(self) -> None:
        try:
            self.ui.status_var.set("Recomputing…")
            self.root.update_idletasks()

            recompute_all(self.state)
            self.ui.status_var.set("Recomputed.")
            self._render_all()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Recompute error", f"{type(e).__name__}: {e}")
            self.ui.status_var.set("Recompute failed.")

    def on_toggle_group_amp(self) -> None:
        self.state.options.group_modified_unmodified = bool(self._var_group_amp.get())
        try:
            self.ui.status_var.set("Recomputing combined…")
            self.root.update_idletasks()
            recompute_combined(self.state)
            self.ui.status_var.set("Combined recomputed.")
            self._render_all()
        except Exception as e:
            messagebox.showerror("Grouping error", str(e))
            self.ui.status_var.set("Grouping failed.")
    
    def on_toggle_sort_amp_pairs(self) -> None:
        self.state.options.sort_plots_by_amp_pairs = bool(self._var_sort_amp_pairs.get())
        self._render_plots()

    def on_export_csv(self) -> None:
        if self.state.results.df_main is None or self.state.results.df_main.empty:
            messagebox.showwarning("Export", "No results to export.")
            return

        out = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export CSV (base name)",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not out:
            return

        try:
            paths = export_csv_bundle(
                out,
                df_main=self.state.results.df_main,
                per_file_matrix=self.state.results.per_file_matrix_main,
                df_combined=self.state.results.df_combined,
                per_file_matrix_combined=self.state.results.per_file_matrix_combined,
                per_file_raw=self.state.data.per_file_raw,
            )
            self.ui.status_var.set(f"Exported {len(paths)} CSV file(s).")
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self.ui.status_var.set("Export failed.")

    def on_export_xlsx(self) -> None:
        if self.state.results.df_main is None or self.state.results.df_main.empty:
            messagebox.showwarning("Export", "No results to export.")
            return

        out = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export XLSX",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not out:
            return

        try:
            stats_pack = {"anova": self.state.results.anova, "tukey": self.state.results.tukey}
            path = export_xlsx(
                out,
                df_main=self.state.results.df_main,
                df_combined=self.state.results.df_combined,
                per_file_matrix=self.state.results.per_file_matrix_main,
                per_file_matrix_combined=self.state.results.per_file_matrix_combined,
                per_file_raw=self.state.data.per_file_raw,
                stats_pack=stats_pack,
            )
            self.ui.status_var.set(f"Exported XLSX: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self.ui.status_var.set("Export failed.")

    def on_export_plots(self) -> None:
        if self.state.results.df_main is None or self.state.results.df_main.empty:
            messagebox.showwarning("Export plot", "No results to plot/export.")
            return

        req = ask_export_plot(self.root)
        if req is None:
            return

        out = filedialog.asksaveasfilename(
            parent=self.root,
            title="Choose export base name (suffixes will be added)",
            defaultextension="",
            filetypes=[("All files", "*.*")],
        )
        if not out:
            return

        try:
            written = export_plot_files(
                out_base=Path(out),
                req=req,
                df_main=self.state.results.df_main,
                per_file_matrix_main=self.state.results.per_file_matrix_main,
                cfg_main=self.state.plots.main,
                df_combined=self.state.results.df_combined,
                per_file_matrix_combined=self.state.results.per_file_matrix_combined,
                cfg_combined=self.state.plots.combined,
                sig_pairs=self.state.results.sig_pairs,
            )
            self.ui.status_var.set(f"Exported {len(written)} plot file(s).")
        except Exception as e:
            messagebox.showerror("Export plot error", str(e))
            self.ui.status_var.set("Plot export failed.")


    # ---------------------------------------------------------------------
    # Normalization listbox helpers
    # ---------------------------------------------------------------------
    def _sync_norm_listbox(self) -> None:
        """Sync listbox contents from state.options.unbound_selected (preserve order)."""
        self.ui.lst_norm.delete(0, tk.END)
        for s in self.state.options.unbound_selected:
            self.ui.lst_norm.insert(tk.END, s)

    def on_norm_add_from_selected_row(self) -> None:
        """
        Add currently selected species from the *main table* to normalization list.
        """
        sel = self.ui.tree_main.selection()
        if not sel:
            messagebox.showinfo("Normalization", "Select a row in the main table first.")
            return
        item = sel[0]
        species = str(self.ui.tree_main.set(item, "species")).strip()
        if not species:
            return

        if species not in self.state.options.unbound_selected:
            self.state.options.unbound_selected.append(species)
            self._sync_norm_listbox()
            self.on_recompute()
    
    def on_norm_all_species(self) -> None:
        """
        Use all species currently shown in the main table as normalization species.
        """
        items = self.ui.tree_main.get_children()
        if not items:
            messagebox.showinfo("Normalization", "No species rows are available.")
            return

        species_list: list[str] = []
        seen: set[str] = set()

        for item in items:
            species = str(self.ui.tree_main.set(item, "species")).strip()
            if not species:
                continue
            key = species.lower()
            if key in seen:
                continue
            seen.add(key)
            species_list.append(species)

        if not species_list:
            messagebox.showinfo("Normalization", "No valid species names were found.")
            return

        self.state.options.unbound_selected = species_list
        self._sync_norm_listbox()
        self.on_recompute()

    def on_norm_clear(self) -> None:
        self.state.options.unbound_selected = []
        self._sync_norm_listbox()
        self.on_recompute()

    # ---------------------------------------------------------------------
    # Placeholder dialogs (to be implemented later)
    # ---------------------------------------------------------------------
    def on_aliases_dialog(self) -> None:
        changed = open_aliases_dialog(self.root, self.state.options)
        if changed:
            try:
                self.ui.status_var.set("Recomputing combined…")
                self.root.update_idletasks()
                recompute_combined(self.state)
                self.ui.status_var.set("Aliases applied.")
                self._render_all()
            except Exception as e:
                messagebox.showerror("Aliases error", str(e))
                self.ui.status_var.set("Alias apply failed.")

    def on_species_table_dialog(self) -> None:
        rows = ask_species_table_rows(
            self.root,
            default_protein="",
            default_marker="v",
            title="Generate species-table rows",
        )
        if not rows:
            return

        print("\nSpecies-table rows returned from dialog:")
        for row in rows:
            print(
                row["species"],
                row["M (th)"],
                row["sequence"],
                row["color"],
                row["marker"],
                row.get("protein", ""),
                row.get("is_dimer", False),
                row.get("ligand_category", ""),
                row.get("ligand", ""),
                row.get("ligand_count", 0),
                row.get("mg_count", 0),
                row.get("protein_is_ampylated", False),
            )

        messagebox.showinfo(
            "Species table",
            f"{len(rows)} species row(s) generated.\n"
            "Next step: insert them into the actual species table model/widget.",
        )

    def on_plot_settings_dialog(self) -> None:
        changed = open_customize_plot_dialog(
            self.root,
            cfg_main=self.state.plots.main,
            cfg_combined=self.state.plots.combined,
        )
        if changed:
            self.ui.status_var.set("Plot settings applied.")
            self._render_plots()

    def on_open_per_file_main(self, event: tk.Event) -> None:
        # only act if user double-clicked a row
        item = self.ui.tree_main.identify_row(event.y)
        if not item:
            return
        try:
            species = str(self.ui.tree_main.set(item, "species")).strip()
        except Exception:
            return
        if not species:
            return

        m = self.state.results.per_file_matrix_main
        if m is None or m.empty or species not in m.columns:
            messagebox.showinfo("Per-file", f"No per-file data for '{species}'.")
            return

        col = m[species]
        values_by_file = {str(idx): (None if pd.isna(v) else float(v)) for idx, v in col.items()}

        open_per_file_dialog(
            self.root,
            title="Per-file values (main)",
            species=species,
            values_by_file=values_by_file,
            value_label="relative_%",
        )

    def on_open_per_file_combined(self, event: tk.Event) -> None:
        item = self.ui.tree_combined.identify_row(event.y)
        if not item:
            return
        try:
            species = str(self.ui.tree_combined.set(item, "species")).strip()
        except Exception:
            return
        if not species:
            return

        m = self.state.results.per_file_matrix_combined
        if m is None or m.empty or species not in m.columns:
            messagebox.showinfo("Per-file", f"No per-file data for '{species}'.")
            return

        col = m[species]
        values_by_file = {str(idx): (None if pd.isna(v) else float(v)) for idx, v in col.items()}

        open_per_file_dialog(
            self.root,
            title="Per-file values (combined)",
            species=species,
            values_by_file=values_by_file,
            value_label="relative_%",
        )

    # ---------------------------------------------------------------------
    # Rendering
    # ---------------------------------------------------------------------
    def _render_all(self) -> None:
        self._render_tables()
        self._render_plots()

    def _render_tables(self) -> None:
        has_norm = bool(self.state.options.unbound_selected)

        df_main = self.state.results.df_main if has_norm else self.state.results.df_loaded_main
        df_combined = self.state.results.df_combined if has_norm else self.state.results.df_loaded_combined

        self._fill_tree_from_df(self.ui.tree_main, df_main)
        self._fill_tree_from_df(self.ui.tree_combined, df_combined)

    def _fill_tree_from_df(self, tree: ttk.Treeview, df: Optional[pd.DataFrame]) -> None:
        import pandas as pd

        # Clear rows
        for item in tree.get_children():
            tree.delete(item)

        if df is None or df.empty:
            # still reset columns so stale headers disappear
            tree["columns"] = ()
            tree["show"] = "headings"
            return

        # Use exactly the DataFrame columns, in exactly that order
        cols = list(df.columns)
        tree["columns"] = tuple(cols)
        tree["show"] = "headings"

        # Rebuild headings/column settings
        for c in cols:
            tree.heading(c, text=c)

            # default width heuristics
            width = 140
            if c.lower() == "species":
                width = 220
            elif "significant_pairs" in c.lower():
                width = 300
            elif "anova" in c.lower():
                width = 120
            elif "mean" in c.lower() or "sd" in c.lower():
                width = 110
            elif c.lower() in ("n", "n_files", "files_n"):
                width = 80

            tree.column(c, width=width, anchor="w", stretch=True)

        # Fill rows
        for _, row in df.iterrows():
            values = []
            for c in cols:
                v = row.get(c, "")
                if pd.isna(v):
                    v = ""
                elif isinstance(v, float):
                    v = f"{v:.3f}"
                values.append(v)

            tree.insert("", tk.END, values=values)

    def _apply_fig_sizing(self, fig: Figure, cfg: Dict[str, Any]) -> None:
        """
        Apply v2.5.6 sizing keys to a matplotlib Figure.

        cfg keys:
        - axes_w_in: float | None
        - axes_h_in: float | None
        - margins_in: (L, R, T, B) in inches
        Behavior:
        If axes_w_in and axes_h_in are provided -> compute full figure size:
            fig_w = L + axes_w + R
            fig_h = B + axes_h + T
        and set subplots_adjust so the *axes* area matches axes_w/axes_h.
        If axes_* are None -> do nothing (keep current figure size).
        """
        axes_w = cfg.get("axes_w_in", None)
        axes_h = cfg.get("axes_h_in", None)
        margins = cfg.get("margins_in", (0.8, 0.25, 0.35, 0.8))

        # Need both to apply deterministically
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

        # Clamp to sane non-negative values
        axes_w = max(0.1, axes_w)
        axes_h = max(0.1, axes_h)
        L = max(0.0, L); R = max(0.0, R); T = max(0.0, T); B = max(0.0, B)

        fig_w = L + axes_w + R
        fig_h = B + axes_h + T

        # Avoid division by zero
        if fig_w <= 0 or fig_h <= 0:
            return

        fig.set_size_inches(fig_w, fig_h, forward=True)
        fig.canvas.draw_idle()

        left = L / fig_w
        right = 1.0 - (R / fig_w)
        bottom = B / fig_h
        top = 1.0 - (T / fig_h)

        # Keep within bounds
        left = min(max(left, 0.0), 0.95)
        right = min(max(right, left + 0.01), 1.0)
        bottom = min(max(bottom, 0.0), 0.95)
        top = min(max(top, bottom + 0.01), 1.0)

        fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)

    def _render_plots(self) -> None:
        has_norm = bool(self.state.options.unbound_selected)

    # MAIN
        self._apply_fig_sizing(self.plot_main.fig, self.state.plots.main)
        cfg_main = dict(self.state.plots.main)
        cfg_main["sort_by_amp_pairs"] = bool(self.state.options.sort_plots_by_amp_pairs)
        draw_main(
            ax=self.plot_main.ax,
            df_main=self.state.results.df_main if has_norm else pd.DataFrame(),
            per_file_matrix_main=self.state.results.per_file_matrix_main if has_norm else pd.DataFrame(),
            plot_cfg_main=cfg_main,
            title="Separate species",
            ylabel="relative (%)",
        )
        self.plot_main.canvas.draw_idle()

        # COMBINED
        self._apply_fig_sizing(self.plot_combined.fig, self.state.plots.combined)
        cfg_combined = dict(self.state.plots.combined)
        cfg_combined["sort_by_amp_pairs"] = bool(self.state.options.sort_plots_by_amp_pairs)
        draw_combined(
            ax=self.plot_combined.ax,
            df_combined=self.state.results.df_combined if has_norm else pd.DataFrame(),
            per_file_matrix_combined=self.state.results.per_file_matrix_combined if has_norm else pd.DataFrame(),
            plot_cfg_combined=cfg_combined,
            sig_pairs=self.state.results.sig_pairs if has_norm else [],
            title="Combined Mg pairs",
            ylabel="relative (%)",
        )
        self.plot_combined.canvas.draw_idle()


def run() -> None:
    root = tk.Tk()
    app = SpecDiggerApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()


__all__ = ["SpecDiggerApp", "run"]

