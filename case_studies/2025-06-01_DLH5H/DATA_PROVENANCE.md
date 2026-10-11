# Data provenance, reproducibility and limitations

## Parent-project observations

- Reference repository: <https://github.com/sayenooo/flight-trajectory-analysis>
- HDBSCAN results: `data/lhr_fra_hdbscan_mcs10_ms5/flight_clusters.csv` and `noise_candidates.csv`.
- Original 2025 source: `data/lhr_fra_2025/` (large raw positions in Git LFS).
- Quality-cleaned positions: `data/lhr_fra_prepared/flight_points_clean.csv.gz`.
- Reference flight ID: `DLH5H_3c65d8_1748765377_1748769232`.
- Original quality report: 3,784 cleaned of 3,784 reference rows and maximum inter-position gap of ~6.596 s (as committed in `flight_qc.csv`).

## Weather files included in this case-study package

These are copies of the user-provided ERA5 NetCDF inputs used in the user-reviewed ERA5 visual analysis:

- `data/era5/data_stream-oper_stepType-instant.nc`: CAPE (`cape`) and total cloud cover (`tcc`).
- `data/era5/data_stream-oper_stepType-accum.nc`: total precipitation (`tp`) and convective precipitation (`cp`).
- `data/era5/wind_2025-06-01.nc`: 350 hPa horizontal wind (`u`, `v`); other pressure levels may be present.

ERA5 is reanalysis rather than airborne direct measurement. Weather hours shown are as defined in the figure caption; check CDS metadata when publishing.

## OpenSky arrivals: what was observed in the local run

- Search: `arrival_airport='EDDF'`, estimated arrivals 2025-06-01 08:40–09:40 UTC, all departure airports.
- The user reported **41 matching arrival records**.
- Seven selected callsigns: OCN77, UAL74, AFR93RE, DLH5H, CFG2045, DLH8F, DLH447.
- The user reported point counts for this seven-flight comparison and showed its plotted trajectories in a screenshot.
- Individual CSVs were generated on the user's Windows machine (`$HOME\OpenSky_FRA_Approach_20250601`) **but have not been uploaded here**. Hence this package includes the screenshot preview and an importer/downloader, but does not pretend to contain the seven original CSV datasets.
- The older exploratory script reported `DRAWN_AGE_UNVERIFIED` for the flights because its `lastposupdate` timestamp check did not validate. Do not describe those positions as age-verified.
- For this case, the plotting script deliberately uses valid time/coordinates for *exploratory visualization* and records that final temporal QA is outstanding. Re-querying and comparing raw/cleaned HDBSCAN paths is a recommended follow-up.

## Original-vs-preview image provenance

- `figures/weather_outlier_2025-06-01_6panels.png`: **cropped screenshot of the user-reviewed six-panel visualization**, captured from the user-submitted Paint screenshot. This is NOT the original exported matplotlib PNG and must not be misrepresented as such. The original screenshot used is `image(20261011-081529).png` in the conversation.
- `figures/7_flights_vs_DLH5H_preview_from_screenshot.png`: crop of the Paint screenshot supplied by the user in the chat, not a pixel-identical copy of the source matplotlib PNG.
- The original `7_flights_vs_DLH5H.png` may be available on the Windows PC. `scripts/import_local_exports.ps1` copies it if found. `scripts/plot_seven_arrivals.py` can regenerate a clean figure from the source CSVs.

## Causal interpretation and external context

Operational runway use, STAR/transition clearance, ATC vectors, radar returns, and live SIGMET/NOTAM were **not** independently verified in this case. Do not interpret mixed approach directions as a controlled weather experiment, nor infer a controller clearance from the ADS-B path alone.

## Ethical/technical notes

- Never commit OAuth tokens, passwords, API-client secrets or personally identifiable credentials.
- Cite OpenSky Network for ADS-B and Copernicus CDS / ERA5 for weather.
- Use a fresh branch and review data provenance before merging into the original student team repository.
- Document AI assistance consistently with the parent repository's `docs/AI_DISCLOSURE.md`.
