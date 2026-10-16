# specdiggeranalyse/stats.py
# -*- coding: utf-8 -*-

"""
Statistics helpers for SpecDiggerAnalyse.

This module is intentionally GUI- and plotting-free.
It contains only statistical computations and formatting helpers.

Extracted from SpecDiggerAnalyse_v2-5-3.py:
- _p_to_stars
- _sci_str
- compute_combined_stats

v2.5.6 compatibility:
- p->stars
- scientific formatting with comma decimal
- ANOVA + Tukey HSD for combined view
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd


def _p_to_stars(p: float) -> str:
    """Map p-value to star annotation."""
    try:
        p = float(p)
    except Exception:
        return "ns"
    if p <= 0.001:
        return "***"
    if p <= 0.01:
        return "**"
    if p <= 0.05:
        return "*"
    return "ns"


def _sci_str(p: float, decimals: int = 3) -> str:
    """
    Format p in scientific notation, with comma decimal separator.

    - Returns "" for NaN/None
    - Clamps extremely small values to avoid underflow printing as 0
    """
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ""
    try:
        p = float(p)
    except Exception:
        return str(p)
    p = max(p, 1e-300)
    return f"{p:.{decimals}E}".replace(".", ",")


def compute_combined_stats(
    per_file_points_combined: List[pd.Series],
    *,
    alpha: float = 0.05,
) -> Tuple[Dict, pd.DataFrame, List[Tuple[str, str, float]]]:
    """
    Compute one-way ANOVA + Tukey HSD for combined (base species) relative_% values.

    Args:
      per_file_points_combined:
        list of Series (index=species, values=relative_%); one Series per file.
      alpha:
        significance level for Tukey HSD.

    Returns:
      anova_dict: {'F','df_between','df_within','p'} or {} if insufficient data
      tukey_df: DataFrame with cols
        ['group1','group2','meandiff','p_adj','lower','upper','reject']
        empty if insufficient data
      sig_pairs: list[(group1, group2, p_adj)] where reject==True
    """
    # Build long table
    rows = []
    for s in per_file_points_combined or []:
        if s is None or len(s) == 0:
            continue
        for sp, val in s.items():
            if pd.notna(val):
                rows.append((str(sp), float(val)))

    if not rows:
        return {}, pd.DataFrame(), []

    long = pd.DataFrame(rows, columns=["species", "value"])

    # Group values for ANOVA (require >=2 per group to be safe)
    grouped = long.groupby("species")["value"].apply(list)
    groups_for_anova = [vals for vals in grouped if len(vals) >= 2]
    if len(groups_for_anova) < 2:
        # Not enough replication for ANOVA; still allow Tukey? (usually not useful)
        return {}, pd.DataFrame(), []

    F, p = stats.f_oneway(*groups_for_anova)
    df_between = len(groups_for_anova) - 1
    df_within = sum(len(g) for g in groups_for_anova) - len(groups_for_anova)

    anova_dict = {
        "F": float(F),
        "df_between": int(df_between),
        "df_within": int(df_within),
        "p": float(p),
    }

    # Tukey HSD across all entries (long table)
    tukey = pairwise_tukeyhsd(
        endog=long["value"].to_numpy(dtype=float),
        groups=long["species"].to_numpy(dtype=str),
        alpha=alpha,
    )

    td = pd.DataFrame(
        tukey._results_table.data[1:],
        columns=tukey._results_table.data[0],
    ).rename(columns={"p-adj": "p_adj"})

    # Normalize dtypes
    for c in ("meandiff", "p_adj", "lower", "upper"):
        if c in td.columns:
            td[c] = pd.to_numeric(td[c], errors="coerce")
    if "reject" in td.columns:
        td["reject"] = td["reject"].astype(bool)

    # Keep only the canonical order/columns
    keep_cols = ["group1", "group2", "meandiff", "p_adj", "lower", "upper", "reject"]
    td = td[keep_cols]

    sig_pairs = [
        (str(r["group1"]), str(r["group2"]), float(r["p_adj"]))
        for _, r in td.iterrows()
        if bool(r["reject"]) and pd.notna(r["p_adj"])
    ]

    return anova_dict, td, sig_pairs


__all__ = ["_p_to_stars", "_sci_str", "compute_combined_stats"]
