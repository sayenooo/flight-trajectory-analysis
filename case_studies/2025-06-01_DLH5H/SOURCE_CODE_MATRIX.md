# Sources, original datasets, code, dates and artifacts

This is a provenance ledger for the 1 June 2025 DLH5H case. No ATC recordings, actual STAR clearances or verified runway allocations were obtained.

| Step | Site / provider | Exact material | Date/time UTC | Program / processing | Saved image or result |
|---|---|---|---|---|---|
| 1 — Detection | [OpenSky Network](https://opensky-network.org) via [parent GitHub repository](https://github.com/sayenooo/flight-trajectory-analysis) | EGLL → EDDF 2025 DLH5H A20N ADS-B points, `flight_points_clean.csv.gz`, `flight_clusters.csv`, `noise_candidates.csv`, medoids | Full **2025** sample: 309 accepted flights; DLH5H on **2025-06-01 08:09:37–09:13:52** | Parent `run_pipeline.py` (prepare, Hausdorff, HDBSCAN); `plot_weather_case.py` overlays accepted flight and medoids | 14 noise flights in working setting, persistent June 1 candidate at **73.80 km** nearest-medoid symmetric Hausdorff |
| 2 — Weather | [Copernicus CDS — ERA5 single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) | Hourly `tp`, `cp`; `cape`, `tcc`; original NetCDF exports in `data/era5/` | **2025-06-01** precipitation 08–09 and 09–10; CAPE/cloud cover 09:00 | `scripts/plot_weather_case.py` | `figures/weather_outlier_2025-06-01_6panels.png` (user-reviewed screenshot crop) |
| 3 — Wind | [Copernicus CDS — ERA5 pressure levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels?tab=overview) | `u`, `v`, **350 hPa** | **2025-06-01 09:00** | Same plotting script | Wind vectors on CAPE/cloud maps |
| 4 — Other arrivals | [OpenSky Trino historical database](https://openskynetwork.github.io/opensky-api/trino.html) using [`pyopensky`](https://mode-s.org/pyopensky/trino.html) | All arrivals to **EDDF**, without departure-airport filter: metadata 41 rows according to user's execution log; historical position `time`, `icao24`, `callsign`, `lat`, `lon`, `lastposupdate` | **2025-06-01**, arrivals 08:40–09:40, positions 08:15–09:45 | `scripts/download_selected_arrivals.py`, following exploratory user's PowerShell `compare_FRA_approaches.py` / `compare_fixed.py` | `flight_*.csv`, diagnostic CSV (on user's Windows PC; **not yet uploaded**) |
| 5 — Flight comparison | Same OpenSky trajectories | Seven chosen flights: **OCN77 09:07:21, UAL74 09:09:22, AFR93RE 09:13:29, DLH5H 09:13:52, CFG2045 09:16:18, DLH8F 09:17:13, DLH447 09:18:55** (arrival estimates) | **2025-06-01** | `scripts/plot_seven_arrivals.py`, `scripts/import_local_exports.ps1` | `figures/7_flights_vs_DLH5H_preview_from_screenshot.png` (screenshot crop; high-resolution original on user's PC) |
| 6 — Interpretation | This case study | Compare southern/northern approaches; consider regional CAPE/precipitation alongside alternative ATC and arrival-procedure explanations | **2025-06-01** | `README.md`, `TEAM_SUMMARY_EN.md` | **ATC/arrival procedure plausible but unconfirmed; common weather avoidance not supported as a universal explanation** |

## Important distinctions

- **73.80 km** is nearest-medoid **symmetric Hausdorff separation**, **not** additional flight distance.
- ERA5 medoid overlays depict representatives **from other dates**, not seven aircraft flying together.
- CAPE indicates the **potential** for convective ascent; it does not observe storm cells or controller decisions.
- This study includes **images from actual user-reviewed screenshots** rather than an inaccurate synthetic example generated during script testing.
- The seven raw CSVs are **not in this GitHub publication** unless the student imports them from the Windows source directory. The importer does not invent missing data.
- Position-age checks in the exploratory OpenSky output were **unverified**; figures are exploratory, not validated operational reconstructions.
- Avoid exposing authentication material in the repository; the scripts use an authorized OpenSky Trino login only when rerun.
