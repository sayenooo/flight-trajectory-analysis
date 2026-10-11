# Team briefing — June 1 DLH5H outlier follow-up

**Purpose.** Investigate why the June 1, 2025 DLH5H (London Heathrow → Frankfurt) trajectory is a persistent HDBSCAN outlier, without treating geometric difference as proof of an operational event.

**Baseline.** The existing project accepted 309 flights for HDBSCAN (`min_cluster_size=10`, `min_samples=5`), assigning 14 noise labels (4.53%). Three flights were noise under all 15 tested parameter settings. The June 1 case has the greatest nearest-medoid symmetric Hausdorff distance among them (73.80 km), indicating a spatial deviation late in the route—not an extra 73.80 km flown.

**Step 1 — Initial hypothesis.** The aircraft appeared to depart from its usual/representative arrival corridor. We overlaid ERA5 precipitation, total cloud cover, 09:00 UTC CAPE and 350 hPa wind. Some precipitation signal and locally elevated CAPE near/south-east of Frankfurt made weather avoidance a plausible hypothesis. CAPE describes potential buoyant energy; it is not direct evidence of active thunderstorm avoidance.

**Step 2 — Comparison test.** OpenSky returned 41 flights arriving at EDDF during 08:40–09:40 UTC. We visually compared DLH5H with six arrivals close to 09:13 UTC. Three selected flights (AFR93RE, CFG2045, DLH8F) approached from the south, UAL74 used a more intermediate/northern corridor, and two (OCN77 and DLH447) entered from the north/another direction.

**Interpretation.** Southern approaches existed at similar arrival times. This weakens a claim that the whole southern arrival corridor was uniformly avoided because of weather; it neither disproves an individual weather deviation nor proves ATC vectoring. Different arrival directions, STARs/transitions, runway allocation, sequencing and local weather remain competing explanations.

**Uncertainty / next work.** Actual controller communications, relevant runway/STAR assignments, and high-resolution contemporaneous weather observations were not verified. Position-age fields in the exploratory comparison remained unvalidated (`DRAWN_AGE_UNVERIFIED`); verify the original CSV timestamps before quantitative claims. The second route comparison panel included in this folder is a cropped screenshot preview until the original PNG or track CSVs are imported.

**Bottom line.** The case demonstrates a complete reasoning chain: detect → localize → hypothesize weather → test against nearby arrivals → revise interpretation. Final cause: **not determined**.

Figures and reproducibility: see [README.md](README.md) and [FIGURE_CAPTIONS.md](FIGURE_CAPTIONS.md).


**Evidence/source matrix:** see [SOURCE_CODE_MATRIX.md](SOURCE_CODE_MATRIX.md). **Student final hypothesis:** see [FINAL_HYPOTHESIS_KO.md](FINAL_HYPOTHESIS_KO.md). The included figures are screenshot crops of the student-reviewed results; source CSVs for other arrivals remain on the local Windows machine.
