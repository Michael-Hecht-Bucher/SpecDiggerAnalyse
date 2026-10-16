# specdiggeranalyse/ui/dialogs_alias.py
# -*- coding: utf-8 -*-

"""
Alias editor dialog for SpecDiggerAnalyse (v2.5.6 compatible).

Purpose:
- Allow user to define canonicalization rules used in combined Mg-pairing
  and (optionally) AMP grouping.
- Edits state.options.alias_map via AnalysisOptions.set_alias_map_from_lines()

This dialog is intentionally self-contained:
- no controller calls inside; app.py should call controllers after applying changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from ..models import AnalysisOptions


HELP_TEXT = (
    "Define canonical names and their aliases.\n\n"
    "Format per line:\n"
    "  Canonical = alias1, alias2, alias3\n"
    "or:\n"
    "  Canonical: alias1; alias2\n\n"
    "Notes:\n"
    "• Matching is case-insensitive.\n"
    "• Aliases are mapped to the canonical name.\n"
    "• Canonical names are also mapped to themselves.\n"
    "• These rules are applied after stripping trailing '+ Mg' tokens.\n"
)


@dataclass(slots=True)
class AliasDialogResult:
    applied: bool
    text: str


def _alias_map_to_text(options: AnalysisOptions) -> str:
    """
    Convert current alias_map (alias->canonical) into a readable canonical listing.

    Because alias_map stores alias->canonical, we invert it into:
      canonical = alias1, alias2, ...
    (canonical itself is omitted from alias list if it appears as alias)
    """
    inv: dict[str, list[str]] = {}
    for alias_lc, canon in (options.alias_map or {}).items():
        canon = str(canon).strip()
        inv.setdefault(canon, []).append(alias_lc)

    lines = []
    for canon in sorted(inv.keys(), key=str.lower):
        aliases_lc = sorted(set(inv[canon]), key=str.lower)
        # remove canonical itself if present (in lowercase form)
        aliases_lc = [a for a in aliases_lc if a.lower() != canon.lower()]
        if aliases_lc:
            lines.append(f"{canon} = {', '.join(aliases_lc)}")
        else:
            lines.append(f"{canon} =")
    return "\n".join(lines).strip()


class AliasesDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        *,
        options: AnalysisOptions,
        title: str = "Aliases",
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._options = options
        self.result: Optional[AliasDialogResult] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- header / help
        lbl = ttk.Label(self, text="Alias mapping editor", font=("TkDefaultFont", 11, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        help_box = ttk.LabelFrame(self, text="Help", padding=8)
        help_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        help_box.grid_columnconfigure(0, weight=1)
        ttk.Label(help_box, text=HELP_TEXT, justify="left").grid(row=0, column=0, sticky="ew")

        # --- main text editor
        editor_frame = ttk.Frame(self)
        editor_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        self.txt = tk.Text(editor_frame, wrap="none", height=14, undo=True)
        ysb = ttk.Scrollbar(editor_frame, orient="vertical", command=self.txt.yview)
        xsb = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.txt.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        # Pre-fill with current mappings
        initial_text = _alias_map_to_text(options)
        if initial_text:
            self.txt.insert("1.0", initial_text)

        # --- buttons
        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        btns.grid_columnconfigure(0, weight=1)

        self.btn_apply = ttk.Button(btns, text="Apply", command=self._on_apply)
        self.btn_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        self.btn_clear = ttk.Button(btns, text="Clear", command=self._on_clear)

        self.btn_clear.grid(row=0, column=0, sticky="w")
        self.btn_cancel.grid(row=0, column=1, sticky="e", padx=(0, 6))
        self.btn_apply.grid(row=0, column=2, sticky="e")

        # Key bindings
        self.bind("<Escape>", lambda e: self._on_cancel(), add=True)
        self.bind("<Control-Return>", lambda e: self._on_apply(), add=True)

        # reasonable default size
        self.geometry("760x520")

    def _on_clear(self) -> None:
        if messagebox.askyesno("Clear aliases", "Clear all alias mappings?", parent=self):
            self.txt.delete("1.0", tk.END)

    def _on_cancel(self) -> None:
        self.result = AliasDialogResult(applied=False, text="")
        self.destroy()

    def _on_apply(self) -> None:
        text = self.txt.get("1.0", tk.END).strip()

        # Validate by attempting parse into a temp dict
        tmp = AnalysisOptions()
        try:
            tmp.set_alias_map_from_lines(text)
        except Exception as e:
            messagebox.showerror("Alias parse error", str(e), parent=self)
            return

        # Apply to provided options
        self._options.set_alias_map_from_lines(text)
        self.result = AliasDialogResult(applied=True, text=text)
        self.destroy()


def open_aliases_dialog(
    parent: tk.Tk | tk.Toplevel,
    options: AnalysisOptions,
) -> bool:
    """
    Open the aliases dialog modally.

    Returns True if user clicked Apply (i.e., options were updated), else False.
    """
    dlg = AliasesDialog(parent, options=options)
    parent.wait_window(dlg)
    return bool(dlg.result and dlg.result.applied)


__all__ = ["open_aliases_dialog", "AliasesDialog", "AliasDialogResult"]
