# specdiggeranalyse/ui/widgets.py
# -*- coding: utf-8 -*-

"""
Reusable UI widgets for SpecDiggerAnalyse.

Currently contains:
- EditableTreeview: ttk.Treeview with in-place editing for editable columns.

Guiding rule:
- This module is UI-only (tkinter/ttk OK),
  but should not contain analysis, plotting, or app orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Set

import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class CellEditEvent:
    """Optional structured edit info (not required, but helpful)."""
    item_id: str
    column: str
    old_value: str
    new_value: str


class EditableTreeview(ttk.Treeview):
    """
    ttk.Treeview with in-place editing of cells on double click.

    - By default all columns are editable.
    - You can block edits by providing read_only_cols.
    - When a cell edit is committed, emits:
        <<CellEdited>>
      and sets:
        self.last_edit (CellEditEvent)  # optional, for convenient callbacks

    Notes:
    - Treeview columns are referenced by their column IDs as in self["columns"].
    - This widget edits with a tk.Entry overlay placed on top of the cell.
    """

    def __init__(
        self,
        *args,
        read_only_cols: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._read_only_cols: Set[str] = set(read_only_cols or [])
        self._editor: Optional[tk.Entry] = None
        self.last_edit: Optional[CellEditEvent] = None

        # Start editing with double click
        self.bind("<Double-1>", self._start_edit, add=True)

    # ---- public API ----
    def set_read_only_cols(self, cols: Iterable[str]) -> None:
        self._read_only_cols = set(cols or [])

    def is_read_only(self, col: str) -> bool:
        return col in self._read_only_cols

    # ---- internal ----
    def _start_edit(self, event: tk.Event) -> None:
        # Only edit actual cells
        if self.identify("region", event.x, event.y) != "cell":
            return

        item_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)  # e.g. "#1"
        if not item_id or not col_id:
            return

        # Convert "#1" -> column name in self["columns"]
        try:
            col_index = int(col_id[1:]) - 1
            col_name = self["columns"][col_index]
        except Exception:
            return

        if self.is_read_only(col_name):
            return

        bbox = self.bbox(item_id, col_id)
        if not bbox:
            return

        x, y, w, h = bbox
        old_value = str(self.set(item_id, col_name))

        # Destroy any prior editor
        if self._editor is not None:
            try:
                self._editor.destroy()
            except Exception:
                pass
            self._editor = None

        # Create editor overlay
        self._editor = tk.Entry(self)
        self._editor.insert(0, old_value)
        self._editor.select_range(0, tk.END)
        self._editor.focus_set()
        self._editor.place(x=x, y=y, width=w, height=h)

        def finish(commit: bool) -> None:
            if self._editor is None:
                return

            new_value = old_value
            if commit:
                new_value = self._editor.get()
                self.set(item_id, col_name, new_value)

                self.last_edit = CellEditEvent(
                    item_id=item_id,
                    column=str(col_name),
                    old_value=old_value,
                    new_value=new_value,
                )

                # notify listeners (GUI can bind to this)
                self.event_generate("<<CellEdited>>", when="tail")

            self._editor.destroy()
            self._editor = None

        # Key bindings
        self._editor.bind("<Return>", lambda e: finish(True), add=True)
        self._editor.bind("<Escape>", lambda e: finish(False), add=True)
        self._editor.bind("<FocusOut>", lambda e: finish(True), add=True)


__all__ = ["EditableTreeview", "CellEditEvent"]
