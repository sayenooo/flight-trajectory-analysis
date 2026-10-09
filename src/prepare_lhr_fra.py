"""Prepare auditable, horizontal LHR -> FRA trajectories; never change raw data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EARTH_KM = 6371.0088
# Approximate airport centres, used with a deliberately broad 15 km radius.
LHR = (51.4706, -0.4619)
FRA = (50.038, 8.5622)


def haversine(a, b):
    """Great-circle distance in km; inputs end in [latitude, longitude]."""
    a, b = np.radians(a), np.radians(b)
    h = np.sin((a[..., 0] - b[..., 0]) / 2) ** 2
    h += np.cos(a[..., 0]) * np.cos(b[..., 0]) * np.sin((a[..., 1] - b[..., 1]) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def find_short_spikes(coords, times, speed_mps=450, tolerance_km=2, max_burst=5):
    """Remove only short, physically inconsistent excursions with a valid bridge.

    Both surrounding legs must exceed the speed envelope plus tolerance.
    Every removed point must be unreachable from BOTH retained neighbours.
    The bridge spans at most 60 seconds. No coordinates are interpolated.
    Unresolved jumps are left for flight-level review instead of guessed away.
    """
    keep = np.ones(len(times), dtype=bool)
    for _ in range(10):
        ids = np.flatnonzero(keep)
        t, c = times[ids], coords[ids]
        bad = haversine(c[:-1], c[1:]) > speed_mps / 1000 * np.diff(t) + tolerance_km
        removed = False
        for left in np.flatnonzero(bad):
            for count in range(1, max_burst + 1):
                right = left + count + 1
                if right >= len(t):
                    break
                if not 0 < t[right] - t[left] <= 60:
                    continue
                allowed = speed_mps / 1000 * (t[right] - t[left]) + tolerance_km
                if haversine(c[left], c[right]) > allowed:
                    continue
                middle = slice(left + 1, right)
                from_left = haversine(c[middle], c[left]) > speed_mps / 1000 * (t[middle] - t[left]) + tolerance_km
                from_right = haversine(c[middle], c[right]) > speed_mps / 1000 * (t[right] - t[middle]) + tolerance_km
                if np.all(from_left & from_right):
                    keep[ids[middle]] = False
                    removed = True
                    break
            if removed:
                break  # Recalculate neighbours after each change.
        if not removed:
            break
    return ~keep


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.points.open('rb') as f:
        signature = f.read(80)
    if signature.startswith(b'version https://git-lfs.github.com/spec'):
        raise ValueError('This is a Git LFS pointer. Run git lfs pull to download the real CSV.')
    columns = ['flight_id', 'icao24', 'callsign', 'time', 'lat', 'lon', 'lastposupdate', 'lastcontact']
    d = pd.read_csv(args.points, usecols=columns)
    d['source_csv_line'] = np.arange(len(d)) + 2
    meta = pd.read_csv(args.flight_list).set_index('flight_id')
    if not meta.index.is_unique or set(d.flight_id) != set(meta.index):
        raise ValueError('Flight IDs are missing, extra, or duplicated in the flight list.')
    if not ((meta.departure == 'EGLL') & (meta.arrival == 'EDDF')).all():
        raise ValueError('The flight list must contain only EGLL -> EDDF.')
    if not ((meta.callsign.str.strip() == 'DLH5H') & (meta.typecode == 'A20N')).all():
        raise ValueError('Expected the DLH5H / A20N flight list.')
    d['state_time_unix'] = pd.to_datetime(d.time, utc=True, errors='raise').astype('int64') / 1e9
    d['position_age_sec'] = d.state_time_unix - d.lastposupdate
    d['contact_age_sec'] = d.state_time_unix - d.lastcontact
    d['removal_reason'] = ''

    def reject(mask, reason):
        d.loc[mask & d.removal_reason.eq(''), 'removal_reason'] = reason

    reject(~d.lat.between(-90, 90) | ~d.lon.between(-180, 180), 'invalid_coordinate')
    reject(~d.position_age_sec.between(0, args.max_age_sec), 'stale_or_invalid_position_time')
    reject(~d.contact_age_sec.between(0, args.max_age_sec), 'stale_or_invalid_contact_time')
    reject(d.icao24 != d.flight_id.map(meta.icao24), 'aircraft_mismatch')
    start, end = d.flight_id.map(meta.start_unix), d.flight_id.map(meta.end_unix)
    reject(~d.state_time_unix.between(start, end + 1), 'outside_flight_interval')
    d = d.sort_values(['flight_id', 'lastposupdate', 'state_time_unix'])
    valid = d.removal_reason.eq('')
    duplicate_indices = d.loc[valid].loc[d.loc[valid].duplicated(['flight_id', 'lastposupdate'])].index
    d.loc[duplicate_indices, 'removal_reason'] = 'duplicate_position_update'
    for _, g in d.loc[d.removal_reason.eq('')].groupby('flight_id', sort=True):
        spike = find_short_spikes(g[['lat', 'lon']].to_numpy(), g.lastposupdate.to_numpy())
        d.loc[g.index[spike], 'removal_reason'] = 'short_position_spike'

    removed = d.loc[d.removal_reason.ne('')].copy()
    clean = d.loc[d.removal_reason.eq('')].copy()
    summaries = []
    original_counts = d.groupby('flight_id').size()
    for flight_id, g in clean.groupby('flight_id', sort=True):
        xy, t = g[['lat', 'lon']].to_numpy(), g.lastposupdate.to_numpy()
        gap = np.diff(t)
        steps = haversine(xy[:-1], xy[1:])
        unresolved = int((steps > .450 * gap + 2).sum())
        start_distance = float(haversine(xy[0], np.array(LHR)))
        end_distance = float(haversine(xy[-1], np.array(FRA)))
        reasons = []
        if len(g) < 100:
            reasons.append('too_few_points')
        max_gap = float(gap.max()) if len(gap) else float('inf')
        if max_gap > args.max_gap_sec:
            reasons.append('gap_over_limit')
        if start_distance > 15 or end_distance > 15:
            reasons.append('endpoint_outside_15km')
        if unresolved:
            reasons.append('unresolved_position_jump')
        summaries.append(dict(
            flight_id=flight_id, date=meta.loc[flight_id, 'date'],
            raw_points=int(original_counts[flight_id]), clean_points=len(g),
            removed_points=int(original_counts[flight_id] - len(g)),
            max_gap_sec=max_gap, median_gap_sec=float(np.median(gap)) if len(gap) else None,
            observed_duration_min=float((t[-1] - t[0]) / 60),
            start_distance_km=start_distance, end_distance_km=end_distance,
            unresolved_jump_segments=unresolved,
            status='review' if reasons else 'pass', review_reason=';'.join(reasons),
        ))
    # Never silently omit a flight whose entire point set failed cleaning.
    represented = {x['flight_id'] for x in summaries}
    for flight_id in meta.index.difference(list(represented)):
        summaries.append(dict(flight_id=flight_id, date=meta.loc[flight_id, 'date'],
                              raw_points=int(original_counts[flight_id]), clean_points=0,
                              removed_points=int(original_counts[flight_id]),
                              status='review', review_reason='no_valid_points'))
    qc = pd.DataFrame(summaries).sort_values('flight_id')
    clean = clean.rename(columns={'lat': 'latitude', 'lon': 'longitude', 'lastposupdate': 'point_time_unix'})
    output_columns = ['flight_id', 'source_csv_line', 'point_time_unix', 'latitude', 'longitude',
                      'state_time_unix', 'position_age_sec', 'contact_age_sec']
    clean[output_columns].to_csv(args.output_dir / 'flight_points_clean.csv.gz', index=False)
    removed.to_csv(args.output_dir / 'removed_points.csv', index=False)
    qc.to_csv(args.output_dir / 'flight_qc.csv', index=False)
    qc.loc[qc.status.eq('pass'), ['flight_id']].to_csv(args.output_dir / 'accepted_flights.csv', index=False)
    if len(clean) + len(removed) != len(d):
        raise AssertionError('Row reconciliation failed.')
    expected = d.callsign.fillna('').str.strip()
    sha = hashlib.sha256()
    with args.points.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            sha.update(block)
    report = dict(
        route='EGLL -> EDDF', callsign='DLH5H', aircraft_type='A20N',
        source_file=args.points.name, source_sha256=sha.hexdigest(),
        source_repository_commit=('3ed740bcaaad81d22a5de6626eac7fa2d5a54b1f'
                                  if sha.hexdigest() == '3848f3829e19848eb025df79b1ca7642cb2298ed4bfb75526de70dd3d4fbe858'
                                  else None),
        raw_points=len(d), clean_points=len(clean), removed_points=len(removed),
        removal_reasons=removed.removal_reason.value_counts().to_dict(),
        input_flights=len(meta), accepted_flights=int(qc.status.eq('pass').sum()),
        review_flights=int(qc.status.eq('review').sum()),
        review_reasons=qc.loc[qc.status.eq('review'), 'review_reason'].value_counts().to_dict(),
        accepted_points=int(qc.loc[qc.status.eq('pass'), 'clean_points'].sum()),
        accepted_worst_gap_sec=float(qc.loc[qc.status.eq('pass'), 'max_gap_sec'].max()),
        missing_callsign_rows=int(expected.eq('').sum()),
        unexpected_callsign_rows=int((~expected.isin(['', 'DLH5H'])).sum()),
        parameters=dict(max_age_sec=args.max_age_sec, max_gap_sec=args.max_gap_sec,
                        airport_radius_km=15, spike_speed_envelope_mps=450,
                        spike_tolerance_km=2, max_spike_burst_points=5,
                        max_spike_bridge_sec=60, min_points=100),
        notes=[
            'Thresholds are project choices, not aviation standards; assess sensitivity later.',
            'Review flights remain in the cleaned file, but are excluded from the baseline matrix.',
            'No smoothing, interpolation, synthetic points, altitude filtering, or route-corridor clipping.',
            'Horizontal coordinates only; altitude and speed are not clustering features.',
            'Callsigns are diagnostic; flight ID and aircraft address define membership.',
            'These are observed trajectory intervals, not independently verified takeoff/landing times.',
        ],
    )
    (args.output_dir / 'preparation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    plot_routes(clean, qc, args.output_dir)
    print(json.dumps(report, indent=2), flush=True)
    return report


def plot_routes(clean, qc, output_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    passed = set(qc.loc[qc.status.eq('pass'), 'flight_id'])
    fig, ax = plt.subplots(figsize=(11, 5.4), layout='constrained')
    for flight_id, g in clean.groupby('flight_id', sort=True):
        if flight_id in passed:
            ax.plot(g.longitude, g.latitude, color='#247b92', alpha=.12, lw=.45)
    for name, (lat, lon) in [('LHR', LHR), ('FRA', FRA)]:
        ax.scatter(lon, lat, s=36, color='#172b4d', zorder=5)
        ax.annotate(name, (lon, lat), xytext=(6, 7), textcoords='offset points', fontweight='bold')
    ax.set(title=f'LHR → FRA · {len(passed)} flights passing baseline quality rules',
           xlabel='Longitude (degrees)', ylabel='Latitude (degrees)')
    ax.set_aspect(1 / np.cos(np.radians(51)))
    ax.grid(alpha=.2)
    fig.savefig(output_dir / 'accepted_trajectories.png', dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--points', type=Path, default=ROOT / 'data/lhr_fra_2025/DLH5H_A20N_2025_ALL_POSITION_POINTS.csv')
    parser.add_argument('--flight-list', type=Path, default=ROOT / 'data/lhr_fra_2025/DLH5H_A20N_2025_FLIGHT_LIST.csv')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/lhr_fra_prepared')
    parser.add_argument('--max-age-sec', type=float, default=15)
    parser.add_argument('--max-gap-sec', type=float, default=60)
    args = parser.parse_args()
    if args.max_age_sec <= 0 or args.max_gap_sec <= 0:
        parser.error('Age and gap limits must be positive.')
    run(args)
