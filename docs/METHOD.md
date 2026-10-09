# Method and limitations

## Dataset and preprocessing

One directed route: EGLL (LHR) to EDDF (FRA), callsign DLH5H, A20N, 2025. The input has 348 flights and 1,242,998 points. This is the available team dataset, not a census of every operation on the route.

`prepare_lhr_fra.py` verifies flight IDs, aircraft addresses, metadata, time intervals and coordinate validity. It uses `lastposupdate` for trajectory time. It rejects invalid/stale position or contact ages outside 0–15 seconds, deduplicates position updates, and screens short physically inconsistent coordinate excursions. A spike burst must be unreachable from both retained neighbours under a 450 m/s plus 2 km tolerance envelope, with a plausible bridge of at most 60 seconds. Bursts contain at most five points. This is a coarse coordinate-error screen, not an aircraft operating standard.

Point removal: 102 stale/invalid-time rows and 122 position spikes. Flight acceptance requires at least 100 points, maximum position gap at most 60 seconds, first and last positions within 15 km of approximate airport centres, and no unresolved jumps under the screening rule. The accepted sample has 309 flights and 1,121,503 points. The 39 held flights remain in the cleaned file.

There is no interpolation, smoothing, altitude filtering or route-corridor clipping. First and last observations are not independently verified takeoff/landing times. Altitude and speed are not certified or used as clustering features.

## Flight distance

For observed point sets A and B:

`h(A,B) = max over a in A of min over b in B d(a,b)`

`H(A,B) = max(h(A,B), h(B,A))`

`d` is spherical great-circle distance in km with mean Earth radius 6371.0088 km. Exact nearest-neighbour queries on unit-sphere XYZ coordinates find chord distances, which are converted to arcs. Three full flight pairs are independently checked with a dense haversine implementation. The matrix is finite, non-negative, symmetric and has a zero diagonal.

The main matrix uses every accepted point. Hausdorff distance is a maximum nearest-point separation, not an average deviation, travelled distance or extra distance flown. It ignores time ordering, speed and altitude. It is sensitive to remaining coordinate errors.

## Clustering and representatives

`sklearn.cluster.HDBSCAN`, precomputed metric, brute algorithm, excess-of-mass selection, `allow_single_cluster=False`, and `copy=True`. The grid is minimum cluster sizes 5, 10, 15, 20, 30 crossed with minimum samples 5, 10, 15. In scikit-learn, minimum samples includes the observation itself.

The original baseline is (15,5). The working visual configuration is (10,5), which preserves a coherent 14-flight northern group. The configuration is exploratory rather than a proven optimum. Cluster numbers are arbitrary.

The representative of each cluster is the real member flight minimizing the sum of within-cluster Hausdorff distances, an unweighted medoid. It is not a synthetic path or a flight-plan recommendation.

## Candidate investigation and scope

Noise frequency across the 15 settings helps prioritise candidate review. The same dataset is reused, so frequency is not independent validation or a risk probability. A noise label does not establish an operational anomaly. The three persistent candidates are compared with the nearest of the four medoids, and their observation gaps are checked.

No verified weather, runway, ATC or flight-plan context is included. Fuel savings and safety implications are not estimated. Thirty-three of the 39 held flights are from April–May, so acceptance introduces potential seasonal selection bias. Preprocessing-threshold sensitivity and operational ground truth remain possible extensions.

## Sources

- OpenSky historical data and timestamps: https://openskynetwork.github.io/opensky-api/trino.html
- HDBSCAN: https://scikit-learn.org/1.6/modules/generated/sklearn.cluster.HDBSCAN.html
- cKDTree exact nearest neighbours: https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html
- Source code and reports in this repository, with AI assistance disclosed in AI_DISCLOSURE.md.
