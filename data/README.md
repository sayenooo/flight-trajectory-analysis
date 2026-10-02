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

The current raw files are stored in the project root, but the script also works if raw files are moved into `data/raw/`.

## Run preprocessing

From the project root with the current files:

```bash
python src/preprocess.py --raw-dir . --file-pattern "DLH713_*.xlsx" --processed-dir data/processed
```

If the team moves the files into `data/raw/` or changes the dataset, use a different pattern:

```bash
python src/preprocess.py --raw-dir data/raw --file-pattern "*.xlsx" --processed-dir data/processed
```

Generated files:

```text
data/processed/flight_points_clean.csv
data/processed/flight_points_scaled.csv
data/processed/flights_summary.csv
data/processed/preprocessing_report.json
```

The generated CSV files are designed for the next project stage: PCA, HDBSCAN clustering, anomaly detection, and visualization.

## Notes for teammates

- `flight_points_clean.csv` keeps original latitude, longitude, altitude, heading, and time values.
- `flight_points_scaled.csv` adds standardized numeric columns for PCA/HDBSCAN.
- `flights_summary.csv` provides one row per reconstructed flight for quick quality checks.
- `preprocessing_report.json` records the input pattern and the number of parsed/removed/saved points.
