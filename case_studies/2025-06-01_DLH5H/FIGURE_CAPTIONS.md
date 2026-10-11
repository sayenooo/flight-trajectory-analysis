# Figure captions and presentation-ready descriptions

## Figure 1 — ERA5 weather overview

**Suggested caption (English):** “ERA5 reanalysis over the London Heathrow–Frankfurt corridor on 1 June 2025. Panels show one-hour total precipitation and convective precipitation (08:00–09:00 and 09:00–10:00 UTC), total cloud cover and CAPE at 09:00 UTC, and 350 hPa wind at 09:00 UTC. The red trajectory is the DLH5H outlier; remaining colored tracks are HDBSCAN cluster medoids flown on other dates. Spatial overlap with an ERA5 weather signal does not demonstrate that the aircraft avoided that condition.”

**Suggested slide narration (English):** “We initially considered weather avoidance because parts of the region had precipitation signals and elevated CAPE. However, CAPE represents the potential for convection, not an observed thunderstorm at a precise location and altitude.”

Source: ERA5 (Copernicus CDS); flight tracks from the project’s OpenSky-based data. Image: `figures/weather_outlier_2025-06-01_6panels.png` (cropped screenshot of the user-reviewed original figure, not the full-resolution export).

## Figure 2 — Seven arrival trajectories

**Suggested caption (English):** “Observed OpenSky ADS-B trajectories of seven flights arriving at Frankfurt around the time of DLH5H on 1 June 2025 (arrival estimates 09:07–09:19 UTC). DLH5H is emphasized in red. Nearby arrivals used multiple approach corridors, including southern paths. These differences alone do not distinguish ATC instructions, arrival procedures or weather-driven decisions. This packaged preview is cropped from a user-provided screenshot; original full-resolution PNG and local flight CSVs should be imported for final submission.”

**Suggested slide narration (English):** “If severe regional weather had made southern approaches unusable for everyone, we would expect a more uniform shift; the observed mixed paths weaken that strong hypothesis. But aircraft entered from different directions, so further operational validation is necessary.”

Source: OpenSky Network historical ADS-B records, retrieved in the user's local Trino run. Preview: `figures/7_flights_vs_DLH5H_preview_from_screenshot.png`.

## Figure-use cautions

- Do not call the 73.80 km symmetric Hausdorff distance an additional flight length.
- Do not label cluster-medoid tracks from different dates as concurrent aircraft.
- Do not claim CAPE alone is evidence of actual turbulence or storm cells.
- Do not claim an ATC vector or weather deviation was confirmed without operational sources.
- State all timestamps in UTC and refer to reported firstSeen/lastSeen as observational/estimated, not independently certified runway times.
