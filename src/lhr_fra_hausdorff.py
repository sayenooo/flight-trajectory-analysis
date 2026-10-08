from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import haversine_distances


EARTH_RADIUS_KM = 6371.0088


@dataclass
class HausdorffReport:
    route: str
    representation: str
    input_file: str
    total_points: int
    total_flights: int
    median_points_per_flight: float
    matrix_shape: tuple[int, int]
    point_metric: str
    trajectory_metric: str
    earth_radius_km: float
    diagonal_max_abs_km: float
    symmetry_max_abs_diff_km: float
    pairwise_min_km: float
    pairwise_median_km: float
    pairwise_p95_km: float
    pairwise_max_km: float
    output_files: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a 2D Haversine-based symmetric Hausdorff distance matrix "
            "for the 30-second Lufthansa LHR-FRA trajectories."
        )
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("data/lhr_fra_downsampling/flight_points_30s.csv.gz"),
        help="30-second downsampled trajectory points.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/lhr_fra_hausdorff"),
        help="Directory for the LHR-FRA Hausdorff outputs.",
    )
    return parser.parse_args()


def normalize_columns(points: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Normalize coordinate/time column names used across repository stages."""
    df = points.copy()

    if "lat" not in df.columns and "latitude" in df.columns:
        df = df.rename(columns={"latitude": "lat"})
    if "lon" not in df.columns and "longitude" in df.columns:
        df = df.rename(columns={"longitude": "lon"})

    required = {"flight_id", "lat", "lon"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(
            f"Missing required columns: {sorted(missing)}. "
            f"Available columns: {list(df.columns)}"
        )

    time_col = None
    for candidate in (
        "lastposupdate",
        "point_time_unix",
        "time",
        "state_time_unix",
    ):
        if candidate in df.columns:
            time_col = candidate
            break

    if time_col is None:
        raise KeyError(
            "No trajectory time column found. Expected one of: "
            "lastposupdate, point_time_unix, time, state_time_unix."
        )

    return df, time_col


def prepare_trajectories(
    points: pd.DataFrame,
) -> tuple[dict[str, np.ndarray], pd.Series]:
    """Return one [lat, lon] trajectory per flight in radians.

    scikit-learn's haversine_distances requires:
      - exactly 2 dimensions,
      - order [latitude, longitude],
      - coordinates in radians.
    """
    df, time_col = normalize_columns(points)

    df["flight_id"] = df["flight_id"].astype(str)
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["flight_id", time_col, "lat", "lon"])
    df = df.loc[
        df["lat"].between(-90.0, 90.0)
        & df["lon"].between(-180.0, 180.0)
    ]

    if "sampling_interval_sec" in df.columns:
        observed_intervals = sorted(
            set(pd.to_numeric(df["sampling_interval_sec"], errors="coerce").dropna())
        )
        if observed_intervals and observed_intervals != [30]:
            raise ValueError(
                "This script expects the final 30-second dataset, but found "
                f"sampling_interval_sec values: {observed_intervals}"
            )

    df = (
        df.sort_values(["flight_id", time_col])
        .drop_duplicates(subset=["flight_id", time_col, "lat", "lon"])
        .reset_index(drop=True)
    )

    trajectories: dict[str, np.ndarray] = {}
    point_counts: dict[str, int] = {}

    for flight_id, group in df.groupby("flight_id", sort=True):
        coords_deg = group[["lat", "lon"]].to_numpy(dtype=float)

        if len(coords_deg) < 2:
            raise ValueError(
                f"Flight {flight_id!r} has fewer than two valid trajectory points."
            )

        trajectories[str(flight_id)] = np.radians(coords_deg)
        point_counts[str(flight_id)] = len(coords_deg)

    if not trajectories:
        raise ValueError("No valid trajectories were found.")

    return trajectories, pd.Series(point_counts, name="point_count", dtype=int)


def symmetric_hausdorff_haversine_km(
    trajectory_a_rad: np.ndarray,
    trajectory_b_rad: np.ndarray,
) -> float:
    """Symmetric discrete Hausdorff distance with Haversine point distances.

    h(A,B) = max_a min_b d_Haversine(a,b)
    h(B,A) = max_b min_a d_Haversine(b,a)
    H(A,B) = max(h(A,B), h(B,A))

    sklearn.metrics.pairwise.haversine_distances returns angular distances.
    Multiplication by mean Earth radius converts radians to kilometers.
    """
    pairwise_angular = haversine_distances(
        trajectory_a_rad,
        trajectory_b_rad,
    )
    pairwise_km = pairwise_angular * EARTH_RADIUS_KM

    directed_a_to_b = float(np.max(np.min(pairwise_km, axis=1)))
    directed_b_to_a = float(np.max(np.min(pairwise_km, axis=0)))

    return max(directed_a_to_b, directed_b_to_a)


def build_distance_matrix(
    trajectories: dict[str, np.ndarray],
) -> tuple[list[str], np.ndarray]:
    flight_ids = list(trajectories.keys())
    n = len(flight_ids)
    matrix = np.zeros((n, n), dtype=np.float64)

    total_pairs = n * (n - 1) // 2
    completed = 0

    print(f"Flights: {n}")
    print(f"Unique trajectory pairs: {total_pairs:,}")
    print("Computing 2D Haversine-based symmetric Hausdorff distances...")

    for i in range(n):
        a = trajectories[flight_ids[i]]

        for j in range(i + 1, n):
            b = trajectories[flight_ids[j]]

            distance_km = symmetric_hausdorff_haversine_km(a, b)
            matrix[i, j] = distance_km
            matrix[j, i] = distance_km

            completed += 1
            if completed % 500 == 0 or completed == total_pairs:
                print(
                    f"  {completed:,}/{total_pairs:,} pairs "
                    f"({completed / total_pairs:.1%})"
                )

    return flight_ids, matrix


def validate_matrix(matrix: np.ndarray) -> tuple[float, float]:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Hausdorff distance matrix must be square.")

    if not np.isfinite(matrix).all():
        raise ValueError("Distance matrix contains NaN or infinite values.")

    if (matrix < 0).any():
        raise ValueError("Distance matrix contains negative distances.")

    diagonal_max = float(np.max(np.abs(np.diag(matrix))))
    symmetry_max = float(np.max(np.abs(matrix - matrix.T)))

    if diagonal_max > 1e-10:
        raise ValueError(f"Non-zero diagonal detected: {diagonal_max} km")

    if symmetry_max > 1e-10:
        raise ValueError(f"Matrix is not symmetric: max diff {symmetry_max} km")

    return diagonal_max, symmetry_max


def pairwise_statistics(matrix: np.ndarray) -> tuple[float, float, float, float]:
    upper = matrix[np.triu_indices_from(matrix, k=1)]

    if len(upper) == 0:
        return 0.0, 0.0, 0.0, 0.0

    return (
        float(np.min(upper)),
        float(np.median(upper)),
        float(np.percentile(upper, 95)),
        float(np.max(upper)),
    )


def run(input_file: Path, output_dir: Path) -> HausdorffReport:
    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file}\n"
            "Run py src\\downsample_sensitivity.py first to create "
            "flight_points_30s.csv.gz."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    points = pd.read_csv(
        input_file,
        compression="infer",
        low_memory=False,
    )

    trajectories, point_counts = prepare_trajectories(points)

    flight_ids, matrix = build_distance_matrix(trajectories)
    diagonal_max, symmetry_max = validate_matrix(matrix)

    (
        pairwise_min,
        pairwise_median,
        pairwise_p95,
        pairwise_max,
    ) = pairwise_statistics(matrix)

    matrix_csv = output_dir / "hausdorff_distance_matrix_km.csv"
    matrix_npy = output_dir / "hausdorff_distance_matrix_km.npy"
    flight_ids_csv = output_dir / "hausdorff_flight_ids.csv"
    report_json = output_dir / "hausdorff_matrix_report.json"

    matrix_df = pd.DataFrame(
        matrix,
        index=flight_ids,
        columns=flight_ids,
    )
    matrix_df.index.name = "flight_id"
    matrix_df.to_csv(matrix_csv)

    np.save(matrix_npy, matrix)

    pd.DataFrame(
        {
            "matrix_index": np.arange(len(flight_ids), dtype=int),
            "flight_id": flight_ids,
            "point_count": [int(point_counts.loc[fid]) for fid in flight_ids],
        }
    ).to_csv(flight_ids_csv, index=False)

    report = HausdorffReport(
        route="EGLL (LHR) -> EDDF (FRA)",
        representation="2D horizontal trajectory: latitude and longitude only",
        input_file=str(input_file),
        total_points=int(sum(point_counts)),
        total_flights=len(flight_ids),
        median_points_per_flight=float(point_counts.median()),
        matrix_shape=(int(matrix.shape[0]), int(matrix.shape[1])),
        point_metric=(
            "sklearn.metrics.pairwise.haversine_distances "
            "on [latitude, longitude] in radians"
        ),
        trajectory_metric="symmetric discrete Hausdorff distance",
        earth_radius_km=EARTH_RADIUS_KM,
        diagonal_max_abs_km=diagonal_max,
        symmetry_max_abs_diff_km=symmetry_max,
        pairwise_min_km=pairwise_min,
        pairwise_median_km=pairwise_median,
        pairwise_p95_km=pairwise_p95,
        pairwise_max_km=pairwise_max,
        output_files={
            "matrix_csv": str(matrix_csv),
            "matrix_npy": str(matrix_npy),
            "flight_ids": str(flight_ids_csv),
            "report": str(report_json),
        },
    )

    report_json.write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )

    print("\nHausdorff matrix completed.")
    print(f"Matrix shape: {matrix.shape}")
    print(f"Pairwise median: {pairwise_median:.3f} km")
    print(f"Pairwise P95:    {pairwise_p95:.3f} km")
    print(f"Pairwise max:    {pairwise_max:.3f} km")
    print(f"Saved: {matrix_csv}")
    print(f"Saved: {matrix_npy}")
    print(f"Saved: {flight_ids_csv}")
    print(f"Saved: {report_json}")

    return report


def main() -> None:
    args = parse_args()
    run(
        input_file=args.input_file,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
