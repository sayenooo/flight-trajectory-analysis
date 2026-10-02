# Data Scope Note

## Project

Aircraft trajectory analysis and clustering using real-world trajectory exports.

## Current dataset

The project no longer uses the earlier ZRH-GVA route idea. The current working files are DLH713 trajectory exports for 2024, 2025, and 2026:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

The exact original provider/source of these files should be confirmed by the team. The files have an OpenSky-style structure, but this repository currently documents and preprocesses the files as provided.

## Current route context

The current route context is:

```text
Seoul / Incheon area (ICN / RKSI) -> Frankfurt area (FRA / EDDF)
```

This is inferred from the DLH713 callsign and coordinate ranges observed in the trajectory points. The raw files do not contain explicit airport columns, so the preprocessing pipeline does not rely on airport names.

## Purpose

Non-commercial university coursework / academic research.

## Intended analysis

- trajectory reconstruction
- preprocessing and visualization
- comparison of repeated flights
- PCA or other dimensionality-reduction methods
- HDBSCAN clustering
- detection and interpretation of unusual trajectories

## Available fields in the current raw files

Flight-level fields:

```text
icao24, callsign, firstseen, lastseen, track
```

Point-level fields inside `track`:

```text
time, latitude, longitude, altitude, heading, onground
```

## Current contribution

The current contribution is limited to preprocessing:

- reconstruct split records from the Excel exports
- parse flight-level data
- expand nested trajectory points
- clean invalid values and duplicates
- sort each trajectory chronologically
- create processed CSV outputs for teammates who will continue with PCA/HDBSCAN
