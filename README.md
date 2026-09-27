# Flight Trajectory Analysis with OpenSky

Academic project for analyzing and clustering real-world aircraft trajectories using data from the OpenSky Network.

## Case study

**Primary route:** Zurich Airport (**ZRH / LSZH**) → Geneva Airport (**GVA / LSGG**), Switzerland.

The project is designed so that other routes can be added later if needed.

## Objective

The goal is to reconstruct historical flight trajectories and study how flights on the same route differ in space and time.

Planned tasks:

1. Collect historical OpenSky trajectory / state-vector data.
2. Filter flights for the selected airport pair.
3. Clean and preprocess latitude, longitude, altitude and timestamp data.
4. Reconstruct one ordered trajectory per flight.
5. Visualize trajectories on a map.
6. Transform trajectories into comparable feature representations.
7. Apply clustering, initially **HDBSCAN**, to identify common flight-path patterns and outliers.
8. Analyze differences between clusters and unusual trajectories.

## Research questions

- What are the most common trajectory patterns between ZRH and GVA?
- How much do trajectories vary between flights on the same route?
- Can density-based clustering identify major route patterns without pre-selecting the number of clusters?
- Which flights appear as trajectory outliers?

## Requested OpenSky data

The current OpenSky access request targets:

- **Geographical area:** Switzerland, especially the ZRH–GVA corridor and surrounding departure/arrival airspace.
- **Preferred period:** 1 January 2025 – 31 December 2025.
- **Fallback period:** any continuous 3–6 month period within 2025 if a full year is unavailable.
- **Access/data types:** Trino and raw historical data where appropriate.
- **Use:** non-commercial university coursework and academic research.

Useful fields include, where available:

- timestamp
- ICAO24
- callsign
- latitude
- longitude
- barometric / geometric altitude
- velocity
- heading / track
- vertical rate
- departure / arrival information

## Planned pipeline

```text
OpenSky historical data
        |
        v
Route / time filtering
        |
        v
Cleaning + trajectory reconstruction
        |
        v
Resampling / feature engineering
        |
        v
Trajectory visualization
        |
        v
HDBSCAN clustering
        |
        v
Cluster + outlier analysis
```

## Repository structure

```text
flight-trajectory-analysis/
├── data/
│   └── README.md
├── docs/
│   └── opensky-data-request.md
├── notebooks/
│   └── README.md
├── src/
│   └── preprocess.py
├── .gitignore
├── requirements.txt
└── README.md
```

Large or restricted OpenSky datasets should **not** be committed to GitHub. Keep downloaded data locally inside `data/`.

## Setup

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Current status

- [x] Define initial research problem
- [x] Select ZRH–GVA as the compact backup route
- [x] Prepare OpenSky historical-data access request
- [ ] Receive OpenSky access
- [ ] Query / download historical data
- [ ] Build preprocessing pipeline
- [ ] Reconstruct trajectories
- [ ] Visualize trajectories
- [ ] Run HDBSCAN experiments
- [ ] Evaluate and interpret clusters

## Data policy

This repository contains code, documentation and analysis only. OpenSky data will be used for non-commercial academic purposes and handled according to the applicable OpenSky access conditions.
