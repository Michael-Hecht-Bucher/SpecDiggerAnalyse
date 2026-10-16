# specdiggeranalyse/mass_tables.py
# -*- coding: utf-8 -*-

"""
Mass tables and mass-related helpers.

Contains:
- MASS_RAW: raw masses (EU decimal commas) as strings
- MASS: parsed float masses

v2.5.6 additions:
- Modification masses (AMP = +329 Da) for species-table wizard auto-AMPylation.

Guiding rule:
- Dependency-light, data-centric.
- Do NOT import tkinter/matplotlib/pandas/scipy/statsmodels here.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional
import colorsys


# -----------------------------------------------------------------------------
# Raw masses as provided (EU decimal comma)
# -----------------------------------------------------------------------------
MASS_RAW: Dict[str, str] = {
    # ions
    "Mg2+": "22",

    # nucleotides
    "CTP": "483,16",
    "GDP": "443,2",
    "GDP-mannose": "605,34",
    "IDP": "428,19",
    "CDP": "403,18",
    "CDP-choline": "488,32",
    "GTP": "523,18",
    "TTP": "482,17", 
    "ITP": "508,165",
    "UDP": "404,17",
    "UDP-GlcNac": "607,32",
    "CDP-Ethanolamine": "446,24",
    "ATP": "507,18",
    "UDP-Glucose": "566,3",
    "S-Adenosylmethionin": "398,44",
    "ADP": "427,201",
    "NAD+": "663,43",
    "UDP-rhamnose": "550,3",
    "ADP-Ribose": "559,32",
    "IMP": "348,206",
    "Acetyl-CoA": "809,57",
    "UMP": "324,18",
    "UDP-Galactose": "566,302",
    "UDP-Glucuronic acid": "580,286",
    "UDP-GalNac": "607,3537",
    "UDP-Xylose": "536,2758",
    "UTP": "484,1411",
    "GDP-Glucose": "605,341",
    "GDP-L-Fucose": "587,334",
    "TDP": "402,19",
    "NADP+": "744,413",

    # Sugars
    "Glucose": "180,156",
    "Mannose": "180,156",
    "Rhamnose": "164,16",
    "Galactose": "180,156",
    "N-Acetylglucosamine": "221,208",
    "Fucose": "164,1565",
    "Xylose": "150,13",
    "Glucuronic acid": "194,139",
    "N-Acetylgalactosamine": "221,208",

    # Nucleobases 
    "Adenine": "135,13",
    "Cytosine": "111,1",
    "Guanine": "151,13",
    "Thymine": "126,1133",

    # proteins
    "AnkX": "90580,37",
    "CbFic2": "43904,71",
    "SoFic": "42418,81",
    "AvrB": "36202,35",
    "Lem23": "42250",
    "LtpG": "60070",
    "FicD": "40928,98",
    "IbpA": "35724,35",
    "A0A009IKX3": "28078,07",
    "A0A0E1NTC6": "42767,61",
    "A0A0H2UUX8": "42560,93",
    "A0A0H2ZLR2": "41908,37",
    "A0A0H3AJ32": "37844,64",
    "A0A0H3GUD1": "13747,12",
    "A0A0H3GW26": "33494,8",
    "A0A0H3PPH4": "22692,91",
    "A0A0M1VWH9": "26977,12",
    "A0A0R4I962": "25553,23",
    "A0A0R4J7V3": "61117,76",
    "A0A0T7CRE9": "39230,83",
    "A0A344R6F3": "49159,72",
    "A0A379XXM2": "38778,72",
    "A0A3R1B2D9": "41034,59",
    "A0A3U8YZK6": "43122,08",
    "A0A6C7IHM4": "13782,12",
    "A0A6F8V498": "38397,23",
    "A0A711K2M7": "43221,88",
    "A0A829PL26": "47129,72",
    "A0A9R0BMY0": "29606,11",
    "A5VY84": "44712,31",
    "A9KH34": "18150,19",
    "B1JDT3": "50032,64",
    "B7LQL1": "28587,88",
    "C6M795": "25444,04",
    "C7M9C2": "28929,88",
    "C8PNB9": "35474,96",
    "C8PRL4": "34202,98",
    "D0CEY5": "38094,02",
    "E3HN30": "43347,8",
    "G6AJG5": "38305,6",
    "I6YCN3": "24174,91",
    "M2VR62": "44189,52",
    "Q5F532": "26120,85",
    "Q83D01": "37294,07",
    "Q892Z9": "14241,32",
    "Q8DWU4": "43275,46",
    "Q9CK64": "43782,92",
    "Q9ZLC9": "27647,93",
    "U1GBP4": "42490,75",
    "U2R437": "25136,95",
    "W2CTY3": "22361,74",
}

# -----------------------------------------------------------------------------
# Curated name lists (used in species-table wizard)
# -----------------------------------------------------------------------------
ION_NAMES = ["Mg2+"]

NUCLEOTIDE_NAMES = [
    "CTP", "GDP", "GDP-mannose", "IDP", "CDP", "CDP-choline", "GTP", "TTP", "ITP", "UDP",
    "UDP-GlcNac", "CDP-Ethanolamine", "ATP", "UDP-Glucose",
    "S-Adenosylmethionin", "ADP", "NAD+", "UDP-rhamnose", "ADP-Ribose",
    "IMP", "Acetyl-CoA", "UMP", "UDP-Galactose", "UDP-Glucuronic acid",
    "UDP-GalNac", "UDP-Xylose", "UTP", "GDP-Glucose", "GDP-L-Fucose",
    "TDP", "NADP+",
]

SUGAR_NAMES = [
    "Glucose", "Mannose", "Rhamnose", "Galactose", "N-Acetylglucosamine",
    "Fucose", "Xylose", "Glucuronic acid", "N-Acetylgalactosamine",
]

NUCLEOBASE_NAMES = ["Adenine", "Cytosine", "Guanine", "Thymine"]

PROTEIN_NAMES = [
    "AnkX", "CbFic2", "SoFic", "AvrB", "Lem23", "LtpG", "FicD", "IbpA",
    "A0A009IKX3", "A0A0E1NTC6", "A0A0H2UUX8", "A0A0H2ZLR2",
    "A0A0H3AJ32", "A0A0H3GUD1", "A0A0H3GW26", "A0A0H3PPH4",
    "A0A0M1VWH9", "A0A0R4I962", "A0A0R4J7V3", "A0A0T7CRE9",
    "A0A344R6F3", "A0A379XXM2", "A0A3R1B2D9", "A0A3U8YZK6",
    "A0A6C7IHM4", "A0A6F8V498", "A0A711K2M7", "A0A829PL26",
    "A0A9R0BMY0", "A5VY84", "A9KH34", "B1JDT3", "B7LQL1",
    "C6M795", "C7M9C2", "C8PNB9", "C8PRL4", "D0CEY5", "E3HN30",
    "G6AJG5", "I6YCN3", "M2VR62", "Q5F532", "Q83D01", "Q892Z9",
    "Q8DWU4", "Q9CK64", "Q9ZLC9", "U1GBP4", "U2R437", "W2CTY3",
]

# -----------------------------------------------------------------------------
# v2.5.6: modification masses (auto-AMPylation)
# -----------------------------------------------------------------------------
# AMPylation mass shift as used in your v2.5.6 monolith: +329 Da
MODIFICATION_RAW: Dict[str, str] = {"AMP": "329"}
MODIFICATION_NAMES = ["AMP"]

# -----------------------------------------------------------------------------
# Default settings for species-table wizard rows
# -----------------------------------------------------------------------------

DEFAULT_SPECIES_MARKER = "v"

# -----------------------------------------------------------------------------
# Parsing & derived float maps
# -----------------------------------------------------------------------------
def parse_eu_mass(x: str) -> float:
    """
    Parse a mass string that may use EU comma decimals into float.
    """
    return float(str(x).strip().replace(",", "."))


# Full float mass lookup (core items)
MASS: Dict[str, float] = {k: parse_eu_mass(v) for k, v in MASS_RAW.items()}

# Modifications float lookup
MODIFICATION_MASS: Dict[str, float] = {k: parse_eu_mass(v) for k, v in MODIFICATION_RAW.items()}

# Category-specific float maps
PROTEIN_MASS: Dict[str, float] = {k: MASS[k] for k in PROTEIN_NAMES if k in MASS}
NUCLEOTIDE_MASS: Dict[str, float] = {k: MASS[k] for k in NUCLEOTIDE_NAMES if k in MASS}
ION_MASS: Dict[str, float] = {k: MASS[k] for k in ION_NAMES if k in MASS}
SUGAR_MASS: Dict[str, float] = {k: MASS[k] for k in SUGAR_NAMES if k in MASS}
NUCLEOBASE_MASS: Dict[str, float] = {k: MASS[k] for k in NUCLEOBASE_NAMES if k in MASS}

# Generate a registry for the categories that the species-table wizard can generate from
LIGAND_CATEGORIES: dict[str, Dict[str, float]] = {
    "Nucleotides": NUCLEOTIDE_MASS,
    "Sugars": SUGAR_MASS,
    "Nucleobases": NUCLEOBASE_MASS,
}

LIGAND_CATEGORY_ORDER: list[str] = [
    "Nucleotides",
    "Sugars",
    "Nucleobases",
]

# -----------------------------------------------------------------------------
# Convenience helpers
# -----------------------------------------------------------------------------
def get_mass(name: str, default: Optional[float] = None) -> Optional[float]:
    """Return base mass for a given key, or default if unknown."""
    return MASS.get(name, default)


def get_mod_mass(name: str, default: Optional[float] = None) -> Optional[float]:
    """Return modification mass (e.g., AMP), or default if unknown."""
    return MODIFICATION_MASS.get(name, default)


def is_known_mass(name: str) -> bool:
    return name in MASS


def filter_known(names: Iterable[str]) -> list[str]:
    """Return only those names that exist in MASS."""
    return [n for n in names if n in MASS]

def _hsv_to_hex(h: float, s: float, v: float) -> str:
    """
    Convert HSV values in [0, 1] to a hex color string.
    """
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(
        int(round(r * 255)),
        int(round(g * 255)),
        int(round(b * 255)),
    )

def generate_distinct_colors(
    n: int,
    *,
    saturation: float = 0.65,
    value: float = 0.95,
) -> list[str]:
    """
    Generate n visually distinct colors as hex strings.

    Uses evenly spaced hues around the HSV wheel.
    Suitable for species-table default row coloring, including larger
    tables with dozens of entries.
    """
    if n <= 0:
        return []

    return [
        _hsv_to_hex(i / n, saturation, value)
        for i in range(n)
    ]

# --------------------------------------------------------------------------
# Internal helper functions for species-table row generation
# --------------------------------------------------------------------------
def _normalize_name_list(names: Optional[Iterable[str]]) -> list[str]:
    """
    Normalize an optional iterable of names:
    - convert to stripped strings
    - drop empty values
    - preserve input order
    - deduplicate
    """
    if not names:
        return []

    out: list[str] = []
    seen: set[str] = set()

    for x in names:
        s = str(x).strip()
        if s and s not in seen:
            out.append(s)
            seen.add(s)

    return out


def _species_label(
    *,
    protein: str,
    is_dimer: bool = False,
    ligand: Optional[str] = None,
    ligand_count: int = 0,
    mg_count: int = 0,
    protein_is_ampylated: bool = False,
) -> str:
    """
    Build canonical species labels matching the monolith logic, generalized
    from nucleotides to arbitrary ligand categories (e.g. nucleotide, sugar,
    nucleobase).

    Examples:
      AnkX
      AnkX-AMP
      AnkX + Mg
      AnkX + ATP
      AnkX + Ribose
      AnkX + Adenine
      AnkX + ATP + Mg
      AnkX_dimer
      AnkX_dimer + 2Mg
      AnkX_dimer + 2ATP
      AnkX_dimer + 2Ribose + Mg
    """
    base = f"{protein}_dimer" if is_dimer else protein
    if protein_is_ampylated:
        base = f"{base}-AMP"

    parts: list[str] = [base]

    if ligand and ligand_count > 0:
        lig_txt = ligand if ligand_count == 1 else f"{ligand_count}{ligand}"
        parts.append(f"+ {lig_txt}")

    if mg_count > 0:
        mg_txt = "Mg" if mg_count == 1 else f"{mg_count}Mg"
        parts.append(f"+ {mg_txt}")

    return " ".join(parts).strip()

# --------------------------------------------------------------------------
# Species-table wizard helpers
# --------------------------------------------------------------------------
def compute_species_mass(
    *,
    protein: Optional[str] = None,
    ligand_category: Optional[str] = None,
    ligand: Optional[str] = None,
    ligand_count: int = 0,
    mg_count: int = 0,
    is_dimer: bool = False,
    protein_is_ampylated: bool = False,
) -> float:
    """
    Compute total mass for a species row.

    Generalized logic:
      total =
          protein_mass * (2 if dimer else 1)
        + ligand_mass * ligand_count
        + Mg_mass * mg_count
        + AMP_shift (if protein_is_ampylated)

    Supported ligand categories:
      - Nucleotides
      - Sugars
      - Nucleobases

    Notes:
    - protein must be given for all supported rows
    - no ligand-only species are generated here
    """
    if not protein:
        raise ValueError("protein must be provided.")

    if protein not in PROTEIN_MASS:
        raise KeyError(f"Unknown protein mass: {protein}")

    if ligand_count < 0:
        raise ValueError("ligand_count must be >= 0.")
    if mg_count < 0:
        raise ValueError("mg_count must be >= 0.")

    total = PROTEIN_MASS[protein] * (2.0 if is_dimer else 1.0)

    if ligand_count:
        if not ligand:
            raise ValueError("ligand must be provided when ligand_count > 0.")
        if not ligand_category:
            raise ValueError("ligand_category must be provided when ligand_count > 0.")
        if ligand_category not in LIGAND_CATEGORIES:
            raise KeyError(f"Unsupported ligand category: {ligand_category}")

        ligand_mass_map = LIGAND_CATEGORIES[ligand_category]
        if ligand not in ligand_mass_map:
            raise KeyError(f"Unknown ligand mass in {ligand_category}: {ligand}")

        total += ligand_mass_map[ligand] * float(ligand_count)

    if mg_count:
        if "Mg2+" not in ION_MASS:
            raise KeyError("Required ion mass 'Mg2+' not found in ION_MASS.")
        total += ION_MASS["Mg2+"] * float(mg_count)

    if protein_is_ampylated:
        if "AMP" not in MODIFICATION_MASS:
            raise KeyError("Required modification mass 'AMP' not found in MODIFICATION_MASS.")
        total += MODIFICATION_MASS["AMP"]

    return total


def build_species_rows(
    *,
    protein: str,
    ligands_by_category: Optional[Mapping[str, Iterable[str]]] = None,
    include_mg: bool = False,
    include_dimer: bool = False,
    dimer_only: bool = False,
    protein_auto_ampylation: bool = False,
    sort_rows: bool = True,
) -> list[dict[str, Any]]:
    """
    Generate structural species rows for the species-table wizard.

    Generalized from nucleotide-only species to arbitrary ligand categories.

    Supported ligand categories:
      - Nucleotides
      - Sugars
      - Nucleobases

    Monomer rows:
      protein
      protein + Mg                        (if include_mg)
      protein + ligand
      protein + ligand + Mg              (if include_mg)

    Dimer rows:
      protein_dimer                      (if include_dimer or dimer_only)
      protein_dimer + Mg                 (if include_mg)
      protein_dimer + 2Mg                (if include_mg)
      protein_dimer + ligand
      protein_dimer + 2ligand
      protein_dimer + ligand + Mg        (if include_mg)
      protein_dimer + ligand + 2Mg       (if include_mg)
      protein_dimer + 2ligand + Mg       (if include_mg)
      protein_dimer + 2ligand + 2Mg      (if include_mg)

    If protein_auto_ampylation=True, all generated rows are duplicated with
    protein_is_ampylated=True and +AMP mass shift.
    """
    prot = str(protein).strip()

    if not prot:
        return []
    if prot not in PROTEIN_MASS:
        return []

    if dimer_only:
        include_dimer = True

    normalized_ligands_by_category: dict[str, list[str]] = {}
    for category, names in (ligands_by_category or {}).items():
        if category not in LIGAND_CATEGORIES:
            continue

        mass_map = LIGAND_CATEGORIES[category]
        normalized = [
            name for name in _normalize_name_list(names)
            if name in mass_map
        ]
        if normalized:
            normalized_ligands_by_category[category] = normalized

    rows: list[dict[str, Any]] = []

    def append_row(
        *,
        is_dimer: bool,
        ligand_category: Optional[str],
        ligand: Optional[str],
        ligand_count: int,
        mg_count: int,
        protein_is_ampylated: bool,
    ) -> None:
        label = _species_label(
            protein=prot,
            is_dimer=is_dimer,
            ligand=ligand,
            ligand_count=ligand_count,
            mg_count=mg_count,
            protein_is_ampylated=protein_is_ampylated,
        )

        mass = compute_species_mass(
            protein=prot,
            ligand_category=ligand_category,
            ligand=ligand,
            ligand_count=ligand_count,
            mg_count=mg_count,
            is_dimer=is_dimer,
            protein_is_ampylated=protein_is_ampylated,
        )

        rows.append(
            {
                # species-table compatible fields
                "species": label,
                "M (th)": mass,
                "sequence": "",
                "color": "",
                "marker": DEFAULT_SPECIES_MARKER,

                # generalized structural/meta fields
                "expected_mass": mass,
                "protein": prot,
                "is_dimer": bool(is_dimer),
                "ligand_category": ligand_category or "",
                "ligand": ligand or "",
                "ligand_count": int(ligand_count),
                "mg_count": int(mg_count),
                "protein_is_ampylated": bool(protein_is_ampylated),

                # backward-compatible aliases for existing downstream code
                "nucleotide": (ligand or "") if ligand_category == "Nucleotides" else "",
                "nucleotide_count": int(ligand_count) if ligand_category == "Nucleotides" else 0,
            }
        )

    def append_base_and_optional_amp(
        *,
        is_dimer: bool,
        ligand_category: Optional[str],
        ligand: Optional[str],
        ligand_count: int,
        mg_count: int,
    ) -> None:
        append_row(
            is_dimer=is_dimer,
            ligand_category=ligand_category,
            ligand=ligand,
            ligand_count=ligand_count,
            mg_count=mg_count,
            protein_is_ampylated=False,
        )
        if protein_auto_ampylation:
            append_row(
                is_dimer=is_dimer,
                ligand_category=ligand_category,
                ligand=ligand,
                ligand_count=ligand_count,
                mg_count=mg_count,
                protein_is_ampylated=True,
            )

    ############################################
    #  Monomer block
    ############################################
    if not dimer_only:
        append_base_and_optional_amp(
            is_dimer=False,
            ligand_category=None,
            ligand=None,
            ligand_count=0,
            mg_count=0,
        )

        if include_mg:
            append_base_and_optional_amp(
                is_dimer=False,
                ligand_category=None,
                ligand=None,
                ligand_count=0,
                mg_count=1,
            )

        for category in LIGAND_CATEGORY_ORDER:
            for lig in normalized_ligands_by_category.get(category, []):
                append_base_and_optional_amp(
                    is_dimer=False,
                    ligand_category=category,
                    ligand=lig,
                    ligand_count=1,
                    mg_count=0,
                )

                if include_mg:
                    append_base_and_optional_amp(
                        is_dimer=False,
                        ligand_category=category,
                        ligand=lig,
                        ligand_count=1,
                        mg_count=1,
                    )

    #################################################
    #  Dimer block
    #################################################
    if include_dimer:
        append_base_and_optional_amp(
            is_dimer=True,
            ligand_category=None,
            ligand=None,
            ligand_count=0,
            mg_count=0,
        )

        if include_mg:
            append_base_and_optional_amp(
                is_dimer=True,
                ligand_category=None,
                ligand=None,
                ligand_count=0,
                mg_count=1,
            )
            append_base_and_optional_amp(
                is_dimer=True,
                ligand_category=None,
                ligand=None,
                ligand_count=0,
                mg_count=2,
            )

        for category in LIGAND_CATEGORY_ORDER:
            for lig in normalized_ligands_by_category.get(category, []):
                append_base_and_optional_amp(
                    is_dimer=True,
                    ligand_category=category,
                    ligand=lig,
                    ligand_count=1,
                    mg_count=0,
                )
                append_base_and_optional_amp(
                    is_dimer=True,
                    ligand_category=category,
                    ligand=lig,
                    ligand_count=2,
                    mg_count=0,
                )

                if include_mg:
                    append_base_and_optional_amp(
                        is_dimer=True,
                        ligand_category=category,
                        ligand=lig,
                        ligand_count=1,
                        mg_count=1,
                    )
                    append_base_and_optional_amp(
                        is_dimer=True,
                        ligand_category=category,
                        ligand=lig,
                        ligand_count=1,
                        mg_count=2,
                    )
                    append_base_and_optional_amp(
                        is_dimer=True,
                        ligand_category=category,
                        ligand=lig,
                        ligand_count=2,
                        mg_count=1,
                    )
                    append_base_and_optional_amp(
                        is_dimer=True,
                        ligand_category=category,
                        ligand=lig,
                        ligand_count=2,
                        mg_count=2,
                    )

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup.setdefault(str(row["species"]), row)

    out = list(dedup.values())

    if sort_rows:
        out.sort(
            key=lambda r: (
                str(r["protein"]).lower(),
                int(bool(r["is_dimer"])),
                int(bool(r["protein_is_ampylated"])),
                str(r.get("ligand_category", "")).lower(),
                str(r.get("ligand", "")).lower(),
                int(r.get("ligand_count", 0)),
                int(r["mg_count"]),
                str(r["species"]).lower(),
            )
        )

    palette = generate_distinct_colors(len(out))
    for row, color in zip(out, palette):
        row["color"] = color
        row["marker"] = DEFAULT_SPECIES_MARKER

    return out

__all__ = [
    "MASS_RAW",
    "MASS",
    "PROTEIN_NAMES",
    "NUCLEOTIDE_NAMES",
    "SUGAR_NAMES",
    "NUCLEOBASE_NAMES",
    "ION_NAMES",
    "LIGAND_CATEGORIES",
    "LIGAND_CATEGORY_ORDER",
    "PROTEIN_MASS",
    "NUCLEOTIDE_MASS",
    "SUGAR_MASS",
    "NUCLEOBASE_MASS",
    "ION_MASS",
    "MODIFICATION_NAMES",
    "MODIFICATION_MASS",
    "parse_eu_mass",
    "get_mass",
    "get_mod_mass",
    "compute_species_mass",
    "is_known_mass",
    "filter_known",
    "build_species_rows",
]
