# Data Preprocessing Methodology

This document explains the preprocessing contribution for the flight trajectory clustering project.

## Role in the team project

The full academic project analyzes real-world aircraft trajectories and applies clustering methods such as HDBSCAN. This part focuses only on **data preprocessing**. PCA, HDBSCAN, cluster interpretation, and anomaly analysis are separate downstream tasks.

## Raw data format

The current raw files are Excel workbooks:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

Although the files are `.xlsx`, the content behaves like CSV text stored in a single Excel column. Because long trajectory records may exceed Excel cell limits, one flight record can be split across multiple rows. The preprocessing script reconstructs these split rows before parsing.

## Pipeline

### 1. Load raw files

The script searches for `DLH713_*.xlsx` files in the selected raw directory.

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

### 4. Expand the trajectory track

The `track` field contains a list of points with:

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

The script does **not** aggressively remove negative altitude values, because barometric altitude and airport/reference effects can produce small negative values. Instead, it adds a flag:

```text
altitude_below_zero
```

This preserves data while making potential altitude artifacts visible for later analysis.

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

These features help the next teammates compare trajectories consistently.

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

Using the 2024–2026 DLH713 files, the preprocessing pipeline produced:

```text
reconstructed_flights: 291
parsed_points_before_cleaning: 86381
invalid_points_removed: 18
duplicated_points_removed: 1
clean_points: 86362
clean_flights: 291
```

## Next team steps

The next teammates can use `flight_points_scaled.csv` for:

- PCA;
- trajectory feature extraction;
- HDBSCAN clustering;
- anomaly detection;
- trajectory visualization.
