# Optional teammate experiments

These three LHR–FRA scripts were present on `main` at commit `823c8bda71994ff0dc06cfbb152380ea4031aead` before cleanup. Their logic is retained. Only default output/input paths and one usage hint were adjusted so they cannot replace the main full-resolution matrix.

| Script | Purpose |
|---|---|
| `downsample_sensitivity.py` | Compare nearest-observation sampling at 10, 30 and 60 seconds |
| `lhr_fra_hausdorff.py` | Dense haversine Hausdorff matrix for the 30-second sample |
| `visual_qc_hausdorff.py` | Inspect large pair distances and their witness points |

Run these commands from the repository root, only for the additional sampling study:

```bat
python experiments\downsample_sensitivity.py
python experiments\lhr_fra_hausdorff.py
python experiments\visual_qc_hausdorff.py
```

Outputs go to `data/experiments/downsampling/`, `data/experiments/hausdorff_30s/` and `data/experiments/visual_qc_30s/`. They are excluded from Git by default. The main HDBSCAN scripts read `data/lhr_fra_hausdorff/` and do not use these sampled products.

The published four-cluster result and presentation use every accepted observation. The existence of these optional scripts does not establish that downsampling preserves cluster assignments. These experiments have not been presented as validated main-analysis results.

Authorship history is retained in Git. The scripts were added by teammate `yunghair`; confirm the full team contribution and tool-use disclosure before submission.
