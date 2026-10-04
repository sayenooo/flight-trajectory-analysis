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
class HausdorffMatrixReport:
    input_file: str
    total_points: int
    total_flights: int
    matrix_shape: tuple[int, int]
    earth_radius_km: float
    distance_metric: str
    diagonal_max_abs_km: float
    symmetry_max_abs_diff_km: float
    output_files: dict[str, str]


def prepare_trajectories(points: pd.DataFrame) -> dict[str, np.ndarray]:
    """Group the final QC dataset into one [lat, lon] array per flight.

    Coordinates remain in degrees here. Conversion to radians is done immediately
    before calling scikit-learn's haversine_distances, as required by the API.
    """
    required = {"flight_id", "point_time_unix", "latitude", "longitude"}
    missing = required - set(points.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    clean = points.dropna(
        subset=["flight_id", "point_time_unix", "latitude", "longitude"]
    ).copy()
    clean = clean.sort_values(["flight_id", "point_time_unix"])

    trajectories: dict[str, np.ndarray] = {}
    for flight_id, group in clean.groupby("flight_id", sort=True):
        coords_deg = group[["latitude", "longitude"]].to_numpy(dtype=float)
        if len(coords_deg) < 2:
            raise ValueError(
                f"Flight {flight_id!r} has fewer than 2 valid trajectory points."
            )
        trajectories[str(flight_id)] = coords_deg

    if not trajectories:
        raise ValueError("No valid flight trajectories were found.")

    return trajectories


def haversine_hausdorff_km(
    trajectory_a_deg: np.ndarray,
    trajectory_b_deg: np.ndarray,
) -> float:
    """Compute symmetric Hausdorff distance using Haversine point distances.

    scikit-learn's haversine_distances expects [latitude, longitude] in radians
    and returns angular distance on a sphere. Multiplying by the mean Earth
    radius converts the result to kilometers.
    """
    a_rad = np.radians(trajectory_a_deg)
    b_rad = np.radians(trajectory_b_deg)

    pairwise_angular = haversine_distances(a_rad, b_rad)
    pairwise_km = pairwise_angular * EARTH_RADIUS_KM

    # Directed Hausdorff A -> B:
    # for every point in A, find its nearest point in B, then take the maximum.
    directed_a_to_b = float(np.max(np.min(pairwise_km, axis=1)))

    # Directed Hausdorff B -> A:
    # for every point in B, find its nearest point in A, then take the maximum.
    directed_b_to_a = float(np.max(np.min(pairwise_km, axis=0)))

    return max(directed_a_to_b, directed_b_to_a)


def build_hausdorff_matrix(
    trajectories: dict[str, np.ndarray],
) -> tuple[list[str], np.ndarray]:
    """Build a symmetric N x N Haversine-based Hausdorff distance matrix."""
    flight_ids = list(trajectories.keys())
    n = len(flight_ids)
    matrix = np.zeros((n, n), dtype=float)

    total_pairs = n * (n - 1) // 2
    completed_pairs = 0

    for i in range(n):
        a = trajectories[flight_ids[i]]
        for j in range(i + 1, n):
            b = trajectories[flight_ids[j]]
            distance_km = haversine_hausdorff_km(a, b)

            matrix[i, j] = distance_km
            matrix[j, i] = distance_km

            completed_pairs += 1
            if completed_pairs % 1000 == 0 or completed_pairs == total_pairs:
                print(
                    f"Computed {completed_pairs}/{total_pairs} trajectory pairs "
                    f"({completed_pairs / total_pairs:.1%})"
                )

    return flight_ids, matrix


def validate_distance_matrix(matrix: np.ndarray) -> tuple[float, float]:
    """Return simple numerical checks for HDBSCAN precomputed input."""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Distance matrix must be square.")

    if not np.isfinite(matrix).all():
        raise ValueError("Distance matrix contains NaN or infinite values.")

    if (matrix < 0).any():
        raise ValueError("Distance matrix contains negative distances.")

    diagonal_max = float(np.max(np.abs(np.diag(matrix))))
    symmetry_max = float(np.max(np.abs(matrix - matrix.T)))

    return diagonal_max, symmetry_max


def run(
    input_file: Path,
    output_dir: Path,
) -> HausdorffMatrixReport:
    output_dir.mkdir(parents=True, exist_ok=True)

    points = pd.read_csv(input_file)
    trajectories = prepare_trajectories(points)

    flight_ids, matrix = build_hausdorff_matrix(trajectories)
    diagonal_max, symmetry_max = validate_distance_matrix(matrix)

    matrix_csv_path = output_dir / "hausdorff_distance_matrix_km.csv"
    matrix_npy_path = output_dir / "hausdorff_distance_matrix_km.npy"
    flight_ids_path = output_dir / "hausdorff_flight_ids.csv"
    report_path = output_dir / "hausdorff_matrix_report.json"

    matrix_df = pd.DataFrame(matrix, index=flight_ids, columns=flight_ids)
    matrix_df.index.name = "flight_id"

    matrix_df.to_csv(matrix_csv_path)
    np.save(matrix_npy_path, matrix)
    pd.DataFrame(
        {
            "matrix_index": np.arange(len(flight_ids), dtype=int),
            "flight_id": flight_ids,
        }
    ).to_csv(flight_ids_path, index=False)

    report = HausdorffMatrixReport(
        input_file=str(input_file),
        total_points=int(len(points)),
        total_flights=int(len(flight_ids)),
        matrix_shape=(int(matrix.shape[0]), int(matrix.shape[1])),
        earth_radius_km=EARTH_RADIUS_KM,
        distance_metric=(
            "symmetric Hausdorff distance using "
            "sklearn.metrics.pairwise.haversine_distances"
        ),
        diagonal_max_abs_km=diagonal_max,
        symmetry_max_abs_diff_km=symmetry_max,
        output_files={
            "matrix_csv": str(matrix_csv_path),
            "matrix_npy": str(matrix_npy_path),
            "flight_ids": str(flight_ids_path),
            "report": str(report_path),
        },
    )

    report_path.write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an N x N symmetric Hausdorff distance matrix for flight "
            "trajectories using scikit-learn Haversine point-to-point distances."
        )
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("data/quality/flight_points_final.csv"),
        help="Final QC-approved point-level trajectory CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/hausdorff"),
        help="Directory for Hausdorff matrix outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run(
        input_file=args.input_file,
        output_dir=args.output_dir,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
