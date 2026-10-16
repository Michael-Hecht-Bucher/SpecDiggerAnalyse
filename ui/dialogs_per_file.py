# specdiggeranalyse/ui/dialogs_per_file.py
# -*- coding: utf-8 -*-

"""
Per-file inspection dialog (v2.5.6 compatible).

Usage:
- Open on double-click of a species row in main/combined summary tables.
- Shows per-file relative_% values for the selected species (or base species).

This dialog is GUI-only; it does not recompute analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox


@dataclass(slots=True)
class PerFileDialogResult:
    closed: bool = True


class PerFileDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        *,
        title: str,
        species: str,
        values_by_file: dict[str, float | None],
        value_label: str = "relative_%",
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[PerFileDialogResult] = None

        self._species = species
        self._value_label = value_label
        self._data = values_by_file

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(10, 10, 10, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=f"Per-file values: {species}",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")

        stats_text = self._make_stats_text(values_by_file)
        ttk.Label(header, text=stats_text, foreground="#444444").grid(row=1, column=0, sticky="w", pady=(4, 0))

        body = ttk.Frame(self, padding=(10, 0, 10, 10))
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # Tree
        self.tree = ttk.Treeview(body, columns=("file", value_label), show="headings", selectmode="browse")
        self.tree.heading("file", text="file", command=lambda: self._sort_by("file"))
        self.tree.heading(value_label, text=value_label, command=lambda: self._sort_by(value_label))
        self.tree.column("file", width=360, anchor="w", stretch=True)
        self.tree.column(value_label, width=120, anchor="e", stretch=False)

        ysb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        # Buttons
        btns = ttk.Frame(body)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.grid_columnconfigure(0, weight=1)

        self.btn_copy = ttk.Button(btns, text="Copy (TSV)", command=self._copy_tsv)
        self.btn_close = ttk.Button(btns, text="Close", command=self._close)

        self.btn_copy.grid(row=0, column=0, sticky="w")
        self.btn_close.grid(row=0, column=1, sticky="e")

        # Fill rows
        self._populate()

        # Bindings
        self.bind("<Escape>", lambda e: self._close(), add=True)
        self.bind("<Control-c>", lambda e: self._copy_tsv(), add=True)

        self._sort_col: str = "file"
        self._sort_desc: bool = False

        self.geometry("640x520")

    # ------------------------------------------------------------------ #
    # Data/stat helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_stats_text(values_by_file: dict[str, float | None]) -> str:
        vals = [v for v in values_by_file.values() if isinstance(v, (int, float))]
        if not vals:
            return "n=0"
        n = len(vals)
        mean = sum(vals) / n
        # sample SD
        if n >= 2:
            var = sum((x - mean) ** 2 for x in vals) / (n - 1)
            sd = var ** 0.5
        else:
            sd = 0.0
        vmin = min(vals)
        vmax = max(vals)
        return f"n={n}  mean={mean:.3f}  sd={sd:.3f}  min={vmin:.3f}  max={vmax:.3f}"

    def _populate(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for fname in sorted(self._data.keys(), key=str.lower):
            v = self._data[fname]
            if v is None:
                vs = ""
            else:
                try:
                    vs = f"{float(v):.3f}"
                except Exception:
                    vs = str(v)
            self.tree.insert("", tk.END, values=(fname, vs))

    # ------------------------------------------------------------------ #
    # Sorting
    # ------------------------------------------------------------------ #
    def _sort_by(self, col: str) -> None:
        # Toggle if same column, else default ascending
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False

        rows = []
        for item in self.tree.get_children():
            f, v = self.tree.item(item, "values")
            if col == "file":
                key = str(f).lower()
            else:
                try:
                    key = float(str(v).replace(",", "."))
                except Exception:
                    key = float("-inf") if self._sort_desc else float("inf")
            rows.append((key, item))

        rows.sort(key=lambda t: t[0], reverse=self._sort_desc)

        for i, (_, item) in enumerate(rows):
            self.tree.move(item, "", i)

    # ------------------------------------------------------------------ #
    # Clipboard export
    # ------------------------------------------------------------------ #
    def _copy_tsv(self) -> None:
        # Export current displayed order
        lines = ["file\t" + self._value_label]
        for item in self.tree.get_children():
            f, v = self.tree.item(item, "values")
            lines.append(f"{f}\t{v}")
        txt = "\n".join(lines)

        try:
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.update_idletasks()
        except Exception as e:
            messagebox.showerror("Copy failed", str(e), parent=self)

    # ------------------------------------------------------------------ #
    # Close
    # ------------------------------------------------------------------ #
    def _close(self) -> None:
        self.result = PerFileDialogResult(closed=True)
        self.destroy()


def open_per_file_dialog(
    parent: tk.Tk | tk.Toplevel,
    *,
    title: str,
    species: str,
    values_by_file: dict[str, float | None],
    value_label: str = "relative_%",
) -> None:
    """
    Open the dialog modally.
    """
    dlg = PerFileDialog(
        parent,
        title=title,
        species=species,
        values_by_file=values_by_file,
        value_label=value_label,
    )
    parent.wait_window(dlg)


__all__ = ["open_per_file_dialog", "PerFileDialog", "PerFileDialogResult"]