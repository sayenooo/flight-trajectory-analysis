# Data

This directory is used for local raw and processed trajectory data.

## Current raw data

The current dataset consists of **DLH713 trajectory exports for 2024, 2025, and 2026**:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

The files contain CSV-like flight records inside Excel workbooks. The exact original provider/source of the data should be confirmed by the team. The current preprocessing script only assumes the observed file structure, not a specific data provider.

## Route context

The working route context for the current dataset is:

```text
Seoul / Incheon area (ICN / RKSI) -> Frankfurt area (FRA / EDDF)
```

This label is inferred from the DLH713 callsign and trajectory coordinate ranges. The raw files do not include explicit departure-airport or arrival-airport columns.

## Recommended local structure

```text
data/
├── raw/          # optional: local raw trajectory files
├── interim/      # optional: intermediate working files
└── processed/    # generated preprocessing outputs
```

The current preprocessing script can read raw DLH713 Excel exports either from the project root or from a selected raw-data directory.

## Run preprocessing

From the project root:

```bash
python src/preprocess.py --raw-dir . --processed-dir data/processed
```

Generated files:

```text
data/processed/flight_points_clean.csv
data/processed/flight_points_scaled.csv
data/processed/flights_summary.csv
data/processed/preprocessing_report.json
```

The generated CSV files are designed for the next project stage: PCA, HDBSCAN clustering, anomaly detection, and visualization.
