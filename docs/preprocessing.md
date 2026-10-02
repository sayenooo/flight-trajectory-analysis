# Data Preprocessing Methodology

This document describes the preprocessing pipeline for the aircraft trajectory analysis project.

## Raw data format

The current raw files are Excel workbooks:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

Although the files are `.xlsx`, the content behaves like CSV text stored in a single Excel column. Long trajectory records may be split across multiple rows, so the preprocessing pipeline reconstructs split records before parsing.

The exact original data source should be confirmed by the project team. The preprocessing pipeline only assumes the observed file structure and does not depend on airport names.

## Flexible input pattern

The current default pattern is:

```bash
--file-pattern "DLH713_*.xlsx"
```

If the dataset or file locations change, the same script can be reused with another pattern:

```bash
python src/preprocess.py --raw-dir data/raw --file-pattern "*.xlsx" --processed-dir data/processed
```

## Pipeline

### 1. Load raw files

The script searches for Excel files using the selected `--file-pattern`.

### 2. Reconstruct flight records

Each complete flight record begins with an ICAO24 aircraft identifier such as `3c4a8c,`. Rows that do not begin with an ICAO24 value are treated as continuations of the previous flight record.

### 3. Parse flight-level fields

The reconstructed CSV records are parsed into:

```text
icao24
callsign
firstseen
lastseen
track
source_year
source_file
flight_id
```

### 4. Expand trajectory tracks

The `track` field contains a list of trajectory points with:

```text
time
latitude
longitude
altitude
heading
onground
```

Each track point becomes one row in the point-level dataset.

### 5. Clean invalid data

The script removes points with:

- missing required values;
- latitude outside `[-90, 90]`;
- longitude outside `[-180, 180]`;
- heading outside `[0, 360]`;
- non-positive timestamps;
- point timestamps outside the corresponding flight interval, with a one-hour tolerance;
- duplicate point records.

Negative altitude values are not automatically removed. Barometric altitude and airport/reference effects can produce small negative values, so the pipeline preserves them and adds this flag:

```text
altitude_below_zero
```

### 6. Create derived preprocessing features

The clean dataset includes:

```text
sequence_index
point_count
first_point_time_unix
last_point_time_unix
time_from_start_sec
trajectory_duration_sec
route_progress
point_time_utc
firstseen_utc
lastseen_utc
altitude_below_zero
```

These features support consistent trajectory comparison and downstream analysis.

### 7. Standardize numeric features

The script applies `StandardScaler` to selected numeric features:

```text
latitude
longitude
altitude
heading
time_from_start_sec
route_progress
```

The original values are preserved, and standardized versions are added with `_scaled` suffixes.

## Outputs

The script creates four files:

```text
flight_points_clean.csv
flight_points_scaled.csv
flights_summary.csv
preprocessing_report.json
```

## Verified result on current data

Using the 2024-2026 DLH713 files, the preprocessing pipeline produced:

```text
reconstructed_flights: 291
parsed_points_before_cleaning: 86381
invalid_points_removed: 18
duplicated_points_removed: 1
clean_points: 86362
clean_flights: 291
```

## Assumptions and limitations

- The exact original provider/source of the raw files should be confirmed by the project team.
- The route label is project context only; the raw files do not contain explicit departure/arrival airport columns.
- The script assumes an OpenSky-style nested `track` field with point objects containing time, latitude, longitude, altitude, heading, and onground values.

## Output usage

- `flight_points_clean.csv`: map visualization, trajectory inspection, and feature engineering.
- `flight_points_scaled.csv`: feature-based modeling, dimensionality reduction, and clustering.
- `flights_summary.csv`: flight-level quality checks.
- `preprocessing_report.json`: preprocessing statistics and reproducibility information.
