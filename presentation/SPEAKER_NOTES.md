# Speaker notes

English speaking draft with a total suggested allocation of 15 minutes. Rehearse and adjust to your pace. Sources follow each note.

## 1. Flight trajectory clustering (00:00–00:31)

Our project studies how actual flight paths vary between London Heathrow and Frankfurt. We use real observations from 2025 and treat each flight as one object. We compare the shapes of the routes, group similar flights with HDBSCAN, and inspect flights that do not fit those groups. Today we will explain our data checks, the distance measure, the parameter experiment and the unusual cases. Our focus is horizontal route geometry.

Sources: Project output files in the accompanying reproducibility package.

## 2. Research question and dataset (00:31–01:33)

Our question is: which route patterns repeat, and which flights have unusual horizontal shapes? We chose one direction, London Heathrow to Frankfurt, and one flight callsign and aircraft type. This limits some variation, although it does not make every flight operationally identical. The uploaded OpenSky dataset contains 348 flights in 2025 and over 1.24 million position rows. We do not claim it covers every flight on this route. Earlier ICN to FRA samples had multi-hour observation gaps, so we moved to a route with better continuity in the available data. This is a data-quality rationale, not a claim about airline performance.

Sources: Project output files in the accompanying reproducibility package. Source dataset commit 3ed740bcaaad81d22a5de6626eac7fa2d5a54b1f. https://openskynetwork.github.io/opensky-api/trino.html

## 3. Preprocessing and flight acceptance (01:33–02:44)

We preserved the source data and recorded the rows removed during cleaning. We checked the aircraft and flight identifiers, coordinates and timestamps. We used the time of the actual position update rather than treating every state-vector row as a new position. We removed 102 stale or invalid-time rows and 122 short, physically inconsistent position spikes. We then applied flight-level rules. Accepted flights need at least 100 points, no observation gap longer than 60 seconds, endpoints within 15 kilometres of the airport centres, and no remaining jumps under our screening rule. These thresholds are project choices. The 39 review flights remain in the cleaned file but are excluded from clustering.

Sources: Project output files in the accompanying reproducibility package. preparation_report.json, flight_qc.csv, removed_points.csv.

## 4. Distance between two flight trajectories (02:44–03:51)

Each trajectory is a set of observed latitude and longitude points. To compare two flights, we find the nearest point on the second flight for every point on the first flight. We keep the largest of those distances, repeat the calculation in the opposite direction, and take the larger result. That is the symmetric point-set Hausdorff distance. Distances use great-circle kilometres. An exact KD-tree search on unit-sphere coordinates makes the computation efficient without reducing the points. We calculated 47,586 unique pairs. The matrix is symmetric with a zero diagonal, and three complete flight pairs matched an independent dense calculation to numerical precision. This distance measures shape, but ignores time ordering.

Sources: Project output files in the accompanying reproducibility package. build_lhr_fra_matrix.py, matrix_report.json. https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html

## 5. HDBSCAN configuration (03:51–04:48)

We use the scikit-learn implementation with our distance matrix as input. HDBSCAN looks for groups supported by the density structure of the data, while allowing some flights to remain unassigned. We vary two parameters. The minimum cluster size controls how small a reported group may be. The minimum samples parameter affects the density estimate. Our implementation counts the point itself in minimum samples. We use excess-of-mass cluster selection and do not allow one cluster containing everything. We started at 15 and 5, then compared 15 parameter combinations. This project uses the library implementation, so we do not claim the optional from-scratch bonus.

Sources: https://scikit-learn.org/1.6/modules/generated/sklearn.cluster.HDBSCAN.html Project output files in the accompanying reproducibility package. cluster_lhr_fra.py.

## 6. Sensitivity across all 15 settings (04:48–05:55)

This table shows all tested combinations. Each cell gives the number of clusters and the number of noise flights. At minimum samples five, the smaller minimum cluster sizes identify four groups. Raising the minimum cluster size to fifteen removes the fourteen-flight group from the selected clusters. At minimum samples fifteen, every tested cluster-size threshold gives two broader groups. Across this grid, the same set of 180 flights stays together as a selected cluster. That supports one repeatable pattern, but the remaining partition depends on the settings. Noise percentages range from 4.53 to 11.65 percent. We therefore report sensitivity rather than presenting one configuration as uniquely correct.

Sources: Project output files in the accompanying reproducibility package. parameter_comparison.csv and parameter_labels.csv.

## 7. Working choice: min_cluster_size 10, min_samples 5 (05:55–06:47)

For the main visual analysis, we use minimum cluster size ten and minimum samples five. It preserves a coherent northern route group with fourteen flights. The original threshold of fifteen could not represent a group that small. The other groups of 180, 68 and 33 flights keep the same members when we make this change from the original baseline. Fourteen flights remain noise. We chose this configuration because it preserves an interpretable rare pattern in this dataset, not simply because it produces less noise. It remains an exploratory working choice. We have no external labels establishing the true number of route patterns.

Sources: Project output files in the accompanying reproducibility package. Comparison of mcs15/ms5 and mcs10/ms5 label files.

## 8. Four groups of observed route shapes (06:47–07:39)

Here are all accepted flights under the chosen configuration. The colours show cluster membership, and grey shows the fourteen noise flights. Thicker lines identify the representative flights. The northern arc contains fourteen flights and forms cluster zero. The other groups share much of the main corridor, with visible differences near the departure and arrival ends. These plots show longitude and latitude, not an operational airspace map. Cluster numbers are just identifiers. We have not linked the groups to particular runway assignments, weather conditions or air traffic control instructions. Those explanations would require additional records.

Sources: Project output files in the accompanying reproducibility package. data/lhr_fra_hdbscan_mcs10_ms5/clusters_overview.png.

## 9. Representative flights: cluster medoids (07:39–08:36)

We represent each cluster with a medoid. For every flight in the cluster, we sum its Hausdorff distances to the other members, and choose the flight with the smallest sum. The representative is therefore an actual observed flight. It is not a synthetic average path, and it does not have to be the shortest route. The four lines here show the chosen medoids using all their retained points. Their dates and full identifiers are available in cluster_representatives.csv. The median distance to the medoid is about 16.22 kilometres in cluster zero, 10.95 in cluster one, 8.45 in cluster two and 7.82 in cluster three.

Sources: Project output files in the accompanying reproducibility package. cluster_representatives.csv and cleaned coordinates.

## 10. Case 1: 2025-06-01 (08:36–09:28)

The first persistent candidate is the flight on June first. Its path moves north of the closest cluster representative later in the route, before returning toward Frankfurt. The symmetric Hausdorff distance to that representative is 73.80 kilometres. This number describes the largest nearest-point separation between the two point sets. It is not the extra distance flown. The flight has 3,784 retained points, and its largest position gap is 6.60 seconds. It passed the quality screening and remained noise in every tested setting. We can describe the geometry confidently, while the operational reason for the deviation remains unknown.

Sources: Project output files in the accompanying reproducibility package. persistent_noise_summary.csv and cleaned coordinates.

## 11. Case 2: 2025-07-27 (09:28–10:20)

The second candidate is July twenty-seventh. Early in the flight, it follows a similar corridor to the nearest representative, but the later part lies farther north. Its symmetric Hausdorff distance to that medoid is 43.94 kilometres. For this case, the medoid-to-candidate direction controls the symmetric maximum, which is why checking both directions matters. The flight has 3,714 points and a largest position gap of 5.15 seconds. It is noise in all fifteen settings. These small gaps make the earlier multi-hour missing-data problem an unlikely explanation for this particular route difference, although screening cannot eliminate every possible coordinate error.

Sources: Project output files in the accompanying reproducibility package. persistent_noise_summary.csv and cleaned coordinates.

## 12. Case 3: 2025-09-04 (10:20–11:12)

The third candidate is September fourth. Its visible deviation occurs earlier, with a southerly excursion before it joins the main corridor. Its closest-medoid Hausdorff distance is 36.87 kilometres. It has 3,858 retained points, with a maximum gap of 6.43 seconds. Like the previous two flights, it remains noise in all tested settings. The comparison identifies an unusual shape, but the representative is not a planned route or an operational requirement. To investigate the cause, we would need independent information such as weather, flight-plan or air traffic control records. We do not infer a safety issue from the cluster label.

Sources: Project output files in the accompanying reproducibility package. persistent_noise_summary.csv and cleaned coordinates.

## 13. Noise stability across the parameter grid (11:12–12:04)

This chart counts how often each flight received a noise label across the fifteen settings. Most flights, 273, were never noise. Eight were noise in three settings, eleven in eight settings, fourteen in eleven settings, and three in all fifteen. We examined the last three as persistent candidates. This frequency is a descriptive sensitivity measure. The settings reuse the same data and are not independent validation experiments, so fifteen out of fifteen is not a probability of danger or proof of a real operational anomaly. We also avoid treating every noise flight as the same kind of case. Some are boundary cases, and some become a coherent rare group under another setting.

Sources: Project output files in the accompanying reproducibility package. parameter_labels.csv.

## 14. Limits of the interpretation (12:04–13:01)

There are several limits to these findings. First, Hausdorff distance ignores the order and timing of points, altitude and speed. Flights that visit similar locations can therefore look similar even if their timing differs. Second, the maximum-distance definition can be sensitive to residual position errors. Third, quality filtering changes the sample. Thirty-three of the thirty-nine held flights are from April and May, so seasonal comparisons would need particular care. Fourth, the parameter grid demonstrates sensitivity within the tested range only. Finally, we have no operational ground truth for the candidates. The analysis can prioritise cases for review, but does not estimate fuel savings or establish why an aircraft followed a particular path.

Sources: Project output files in the accompanying reproducibility package. flight_qc.csv, matrix definition and experiment scope.

## 15. Reproducible analysis (13:01–13:44)

The accompanying code package includes the preparation script, the distance-matrix calculation, clustering, and candidate review. The prepared data distinguishes all cleaned flights from the accepted list used by clustering. Run the matrix script first if recomputing, then the clustering script with minimum cluster size ten and minimum samples five, and finally the candidate review. The parameter grid is produced by the clustering script. The package records its file hashes and runtime versions. Our numerical checks cover impossible position spikes, preservation of plausible turns, and agreement between KD-tree and dense spherical distances. The student Windows run used scikit-learn 1.6.1, while the packaged analysis outputs use 1.8.0. The compared cluster memberships agree.

Sources: Project output files in the accompanying reproducibility package. tests/test_lhr_fra.py and runtime reports.

## 16. Findings (13:44–14:22)

Our main result is that the accepted LHR to FRA observations contain several repeatable horizontal route patterns. Under the working configuration, 309 flights form four clusters with fourteen noise flights. A fourteen-flight northern route becomes visible as its own group when the minimum cluster size permits it. We selected actual flights as representatives and investigated three persistent geometric candidates. The practical value is a compact description of observed variation and a focused list for further operational review. Additional context and independent validation would be needed before using these findings for decisions about efficiency or safety.

Sources: Project output files in the accompanying reproducibility package.

## 17. Sources (14:22–14:41)

The main data source is the OpenSky dataset uploaded to the team repository. The cited commit identifies the original 2025 LHR to FRA data. The preparation and result tables in our package support the reported counts. We used the official scikit-learn, SciPy and OpenSky documentation for implementation details. The following disclosure explains the use of AI assistance.

Sources: Project output files in the accompanying reproducibility package. https://scikit-learn.org/1.6/modules/generated/sklearn.cluster.HDBSCAN.html https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html https://openskynetwork.github.io/opensky-api/trino.html

## 18. AI assistance disclosure (14:41–15:00)

We used ChatGPT and Codex to help generate and debug preprocessing, distance, clustering and diagnostic code, to inspect outputs, and to draft explanations and slides. The recorded student activities include choosing the route with the team, obtaining data through the project workflow, running the pipeline locally and uploading the prepared dataset to GitHub. AI assistance does not replace our responsibility to understand the method and verify our claims. Before submission, each team member should confirm their own contribution and the team should review this disclosure against its actual work.

Sources: Project conversation, user execution logs and generated code history.
