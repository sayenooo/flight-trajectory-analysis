"""Plot persistent noise flights against their nearest cluster representatives.

Run after: python src/cluster_lhr_fra.py --min-cluster-size 10 --min-samples 5
Prepared with ChatGPT/Codex assistance, 2026-10-07.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from build_lhr_fra_matrix import unit_sphere, EARTH_KM


def arc_km(chord):
    return 2 * EARTH_KM * np.arcsin(np.clip(chord / 2, 0, 1))


def run(root):
    cluster_dir = root / 'data/lhr_fra_hdbscan_mcs10_ms5'
    labels = pd.read_csv(cluster_dir / 'flight_clusters.csv')
    medoids = pd.read_csv(cluster_dir / 'cluster_representatives.csv')
    candidates = labels[(labels.cluster == -1) & (labels.noise_fraction_across_grid == 1)].sort_values('date')
    if candidates.empty or medoids.empty:
        raise ValueError('No persistent noise candidates or no cluster representatives.')
    matrix_dir = root / 'data/lhr_fra_hausdorff'
    ids = pd.read_csv(matrix_dir / 'hausdorff_flight_ids.csv')
    if not ids.flight_id.equals(labels.sort_values('matrix_index').flight_id.reset_index(drop=True)):
        raise ValueError('Cluster labels and matrix flight IDs are not aligned.')
    matrix = np.load(matrix_dir / 'hausdorff_distance_matrix_km.npy', allow_pickle=False)
    chosen = []
    for candidate in candidates.itertuples():
        j = int(np.argmin(matrix[candidate.matrix_index, medoids.medoid_matrix_index.to_numpy(dtype=int)]))
        chosen.append((candidate, medoids.iloc[j]))
    wanted = set(candidates.flight_id) | {m.medoid_flight_id for _, m in chosen}
    points = pd.read_csv(root / 'data/lhr_fra_prepared/flight_points_clean.csv.gz',
                         usecols=['flight_id', 'point_time_unix', 'latitude', 'longitude'])
    points = points[points.flight_id.isin(wanted)].sort_values(['flight_id', 'point_time_unix'])
    groups = {fid: g for fid, g in points.groupby('flight_id')}
    out = root / 'data/lhr_fra_candidate_review'
    out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(chosen), 2, figsize=(14, 4.1 * len(chosen)),
                             squeeze=False, layout='constrained')
    results = []
    for row, (candidate, medoid) in enumerate(chosen):
        a, b = groups[candidate.flight_id], groups[medoid.medoid_flight_id]
        ca, cb = a[['latitude', 'longitude']].to_numpy(), b[['latitude', 'longitude']].to_numpy()
        xa, xb = unit_sphere(ca), unit_sphere(cb)
        dab, jab = cKDTree(xb).query(xa, k=1, eps=0)
        dba, jba = cKDTree(xa).query(xb, k=1, eps=0)
        ab, ba = arc_km(dab), arc_km(dba)
        if ab.max() >= ba.max():
            ia = int(ab.argmax()); ib = int(jab[ia]); direction = 'candidate_to_medoid'
        else:
            ib = int(ba.argmax()); ia = int(jba[ib]); direction = 'medoid_to_candidate'
        distance = float(max(ab.max(), ba.max()))
        expected = matrix[candidate.matrix_index, int(medoid.medoid_matrix_index)]
        if not np.isclose(distance, expected, atol=1e-7, rtol=0):
            raise ValueError('Point geometry does not reproduce the stored matrix distance.')
        witnesses = np.array([ca[ia], cb[ib]])
        dt = np.diff(a.point_time_unix.to_numpy())
        results.append(dict(
            date=candidate.date, flight_id=candidate.flight_id,
            nearest_cluster=int(medoid.cluster), medoid_flight_id=medoid.medoid_flight_id,
            hausdorff_km=distance, candidate_to_medoid_max_km=float(ab.max()),
            medoid_to_candidate_max_km=float(ba.max()), controlling_direction=direction,
            max_position_gap_sec=float(dt.max()), point_count=len(a),
            observed_duration_min=float((a.point_time_unix.iloc[-1]-a.point_time_unix.iloc[0])/60),
            candidate_witness_latitude=float(ca[ia,0]), candidate_witness_longitude=float(ca[ia,1]),
            candidate_witness_utc=str(pd.to_datetime(a.point_time_unix.iloc[ia], unit='s', utc=True)),
            witness_minutes_before_last_observation=float((a.point_time_unix.iloc[-1]-a.point_time_unix.iloc[ia])/60),
        ))
        for col, ax in enumerate(axes[row]):
            ax.plot(b.longitude, b.latitude, color='#b26b19', ls='--', lw=1.4, label=f'Cluster {int(medoid.cluster)} representative')
            ax.plot(a.longitude, a.latitude, color='#167b91', lw=1.6, label='Candidate flight')
            ax.plot(witnesses[:,1], witnesses[:,0], 'o:', color='#bd3348', ms=4, lw=1,
                    label=f'Hausdorff witness: {distance:.1f} km')
            ax.set(xlabel='Longitude (degrees)', ylabel='Latitude (degrees)')
            ax.set_aspect(1 / np.cos(np.radians(51)))
            ax.grid(alpha=.2)
            if col == 0:
                ax.set_title(f'{candidate.date} · full observed route')
                ax.legend(fontsize=8, loc='best')
            else:
                lat0, lon0 = witnesses.mean(axis=0)
                half_lon = max(np.ptp(witnesses[:,1])*.7, .65)
                half_lat = max(np.ptp(witnesses[:,0])*.7, .3)
                ax.set_xlim(lon0-half_lon, lon0+half_lon)
                ax.set_ylim(lat0-half_lat, lat0+half_lat)
                ax.set_title('Detail around the distance-defining points')
    fig.savefig(out / 'persistent_noise_comparison.png', dpi=165)
    plt.close(fig)
    summary = pd.DataFrame(results)
    summary.to_csv(out / 'persistent_noise_summary.csv', index=False)
    (out / 'review_notes.txt').write_text(
        'Candidates are noise under all 15 tested parameter settings, not all possible settings.\n'
        'Orange dashed line: nearest unweighted cluster medoid under the four-cluster model.\n'
        'The red dotted segment identifies the controlling nearest-neighbour pair for Hausdorff distance.\n'
        'The paired positions need not share a timestamp. The distance is not an average route deviation.\n'
        'Candidate plots use observed horizontal coordinates, with no new interpolation or smoothing.\n'
        'Passing data-quality checks does not prove absence of residual errors.\n'
        'Geometry alone cannot establish weather, ATC instructions, runway configuration or safety significance.\n',
        encoding='utf-8')
    print(summary.to_string(index=False))
    print('Saved review to:', out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, default=Path(__file__).resolve().parents[1])
    run(parser.parse_args().project_dir)
