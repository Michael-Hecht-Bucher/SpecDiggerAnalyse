# specdiggeranalyse/io_export.py
# -*- coding: utf-8 -*-

"""
Export helpers for SpecDiggerAnalyse (GUI-free).

Extracted from SpecDiggerAnalyse_v2-5-3.py:
- _export_csv
- _export_xlsx
- statistics sheet export (ANOVA + Tukey) with scientific p formatting
- analysis_files sidecar export

Guiding rule:
- No tkinter, no filedialog/messagebox here.
- These functions write to disk and raise exceptions on failure.

v2.5.6 compatibility:
- CSV bundle with per-file long tables + analysis_files sidecar
- XLSX with multiple sheets incl. statistics (ANOVA + Tukey)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .constants import (
    SHEET_ANALYSIS_FILES,
    SHEET_COMBINED_MG_PAIRS,
    SHEET_PER_FILE_COMBINED,
    SHEET_PER_FILE_MAIN,
    SHEET_SEPARATE_SPECIES,
    SHEET_STATISTICS,
)
from .stats import _p_to_stars, _sci_str


def _as_path(p: str | Path) -> Path:
    return p if isinstance(p, Path) else Path(p)


def _collect_analysis_files(per_file_raw: Optional[List[Tuple[Path, pd.DataFrame]]]) -> List[str]:
    if not per_file_raw:
        return []
    return sorted({p.name for p, _ in per_file_raw})


def _melt_per_file_matrix(m: pd.DataFrame) -> pd.DataFrame:
    """
    Convert per-file matrix (index=file, columns=species) to long format:
      file | species | relative_%
    """
    out = m.copy()
    out.index.name = "file"
    out = out.reset_index().melt(id_vars="file", var_name="species", value_name="relative_%")
    return out


# -----------------------------------------------------------------------------
# CSV exports
# -----------------------------------------------------------------------------
def export_csv_bundle(
    base_csv_path: str | Path,
    *,
    df_main: pd.DataFrame,
    per_file_matrix: Optional[pd.DataFrame] = None,
    df_combined: Optional[pd.DataFrame] = None,
    per_file_matrix_combined: Optional[pd.DataFrame] = None,
    per_file_raw: Optional[List[Tuple[Path, pd.DataFrame]]] = None,
) -> List[Path]:
    """
    Write a set of CSV files (v2.5.6 naming scheme).
    Returns list of written paths.
    """
    base = _as_path(base_csv_path)
    if base.suffix.lower() != ".csv":
        base = base.with_suffix(".csv")

    if df_main is None or df_main.empty:
        raise ValueError("df_main is empty; nothing to export.")

    saved: List[Path] = []

    # 1) main summary
    df_main.to_csv(base, index=False)
    saved.append(base)

    # 1b) main per-file
    if isinstance(per_file_matrix, pd.DataFrame) and not per_file_matrix.empty:
        perfile_csv = base.with_name(f"{base.stem}_perfile.csv")
        _melt_per_file_matrix(per_file_matrix).to_csv(perfile_csv, index=False)
        saved.append(perfile_csv)

    # 2) combined summary
    if isinstance(df_combined, pd.DataFrame) and not df_combined.empty:
        comb_csv = base.with_name(f"{base.stem}_combined.csv")
        df_combined.to_csv(comb_csv, index=False)
        saved.append(comb_csv)

        # 2b) combined per-file
        if isinstance(per_file_matrix_combined, pd.DataFrame) and not per_file_matrix_combined.empty:
            perfile_comb_csv = base.with_name(f"{base.stem}_combined_perfile.csv")
            _melt_per_file_matrix(per_file_matrix_combined).to_csv(perfile_comb_csv, index=False)
            saved.append(perfile_comb_csv)

    # 3) analysis_files sidecar
    files = _collect_analysis_files(per_file_raw)
    if files:
        files_csv = base.with_name(f"{base.stem}_files.csv")
        pd.DataFrame({"analysis_files": files}).to_csv(files_csv, index=False)
        saved.append(files_csv)

    return saved


# -----------------------------------------------------------------------------
# XLSX export
# -----------------------------------------------------------------------------
def export_xlsx(
    xlsx_path: str | Path,
    *,
    df_main: pd.DataFrame,
    df_combined: Optional[pd.DataFrame] = None,
    per_file_matrix: Optional[pd.DataFrame] = None,
    per_file_matrix_combined: Optional[pd.DataFrame] = None,
    per_file_raw: Optional[List[Tuple[Path, pd.DataFrame]]] = None,
    stats_pack: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Export an Excel workbook (v2.5.6 structure).

    stats_pack expected:
      {"anova": anova_dict, "tukey": tukey_df}
    """
    out = _as_path(xlsx_path)
    if out.suffix.lower() != ".xlsx":
        out = out.with_suffix(".xlsx")

    if df_main is None or df_main.empty:
        raise ValueError("df_main is empty; nothing to export.")

    with pd.ExcelWriter(out, engine="xlsxwriter") as xw:
        wb = xw.book
        num_fmt = wb.add_format({"num_format": "0.00"})

        # --- separate_species ---
        df_main.to_excel(xw, index=False, sheet_name=SHEET_SEPARATE_SPECIES)
        ws = xw.sheets[SHEET_SEPARATE_SPECIES]
        ws.autofilter(0, 0, len(df_main), max(0, len(df_main.columns) - 1))

        # --- combined_Mg_pairs ---
        if isinstance(df_combined, pd.DataFrame) and not df_combined.empty:
            df_combined.to_excel(xw, index=False, sheet_name=SHEET_COMBINED_MG_PAIRS)
            ws2 = xw.sheets[SHEET_COMBINED_MG_PAIRS]
            ws2.autofilter(0, 0, len(df_combined), max(0, len(df_combined.columns) - 1))

        # --- per_file_main ---
        if isinstance(per_file_matrix, pd.DataFrame) and not per_file_matrix.empty:
            m_long = _melt_per_file_matrix(per_file_matrix)
            m_long.to_excel(xw, index=False, sheet_name=SHEET_PER_FILE_MAIN)
            ws_pf = xw.sheets[SHEET_PER_FILE_MAIN]
            ws_pf.set_column(0, 0, 28)  # file
            ws_pf.set_column(1, 1, 36)  # species
            ws_pf.set_column(2, 2, 12, num_fmt)  # relative_%
            ws_pf.autofilter(0, 0, len(m_long), max(0, len(m_long.columns) - 1))

        # --- per_file_combined ---
        if isinstance(per_file_matrix_combined, pd.DataFrame) and not per_file_matrix_combined.empty:
            mc_long = _melt_per_file_matrix(per_file_matrix_combined)
            mc_long.to_excel(xw, index=False, sheet_name=SHEET_PER_FILE_COMBINED)
            ws_pfc = xw.sheets[SHEET_PER_FILE_COMBINED]
            ws_pfc.set_column(0, 0, 28)
            ws_pfc.set_column(1, 1, 36)
            ws_pfc.set_column(2, 2, 12, num_fmt)
            ws_pfc.autofilter(0, 0, len(mc_long), max(0, len(mc_long.columns) - 1))

        # --- analysis_files ---
        files = _collect_analysis_files(per_file_raw)
        if files:
            pd.DataFrame({"analysis_files": files}).to_excel(
                xw, index=False, sheet_name=SHEET_ANALYSIS_FILES
            )

        # --- statistics sheet ---
        if stats_pack and isinstance(stats_pack, dict) and ("anova" in stats_pack or "tukey" in stats_pack):
            anova = stats_pack.get("anova") or {}
            tukey_df = stats_pack.get("tukey")

            has_anova = isinstance(anova, dict) and bool(anova)
            has_tukey = isinstance(tukey_df, pd.DataFrame) and not tukey_df.empty

            if has_anova or has_tukey:
                start_row = 0

                # ANOVA block
                if has_anova:
                    anova_df = pd.DataFrame([anova], columns=["F", "df_between", "df_within", "p"])
                    anova_disp = anova_df.copy()
                    anova_disp["p"] = anova_disp["p"].map(lambda x: _sci_str(x, decimals=3))
                    # Add stars too (handy in exports)
                    anova_disp["stars"] = anova_df["p"].map(_p_to_stars)

                    anova_disp.to_excel(
                        xw, index=False, sheet_name=SHEET_STATISTICS, startrow=start_row
                    )
                    start_row += len(anova_disp) + 2

                # Tukey block
                if has_tukey:
                    tuk = tukey_df.copy()
                    # normalize name (support either p_adj or p-adj coming in)
                    if "p-adj" in tuk.columns and "p_adj" not in tuk.columns:
                        tuk = tuk.rename(columns={"p-adj": "p_adj"})

                    tuk["stars"] = tuk["p_adj"].map(_p_to_stars)
                    tuk_disp = tuk.copy()
                    tuk_disp["p_adj"] = tuk_disp["p_adj"].map(lambda x: _sci_str(x, decimals=3))

                    tuk_disp.to_excel(
                        xw, index=False, sheet_name=SHEET_STATISTICS, startrow=start_row
                    )

                    ws_stats = xw.sheets[SHEET_STATISTICS]
                    ws_stats.autofilter(
                        start_row, 0,
                        start_row + len(tuk_disp),
                        max(0, len(tuk_disp.columns) - 1),
                    )

    return out


__all__ = ["export_csv_bundle", "export_xlsx"]
