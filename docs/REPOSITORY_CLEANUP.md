# Repository cleanup record

Cleanup baseline: `823c8bda71994ff0dc06cfbb152380ea4031aead` (main, read on 2026-10-09).

The new active tree focuses on the selected 2025 LHR-to-FRA analysis. The cleanup is a normal descendant commit. Previous versions remain accessible in Git history.

Removed from the active tree:

- `DLH713_2024.csv.xlsx`, `DLH713_2025.csv.xlsx`, `DLH713_2026.csv.xlsx`.
- Old ICN-to-FRA products in `data/processed/` and `data/hausdorff/`.
- The old DLH713 notebook and its notebook README.
- `src/preprocess.py`, `src/quality_check.py`, `src/hausdorff_matrix.py` for the earlier workflow.
- Outdated ICN-to-FRA instructions in the root/data READMEs and the old preprocessing/output/request documents, replaced by current LHR-to-FRA documentation.

Preserved:

- Original LHR-to-FRA data and Git LFS tracking.
- All five student-uploaded prepared files, reusing their existing Git blob objects unchanged.
- Team history and contributor attribution.

Moved and retained:

- Three recent LHR-to-FRA teammate scripts moved from `src/` to `experiments/`, with separate experiment output paths. They were not removed as obsolete.

Added:

- The verified full-resolution pipeline, one-command runner and focused tests.
- Regenerated matrix, both HDBSCAN results, sensitivity labels and candidate analysis.
- Presentation, speaker notes, current method/results documentation and AI disclosure.

The full raw LFS object is not re-uploaded or deleted. The 40 MB prepared CSV is not re-uploaded. The commit references the existing blobs. No force push, repository deletion or orphan history is used.

To inspect an earlier file, use GitHub's history at the baseline commit or `git show 823c8bda71994ff0dc06cfbb152380ea4031aead:path/to/file`.
