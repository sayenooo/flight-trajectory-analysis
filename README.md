# Flight Trajectory Analysis with OpenSky

Academic project for analyzing and clustering real-world aircraft trajectories using data from the OpenSky Network.

## Current dataset

The current working dataset contains **DLH713 trajectory exports for 2024, 2025, and 2026**:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

Each workbook stores CSV-like OpenSky flight records in one Excel column. Long trajectory records may be split across several Excel rows. The preprocessing code therefore reconstructs complete flight records first, then expands every `track` list into point-level trajectory data.

## Objective

The full team project is to analyze real-world aircraft trajectories and prepare them for clustering with **HDBSCAN**.

This repository currently focuses on the **data preprocessing stage**, which prepares clean and standardized trajectory data for teammates who will continue with PCA, HDBSCAN, visualization, and anomaly analysis.

## Preprocessing scope

The preprocessing script performs:

1. Load raw `DLH713_*.xlsx` files.
2. Reconstruct complete CSV flight records from split Excel fragments.
3. Parse flight-level columns: `icao24`, `callsign`, `firstseen`, `lastseen`, and `track`.
4. Expand the nested `track` field into point-level trajectory rows.
5. Convert numeric and timestamp fields into correct types.
6. Remove duplicate trajectory points.
7. Remove invalid records with impossible coordinates, headings, timestamps, or points outside the flight time interval.
8. Sort each trajectory chronologically.
9. Create useful preprocessing features such as:
   - `sequence_index`
   - `point_count`
   - `time_from_start_sec`
   - `trajectory_duration_sec`
   - `route_progress`
   - `altitude_below_zero`
10. Create standardized numeric columns for the next PCA/HDBSCAN stage.

This script **does not run PCA or HDBSCAN**. Those steps are left for the next teammates in the workflow.

## Repository structure

```text
flight-trajectory-analysis/
├── data/
│   ├── README.md
│   └── processed/              # generated locally after running preprocessing
├── docs/
│   ├── opensky-data-request.md
│   └── preprocessing.md
├── notebooks/
│   └── README.md
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

## How to run preprocessing

From the project root:

```bash
python src/preprocess.py --raw-dir . --processed-dir data/processed
```

The script searches for files matching:

```text
DLH713_*.xlsx
```

## Generated outputs

After running preprocessing, the following files are created locally:

```text
data/processed/flight_points_clean.csv
data/processed/flight_points_scaled.csv
data/processed/flights_summary.csv
data/processed/preprocessing_report.json
```

### `flight_points_clean.csv`

Clean point-level trajectory dataset. One row represents one recorded point of one flight.

### `flight_points_scaled.csv`

Same as the clean point-level dataset, with additional standardized columns:

```text
latitude_scaled
longitude_scaled
altitude_scaled
heading_scaled
time_from_start_sec_scaled
route_progress_scaled
```

These columns are ready for PCA or HDBSCAN experiments.

### `flights_summary.csv`

One row per reconstructed flight. Useful for checking point counts, duration, coordinate ranges, and altitude ranges.

### `preprocessing_report.json`

A short reproducibility report showing how many flights and points were parsed, removed, and saved.

## Current preprocessing result

Using the provided 2024–2026 DLH713 files, the pipeline produced:

```text
reconstructed_flights: 291
parsed_points_before_cleaning: 86381
invalid_points_removed: 18
duplicated_points_removed: 1
clean_points: 86362
clean_flights: 291
```

## Planned full project pipeline

```text
Raw OpenSky trajectory exports
        |
        v
Data preprocessing  <-- current contribution
        |
        v
Feature engineering / dimensionality reduction
        |
        v
HDBSCAN clustering
        |
        v
Cluster + anomaly analysis
        |
        v
Visualization and interpretation
```

## Data policy

The code and documentation can be committed to GitHub. Large, restricted, credential-bearing, or access-controlled datasets should be handled carefully. Generated processed datasets can be reproduced locally by running the preprocessing script.
