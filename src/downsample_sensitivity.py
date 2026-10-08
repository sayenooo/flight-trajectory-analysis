from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


EARTH_RADIUS_KM = 6371.0088


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare fixed-time trajectory downsampling intervals (10/30/60 s) "
            "for the Lufthansa LHR-FRA dataset without interpolation."
        )
    )
    parser.add_argument(
        "--points",
        type=Path,
        default=Path("data/lhr_fra_prepared/flight_points_clean.csv.gz"),
        help="Clean point-level trajectory file.",
    )
    parser.add_argument(
        "--accepted",
        type=Path,
        default=Path("data/lhr_fra_prepared/accepted_flights.csv"),
        help="CSV containing accepted flight_id values.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/lhr_fra_downsampling"),
        help="Directory for sensitivity outputs.",
    )
    parser.add_argument(
        "--intervals",
        type=int,
        nargs="+",
        default=[10, 30, 60],
        help="Sampling intervals in seconds.",
    )
    return parser.parse_args()


def choose_time_column(df: pd.DataFrame) -> str:
    # Prefer the timestamp that belongs directly to the stored trajectory point.
    # Different preprocessing stages in this repository use different names.
    for candidate in (
        "lastposupdate",
        "point_time_unix",
        "time",
        "state_time_unix",
    ):
        if candidate in df.columns:
            return candidate
    raise KeyError(
        "No usable trajectory timestamp found. Expected one of: "
        "lastposupdate, point_time_unix, time, state_time_unix."
    )


def normalize_coordinate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize repository coordinate naming to lat/lon."""
    out = df.copy()

    if "lat" not in out.columns and "latitude" in out.columns:
        out = out.rename(columns={"latitude": "lat"})
    if "lon" not in out.columns and "longitude" in out.columns:
        out = out.rename(columns={"longitude": "lon"})

    missing = {"lat", "lon"}.difference(out.columns)
    if missing:
        raise KeyError(
            "Missing coordinate columns after normalization. "
            f"Expected lat/lon or latitude/longitude; missing: {sorted(missing)}. "
            f"Available columns: {list(out.columns)}"
        )

    return out


def prepare_points(points: pd.DataFrame, accepted_ids: set[str]) -> tuple[pd.DataFrame, str]:
    if "flight_id" not in points.columns:
        raise KeyError(
            f"Missing required column: flight_id. Available columns: {list(points.columns)}"
        )

    points = normalize_coordinate_columns(points)
    time_col = choose_time_column(points)

    df = points.loc[points["flight_id"].astype(str).isin(accepted_ids)].copy()
    df["flight_id"] = df["flight_id"].astype(str)
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["flight_id", time_col, "lat", "lon"])
    df = df.loc[
        df["lat"].between(-90.0, 90.0)
        & df["lon"].between(-180.0, 180.0)
    ]

    df = (
        df.sort_values(["flight_id", time_col])
        .drop_duplicates(subset=["flight_id", time_col, "lat", "lon"])
        .reset_index(drop=True)
    )
    return df, time_col


def nearest_observed_indices(times: np.ndarray, interval_sec: int) -> tuple[np.ndarray, np.ndarray]:
    """Select actual observations nearest to regular target times.

    No interpolation, averaging, or synthetic coordinates are created.
    First and last observed points are always retained.
    """
    if len(times) == 0:
        return np.array([], dtype=int), np.array([], dtype=float)
    if len(times) == 1:
        return np.array([0], dtype=int), np.array([0.0], dtype=float)

    start = float(times[0])
    end = float(times[-1])
    targets = np.arange(start, end + 1e-9, float(interval_sec))

    right = np.searchsorted(times, targets, side="left")
    right = np.clip(right, 0, len(times) - 1)
    left = np.clip(right - 1, 0, len(times) - 1)

    left_diff = np.abs(times[left] - targets)
    right_diff = np.abs(times[right] - targets)
    chosen = np.where(right_diff < left_diff, right, left)

    # Time offsets are measured against every target before duplicate removal.
    target_offsets = np.minimum(left_diff, right_diff)

    selected = np.unique(np.concatenate(([0], chosen, [len(times) - 1]))).astype(int)
    return selected, target_offsets


def haversine_path_length_km(lat: np.ndarray, lon: np.ndarray) -> float:
    if len(lat) < 2:
        return 0.0

    lat1 = np.radians(lat[:-1])
    lat2 = np.radians(lat[1:])
    dlat = lat2 - lat1
    dlon = np.radians(lon[1:] - lon[:-1])

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    a = np.clip(a, 0.0, 1.0)
    central_angle = 2.0 * np.arcsin(np.sqrt(a))
    return float(EARTH_RADIUS_KM * central_angle.sum())


def symmetric_haversine_hausdorff_km(
    full_latlon: np.ndarray,
    sampled_latlon: np.ndarray,
) -> float:
    """Exact symmetric Hausdorff distance using great-circle point distance."""
    full_rad = np.radians(full_latlon)
    sampled_rad = np.radians(sampled_latlon)

    sampled_tree = BallTree(sampled_rad, metric="haversine")
    full_to_sampled = sampled_tree.query(full_rad, k=1, return_distance=True)[0][:, 0]

    full_tree = BallTree(full_rad, metric="haversine")
    sampled_to_full = full_tree.query(sampled_rad, k=1, return_distance=True)[0][:, 0]

    return float(
        max(float(full_to_sampled.max()), float(sampled_to_full.max()))
        * EARTH_RADIUS_KM
    )


def evaluate_interval(
    points: pd.DataFrame,
    time_col: str,
    interval_sec: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sampled_frames: list[pd.DataFrame] = []
    metrics: list[dict[str, float | int | str]] = []

    for flight_id, flight in points.groupby("flight_id", sort=False):
        flight = flight.sort_values(time_col).reset_index(drop=True)
        times = flight[time_col].to_numpy(dtype=float)

        selected_idx, target_offsets = nearest_observed_indices(times, interval_sec)
        sampled = flight.iloc[selected_idx].copy()
        sampled["sampling_interval_sec"] = interval_sec
        sampled_frames.append(sampled)

        full_lat = flight["lat"].to_numpy(dtype=float)
        full_lon = flight["lon"].to_numpy(dtype=float)
        sampled_lat = sampled["lat"].to_numpy(dtype=float)
        sampled_lon = sampled["lon"].to_numpy(dtype=float)

        full_path_km = haversine_path_length_km(full_lat, full_lon)
        sampled_path_km = haversine_path_length_km(sampled_lat, sampled_lon)
        if full_path_km > 0:
            path_abs_error_pct = abs(sampled_path_km - full_path_km) / full_path_km * 100.0
        else:
            path_abs_error_pct = np.nan

        metrics.append(
            {
                "interval_sec": interval_sec,
                "flight_id": flight_id,
                "full_points": len(flight),
                "sampled_points": len(sampled),
                "retention_pct": len(sampled) / len(flight) * 100.0,
                "hausdorff_km": symmetric_haversine_hausdorff_km(
                    flight[["lat", "lon"]].to_numpy(dtype=float),
                    sampled[["lat", "lon"]].to_numpy(dtype=float),
                ),
                "full_path_km": full_path_km,
                "sampled_path_km": sampled_path_km,
                "path_length_abs_error_pct": path_abs_error_pct,
                "median_target_time_offset_sec": float(np.median(target_offsets))
                if len(target_offsets)
                else np.nan,
                "p95_target_time_offset_sec": float(np.percentile(target_offsets, 95))
                if len(target_offsets)
                else np.nan,
                "max_target_time_offset_sec": float(np.max(target_offsets))
                if len(target_offsets)
                else np.nan,
            }
        )

    sampled_all = pd.concat(sampled_frames, ignore_index=True)
    metrics_df = pd.DataFrame(metrics)
    return sampled_all, metrics_df


def make_summary(per_flight: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []

    for interval_sec, group in per_flight.groupby("interval_sec", sort=True):
        full_points_total = int(group["full_points"].sum())
        sampled_points_total = int(group["sampled_points"].sum())

        rows.append(
            {
                "interval_sec": int(interval_sec),
                "flights": int(group["flight_id"].nunique()),
                "full_points_total": full_points_total,
                "sampled_points_total": sampled_points_total,
                "sampled_points_median": float(group["sampled_points"].median()),
                "retention_pct": sampled_points_total / full_points_total * 100.0,
                "point_reduction_pct": (1.0 - sampled_points_total / full_points_total) * 100.0,
                "hausdorff_median_km": float(group["hausdorff_km"].median()),
                "hausdorff_p95_km": float(group["hausdorff_km"].quantile(0.95)),
                "hausdorff_max_km": float(group["hausdorff_km"].max()),
                "path_length_abs_error_median_pct": float(
                    group["path_length_abs_error_pct"].median()
                ),
                "path_length_abs_error_p95_pct": float(
                    group["path_length_abs_error_pct"].quantile(0.95)
                ),
                "target_time_offset_median_sec": float(
                    group["median_target_time_offset_sec"].median()
                ),
                "target_time_offset_p95_sec": float(
                    group["p95_target_time_offset_sec"].quantile(0.95)
                ),
            }
        )

    return pd.DataFrame(rows).sort_values("interval_sec").reset_index(drop=True)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    accepted = pd.read_csv(args.accepted)
    if "flight_id" not in accepted.columns:
        raise KeyError("accepted_flights.csv must contain a flight_id column.")
    accepted_ids = set(accepted["flight_id"].dropna().astype(str))

    points = pd.read_csv(args.points, compression="infer", low_memory=False)
    points, time_col = prepare_points(points, accepted_ids)

    present_ids = set(points["flight_id"].unique())
    missing_ids = accepted_ids.difference(present_ids)
    if missing_ids:
        raise ValueError(
            f"{len(missing_ids)} accepted flights are missing from the point file."
        )

    all_metrics: list[pd.DataFrame] = []
    final_30s: pd.DataFrame | None = None

    for interval_sec in sorted(set(args.intervals)):
        sampled, metrics = evaluate_interval(points, time_col, interval_sec)
        all_metrics.append(metrics)

        # Only the 30-s product is kept as the candidate final clustering input.
        if interval_sec == 30:
            final_30s = sampled

    per_flight = pd.concat(all_metrics, ignore_index=True)
    summary = make_summary(per_flight)

    per_flight_path = args.output_dir / "downsampling_sensitivity_per_flight.csv"
    summary_path = args.output_dir / "downsampling_sensitivity_summary.csv"
    report_path = args.output_dir / "downsampling_report.json"

    per_flight.to_csv(per_flight_path, index=False)
    summary.to_csv(summary_path, index=False)

    final_30s_path = None
    if final_30s is not None:
        final_30s_path = args.output_dir / "flight_points_30s.csv.gz"
        final_30s.to_csv(final_30s_path, index=False, compression="gzip")

    report = {
        "route": "EGLL -> EDDF",
        "airline": "Lufthansa",
        "callsign": "DLH5H",
        "aircraft_type": "A20N",
        "input_points_file": str(args.points),
        "accepted_flights_file": str(args.accepted),
        "accepted_flights": len(accepted_ids),
        "timestamp_used_for_sampling": time_col,
        "intervals_sec": sorted(set(args.intervals)),
        "sampling_rule": (
            "For each regular target timestamp, retain the nearest actual observed "
            "position. Always retain the first and last observation. Duplicate selected "
            "observations are removed. No interpolation, averaging, or synthetic points."
        ),
        "geometry_check": (
            "Symmetric Hausdorff distance between the full accepted trajectory and each "
            "downsampled trajectory, using Haversine/great-circle point distance."
        ),
        "path_check": "Absolute relative difference in Haversine polyline path length.",
        "reference": (
            "Bolic et al. (2022), Trajectory Clustering for Air Traffic Categorisation, "
            "Aerospace 9(5), 227, DOI: 10.3390/aerospace9050227. "
            "The 30-s interval follows the paper; nearest-observation selection is this "
            "project's explicit implementation choice."
        ),
        "decision_guidance": (
            "Use the sensitivity table rather than a universal aviation threshold. "
            "Prefer 30 s if its geometric error remains close to 10 s while providing "
            "substantially greater point reduction, and if 60 s shows materially larger "
            "geometry/path distortion."
        ),
        "outputs": {
            "per_flight_metrics": str(per_flight_path),
            "summary": str(summary_path),
            "candidate_30s_points": str(final_30s_path) if final_30s_path else None,
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nDownsampling sensitivity summary")
    print(summary.to_string(index=False))
    print(f"\nSaved: {summary_path}")
    print(f"Saved: {per_flight_path}")
    print(f"Saved: {report_path}")
    if final_30s_path:
        print(f"Saved: {final_30s_path}")


if __name__ == "__main__":
    main()
