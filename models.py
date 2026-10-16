# specdiggeranalyse/models.py
# -*- coding: utf-8 -*-

"""
Dataclasses / state models for SpecDiggerAnalyse.

Goal:
- Stop scattering state across the Tk App class.
- Centralize "what the app knows" (data, results, configs) in structured objects.
- Keep GUI-free: no tkinter, no matplotlib.

These models are designed to mirror your current monolith's attributes:
- per_file_raw (list of (Path, DataFrame))
- unbound_selected (normalization species list)
- alias_map (mapping for Mg-pair combining / canonical base naming)
- plot_cfg_main / plot_cfg_comb (customization dialog outputs)
- current_df_view / current_df_view_combined (summary tables)
- per_file_matrix / per_file_matrix_combined (per-file points matrices)
- stats outputs (anova/tukey/sig_pairs)

Patched for v2.5.6:
- Analysis option: group_modified_unmodified (AMP grouping toggle)
- Plot config keys (axes sizing in inches) are supported through dicts
- Results carry combined stats + per-row convenience fields for export/UI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .constants import new_default_plot_cfg_combined, new_default_plot_cfg_main


# -----------------------------------------------------------------------------
# User-configurable analysis options
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class AnalysisOptions:
    """
    - unbound_selected: species used as normalization denominator
    - alias_map: mapping alias->canonical (lowercase keys recommended)
    - group_modified_unmodified: v2.5.6 toggle to collapse '-AMP' variants
    """
    unbound_selected: List[str] = field(default_factory=list)
    alias_map: Dict[str, str] = field(default_factory=dict)
    group_modified_unmodified: bool = False
    sort_plots_by_amp_pairs: bool = False

    def set_alias_map_from_lines(self, text: str) -> None:
        """
        Parse alias editor lines into alias_map.

        Expected formats:
          canonical = alias1, alias2
          canonical: alias1; alias2

        Stores mapping alias->canonical (lower-cased keys).
        """
        self.alias_map.clear()
        if not text:
            return

        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                left, right = line.split("=", 1)
            elif ":" in line:
                left, right = line.split(":", 1)
            else:
                continue

            canonical = left.strip()
            if not canonical:
                continue

            aliases = [a.strip() for a in right.replace(";", ",").split(",") if a.strip()]

            # map canonical to itself as well
            self.alias_map[canonical.lower()] = canonical
            for a in aliases:
                self.alias_map[a.lower()] = canonical


# -----------------------------------------------------------------------------
# Plot config model (dict-based for backward compatibility with dialogs)
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class PlotConfigs:
    main: Dict[str, Any] = field(default_factory=new_default_plot_cfg_main)
    combined: Dict[str, Any] = field(default_factory=new_default_plot_cfg_combined)


# -----------------------------------------------------------------------------
# Ingested data state
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class DataState:
    per_file_raw: List[Tuple[Path, pd.DataFrame]] = field(default_factory=list)

    @property
    def files(self) -> List[Path]:
        return [p for p, _ in self.per_file_raw]

    @property
    def filenames(self) -> List[str]:
        return [p.name for p, _ in self.per_file_raw]

    def clear(self) -> None:
        self.per_file_raw.clear()

    def is_empty(self) -> bool:
        return len(self.per_file_raw) == 0


# -----------------------------------------------------------------------------
# Computed results state (what the UI renders / exports)
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class ResultsState:
    # Loaded/raw species summaries (pre-normalization UI)
    df_loaded_main: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_loaded_combined: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Main summary and per-file points
    df_main: pd.DataFrame = field(default_factory=pd.DataFrame)
    per_file_matrix_main: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Combined summary and per-file points
    df_combined: pd.DataFrame = field(default_factory=pd.DataFrame)
    per_file_matrix_combined: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Combined stats outputs
    anova: Dict[str, Any] = field(default_factory=dict)
    tukey: pd.DataFrame = field(default_factory=pd.DataFrame)
    sig_pairs: List[Tuple[str, str, float]] = field(default_factory=list)

    # Optional export/UI convenience: analysis files list
    analysis_files: List[str] = field(default_factory=list)

    # Metadata (hover/click info)
    global_files: List[str] = field(default_factory=list)
    zmin_by_species: Dict[str, float] = field(default_factory=dict)
    zmax_by_species: Dict[str, float] = field(default_factory=dict)

    global_files_combined: List[str] = field(default_factory=list)
    zmin_by_base: Dict[str, float] = field(default_factory=dict)
    zmax_by_base: Dict[str, float] = field(default_factory=dict)

    def clear(self) -> None:
        self.df_loaded_main = pd.DataFrame()
        self.df_loaded_combined = pd.DataFrame()
        self.df_main = pd.DataFrame()
        self.per_file_matrix_main = pd.DataFrame()
        self.df_combined = pd.DataFrame()
        self.per_file_matrix_combined = pd.DataFrame()
        self.anova = {}
        self.tukey = pd.DataFrame()
        self.sig_pairs = []
        self.analysis_files = []
        self.global_files = []
        self.zmin_by_species = {}
        self.zmax_by_species = {}
        self.global_files_combined = []
        self.zmin_by_base = {}
        self.zmax_by_base = {}


# -----------------------------------------------------------------------------
# Top-level app state
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class AppState:
    data: DataState = field(default_factory=DataState)
    options: AnalysisOptions = field(default_factory=AnalysisOptions)
    plots: PlotConfigs = field(default_factory=PlotConfigs)
    results: ResultsState = field(default_factory=ResultsState)

    def reset_all(self) -> None:
        self.data.clear()
        self.results.clear()
        self.options.unbound_selected = []
        self.options.alias_map = {}
        self.options.group_modified_unmodified = False
        self.options.sort_plots_by_amp_pairs = False


__all__ = [
    "AnalysisOptions",
    "PlotConfigs",
    "DataState",
    "ResultsState",
    "AppState",
]
