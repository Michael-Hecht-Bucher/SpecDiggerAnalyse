# specdiggeranalyse/dialogs_species_table.py
# -*- coding: utf-8 -*-

"""
Species-table wizard dialog.

Purpose
-------
UI dialog that lets the user generate species-table rows based on:
- one protein
- zero or more ligands, which can be any combination of supported nucleotides, sugars and nucleobases
- optional Mg-containing species
- optional dimer species
- optional protein auto-AMPylation

Generation logic is delegated to:
    specdiggeranalyse.mass_tables.build_species_rows

This module is intentionally UI-focused:
- no mass tables are hardcoded here
- no scientific mass logic is implemented here
- returned rows are shaped for downstream insertion into the species table

Expected output row shape
-------------------------
Each generated row is returned as a dict such as:
    {
        "species": "AnkX + ATP + Mg",
        "M (th)": 91109.55,
        "sequence": "",
        "color": "#1f77b4",
        "marker": "o",

        # optional structural metadata retained for later use/debugging
        "expected_mass": 91109.55,
        "protein": "AnkX",
        "is_dimer": False,
        "ligand_category": "Nucleotides",
        "ligand": "ATP",
        "ligand_count": 1,
        "mg_count": 1,
        "protein_is_ampylated": False,
    }
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path 
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any, Optional

from ..mass_tables import LIGAND_CATEGORIES, LIGAND_CATEGORY_ORDER, PROTEIN_NAMES, build_species_rows

import pandas as pd 


DEFAULT_COLOR = ""
DEFAULT_MARKER = "v"

MARKER_OPTIONS = [
    "o",   # circle
    "s",   # square
    "^",   # triangle up
    "v",   # triangle down
    "D",   # diamond
    "*",   # star
    "+",   # plus
    "x",   # x
    ".",   # point
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _format_mass_for_tree(value: Any) -> str:
    """
    Display formatter for preview tree.
    Keep dot-decimal formatting conservative and stable.
    """
    return _format_mass_for_output(value)

def _format_mass_for_output(value: Any) -> str:
    """
    Format mass as a dot-decimal string for export/downstream tools.

    Uses a fixed-point representation with trailing zeros removed, while
    preserving meaningful decimal precision from the underlying float.
    """
    x = _safe_float(value, 0.0)
    return f"{x:.10f}".rstrip("0").rstrip(".")

def _coerce_generated_row_for_table(
    row: dict[str, Any],
    *,
    color_override: str = "",
    use_color_override: bool = False,
    marker_override: str = DEFAULT_MARKER,
) -> dict[str, Any]:
    """
    Convert a structural row from build_species_rows(...) into a table-ready row.

    Keeps structural metadata because it can be useful later for debugging,
    regeneration, export, or more advanced filtering.
    """

    expected_mass = _safe_float(row.get("expected_mass"), 0.0)

    color = str(row.get("color", ""))
    if use_color_override and color_override:
        color = color_override

    marker = marker_override or str(row.get("marker", DEFAULT_MARKER))

    return {
        "species": str(row.get("species", "")),
        "M (th)": _format_mass_for_output(row.get("M (th)", expected_mass)),
        "sequence": str(row.get("sequence", "")),
        "color": color,
        "marker": marker,

        # structural metadata retained
        "expected_mass": expected_mass,
        "protein": str(row.get("protein", "")),
        "is_dimer": bool(row.get("is_dimer", False)),
        "ligand_category": str(row.get("ligand_category", "")),
        "ligand": str(row.get("ligand", "")),
        "ligand_count": int(row.get("ligand_count", 0)),
        "mg_count": int(row.get("mg_count", 0)),
        "protein_is_ampylated": bool(row.get("protein_is_ampylated", False)),
    }

def export_species_rows_to_xlsx(
    rows: list[dict[str, Any]],
    out_path: str | Path,
) -> Path:
    """
    Export species-table rows to an Excel file.

    Only the species-table-facing columns are exported.
    'M (th)' is written as dot-decimal text so SpecDigger import can properly recognize the exported species table.
    """
    export_cols = ["species", "M (th)", "sequence", "color", "marker"]

    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "species": row.get("species", ""),
                "M (th)": _format_mass_for_output(row.get("M (th)", "")),
                "sequence": row.get("sequence", ""),
                "color": row.get("color", ""),
                "marker": row.get("marker", ""),
            }
        )

    df = pd.DataFrame(records, columns=export_cols)
    out = Path(out_path)
    df.to_excel(out, index=False)
    return out


class SpeciesTableDialog(tk.Toplevel):
    """
    Modal dialog that generates species rows for insertion into the species table.

    Public result:
        self.result -> list[dict[str, Any]] | None
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str = "Generate species-table rows",
        default_protein: str = "",
        default_color: str = DEFAULT_COLOR,
        default_marker: str = DEFAULT_MARKER,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.result: Optional[list[dict[str, Any]]] = None

        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)

        # ----------------------------
        # Variables
        # ----------------------------
        self.protein_var = tk.StringVar(value=default_protein)
        self.include_mg_var = tk.BooleanVar(value=True)
        self.include_dimer_var = tk.BooleanVar(value=False)
        self.dimer_only_var = tk.BooleanVar(value=False)
        self.auto_amp_var = tk.BooleanVar(value=False)

        self.color_var = tk.StringVar(value=default_color)
        self.marker_var = tk.StringVar(
            value=default_marker if default_marker in MARKER_OPTIONS else DEFAULT_MARKER
        )
        self.use_color_override_var = tk.BooleanVar(value=False)

        self.preview_rows: list[dict[str, Any]] = []
        self.ligand_listboxes: dict[str, tk.Listbox] = {}

        # ----------------------------
        # Build UI
        # ----------------------------
        self._build_ui()
        self._bind_events()

        # initialize preview
        self._sync_dimer_state()
        self._refresh_preview()

        # modal behavior
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()
        self._center_over_parent()
        self.wait_visibility()
        self.focus_set()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        # --------------------------------------------------------------
        # Top options frame
        # --------------------------------------------------------------
        options = ttk.LabelFrame(outer, text="Species generation", padding=10)
        options.grid(row=0, column=0, sticky="ew")

        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        # Protein
        ttk.Label(options, text="Protein").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.protein_combo = ttk.Combobox(
            options,
            textvariable=self.protein_var,
            values=PROTEIN_NAMES,
            state="readonly",
        )
        self.protein_combo.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)

        # Ligand categories
        ligand_categories = [c for c in LIGAND_CATEGORY_ORDER if c not in {"Proteins", "Ions"}]

        ligands_outer = ttk.LabelFrame(options, text="Ligands", padding=8)
        ligands_outer.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(8, 4))

        ligands_outer.rowconfigure(0, weight=1)

        for col, category in enumerate(ligand_categories):
            ligands_outer.columnconfigure(col, weight=1)

        for col, category in enumerate(ligand_categories):
            cat_frame = ttk.LabelFrame(ligands_outer, text=category, padding=6)
            cat_frame.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0))
            cat_frame.columnconfigure(0, weight=1)
            cat_frame.rowconfigure(0, weight=1)

            lb = tk.Listbox(
                cat_frame,
                selectmode=tk.EXTENDED,
                exportselection=False,
                height=8,
            )
            lb.grid(row=0, column=0, sticky="nsew")

            scroll = ttk.Scrollbar(cat_frame, orient="vertical", command=lb.yview)
            scroll.grid(row=0, column=1, sticky="ns")
            lb.configure(yscrollcommand=scroll.set)

            for name in LIGAND_CATEGORIES.get(category, []):
                lb.insert(tk.END, name)

            self.ligand_listboxes[category] = lb

            btns = ttk.Frame(cat_frame)
            btns.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

            ttk.Button(
                btns,
                text="Select all",
                command=lambda c=category: self._select_all_ligands(c),
            ).grid(row=0, column=0, sticky="w")

            ttk.Button(
                btns,
                text="Clear",
                command=lambda c=category: self._clear_ligand_selection(c),
            ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        # Checkboxes
        flags = ttk.Frame(options)
        flags.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        ttk.Checkbutton(
            flags,
            text="Include Mg-containing species",
            variable=self.include_mg_var,
            command=self._refresh_preview,
        ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=2)

        ttk.Checkbutton(
            flags,
            text="Include dimer species",
            variable=self.include_dimer_var,
            command=self._on_include_dimer_changed,
        ).grid(row=0, column=1, sticky="w", padx=(0, 16), pady=2)

        self.dimer_only_check = ttk.Checkbutton(
            flags,
            text="Dimer only",
            variable=self.dimer_only_var,
            command=self._on_dimer_only_changed,
        )
        self.dimer_only_check.grid(row=0, column=2, sticky="w", pady=2)

        ttk.Checkbutton(
            flags,
            text="Auto-AMPylation",
            variable=self.auto_amp_var,
            command=self._refresh_preview,
        ).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=2)

        # Style defaults
        style_frame = ttk.LabelFrame(options, text="Default row styling", padding=8)
        style_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        style_frame.columnconfigure(3, weight=1)

        ttk.Checkbutton(
            style_frame,
            text="Override all row colors",
            variable=self.use_color_override_var,
            command=self._refresh_preview,
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=2)

        ttk.Label(style_frame, text="Color").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)

        self.color_preview = tk.Label(
            style_frame,
            width=3,
            relief="sunken",
            bg=self.color_var.get() if self.color_var.get() else "#ffffff",
        )
        self.color_preview.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Button(style_frame, text="Choose…", command=self._choose_color).grid(
            row=1, column=2, sticky="w", padx=(6, 12), pady=2
        )

        ttk.Label(style_frame, text="Marker").grid(row=1, column=3, sticky="e", padx=(0, 6), pady=2)

        self.marker_combo = ttk.Combobox(
            style_frame,
            textvariable=self.marker_var,
            values=MARKER_OPTIONS,
            state="readonly",
            width=8,
        )
        self.marker_combo.grid(row=1, column=4, sticky="w", pady=2)

        # --------------------------------------------------------------
        # Preview frame
        # --------------------------------------------------------------
        preview = ttk.LabelFrame(outer, text="Preview", padding=8)
        preview.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)

        columns = ("species", "mass", "sequence", "color", "marker")
        self.tree = ttk.Treeview(preview, columns=columns, show="headings", height=14)
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.tree.heading("species", text="Species")
        self.tree.heading("mass", text="M (th)")
        self.tree.heading("sequence", text="Sequence")
        self.tree.heading("color", text="Color")
        self.tree.heading("marker", text="Marker")

        self.tree.column("species", width=320, anchor="w")
        self.tree.column("mass", width=110, anchor="e")
        self.tree.column("sequence", width=120, anchor="w")
        self.tree.column("color", width=90, anchor="center")
        self.tree.column("marker", width=80, anchor="center")

        tree_scroll_y = ttk.Scrollbar(preview, orient="vertical", command=self.tree.yview)
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        footer = ttk.Frame(preview)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        footer.columnconfigure(0, weight=1)

        self.preview_info_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.preview_info_var).grid(row=0, column=0, sticky="w")

        # --------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------
        btns = ttk.Frame(outer)
        btns.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)

        ttk.Button(btns, text="Refresh preview", command=self._refresh_preview).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(btns, text="Export to Excel", command=self._on_export_xlsx).grid(
            row=0, column=1, sticky="e", padx=(6,0)
        )
        ttk.Button(btns, text="Cancel", command=self._on_cancel).grid(
            row=0, column=2, sticky="e", padx=(6, 0)
        )
        ttk.Button(btns, text="Return rows", command=self._on_ok).grid(
            row=0, column=3, sticky="e", padx=(6, 0)
        )
        
    # ------------------------------------------------------------------
    # Event binding
    # ------------------------------------------------------------------
    def _bind_events(self) -> None:
        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.bind("<Return>", lambda _e: self._on_ok())

        self.protein_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_preview())
        self.marker_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_preview())

        for lb in self.ligand_listboxes.values():
            lb.bind("<<ListboxSelect>>", lambda _e: self._refresh_preview())

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _center_over_parent(self) -> None:
        self.update_idletasks()

        try:
            parent = self.parent.winfo_toplevel()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except Exception:
            px, py, pw, ph = 100, 100, 900, 700

        w = max(self.winfo_reqwidth(), 720)
        h = max(self.winfo_reqheight(), 620)

        x = px + max((pw - w) // 2, 0)
        y = py + max((ph - h) // 2, 0)

        self.geometry(f"{w}x{h}+{x}+{y}")

    def _selected_ligands_by_category(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for category, lb in self.ligand_listboxes.items():
            out[category] = [lb.get(i) for i in lb.curselection()]
        return out


    def _select_all_ligands(self, category: str) -> None:
        lb = self.ligand_listboxes.get(category)
        if lb is None:
            return
        lb.selection_set(0, tk.END)
        self._refresh_preview()


    def _clear_ligand_selection(self, category: str) -> None:
        lb = self.ligand_listboxes.get(category)
        if lb is None:
            return
        lb.selection_clear(0, tk.END)
        self._refresh_preview()

    def _choose_color(self) -> None:
        initial = self.color_var.get() or "#1f77b4"
        _rgb, hex_color = colorchooser.askcolor(color=initial, parent=self)
        if hex_color:
            self.color_var.set(hex_color)
            self.use_color_override_var.set(True)
            self.color_preview.configure(bg=hex_color)
            self._refresh_preview()

    def _sync_dimer_state(self) -> None:
        """
        Keep checkbox states consistent:
        - dimer_only implies include_dimer
        - dimer_only disabled unless include_dimer is enabled
        """
        include_dimer = bool(self.include_dimer_var.get())
        dimer_only = bool(self.dimer_only_var.get())

        if dimer_only and not include_dimer:
            self.include_dimer_var.set(True)
            include_dimer = True

        if include_dimer:
            self.dimer_only_check.state(["!disabled"])
        else:
            self.dimer_only_var.set(False)
            self.dimer_only_check.state(["disabled"])

    def _on_include_dimer_changed(self) -> None:
        self._sync_dimer_state()
        self._refresh_preview()

    def _on_dimer_only_changed(self) -> None:
        if self.dimer_only_var.get():
            self.include_dimer_var.set(True)
        self._sync_dimer_state()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Preview generation
    # ------------------------------------------------------------------
    def _build_preview_rows(self) -> list[dict[str, Any]]:
        protein = self.protein_var.get().strip()
        ligands_by_category = self._selected_ligands_by_category()
        include_mg = bool(self.include_mg_var.get())
        include_dimer = bool(self.include_dimer_var.get())
        dimer_only = bool(self.dimer_only_var.get())
        auto_amp = bool(self.auto_amp_var.get())

        if not protein:
            return []

        structural_rows = build_species_rows(
            protein=protein,
            ligands_by_category=ligands_by_category,
            include_mg=include_mg,
            include_dimer=include_dimer,
            dimer_only=dimer_only,
            protein_auto_ampylation=auto_amp,
            sort_rows=True,
        )

        color_override = self.color_var.get().strip()
        use_color_override = bool(self.use_color_override_var.get())
        marker_override = self.marker_var.get().strip() or DEFAULT_MARKER

        return [
            _coerce_generated_row_for_table(
                row,
                color_override=color_override,
                use_color_override=use_color_override,
                marker_override=marker_override,
            )
            for row in structural_rows
        ]

    def _refresh_preview(self) -> None:
        self.preview_rows = self._build_preview_rows()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in self.preview_rows:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("species", ""),
                    _format_mass_for_tree(row.get("M (th)", 0.0)),
                    row.get("sequence", ""),
                    row.get("color", ""),
                    row.get("marker", ""),
                ),
            )

        n_rows = len(self.preview_rows)
        protein = self.protein_var.get().strip()
        selected = self._selected_ligands_by_category()
        
        parts = [
                f"{category}: {len(names)}"
                for category, names in selected.items()
                if names
            ]
        ligand_info = ", ".join(parts) if parts else "no ligands selected"

        if not protein:
            self.preview_info_var.set("Select a protein to generate preview rows.")
        else:
            self.preview_info_var.set(f"{n_rows} row(s) generated | {ligand_info}")

    # ------------------------------------------------------------------
    # Dialog actions
    # ------------------------------------------------------------------
    def _on_ok(self) -> None:
        protein = self.protein_var.get().strip()
        if not protein:
            messagebox.showwarning(
                "No protein selected",
                "Please select a protein before adding species rows.",
                parent=self,
            )
            return

        rows = self._build_preview_rows()
        if not rows:
            messagebox.showwarning(
                "No rows generated",
                "The current selection did not generate any rows.",
                parent=self,
            )
            return

        self.result = rows
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    def _on_export_xlsx(self) -> None:
        rows = self._build_preview_rows()
        if not rows:
            messagebox.showwarning(
                "Export Excel",
                "No preview rows are available to export.",
                parent=self,
            )
            return

        protein = self.protein_var.get().strip() or "species_table"
        suggested_name = f"{protein}_species_table.xlsx"

        out = filedialog.asksaveasfilename(
            parent=self,
            title="Export species table to Excel",
            defaultextension=".xlsx",
            initialfile=suggested_name,
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not out:
            return

        try:
            path = export_species_rows_to_xlsx(rows, out)
            self.preview_info_var.set(f"Exported Excel: {Path(path).name}")
            messagebox.showinfo(
                "Export Excel",
                f"Exported {len(rows)} row(s) to:\n{Path(path).name}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Export Excel error",
                str(e),
                parent=self,
            )


def ask_species_table_rows(
    parent: tk.Misc,
    *,
    default_protein: str = "",
    default_color: str = DEFAULT_COLOR,
    default_marker: str = DEFAULT_MARKER,
    title: str = "Generate species-table rows",
) -> Optional[list[dict[str, Any]]]:
    """
    Convenience wrapper.

    Returns:
        list[dict[str, Any]] if the user confirmed
        None if the user cancelled
    """
    dialog = SpeciesTableDialog(
        parent,
        title=title,
        default_protein=default_protein,
        default_color=default_color,
        default_marker=default_marker,
    )
    parent.wait_window(dialog)
    return dialog.result

#############################################################
# The small __main__ block below is just for quick testing of the dialog standalone
#############################################################

if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("Dialog test host")
    root.geometry("300x120+100+100")

    tk.Label(root, text="Root host window").pack(pady=20)

    dialog = SpeciesTableDialog(
        root,
        default_protein="AvrB",
        default_marker="v",
    )

    def _print_result() -> None:
        print("\nReturned rows:")
        if dialog.result is None:
            print("Dialog cancelled.")
        else:
            for row in dialog.result:
                print(
                    row["species"],
                    row["M (th)"],
                    row["sequence"],
                    row["color"],
                    row["marker"],
                )
        root.destroy()

    dialog.bind("<Destroy>", lambda _e: root.after(50, _print_result))
    root.mainloop()