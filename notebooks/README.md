# Notebooks

This folder contains notebook-style workflows for explaining and running the project step by step.

## Current notebook

1. `01_dlh713_trajectory_preprocessing.ipynb`

This notebook shows the preprocessing workflow in a readable academic format:

- define dataset paths;
- verify raw DLH713 files;
- inspect the raw Excel/CSV-like structure;
- run the reusable preprocessing code from `src/preprocess.py`;
- load and validate generated outputs;
- explain the handoff to teammates.

## Why there is both a notebook and a Python script

- `src/preprocess.py` contains the reusable pipeline and can be run from the command line.
- `01_dlh713_trajectory_preprocessing.ipynb` presents the same preprocessing work in a step-by-step notebook format for coursework, reporting, and team explanation.

Keep heavy reusable logic in `src/`, and use notebooks for explanation, inspection, and presentation.

## Suggested next notebooks

2. `02_trajectory_visualization.ipynb`
3. `03_pca_feature_preparation.ipynb`
4. `04_hdbscan_clustering.ipynb`
5. `05_cluster_analysis.ipynb`
