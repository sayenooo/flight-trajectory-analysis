# Data

This directory is used for local raw and processed trajectory data.

Recommended structure:

```text
data/
├── raw/          # optional: local raw OpenSky files
├── interim/      # optional: intermediate working files
└── processed/    # generated preprocessing outputs
```

The current preprocessing script can read raw DLH713 Excel exports either from the project root or from a selected raw-data directory.

Example raw files:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

Run preprocessing from the project root:

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
