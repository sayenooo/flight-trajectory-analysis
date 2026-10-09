# Data and result inventory

## Inputs preserved from the team repository

`lhr_fra_2025/` contains the original 2025 LHR to FRA source. The full position CSV is stored with Git LFS. Its SHA256 is `3848f3829e19848eb025df79b1ca7642cb2298ed4bfb75526de70dd3d4fbe858`, introduced at commit `3ed740bcaaad81d22a5de6626eac7fa2d5a54b1f`. The flight list and original provider QC summary are retained alongside it. The provider QC summary is not a substitute for the project's coordinate checks.

`lhr_fra_prepared/` preserves the five files uploaded by the student at commit `c75a8f9`:

| File | Meaning |
|---|---|
| `flight_points_clean.csv.gz` | 1,242,774 retained points from all 348 flights |
| `accepted_flights.csv` | The 309 flight IDs selected for the main analysis |
| `flight_qc.csv` | Quality metrics and pass/review decision for every flight |
| `removed_points.csv` | 224 removed rows with reasons |
| `preparation_report.json` | Source hash, counts and processing thresholds |

The committed compressed-point SHA256 is `7e4925a67577ed4cb5f34aa72be4d786a150ee5850b5ca9f1f021309c5969acc`. All five prepared files remain byte-for-byte unchanged during cleanup. A fresh preprocessing run may produce a different compressed-file hash due to gzip metadata or numeric serialization.

## Derived outputs

- `lhr_fra_hausdorff/`: the 309 × 309 full-resolution symmetric Hausdorff matrix, flight-ID order, report and checksum. A CSV duplicate can be regenerated but is not committed.
- `lhr_fra_hdbscan_mcs10_ms5/`: working configuration, cluster labels and medoids, parameter labels and all 15 settings, noise candidates and plots.
- `lhr_fra_hdbscan_mcs15_ms5/`: original baseline and its outputs.
- `lhr_fra_candidate_review/`: three persistent candidates, distances to nearest medoids, point-gap checks and plots.
- `experiments/`: local outputs of optional teammate experiments. These are ignored by Git and have different paths from the main outputs.

The published analysis was regenerated using the committed prepared CSV during the repository cleanup. Input and output checksums are recorded in `docs/REPRODUCIBILITY.json` and per-stage reports. The flight-ID order is part of the matrix and must be kept with it.
