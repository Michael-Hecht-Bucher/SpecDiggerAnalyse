from mass_tables import build_species_rows

rows = build_species_rows(
    protein="AvrB",
    nucleotides=["UDP", "UDP-rhamnose"],
    include_mg=True,
    include_dimer=False,
    dimer_only=False,
    protein_auto_ampylation=False,
    sort_rows=True,
)

for row in rows:
    print(row["species"], row["M (th)"], row["sequence"], row["color"], row["marker"])