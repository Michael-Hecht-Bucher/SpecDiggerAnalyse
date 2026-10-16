# specdiggeranalyse/plotting.py
# -*- coding: utf-8 -*-

"""
Matplotlib plotting helpers for SpecDiggerAnalyse (GUI-free).

This module draws the two primary plots you have in the monolith:
- "main" (separate species; no Mg pairing)
- "combined" (Mg-paired base species), optionally with significance annotations

Design goals:
- No tkinter here (no FigureCanvasTkAgg).
- Accept an existing matplotlib Axes and draw into it.
- Return a small "render map" that the GUI can use for click/hover mapping:
    species_order, x_positions, bar_patches (optional)

Expected input data shapes (matching controllers/models):
- df_main / df_combined: columns at least ['species','mean_relative_%','sd','n'] (sd/n optional)
- per_file_matrix_*: DataFrame with index=file, columns=species, values=relative_%

The config dicts are those from constants.DEFAULT_PLOT_CFG_MAIN/COMBINED
and may be extended later without breaking these functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from .analysis import species_sort_key_amp_pairing


# -----------------------------------------------------------------------------
# Returned mapping for GUI interactions (click-to-open, hover, etc.)
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class PlotRenderMap:
    species_order: List[str]
    x_positions: np.ndarray
    bar_patches: List[Any]  # matplotlib.patches.Rectangle


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------
def _get_col(df: pd.DataFrame, name: str, default: float = 0.0) -> np.ndarray:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").to_numpy(dtype=float)
    return np.full(len(df), float(default), dtype=float)


def _apply_axis_style(ax: Axes, cfg: Dict[str, Any]) -> None:
    # This is intentionally conservative; keep it close to your current look.
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Optional grid toggle
    if cfg.get("grid", False):
        ax.grid(True, axis="y", linestyle="--", linewidth=0.8, alpha=0.4)


def _species_order_from_df(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty:
        return []
    if "species" not in df.columns:
        raise ValueError("Summary DataFrame must contain a 'species' column.")
    return df["species"].astype(str).tolist()


def _extract_points_for_species(
    per_file_matrix: Optional[pd.DataFrame],
    species_order: Sequence[str],
) -> Dict[str, np.ndarray]:
    """
    Returns dict: species -> array of per-file values (NaNs removed)
    """
    out: Dict[str, np.ndarray] = {}
    if per_file_matrix is None or per_file_matrix.empty:
        for s in species_order:
            out[s] = np.array([], dtype=float)
        return out

    # Ensure columns are strings
    cols = {str(c): c for c in per_file_matrix.columns}
    for s in species_order:
        if s in cols:
            vals = pd.to_numeric(per_file_matrix[cols[s]], errors="coerce").to_numpy(dtype=float)
            vals = vals[~np.isnan(vals)]
            out[s] = vals
        else:
            out[s] = np.array([], dtype=float)
    return out


def _jitter(n: int, width: float = 0.12, rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    rng = rng or np.random.default_rng(0)  # deterministic by default
    return rng.uniform(-width, width, size=n)


def _annotate_significance(
    ax: Axes,
    x_positions: np.ndarray,
    species_order: Sequence[str],
    means: np.ndarray,
    sig_pairs: Sequence[Tuple[str, str, float]],
    *,
    y_pad: float = 1.0,
    line_height: float = 0.8,
    fontsize: int = 10,
    skip_species_without_plus: bool = True,
) -> None:
    """
    Draw significance brackets for pairs in sig_pairs.

    Changes vs old behavior:
    - optionally skip species without ' + ' (e.g. protein alone like 'IbpA')
    - place brackets locally above the corresponding bars instead of globally at plot top
    """

    if not sig_pairs:
        return

    def p_to_stars(p: float) -> str:
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

    idx = {s: i for i, s in enumerate(species_order)}

    # keep track of already used y-levels for overlapping x-ranges
    placed_segments: List[Tuple[float, float, float]] = []

    # sort by span first (shorter/local comparisons lower), then by p-value
    def sort_key(t: Tuple[str, str, float]) -> Tuple[int, float]:
        g1, g2, p = t
        if g1 not in idx or g2 not in idx:
            return (9999, 1.0)
        span = abs(idx[g2] - idx[g1])
        try:
            pval = float(p)
        except Exception:
            pval = 1.0
        return (span, pval)

    pairs_sorted = sorted(sig_pairs, key=sort_key)

    for g1, g2, p in pairs_sorted:
        if g1 not in idx or g2 not in idx:
            continue
        if g1 == g2:
            continue

        # Skip protein-alone/main species comparisons
        if skip_species_without_plus:
            if (" + " not in g1) or (" + " not in g2):
                continue

        i, j = idx[g1], idx[g2]
        i, j = min(i, j), max(i, j)

        x1, x2 = float(x_positions[i]), float(x_positions[j])
        star = p_to_stars(p)

        # place locally above the taller of the two bars
        base_y = max(float(means[i]), float(means[j])) + y_pad

        # if overlapping an already placed segment, lift upward
        current_y = base_y
        while True:
            overlap = False
            for old_x1, old_x2, old_y in placed_segments:
                x_overlap = not (x2 < old_x1 or x1 > old_x2)
                y_close = abs(current_y - old_y) < (line_height + 0.4)
                if x_overlap and y_close:
                    current_y = old_y + line_height + 0.8
                    overlap = True
                    break
            if not overlap:
                break

        ax.plot(
            [x1, x1, x2, x2],
            [current_y, current_y + line_height, current_y + line_height, current_y],
            linewidth=1.2,
        )
        ax.text(
            (x1 + x2) / 2.0,
            current_y + line_height + 0.15,
            star,
            ha="center",
            va="bottom",
            fontsize=fontsize,
        )

        placed_segments.append((x1, x2, current_y))


def _draw_barplot_with_points(
    ax: Axes,
    summary_df: pd.DataFrame,
    per_file_matrix: Optional[pd.DataFrame],
    cfg: Dict[str, Any],
    *,
    title: Optional[str] = None,
    ylabel: str = "relative (%)",
    sig_pairs: Optional[Sequence[Tuple[str, str, float]]] = None,
) -> PlotRenderMap:
    """
    Core drawing routine for both main and combined plots.
    """
    ax.clear()
    _apply_axis_style(ax, cfg)

    if summary_df is None or summary_df.empty:
        ax.set_title(title or "")
        ax.set_ylabel(ylabel)
        ax.text(0.5, 0.5, "No data loaded.", ha="center", va="center", transform=ax.transAxes)
        return PlotRenderMap(species_order=[], x_positions=np.array([]), bar_patches=[])

    # Sort bars by plotted y-value (highest first)
    dfp = summary_df.copy()

    sort_by_amp_pairs = bool(cfg.get("sort_by_amp_pairs", False))

    if sort_by_amp_pairs:
        dfp["__sort_key"] = dfp["species"].map(species_sort_key_amp_pairing)
        dfp = dfp.sort_values("__sort_key", kind="mergesort").drop(columns="__sort_key")
    else:
        if "mean_relative_%" in dfp.columns:
            dfp["mean_relative_%"] = pd.to_numeric(dfp["mean_relative_%"], errors="coerce")
            dfp = dfp.sort_values(
                by="mean_relative_%",
                ascending=False,
                kind="mergesort",
                na_position="last",
                ignore_index=True,
            )

    species_order = _species_order_from_df(dfp)

    means = _get_col(dfp, "mean_relative_%", default=0.0)
    sds = _get_col(dfp, "sd", default=np.nan)

    # x positions
    spacing = float(cfg.get("spacing", 1.0) or 1.0)
    x = np.arange(len(species_order), dtype=float) * spacing

    bar_width = float(cfg.get("bar_width", 0.65) or 0.65)
    edgecolor = cfg.get("edgecolor", "#000000")
    edgewidth = float(cfg.get("edgewidth", 1.0) or 1.0)
    alpha = float(cfg.get("bars_alpha", 1.0) or 1.0)
    bar_color = cfg.get("bar_color", "#FFFFFF")

    # Bars
    bars = ax.bar(
        x,
        means,
        width=bar_width,
        alpha=alpha,
        edgecolor=edgecolor,
        linewidth=edgewidth,
        color=bar_color,
    )

    # Error bars if sd exists and enabled
    if cfg.get("show_errorbars", True) and "sd" in summary_df.columns:
        yerr = sds.copy()
        # ignore NaN SD
        yerr = np.where(np.isfinite(yerr), yerr, 0.0)
        ax.errorbar(x, means, yerr=yerr, fmt="none", capsize=3, linewidth=1.2)

    # Scatter per-file points
    if cfg.get("show_points", True):
        points_by_species = _extract_points_for_species(per_file_matrix, species_order)
        rng = np.random.default_rng(int(cfg.get("jitter_seed", 0) or 0))
        jitter_width = float(cfg.get("jitter_width", 0.12) or 0.12)

        for i, sp in enumerate(species_order):
            vals = points_by_species.get(sp, np.array([], dtype=float))
            if vals.size == 0:
                continue
            j = _jitter(vals.size, width=jitter_width, rng=rng)
            # if user specifies point_color use it; else default
            if cfg.get("point_color", None) is None:
                ax.scatter(x[i] + j, vals, s=18, alpha=0.9, zorder=3)
            else:
                ax.scatter(x[i] + j, vals, s=18, alpha=0.9, zorder=3, color=cfg["point_color"])

    # Labels, ticks, title
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    rotate = int(cfg.get("xtick_rotation", 45) or 45)
    ha = cfg.get("xtick_ha", "right")
    ax.set_xticks(x)
    ax.set_xticklabels(species_order, rotation=rotate, ha=ha)

    # y-limits: explicit if provided, otherwise automatic with headroom
    headroom = float(cfg.get("y_headroom", 10.0) or 10.0)
    ymax_auto = float(np.nanmax(means)) if len(means) else 0.0

    ylim_min = cfg.get("ylim_min", None)
    ylim_max = cfg.get("ylim_max", None)

    try:
        ymin = float(ylim_min) if ylim_min not in (None, "") else 0.0
    except Exception:
        ymin = 0.0

    try:
        ymax = float(ylim_max) if ylim_max not in (None, "") else max(0.0, ymax_auto + headroom)
    except Exception:
        ymax = max(0.0, ymax_auto + headroom)

    if ymax <= ymin:
        ymax = ymin + 1.0

    ax.set_ylim(ymin, ymax)

    # Significance annotations (typically on combined plot)
    if sig_pairs:
        _annotate_significance(
            ax,
            x_positions=x,
            species_order=species_order,
            means=means,
            sig_pairs=sig_pairs,
            y_pad=float(cfg.get("sig_y_pad", 2.0) or 2.0),
            line_height=float(cfg.get("sig_line_height", 0.8) or 0.8),
            fontsize=int(cfg.get("sig_fontsize", 10) or 10),
        )
        # Extend ylim for significance only if no explicit upper limit was set
        ylim_max = cfg.get("ylim_max", None)
        if ylim_max in (None, ""):
            ax.set_ylim(ax.get_ylim()[0], max(ax.get_ylim()[1], ymax_auto + headroom + 10.0))

    return PlotRenderMap(
        species_order=list(species_order),
        x_positions=x,
        bar_patches=list(bars),
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def draw_main(
    ax: Axes,
    df_main: pd.DataFrame,
    per_file_matrix_main: Optional[pd.DataFrame],
    plot_cfg_main: Dict[str, Any],
    *,
    title: str = "Separate species",
    ylabel: str = "relative (%)",
) -> PlotRenderMap:
    """
    Draw the main plot into ax.
    """
    return _draw_barplot_with_points(
        ax=ax,
        summary_df=df_main,
        per_file_matrix=per_file_matrix_main,
        cfg=plot_cfg_main,
        title=title,
        ylabel=ylabel,
        sig_pairs=None,
    )


def draw_combined(
    ax: Axes,
    df_combined: pd.DataFrame,
    per_file_matrix_combined: Optional[pd.DataFrame],
    plot_cfg_combined: Dict[str, Any],
    *,
    sig_pairs: Optional[Sequence[Tuple[str, str, float]]] = None,
    title: str = "Combined Mg pairs",
    ylabel: str = "relative (%)",
) -> PlotRenderMap:
    """
    Draw the combined plot into ax, optionally adding significance brackets.
    """
    return _draw_barplot_with_points(
        ax=ax,
        summary_df=df_combined,
        per_file_matrix=per_file_matrix_combined,
        cfg=plot_cfg_combined,
        title=title,
        ylabel=ylabel,
        sig_pairs=sig_pairs,
    )


__all__ = [
    "PlotRenderMap",
    "draw_main",
    "draw_combined",
]
