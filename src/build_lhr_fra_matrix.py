"""Exact spherical Hausdorff distances between cleaned, accepted flight point sets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
EARTH_KM = 6371.0088


def unit_sphere(coords):
    latitude, longitude = np.radians(coords).T
    return np.column_stack([np.cos(latitude) * np.cos(longitude),
                            np.cos(latitude) * np.sin(longitude), np.sin(latitude)])


def hausdorff_km(a, b, tree_a=None, tree_b=None):
    """a/b are unit-sphere XYZ. Chord distance preserves spherical NN ordering.

    Exact KD-tree queries (eps=0) avoid allocating a dense point-pair matrix.
    Convert the largest nearest-neighbour chord to arc length via 2*asin(c/2).
    This is the same point-set Hausdorff metric as dense spherical haversine.
    """
    tree_a = cKDTree(a) if tree_a is None else tree_a
    tree_b = cKDTree(b) if tree_b is None else tree_b
    ab = tree_b.query(a, k=1, eps=0)[0].max()
    ba = tree_a.query(b, k=1, eps=0)[0].max()
    return float(2 * EARTH_KM * np.arcsin(np.clip(max(ab, ba) / 2, 0, 1)))


def run(args):
    start = time.perf_counter()
    ids = pd.read_csv(args.input_dir / 'accepted_flights.csv').flight_id.tolist()
    if len(ids) < 2 or len(ids) != len(set(ids)):
        raise ValueError('Need at least two unique accepted flight IDs.')
    points_path = args.input_dir / 'flight_points_clean.csv.gz'
    d = pd.read_csv(points_path, usecols=['flight_id', 'point_time_unix', 'latitude', 'longitude'])
    d = d[d.flight_id.isin(ids)].sort_values(['flight_id', 'point_time_unix'])
    groups = {fid: g[['latitude', 'longitude']].to_numpy() for fid, g in d.groupby('flight_id')}
    if set(groups) != set(ids) or not np.isfinite(d[['latitude', 'longitude']].values).all():
        raise ValueError('Missing flights or nonfinite coordinates.')
    xyz = [unit_sphere(groups[fid]) for fid in ids]
    trees = [cKDTree(a) for a in xyz]
    matrix = np.zeros((len(ids), len(ids)), dtype=np.float64)
    pairs, done = len(ids) * (len(ids) - 1) // 2, 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            matrix[i, j] = matrix[j, i] = hausdorff_km(xyz[i], xyz[j], trees[i], trees[j])
            done += 1
        if i % 20 == 0 or i == len(ids) - 1:
            print(f'Distance pairs: {done}/{pairs}', flush=True)
    assert np.isfinite(matrix).all() and (matrix >= 0).all()
    assert np.allclose(matrix, matrix.T) and np.all(np.diag(matrix) == 0)
    # Check several actual full-flight pairs against the independent dense implementation.
    from sklearn.metrics.pairwise import haversine_distances
    validation = []
    for i, j in [(0, 1), (0, len(ids) - 1), (len(ids) // 2, len(ids) - 1)]:
        dense = haversine_distances(np.radians(groups[ids[i]]), np.radians(groups[ids[j]])) * EARTH_KM
        reference = max(dense.min(axis=0).max(), dense.min(axis=1).max())
        error = abs(float(reference) - matrix[i, j])
        if error > 1e-7:
            raise AssertionError(f'Dense reference mismatch: {error} km')
        validation.append(dict(i=i, j=j, absolute_error_km=error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.save(args.output_dir / 'hausdorff_distance_matrix_km.npy', matrix)
    pd.DataFrame(matrix, index=ids, columns=ids).rename_axis('flight_id').to_csv(args.output_dir / 'hausdorff_distance_matrix_km.csv')
    pd.DataFrame({'matrix_index': np.arange(len(ids)), 'flight_id': ids}).to_csv(args.output_dir / 'hausdorff_flight_ids.csv', index=False)
    report = dict(matrix_shape=list(matrix.shape), flights=len(ids), points=len(d),
                  metric='symmetric point-set Hausdorff using spherical great-circle distance (km)',
                  method='exact KD-tree nearest neighbours on unit-sphere XYZ; chord converted to arc',
                  interpolation=False, downsampling=False, earth_radius_km=EARTH_KM,
                  diagonal_max_abs_km=float(np.abs(np.diag(matrix)).max()),
                  symmetry_max_abs_diff_km=float(np.abs(matrix - matrix.T).max()),
                  dense_reference_checks=validation, elapsed_seconds=time.perf_counter() - start,
                  clean_points_sha256=hashlib.sha256(points_path.read_bytes()).hexdigest(),
                  limitation='Compares observed horizontal geometry; ignores time ordering, speed and altitude. Sensitive to residual position errors.')
    (args.output_dir / 'matrix_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT / 'data/lhr_fra_prepared')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/lhr_fra_hausdorff')
    run(parser.parse_args())
