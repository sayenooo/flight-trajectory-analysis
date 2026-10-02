# Data Scope Note

## Project

Aircraft trajectory analysis and clustering using real-world trajectory exports.

## Current dataset

The current working files are DLH713 trajectory exports for 2024, 2025, and 2026:

```text
DLH713_2024.csv.xlsx
DLH713_2025.csv.xlsx
DLH713_2026.csv.xlsx
```

The exact original provider/source of these files should be confirmed by the project team. The files have an OpenSky-style structure, but this repository documents and preprocesses the files as provided.

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
- dimensionality reduction
- trajectory clustering
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

## Processing scope

The preprocessing pipeline covers:

- reconstructing split records from the Excel exports;
- parsing flight-level data;
- expanding nested trajectory points;
- cleaning invalid values and duplicates;
- sorting each trajectory chronologically;
- creating processed CSV outputs for downstream analysis.
