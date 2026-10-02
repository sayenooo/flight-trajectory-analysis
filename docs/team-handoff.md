# Team Handoff: Preprocessing Outputs

This document explains what the preprocessing contribution produces and how teammates can continue the project.

## Scope of this contribution

This contribution focuses only on **data preprocessing**.

It does not perform:

- PCA;
- HDBSCAN;
- cluster interpretation;
- anomaly explanation;
- final visualization.

Those tasks belong to the next stages of the team project.

## How to reproduce preprocessing

From the project root:

```bash
pip install -r requirements.txt
python src/preprocess.py --raw-dir . --file-pattern "DLH713_*.xlsx" --processed-dir data/processed
```

If the raw files are moved into a different folder, for example `data/raw/`, run:

```bash
python src/preprocess.py --raw-dir data/raw --file-pattern "*.xlsx" --processed-dir data/processed
```

## Files produced

```text
data/processed/flight_points_clean.csv
data/processed/flight_points_scaled.csv
data/processed/flights_summary.csv
data/processed/preprocessing_report.json
```

## Which file should teammates use?

### For PCA / HDBSCAN

Use:

```text
flight_points_scaled.csv
```

This file contains the original point-level trajectory data plus standardized numeric columns:

```text
latitude_scaled
longitude_scaled
altitude_scaled
heading_scaled
time_from_start_sec_scaled
route_progress_scaled
```

### For map visualization

Use:

```text
flight_points_clean.csv
```

This file preserves the original latitude, longitude, altitude, heading, and timestamp values.

### For flight-level checks

Use:

```text
flights_summary.csv
```

This file has one row per reconstructed flight and includes point counts, duration, coordinate ranges, and altitude ranges.

### For reproducibility

Use:

```text
preprocessing_report.json
```

This file records the file pattern, input files, number of reconstructed flights, removed invalid points, removed duplicates, and final clean point count.

## Current verified result

Using the provided 2024-2026 DLH713 files:

```text
reconstructed_flights: 291
parsed_points_before_cleaning: 86381
invalid_points_removed: 18
duplicated_points_removed: 1
clean_points: 86362
clean_flights: 291
```

## Important assumptions

- The exact original source/provider of the raw files should be confirmed by the team.
- The current airport route label is project context only; the raw files do not include explicit airport columns.
- The preprocessing code depends on the observed raw structure: flight-level CSV-like records with a nested `track` field.
