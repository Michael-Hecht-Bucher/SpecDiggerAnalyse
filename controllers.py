# specdiggeranalyse/controllers.py
# -*- coding: utf-8 -*-

"""
Controller layer for SpecDiggerAnalyse.

Glue together IO + analysis + stats to populate ResultsState.

v2.5.6 additions:
- Option to group modified/unmodified species (AMP pairing toggle)
- Combined summary gets anova_p and significant_pairs columns (for UI/export)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import pandas as pd

from .analysis import (
    canonical_no_amp_label,
    combine_relatives,
    per_file_relative,
    per_file_relative_combined,
    build_main_metadata,
    build_combined_metadata,
)
from .io_excel import read_excels_separate
from .models import AppState
from .stats import _p_to_stars, compute_combined_stats
from .analysis import map_to_base
from .constants import COL_AREA_REAL, COL_SPECIES

def load_files_into_state(state: AppState, files: Sequence[str | Path]) -> None:
    paths = [Path(f) for f in files]
    state.data.per_file_raw = read_excels_separate(paths)

    # Pre-normalization summaries for immediate UI display
    state.results.df_loaded_main = _build_loaded_main_summary(state)
    state.results.df_loaded_combined = _build_loaded_combined_summary(state)


def _build_per_file_matrix_from_named(named_rel: List[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    """
    named_rel: [(filename, df_rel), ...]
    df_rel must have columns ['species','relative_%'].
    Returns a pivot matrix with index=file, columns=species, values=relative_%.
    """
    if not named_rel:
        return pd.DataFrame()

    frames = []
    for fname, df_rel in named_rel:
        d = df_rel.copy()
        d["file"] = fname
        frames.append(d)

    long = pd.concat(frames, ignore_index=True)
    long["relative_%"] = pd.to_numeric(long["relative_%"], errors="coerce")

    mat = long.pivot_table(
        index="file",
        columns="species",
        values="relative_%",
        aggfunc="first",
    ).sort_index()

    # Ensure deterministic column order (alphabetical) for stable exports
    mat = mat.reindex(sorted(mat.columns, key=lambda x: str(x).lower()), axis=1)
    return mat

def _build_loaded_main_summary(state: AppState) -> pd.DataFrame:
    """
    Build a pre-normalization species summary from raw loaded files.
    One row per exact species label.
    """
    if state.data.is_empty():
        return pd.DataFrame()

    frames = []
    for p, df in state.data.per_file_raw:
        d = df[[COL_SPECIES, COL_AREA_REAL]].copy()
        d["file"] = p.name
        frames.append(d)

    long = pd.concat(frames, ignore_index=True)

    out = (
        long.groupby(COL_SPECIES, as_index=False)
        .agg(
            A_real_sum=(COL_AREA_REAL, "sum"),
            files_n=("file", "nunique"),
        )
        .sort_values("A_real_sum", ascending=False, ignore_index=True)
    )

    return out

def _build_loaded_combined_summary(state: AppState) -> pd.DataFrame:
    """
    Build a pre-normalization combined/base-species summary from raw loaded files.
    Mg variants are merged via map_to_base().
    """
    if state.data.is_empty():
        return pd.DataFrame()

    alias_map = dict(state.options.alias_map) if state.options.alias_map else None

    frames = []
    for p, df in state.data.per_file_raw:
        d = df[[COL_SPECIES, COL_AREA_REAL]].copy()
        d["species"] = d[COL_SPECIES].map(lambda s: map_to_base(s, alias_map))
        d["file"] = p.name
        frames.append(d[["species", COL_AREA_REAL, "file"]])

    long = pd.concat(frames, ignore_index=True)

    out = (
        long.groupby("species", as_index=False)
        .agg(
            A_real_sum=(COL_AREA_REAL, "sum"),
            files_n=("file", "nunique"),
        )
        .sort_values("A_real_sum", ascending=False, ignore_index=True)
    )

    return out

def recompute_main(state: AppState) -> None:
    if state.data.is_empty():
        state.results.df_main = pd.DataFrame()
        state.results.per_file_matrix_main = pd.DataFrame()
        state.results.global_files = []
        state.results.zmin_by_species = {}
        state.results.zmax_by_species = {}
        return

    unbound = list(state.options.unbound_selected)

    named_rel: List[tuple[str, pd.DataFrame]] = []
    for p, df in state.data.per_file_raw:
        df_rel = per_file_relative(df, unbound)
        named_rel.append((p.name, df_rel))

    state.results.per_file_matrix_main = _build_per_file_matrix_from_named(named_rel)
    state.results.df_main = combine_relatives([df for _, df in named_rel])

    global_files, zmin, zmax = build_main_metadata(state.data.per_file_raw)
    state.results.global_files = global_files
    state.results.zmin_by_species = dict(zmin)
    state.results.zmax_by_species = dict(zmax)


def _group_amp_variants_in_rel_table(df_rel: pd.DataFrame) -> pd.DataFrame:
    """
    v2.5.6 feature: group modified/unmodified species.
    Here we collapse '-AMP' variants into their unmodified canonical label
    by summing relative_% per canonical label.

    NOTE: This groups at the *relative_%* level.
    In v2.5.6 the grouping is intended mainly for display adjacency and
    optional collapsing. This approach is consistent and simple.
    """
    if df_rel is None or df_rel.empty:
        return df_rel

    d = df_rel.copy()
    d["canon"] = d["species"].map(canonical_no_amp_label)
    d["relative_%"] = pd.to_numeric(d["relative_%"], errors="coerce")
    out = (
        d.groupby("canon", as_index=False)["relative_%"]
        .sum(min_count=1)
        .rename(columns={"canon": "species"})
    )
    return out


def recompute_combined(state: AppState) -> None:
    if state.data.is_empty():
        state.results.df_combined = pd.DataFrame()
        state.results.per_file_matrix_combined = pd.DataFrame()
        state.results.global_files_combined = []
        state.results.zmin_by_base = {}
        state.results.zmax_by_base = {}
        state.results.anova = {}
        state.results.tukey = pd.DataFrame()
        state.results.sig_pairs = []
        return

    unbound = list(state.options.unbound_selected)
    alias_map = dict(state.options.alias_map) if state.options.alias_map else None
    group_amp = bool(getattr(state.options, "group_modified_unmodified", False))

    named_rel: List[tuple[str, pd.DataFrame]] = []
    per_file_points_combined: List[pd.Series] = []

    for p, df in state.data.per_file_raw:
        df_rel = per_file_relative_combined(df, unbound, alias_map=alias_map)

        if group_amp:
            df_rel = _group_amp_variants_in_rel_table(df_rel)

        named_rel.append((p.name, df_rel))

        s = pd.Series(
            pd.to_numeric(df_rel["relative_%"], errors="coerce").values,
            index=df_rel["species"].astype(str).values,
        )
        per_file_points_combined.append(s.dropna())

    state.results.per_file_matrix_combined = _build_per_file_matrix_from_named(named_rel)

    df_comb = combine_relatives([df for _, df in named_rel])

    # --- stats on combined ---
    anova, tukey_df, sig_pairs = compute_combined_stats(per_file_points_combined)
    state.results.anova = anova
    state.results.tukey = tukey_df
    state.results.sig_pairs = sig_pairs

    # v2.5.6: add per-row columns to combined summary for UI/export convenience
    if not df_comb.empty:
        anova_p = anova.get("p") if isinstance(anova, dict) else None
        df_comb = df_comb.copy()
        df_comb["anova_p"] = anova_p

        # Store a compact summary string of significant pairs (stars)
        if sig_pairs:
            parts = [f"{a} vs {b} ({_p_to_stars(p)})" for a, b, p in sig_pairs]
            df_comb["significant_pairs"] = "; ".join(parts)
        else:
            df_comb["significant_pairs"] = ""

    state.results.df_combined = df_comb

    global_files, zmin, zmax = build_combined_metadata(state.data.per_file_raw, alias_map=alias_map)
    state.results.global_files_combined = global_files
    state.results.zmin_by_base = dict(zmin)
    state.results.zmax_by_base = dict(zmax)


def recompute_all(state: AppState) -> None:
    recompute_main(state)
    recompute_combined(state)


__all__ = [
    "load_files_into_state",
    "recompute_main",
    "recompute_combined",
    "recompute_all",
]
