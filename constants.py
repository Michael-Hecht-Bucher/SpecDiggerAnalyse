# specdiggeranalyse/constants.py
# -*- coding: utf-8 -*-

"""
Central constants for SpecDiggerAnalyse.

Rule:
- Only constants + tiny dependency-free helpers.
- No tkinter/matplotlib/pandas/scipy here.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# App identity
# -----------------------------------------------------------------------------
APP_NAME: str = "SpecDiggerAnalyse"
APP_TITLE: str = "SpecDiggerAnalyse - Analysis GUI for SpecDigger Output"

# -----------------------------------------------------------------------------
# Input / output file conventions
# -----------------------------------------------------------------------------
INPUT_FILE_EXTENSIONS: tuple[str, ...] = (".xlsx",)
EXPORT_DEFAULT_BASENAME: str = "SpecDiggerAnalyse_export"

# -----------------------------------------------------------------------------
# DataFrame column names (single source of truth)
# -----------------------------------------------------------------------------
COL_SPECIES: str = "species"
COL_AREA_REAL: str = "A (real)"

# Derived / internal columns used across the app
COL_AREA_SUM: str = "A_real_sum"
COL_RELATIVE: str = "relative_%"

REQUIRED_COLS: List[str] = [COL_SPECIES, COL_AREA_REAL]

# -----------------------------------------------------------------------------
# Species string conventions (v2.5.6 additions)
# -----------------------------------------------------------------------------
# AMPylation label suffix used by v2.5.6
AMP_SUFFIX: str = "-AMP"

# Matches a trailing "+ Mg" / "+ 2 Mg" / "+ Mg2+" etc. (case-insensitive)
MG_SUFFIX_RE = re.compile(
    r"(?:\s*\+\s*(?:\d+\s*)?Mg(?:2\+)?\s*)$",
    re.IGNORECASE,
)

# -----------------------------------------------------------------------------
# Plot configuration defaults
# (Keep dict-based: dialogs likely mutate these directly.)
#
# v2.5.6 adds axes sizing in inches; include those keys now so configs round-trip.
# -----------------------------------------------------------------------------
DEFAULT_PLOT_CFG_MAIN: Dict[str, Any] = {
    "bar_width": 0.65,
    "bar_color": "#FFFFFF",
    "bars_alpha": 1.0,
    "edgecolor": "#000000",
    "edgewidth": 1.0,

    "show_points": True,
    "point_color": None,
    "jitter_width": 0.12,
    "jitter_seed": 0,

    "show_errorbars": True,

    "xtick_rotation": 45,
    "xtick_ha": "right",

    "grid": False,

    # v2.5.6-style axes sizing (inches); if None, fall back to legacy fig_w/fig_h
    "axes_w_in": None,
    "axes_h_in": None,
    # margins in inches: left, right, top, bottom
    "margins_in": (0.8, 0.25, 0.35, 0.8),

    # legacy figure sizing (kept for backward compatibility)
    "fig_w": None,
    "fig_h": 6.5,

    # spacing multiplier between categories
    "spacing": 1.0,

    # significance annotations (only used on combined plot normally)
    "sig_y_pad": 2.0,
    "sig_line_height": 0.8,
    "sig_fontsize": 10,

    "y_headroom": 10.0,
    "ylim_min": None,
    "ylim_max": None,
}

DEFAULT_PLOT_CFG_COMBINED: Dict[str, Any] = {
    "bar_width": 0.5,
    "bar_color": "#FFFFFF",
    "bars_alpha": 1.0,
    "edgecolor": "#000000",
    "edgewidth": 1.0,

    "show_points": True,
    "point_color": None,
    "jitter_width": 0.12,
    "jitter_seed": 0,

    "show_errorbars": True,

    "xtick_rotation": 45,
    "xtick_ha": "right",

    "grid": False,

    # v2.5.6 sizing
    "axes_w_in": None,
    "axes_h_in": None,
    "margins_in": (0.8, 0.25, 0.35, 0.8),

    # legacy sizing
    "fig_w": None,
    "fig_h": 6.5,

    "spacing": 1.0,

    "sig_y_pad": 2.0,
    "sig_line_height": 0.8,
    "sig_fontsize": 10,

    "y_headroom": 10.0,
    "ylim_min": None,
    "ylim_max": None,
}


def new_default_plot_cfg_main() -> Dict[str, Any]:
    return deepcopy(DEFAULT_PLOT_CFG_MAIN)


def new_default_plot_cfg_combined() -> Dict[str, Any]:
    return deepcopy(DEFAULT_PLOT_CFG_COMBINED)

# -----------------------------------------------------------------------------
# Export conventions (xlsx sheet names)
# -----------------------------------------------------------------------------
SHEET_SEPARATE_SPECIES: str = "separate_species"
SHEET_PER_FILE_MAIN: str = "per_file_main"
SHEET_COMBINED_MG_PAIRS: str = "combined_Mg_pairs"
SHEET_PER_FILE_COMBINED: str = "per_file_combined"
SHEET_STATISTICS: str = "statistics"
SHEET_ANALYSIS_FILES: str = "analysis_files"

EXPORT_SHEET_NAMES: Dict[str, str] = {
    "separate_species": SHEET_SEPARATE_SPECIES,
    "per_file_main": SHEET_PER_FILE_MAIN,
    "combined_Mg_pairs": SHEET_COMBINED_MG_PAIRS,
    "per_file_combined": SHEET_PER_FILE_COMBINED,
    "statistics": SHEET_STATISTICS,
    "analysis_files": SHEET_ANALYSIS_FILES,
}
