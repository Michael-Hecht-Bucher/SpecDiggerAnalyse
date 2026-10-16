# specdiggeranalyse/io_excel.py
# -*- coding: utf-8 -*-

"""
Excel I/O for SpecDiggerAnalyse (GUI-free).

Extracted from SpecDiggerAnalyse_v2-5-3.py:
- read_excels
- read_excels_separate

Extended slightly to keep responsibilities clean:
- small helpers for column validation + numeric coercion
- optional inclusion of column "z" if present (as in your monolith)

Guiding rule:
- No tkinter, no matplotlib here.
- This module is responsible for reading/cleaning input tables only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import pandas as pd

from .constants import COL_AREA_REAL, COL_SPECIES, REQUIRED_COLS


def _ensure_files(files: Sequence[Path]) -> List[Path]:
    if not files:
        raise FileNotFoundError("No files were provided.")
    out: List[Path] = []
    for f in files:
        p = Path(f)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        out.append(p)
    return out


def _validate_required_columns(df: pd.DataFrame, required: Sequence[str], filename: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{filename} is missing columns: {missing}")


def _clean_species_and_area(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standard cleaning used in the monolith:
    - species: cast to str + strip
    - A(real): to_numeric(errors='coerce')
    - drop rows where species or A(real) is NaN/empty
    """
    d = df.copy()

    d[COL_SPECIES] = d[COL_SPECIES].astype(str).str.strip()
    # Treat empty species strings as missing
    d.loc[d[COL_SPECIES].eq(""), COL_SPECIES] = pd.NA

    d[COL_AREA_REAL] = pd.to_numeric(d[COL_AREA_REAL], errors="coerce")

    d = d.dropna(subset=[COL_SPECIES, COL_AREA_REAL])
    return d


def _maybe_clean_z(d: pd.DataFrame) -> pd.DataFrame:
    """If column 'z' exists, coerce to numeric (as in your monolith)."""
    if "z" in d.columns:
        d["z"] = pd.to_numeric(d["z"], errors="coerce")
    return d


def read_excels(files: Sequence[Path]) -> pd.DataFrame:
    """
    Read and combine the given Excel files, enforcing required columns and EU number formats.

    - Uses decimal="," and thousands="." like your current implementation.
    - Keeps only REQUIRED_COLS (species, A(real)).
    - Returns concatenated long table.
    """
    files = _ensure_files(files)

    dfs: List[pd.DataFrame] = []
    for f in files:
        df = pd.read_excel(f, decimal=",", thousands=".")
        _validate_required_columns(df, REQUIRED_COLS, f.name)

        d = df[list(REQUIRED_COLS)].copy()
        d = _clean_species_and_area(d)

        dfs.append(d)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=list(REQUIRED_COLS))


def read_excels_separate(files: Sequence[Path]) -> List[Tuple[Path, pd.DataFrame]]:
    """
    Read each Excel file separately and return a list of (Path, DataFrame).

    Mirrors monolith behavior:
    - Requires REQUIRED_COLS
    - additionally keeps "z" if present
    - cleans species + A(real) (+ z numeric coercion if present)
    """
    files = _ensure_files(files)

    out: List[Tuple[Path, pd.DataFrame]] = []
    for f in files:
        df = pd.read_excel(f, decimal=",", thousands=".")
        _validate_required_columns(df, REQUIRED_COLS, f.name)

        cols = [COL_SPECIES, COL_AREA_REAL] + (["z"] if "z" in df.columns else [])
        d = df[cols].copy()

        d = _clean_species_and_area(d)
        d = _maybe_clean_z(d)

        out.append((f, d))

    return out


__all__ = [
    "read_excels",
    "read_excels_separate",
]
