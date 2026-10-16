# specdiggeranalyse/analysis.py
# -*- coding: utf-8 -*-

"""
Core data transformations for SpecDiggerAnalyse (GUI-free).

Extracted from SpecDiggerAnalyse_v2-5-3.py:
- base_without_mg
- collapse_two_nucleotides
- map_to_base
- aggregate_by_species
- compute_relative
- per_file_relative
- per_file_relative_combined
- per_file_intermediates
- combine_relatives
- build_main_metadata
- build_combined_metadata
- _fmt_z_range
- _files_signature

Guiding rule:
- No tkinter, no matplotlib here.
- Pure computations on pandas objects + small formatting helpers.

Patched for v2.5.6:
- Update imports
- Add AMP helper functions
"""

from __future__ import annotations

import re
from collections import defaultdict
from math import inf
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from .constants import (
    COL_AREA_REAL,
    COL_AREA_SUM,
    COL_RELATIVE,
    COL_SPECIES,
    MG_SUFFIX_RE,
    AMP_SUFFIX,
)

from .mass_tables import NUCLEOTIDE_NAMES


# -----------------------------------------------------------------------------
# Species name normalization / mapping
# -----------------------------------------------------------------------------
def base_without_mg(name: str) -> str:
    """Strip a trailing Mg token like '+ Mg', '+ 2Mg', '+ Mg2+' at the end of the species."""
    s = str(name).strip()
    # Strip exactly one trailing Mg token
    return MG_SUFFIX_RE.sub("", s).strip()


def collapse_two_nucleotides(name: str) -> str:
    """
    Collapse trailing ' + 2<NUC>' to ' + <NUC>' (after Mg was stripped in the usual workflow).
    """
    s = str(name).strip()
    for nuc in NUCLEOTIDE_NAMES:
        s = re.sub(
            rf"(\s*\+\s*)2\s*{re.escape(nuc)}\s*$",
            r"\1" + nuc,
            s,
            flags=re.IGNORECASE,
        )
    return s


def map_to_base(name: str, alias_map: Optional[Dict[str, str]] = None) -> str:
    """
    1) Strip Mg suffix
    2) Apply user alias map (case-insensitive keys)

    Alias map keys are matched after Mg-strip, lower-cased.
    Values are returned as canonical base (Mg stripped as well).
    """
    base = base_without_mg(name)
    if alias_map:
        mapped = alias_map.get(base.lower())
        if mapped:
            return base_without_mg(mapped).strip()
    return base

def split_species_amp(species: str) -> tuple[str, bool]:
    """
    Split a species label into (base_without_amp, is_ampylated).

    v2.5.6 convention: AMPylated species end with "-AMP".
    """
    s = str(species).strip()
    if s.endswith(AMP_SUFFIX):
        return s[: -len(AMP_SUFFIX)].rstrip(), True
    return s, False


def canonical_no_amp_label(species: str) -> str:
    """
    Return species label without the trailing '-AMP' if present.
    """
    base, _is_amp = split_species_amp(species)
    return base


def species_sort_key_amp_pairing(species: str) -> tuple[str, int, str]:
    """
    Sorting key that groups unmodified and AMPylated species next to each other.

    Order:
      1) canonical base (species without '-AMP')
      2) unmodified first (0), then AMPylated (1)
      3) tie-breaker by full label for stability

    This mirrors the intent in v2.5.6 (paired visual adjacency).
    """
    full = str(species).strip()
    base, is_amp = split_species_amp(full)
    return (base.lower(), 1 if is_amp else 0, full.lower())

# -----------------------------------------------------------------------------
# Aggregation & normalization (single file / global)
# -----------------------------------------------------------------------------
def aggregate_by_species(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sum A(real) per species.

    Returns DataFrame with columns: ['species', 'A_real_sum'] sorted descending by A_real_sum.
    """
    agg = (
        df.groupby(COL_SPECIES, as_index=False)[COL_AREA_REAL]
        .sum()
        .rename(columns={COL_AREA_REAL: COL_AREA_SUM})
    )
    return agg.sort_values(COL_AREA_SUM, ascending=False, ignore_index=True)


def compute_relative(df_agg: pd.DataFrame, normalization_species: List[str]) -> Tuple[pd.DataFrame, float]:
    """
    Compute relative_% from an already aggregated table (species, A_real_sum),
    normalizing by sum(A_real_sum) of selected normalization_species.

    Returns (df_out, denom).
    """
    out = df_agg.copy()

    if not normalization_species:
        out[COL_RELATIVE] = 0.0
        return out, 0.0

    # Case-insensitive selection against df_agg's species
    lower_map = {s.lower(): s for s in out[COL_SPECIES].tolist()}
    selected = [lower_map[s.lower()] for s in normalization_species if s.lower() in lower_map]

    denom = float(out.loc[out[COL_SPECIES].isin(selected), COL_AREA_SUM].sum())
    if denom <= 0:
        out[COL_RELATIVE] = 0.0
        return out, 0.0

    out[COL_RELATIVE] = 100.0 * out[COL_AREA_SUM] / denom
    return out.sort_values(COL_RELATIVE, ascending=False, ignore_index=True), denom


def per_file_relative(df_one: pd.DataFrame, normalization_species: List[str]) -> pd.DataFrame:
    """
    For a single file:
      1) sum A(real) by species
      2) compute relative_% by normalizing to sum(A_real_sum) of selected normalization species

    Returns DataFrame with columns ['species', 'relative_%'] (relative_% may be <NA>).
    """
    agg = (
        df_one.groupby(COL_SPECIES, as_index=False)[COL_AREA_REAL]
        .sum()
        .rename(columns={COL_AREA_REAL: COL_AREA_SUM})
    )

    if not normalization_species:
        agg[COL_RELATIVE] = pd.NA
        return agg[[COL_SPECIES, COL_RELATIVE]]

    lower_map = {s.lower(): s for s in agg[COL_SPECIES].tolist()}
    selected = [lower_map[s.lower()] for s in normalization_species if s.lower() in lower_map]

    denom = float(agg.loc[agg[COL_SPECIES].isin(selected), COL_AREA_SUM].sum())
    if denom <= 0:
        agg[COL_RELATIVE] = pd.NA
        return agg[[COL_SPECIES, COL_RELATIVE]]

    agg[COL_RELATIVE] = 100.0 * agg[COL_AREA_SUM] / denom
    return agg[[COL_SPECIES, COL_RELATIVE]]


def per_file_relative_combined(
    df_one: pd.DataFrame,
    normalization_species: List[str],
    alias_map: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Combine A(real) for base species with their '+ Mg' counterpart within a single file,
    then compute relative_% per *base* species using combined sums and combined unbound denom.

    Returns: ['species', 'relative_%'] where 'species' are canonical base names.
    """
    agg = (
        df_one.groupby(COL_SPECIES, as_index=False)[COL_AREA_REAL]
        .sum()
        .rename(columns={COL_AREA_REAL: COL_AREA_SUM})
    )

    # Map to canonical base
    agg["base"] = agg[COL_SPECIES].map(lambda s: map_to_base(s, alias_map))
    comb = (
        agg.groupby("base", as_index=False)[COL_AREA_SUM]
        .sum()
        .rename(columns={"base": COL_SPECIES})
    )

    if not normalization_species:
        comb[COL_RELATIVE] = pd.NA
        return comb[[COL_SPECIES, COL_RELATIVE]]

    unbound_bases = {map_to_base(s, alias_map) for s in normalization_species}
    denom = float(comb.loc[comb[COL_SPECIES].isin(unbound_bases), COL_AREA_SUM].sum())
    if denom <= 0:
        comb[COL_RELATIVE] = pd.NA
        return comb[[COL_SPECIES, COL_RELATIVE]]

    comb[COL_RELATIVE] = 100.0 * comb[COL_AREA_SUM] / denom
    return comb[[COL_SPECIES, COL_RELATIVE]]


# -----------------------------------------------------------------------------
# Per-file intermediates for export/debugging
# -----------------------------------------------------------------------------
def per_file_intermediates(df_one: pd.DataFrame, normalization_species: List[str]) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      ['species', 'A_real_sum', 'relative_%', 'Total sum A(real)', 'Sum A(real):<name>', ...]
    One row per species in this file.

    NOTE: Column "Total sum A(real)" is the normalization denominator (sum over selected species).
    """
    agg = (
        df_one.groupby(COL_SPECIES, as_index=False)[COL_AREA_REAL]
        .sum()
        .rename(columns={COL_AREA_REAL: COL_AREA_SUM})
    )

    # Map for case-insensitive selection
    lower_map = {s.lower(): s for s in agg[COL_SPECIES].tolist()}
    selected = [lower_map[s.lower()] for s in normalization_species if s.lower() in lower_map]

    out = agg.copy()

    # Per-normalization-species sums (constant across rows for this file)
    for u in normalization_species:
        u_real = float(agg.loc[agg[COL_SPECIES].str.lower().eq(u.lower()), COL_AREA_SUM].sum())
        out[f"Sum A(real):{u}"] = u_real

    denom = float(agg.loc[agg[COL_SPECIES].isin(selected), COL_AREA_SUM].sum()) if selected else 0.0
    out["Total sum A(real)"] = denom
    out[COL_RELATIVE] = (100.0 * out[COL_AREA_SUM] / denom) if denom > 0 else pd.NA

    return out[
        [COL_SPECIES, COL_AREA_SUM, COL_RELATIVE, "Total sum A(real)"]
        + [f"Sum A(real):{u}" for u in normalization_species]
    ]


# -----------------------------------------------------------------------------
# Combine multiple per-file relative tables into mean/SD/n per species
# -----------------------------------------------------------------------------
def combine_relatives(rel_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    rel_list: list of DataFrames (one per file) with ['species','relative_%'] (may contain NaNs)

    Returns a DataFrame with columns:
      ['species', 'mean_relative_%', 'sd', 'n']
    """
    if not rel_list:
        return pd.DataFrame(columns=[COL_SPECIES, "mean_relative_%", "sd", "n"])

    base = rel_list[0].rename(columns={COL_RELATIVE: "rel_0"})
    for i, df in enumerate(rel_list[1:], start=1):
        base = base.merge(df.rename(columns={COL_RELATIVE: f"rel_{i}"}), on=COL_SPECIES, how="outer")

    rel_cols = [c for c in base.columns if c.startswith("rel_")]
    vals = base[rel_cols].apply(pd.to_numeric, errors="coerce")

    mean = vals.mean(axis=1, skipna=True)
    sd = vals.std(axis=1, ddof=1, skipna=True)  # sample SD
    n = vals.count(axis=1)

    out = (
        pd.DataFrame(
            {
                COL_SPECIES: base[COL_SPECIES],
                "mean_relative_%": mean,
                "sd": sd,
                "n": n,
            }
        )
        .sort_values("mean_relative_%", ascending=False, na_position="last", ignore_index=True)
    )
    return out


# -----------------------------------------------------------------------------
# Metadata helpers (used for hover/click info in the UI)
# -----------------------------------------------------------------------------
def _fmt_z_range(zmin: float, zmax: float) -> str:
    if zmin is None or zmax is None or zmin is inf or zmax == -inf:
        return ""
    try:
        a, b = int(round(zmin)), int(round(zmax))
        return f"{a}" if a == b else f"{a}–{b}"
    except Exception:
        return ""


def _files_signature(files: List[str], preview: int = 2) -> str:
    """Compact display: first N filenames, then an '… (+k)' suffix if more."""
    if not files:
        return ""
    files = sorted(files)
    if len(files) <= preview:
        return ", ".join(files)
    return f"{', '.join(files[:preview])} … (+{len(files)-preview})"


def build_main_metadata(
    per_file_raw: List[Tuple[Path, pd.DataFrame]]
) -> Tuple[List[str], Dict[str, float], Dict[str, float]]:
    """
    MAIN table metadata:
    - global_files: sorted list of all filenames
    - zmin_by_species: min z per exact species label
    - zmax_by_species: max z per exact species label
    """
    global_files = sorted({p.name for p, _ in per_file_raw})
    zmin_by_species = defaultdict(lambda: inf)
    zmax_by_species = defaultdict(lambda: -inf)

    for _, df in per_file_raw:
        if "z" in df.columns:
            tmp = df[[COL_SPECIES, "z"]].dropna(subset=[COL_SPECIES, "z"])
            if not tmp.empty:
                g = tmp.groupby(COL_SPECIES)["z"].agg(["min", "max"])
                for s, r in g.iterrows():
                    zmin_by_species[s] = min(zmin_by_species[s], r["min"])
                    zmax_by_species[s] = max(zmax_by_species[s], r["max"])

    return global_files, zmin_by_species, zmax_by_species


def build_combined_metadata(
    per_file_raw: List[Tuple[Path, pd.DataFrame]],
    alias_map: Optional[Dict[str, str]],
) -> Tuple[List[str], Dict[str, float], Dict[str, float]]:
    """
    COMBINED table metadata:
    - base names (±Mg merged, aliases applied, and " + 2NUC" collapsed)
    - global_files: sorted list of all filenames
    - zmin_by_base: min z per base
    - zmax_by_base: max z per base
    """
    global_files = sorted({p.name for p, _ in per_file_raw})
    zmin_by_base = defaultdict(lambda: inf)
    zmax_by_base = defaultdict(lambda: -inf)

    for _, df in per_file_raw:
        df2 = df.copy()
        df2["base"] = df2[COL_SPECIES].map(
            lambda s: map_to_base(collapse_two_nucleotides(base_without_mg(s)), alias_map)
        )
        if "z" in df2.columns:
            tmp = df2[["base", "z"]].dropna(subset=["base", "z"])
            if not tmp.empty:
                g = tmp.groupby("base")["z"].agg(["min", "max"])
                for b, r in g.iterrows():
                    zmin_by_base[b] = min(zmin_by_base[b], r["min"])
                    zmax_by_base[b] = max(zmax_by_base[b], r["max"])

    return global_files, zmin_by_base, zmax_by_base


__all__ = [
    "base_without_mg",
    "collapse_two_nucleotides",
    "map_to_base",
    "aggregate_by_species",
    "compute_relative",
    "per_file_relative",
    "per_file_relative_combined",
    "per_file_intermediates",
    "combine_relatives",
    "build_main_metadata",
    "build_combined_metadata",
    "_fmt_z_range",
    "_files_signature",
]
