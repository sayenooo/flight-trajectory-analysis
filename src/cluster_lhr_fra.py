"""HDBSCAN baseline and parameter comparison for LHR -> FRA flights.

Run from the starter package: python src/cluster_lhr_fra.py
Requires scikit-learn >= 1.3 and the existing starter-package dependencies.
Uses sklearn.cluster.HDBSCAN, not the separate hdbscan package.
sklearn min_samples includes the flight itself; contrib/hdbscan excludes it.
Reference: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html
Prepared with ChatGPT/Codex assistance, 2026-10-07. Review before submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import HDBSCAN

ROOT = Path(__file__).resolve().parents[1]


def fit_model(distances, min_cluster_size, min_samples):
    # Rows/columns represent flights. The entries are distances, not features.
    # copy=True prevents fits in the parameter sweep from changing the input.
    return HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples,
        metric='precomputed', algorithm='brute', copy=True,
        cluster_selection_method='eom', allow_single_cluster=False,
    ).fit(distances)


def describe_labels(labels):
    clusters = sorted(int(x) for x in np.unique(labels) if x >= 0)
    sizes = {str(c): int((labels == c).sum()) for c in clusters}
    return clusters, sizes, int((labels == -1).sum())


def setup_axes(ax):
    ax.set(xlabel='Longitude (degrees)', ylabel='Latitude (degrees)')
    ax.set_aspect(1 / np.cos(np.radians(51)))
    ax.grid(alpha=.2)
    for name, lat, lon in [('LHR', 51.4706, -.4619), ('FRA', 50.038, 8.5622)]:
        ax.scatter(lon, lat, color='#182b49', s=22, zorder=5)
        ax.annotate(name, (lon, lat), xytext=(4, 5), textcoords='offset points', fontsize=9)


def plot_results(points, assignments, representatives, output_dir):
    groups = {fid: g for fid, g in points.groupby('flight_id', sort=False)}
    clusters = sorted(int(x) for x in assignments.cluster.unique() if x >= 0)
    colours = {c: plt.get_cmap('tab10')(c % 10) for c in clusters}
    medoids = dict(zip(representatives.cluster, representatives.medoid_flight_id))
    fig, ax = plt.subplots(figsize=(12, 6), layout='constrained')
    handles = []
    for c in [-1] + clusters:
        subset = assignments[assignments.cluster == c]
        if subset.empty:
            continue
        colour = '#777777' if c == -1 else colours[c]
        for fid in subset.flight_id:
            g = groups[fid]
            ax.plot(g.longitude, g.latitude, color=colour, alpha=.25, lw=.65)
        handles.append(Line2D([0], [0], color=colour, lw=2,
                             label=f'{"Noise" if c == -1 else "Cluster " + str(c)}: {len(subset)} flights'))
    for c, fid in medoids.items():
        g = groups[fid]
        ax.plot(g.longitude, g.latitude, color=colours[c], lw=2)
    setup_axes(ax)
    ax.set_title('LHR → FRA · HDBSCAN baseline\nBold lines are representative flights (medoids)')
    ax.legend(handles=handles, loc='upper right', fontsize=9)
    fig.savefig(output_dir / 'clusters_overview.png', dpi=170)
    plt.close(fig)

    panels = clusters + ([-1] if (assignments.cluster == -1).any() else [])
    fig, axes = plt.subplots((len(panels) + 1) // 2, 2, figsize=(13, 4.1 * ((len(panels) + 1) // 2)),
                             squeeze=False, sharex=True, sharey=True, layout='constrained')
    for ax, c in zip(axes.flat, panels):
        subset = assignments[assignments.cluster == c]
        colour = '#777777' if c == -1 else colours[c]
        for fid in subset.flight_id:
            g = groups[fid]
            ax.plot(g.longitude, g.latitude, color=colour, alpha=.35, lw=.6)
        if c in medoids:
            g = groups[medoids[c]]
            ax.plot(g.longitude, g.latitude, color='#172b4d', lw=2)
        setup_axes(ax)
        ax.set_title(f'{"Noise: review candidates" if c == -1 else "Cluster " + str(c)} · {len(subset)} flights')
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)
    fig.savefig(output_dir / 'clusters_separate.png', dpi=160)
    plt.close(fig)


def run(args):
    matrix_dir = args.project_dir / 'data/lhr_fra_hausdorff'
    prepared_dir = args.project_dir / 'data/lhr_fra_prepared'
    matrix_path = matrix_dir / 'hausdorff_distance_matrix_km.npy'
    distances = np.load(matrix_path, allow_pickle=False)
    ids_path = matrix_dir / 'hausdorff_flight_ids.csv'
    ids = pd.read_csv(ids_path)
    n = len(ids)
    if distances.shape != (n, n) or not ids.flight_id.is_unique:
        raise ValueError('Matrix shape or unique flight IDs do not match.')
    if not np.array_equal(ids.matrix_index.to_numpy(), np.arange(n)):
        raise ValueError('The flight-ID file is not in matrix order. Do not sort it separately.')
    if not np.isfinite(distances).all() or (distances < 0).any():
        raise ValueError('Matrix contains missing, infinite, or negative values.')
    if not np.allclose(distances, distances.T, atol=1e-8, rtol=0) or not np.allclose(np.diag(distances), 0, atol=1e-8):
        raise ValueError('Matrix must be symmetric with a zero diagonal.')
    accepted = pd.read_csv(prepared_dir / 'accepted_flights.csv')
    if not accepted.flight_id.is_unique or set(accepted.flight_id) != set(ids.flight_id):
        raise ValueError('The matrix does not match the accepted flight list. Rebuild it.')
    qc = pd.read_csv(prepared_dir / 'flight_qc.csv')
    if not qc.flight_id.is_unique:
        raise ValueError('Duplicate flight IDs in quality report.')
    if not 2 <= args.min_cluster_size <= n or not 1 <= args.min_samples <= n:
        raise ValueError('Parameters exceed the available flight count.')
    original = distances.copy()
    model = fit_model(distances, args.min_cluster_size, args.min_samples)
    clusters, sizes, noise = describe_labels(model.labels_)
    labels = ids.copy()
    labels['cluster'] = model.labels_
    labels['membership_strength'] = model.probabilities_
    labels = labels.merge(qc[['flight_id', 'date']], on='flight_id', how='left', validate='one_to_one').sort_values('matrix_index')
    if labels.date.isna().any():
        raise ValueError('Some matrix flights are missing from the QC report.')

    rows = []
    for c in clusters:
        members = np.flatnonzero(model.labels_ == c)
        within = distances[np.ix_(members, members)]
        medoid = members[np.argmin(within.sum(axis=1))]
        member_distances = distances[medoid, members]
        rows.append(dict(cluster=c, flights=len(members), medoid_flight_id=ids.flight_id.iloc[medoid],
                         medoid_matrix_index=int(medoid),
                         median_distance_to_medoid_km=float(np.median(member_distances)),
                         max_distance_to_medoid_km=float(member_distances.max())))
    representatives = pd.DataFrame(rows, columns=['cluster', 'flights', 'medoid_flight_id', 'medoid_matrix_index',
                                                    'median_distance_to_medoid_km', 'max_distance_to_medoid_km'])

    # Compare preset values, without automatically picking a winning configuration.
    grid = sorted({(c, s) for c in [5, 10, 15, 20, 30] for s in [5, 10, 15]
                   if c <= n and s <= n} | {(args.min_cluster_size, args.min_samples)})
    sweep, label_grid, noise_counts = [], ids.copy(), np.zeros(n, dtype=int)
    for c, s in grid:
        fitted = model if (c, s) == (args.min_cluster_size, args.min_samples) else fit_model(distances, c, s)
        group_ids, counts, n_noise = describe_labels(fitted.labels_)
        sweep.append(dict(min_cluster_size=c, min_samples=s, clusters=len(group_ids),
                          noise_flights=n_noise, noise_percent=100 * n_noise / n,
                          cluster_sizes=json.dumps(counts)))
        label_grid[f'mcs_{c}_ms_{s}'] = fitted.labels_
        noise_counts += fitted.labels_ == -1
    labels['noise_fraction_across_grid'] = noise_counts / len(grid)
    candidates = labels.loc[labels.cluster.eq(-1)].copy()
    if len(representatives):
        medoid_indices = representatives.medoid_matrix_index.to_numpy(dtype=int)
        candidates['nearest_cluster_medoid_distance_km'] = distances[
            np.ix_(candidates.matrix_index.to_numpy(dtype=int), medoid_indices)].min(axis=1)
        candidates = candidates.sort_values(['noise_fraction_across_grid', 'nearest_cluster_medoid_distance_km'], ascending=False)
    if not np.array_equal(distances, original):
        raise AssertionError('Fitting changed the original distance matrix.')

    print(f'Reading trajectory coordinates for plots ({n} flights)...', flush=True)
    points = pd.read_csv(prepared_dir / 'flight_points_clean.csv.gz',
                         usecols=['flight_id', 'point_time_unix', 'latitude', 'longitude'])
    points = points[points.flight_id.isin(ids.flight_id)].sort_values(['flight_id', 'point_time_unix'])
    counts = points.groupby('flight_id').size().reindex(ids.flight_id)
    expected_counts = qc.set_index('flight_id').clean_points.reindex(ids.flight_id)
    if counts.isna().any() or not np.array_equal(counts.to_numpy(), expected_counts.to_numpy()):
        raise ValueError('Cleaned points and quality report have inconsistent flight counts.')
    output_dir = args.project_dir / 'data' / f'lhr_fra_hdbscan_mcs{args.min_cluster_size}_ms{args.min_samples}'
    output_dir.mkdir(parents=True, exist_ok=True)
    labels.to_csv(output_dir / 'flight_clusters.csv', index=False)
    representatives.to_csv(output_dir / 'cluster_representatives.csv', index=False)
    candidates.to_csv(output_dir / 'noise_candidates.csv', index=False)
    pd.DataFrame(sweep).to_csv(output_dir / 'parameter_comparison.csv', index=False)
    label_grid.to_csv(output_dir / 'parameter_labels.csv', index=False)
    plot_results(points, labels, representatives, output_dir)
    report = dict(
        implementation='sklearn.cluster.HDBSCAN', sklearn_version=sklearn.__version__,
        min_cluster_size=args.min_cluster_size, min_samples=args.min_samples,
        min_samples_includes_self=True, metric='precomputed', cluster_selection_method='eom',
        allow_single_cluster=False, flights=n, clusters=len(clusters), cluster_sizes=sizes,
        noise_flights=noise, noise_percent=100 * noise / n, parameter_settings=len(grid),
        matrix_sha256=hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        flight_id_file_sha256=hashlib.sha256(ids_path.read_bytes()).hexdigest(),
        representative_method='Real flight minimizing the sum of within-cluster Hausdorff distances (unweighted medoid).',
        output_dir=str(output_dir),
        interpretation=[
            'This is a baseline, not an automatically selected optimal model.',
            'Label -1 means density-based noise, not a confirmed operational anomaly.',
            'Membership strength and noise frequency are not probabilities of a dangerous or abnormal flight.',
            'The grid includes the baseline; noise frequency is a descriptive sensitivity check, not independent validation.',
            'Cluster numbers are arbitrary and need not match across parameter settings or library versions.',
            'Quality-review flights are excluded before clustering and differ from HDBSCAN noise flights.',
            'Review held-flight selection bias, residual coordinate errors and real route shapes before interpreting anomalies.',
        ],
    )
    (output_dir / 'clustering_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, default=ROOT)
    parser.add_argument('--min-cluster-size', type=int, default=15)
    parser.add_argument('--min-samples', type=int, default=5)
    run(parser.parse_args())
