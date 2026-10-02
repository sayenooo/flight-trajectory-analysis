# Flight Trajectory Analysis

Academic project for preprocessing, analyzing, and clustering real-world aircraft trajectory data.

## Dataset

The current working dataset uses DLH713 trajectory exports for 2024, 2025, and 2026:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

The exact original provider/source of the files should be confirmed by the project team. The files have an OpenSky-style structure and contain CSV-like flight records stored inside Excel workbooks.

Each raw record contains the following main fields:

```text
icao24, callsign, firstseen, lastseen, track
```

The `track` field contains point-level trajectory observations:

```text
time, latitude, longitude, altitude, heading, onground
```

Long trajectory records may be split across several Excel rows. The preprocessing pipeline reconstructs complete flight records before expanding each `track` list into point-level trajectory data.

## Route / airport context

The current dataset is based on the callsign DLH713. Based on the callsign and observed trajectory coordinates, the working route context is:

```text
Seoul / Incheon area (ICN / RKSI) -> Frankfurt area (FRA / EDDF)
```

The raw files do not contain explicit departure-airport or arrival-airport columns. Airport labels are used only as project context; the preprocessing pipeline does not depend on airport names.

## Project objective

The project prepares aircraft trajectory data for downstream trajectory analysis, dimensionality reduction, clustering, anomaly detection, and visualization.

The current repository includes a reproducible preprocessing pipeline that converts the raw trajectory exports into clean and standardized datasets.

## Preprocessing workflow

The preprocessing script performs the following steps:

1. Load raw Excel trajectory files using a configurable file pattern.
2. Reconstruct complete CSV flight records from split Excel fragments.
3. Parse flight-level columns: `icao24`, `callsign`, `firstseen`, `lastseen`, and `track`.
4. Expand the nested `track` field into point-level trajectory rows.
5. Convert numeric and timestamp fields into correct types.
6. Remove duplicate trajectory points.
7. Remove invalid records with impossible coordinates, headings, timestamps, or points outside the flight time interval.
8. Sort each trajectory chronologically.
9. Create preprocessing features such as:
   - `sequence_index`
   - `point_count`
   - `time_from_start_sec`
   - `trajectory_duration_sec`
   - `route_progress`
   - `altitude_below_zero`
10. Create standardized numeric columns for downstream feature-based analysis.

## Repository structure

```text
flight-trajectory-analysis/
├── data/
│   ├── README.md
│   └── processed/              # generated locally after running preprocessing
├── docs/
│   ├── opensky-data-request.md
│   ├── preprocessing.md
│   └── output-guide.md
├── notebooks/
│   ├── README.md
│   └── 01_dlh713_trajectory_preprocessing.ipynb
├── src/
│   └── preprocess.py
├── DLH713_2024.csv.xlsx
├── DLH713_2025.csv.xlsx
├── DLH713_2026.csv.xlsx
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run preprocessing

From the project root, run:

```bash
python src/preprocess.py --raw-dir . --file-pattern "DLH713_*.xlsx" --processed-dir data/processed
```

The `--file-pattern` argument makes the script reusable if the route, callsign, or raw-file names change later.

Example with raw files stored in `data/raw/`:

```bash
python src/preprocess.py --raw-dir data/raw --file-pattern "*.xlsx" --processed-dir data/processed
```

## Generated outputs

After preprocessing, the following files are created locally:

```text
data/processed/flight_points_clean.csv
data/processed/flight_points_scaled.csv
data/processed/flights_summary.csv
data/processed/preprocessing_report.json
```

### `flight_points_clean.csv`

Clean point-level trajectory dataset. One row represents one recorded point of one flight.

### `flight_points_scaled.csv`

Point-level trajectory dataset with additional standardized columns:

```text
latitude_scaled
longitude_scaled
altitude_scaled
heading_scaled
time_from_start_sec_scaled
route_progress_scaled
```

### `flights_summary.csv`

Flight-level summary table with point counts, duration, coordinate ranges, and altitude ranges.

### `preprocessing_report.json`

Reproducibility report showing the filename pattern, input files, number of reconstructed flights, removed invalid points, removed duplicates, and final clean point count.

## Current preprocessing result

Using the provided 2024-2026 DLH713 files, the pipeline produced:

```text
reconstructed_flights: 291
parsed_points_before_cleaning: 86381
invalid_points_removed: 18
duplicated_points_removed: 1
clean_points: 86362
clean_flights: 291
```

## Suggested project pipeline

```text
Raw trajectory exports
        |
        v
Data preprocessing
        |
        v
Feature engineering / dimensionality reduction
        |
        v
Trajectory clustering
        |
        v
Cluster and anomaly analysis
        |
        v
Visualization and interpretation
```

## Assumptions and limitations

- The exact original data provider/source should be confirmed by the project team.
- Airport labels are used only as project context because the raw files do not include explicit airport columns.
- The preprocessing pipeline relies on the observed raw-file structure: flight-level CSV-like records with a nested `track` field.
- Generated processed datasets can be reproduced locally by running the preprocessing script.

## Data policy

Code and documentation can be committed to GitHub. Large, restricted, credential-bearing, or access-controlled datasets should be handled carefully. Generated processed datasets can be reproduced locally from the raw files.
