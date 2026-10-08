from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import haversine_distances


EARTH_RADIUS_KM = 6371.0088


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visual QC for the largest LHR-FRA Hausdorff distances. "
            "Plots the most distant trajectory pairs and the point pair that "
            "realizes the symmetric Hausdorff distance."
        )
    )
    parser.add_argument(
        "--points",
        type=Path,
        default=Path("data/lhr_fra_downsampling/flight_points_30s.csv.gz"),
        help="30-second trajectory point file.",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("data/lhr_fra_hausdorff/hausdorff_distance_matrix_km.npy"),
        help="Precomputed Hausdorff matrix (.npy preferred, .csv also supported).",
    )
    parser.add_argument(
        "--flight-ids",
        type=Path,
        default=Path("data/lhr_fra_hausdorff/hausdorff_flight_ids.csv"),
        help="Matrix index to flight_id mapping.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/lhr_fra_visual_qc"),
        help="Output directory for QC plots and tables.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of largest Hausdorff pairs to inspect.",
    )
    return parser.parse_args()


def normalize_points(points: pd.DataFrame) -> tuple[pd.DataFrame, str]:
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
        raise KeyError("No usable trajectory time column found.")

    df["flight_id"] = df["flight_id"].astype(str)
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["flight_id", time_col, "lat", "lon"])
    df = df.loc[
        df["lat"].between(-90.0, 90.0)
        & df["lon"].between(-180.0, 180.0)
    ]
    df = df.sort_values(["flight_id", time_col]).reset_index(drop=True)

    return df, time_col


def load_matrix(matrix_path: Path, flight_ids_path: Path) -> tuple[np.ndarray, list[str]]:
    ids = pd.read_csv(flight_ids_path)
    if "flight_id" not in ids.columns:
        raise KeyError("hausdorff_flight_ids.csv must contain flight_id.")

    if "matrix_index" in ids.columns:
        ids = ids.sort_values("matrix_index")

    flight_ids = ids["flight_id"].astype(str).tolist()

    if matrix_path.suffix.lower() == ".npy":
        matrix = np.load(matrix_path)
    else:
        matrix_df = pd.read_csv(matrix_path, index_col=0)
        matrix = matrix_df.to_numpy(dtype=float)

    if matrix.shape != (len(flight_ids), len(flight_ids)):
        raise ValueError(
            f"Matrix shape {matrix.shape} does not match "
            f"{len(flight_ids)} flight IDs."
        )

    return matrix, flight_ids


def top_pairs(matrix: np.ndarray, flight_ids: list[str], top_n: int) -> pd.DataFrame:
    i_idx, j_idx = np.triu_indices_from(matrix, k=1)
    distances = matrix[i_idx, j_idx]

    order = np.argsort(distances)[::-1][:top_n]

    return pd.DataFrame(
        {
            "rank": np.arange(1, len(order) + 1),
            "matrix_i": i_idx[order],
            "matrix_j": j_idx[order],
            "flight_a": [flight_ids[i] for i in i_idx[order]],
            "flight_b": [flight_ids[j] for j in j_idx[order]],
            "hausdorff_km": distances[order],
        }
    )


def hausdorff_witness(
    trajectory_a_deg: np.ndarray,
    trajectory_b_deg: np.ndarray,
) -> dict[str, object]:
    a_rad = np.radians(trajectory_a_deg)
    b_rad = np.radians(trajectory_b_deg)

    d_km = haversine_distances(a_rad, b_rad) * EARTH_RADIUS_KM

    # A -> B directed Hausdorff witness
    a_nearest_b = np.argmin(d_km, axis=1)
    a_min_dist = d_km[np.arange(len(a_rad)), a_nearest_b]
    a_source_idx = int(np.argmax(a_min_dist))
    a_target_idx = int(a_nearest_b[a_source_idx])
    a_to_b = float(a_min_dist[a_source_idx])

    # B -> A directed Hausdorff witness
    b_nearest_a = np.argmin(d_km, axis=0)
    b_min_dist = d_km[b_nearest_a, np.arange(len(b_rad))]
    b_source_idx = int(np.argmax(b_min_dist))
    b_target_idx = int(b_nearest_a[b_source_idx])
    b_to_a = float(b_min_dist[b_source_idx])

    if a_to_b >= b_to_a:
        source_flight = "A"
        source_idx = a_source_idx
        target_flight = "B"
        target_idx = a_target_idx
        witness_distance = a_to_b
        source_point = trajectory_a_deg[source_idx]
        target_point = trajectory_b_deg[target_idx]
    else:
        source_flight = "B"
        source_idx = b_source_idx
        target_flight = "A"
        target_idx = b_target_idx
        witness_distance = b_to_a
        source_point = trajectory_b_deg[source_idx]
        target_point = trajectory_a_deg[target_idx]

    return {
        "directed_a_to_b_km": a_to_b,
        "directed_b_to_a_km": b_to_a,
        "source_flight": source_flight,
        "source_index": source_idx,
        "target_flight": target_flight,
        "target_index": target_idx,
        "witness_distance_km": witness_distance,
        "source_lat": float(source_point[0]),
        "source_lon": float(source_point[1]),
        "target_lat": float(target_point[0]),
        "target_lon": float(target_point[1]),
    }


def set_geographic_aspect(ax: plt.Axes, latitudes: np.ndarray) -> None:
    mean_lat = float(np.mean(latitudes))
    cos_lat = np.cos(np.radians(mean_lat))
    if cos_lat > 1e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def plot_pair(
    group_a: pd.DataFrame,
    group_b: pd.DataFrame,
    pair_row: pd.Series,
    witness: dict[str, object],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))

    ax.plot(
        group_a["lon"],
        group_a["lat"],
        linewidth=1.8,
        label=f"A: {pair_row['flight_a']}",
    )
    ax.plot(
        group_b["lon"],
        group_b["lat"],
        linewidth=1.8,
        label=f"B: {pair_row['flight_b']}",
    )

    # Start/end markers for both flights.
    ax.scatter(group_a["lon"].iloc[0], group_a["lat"].iloc[0], marker="o", s=45)
    ax.scatter(group_a["lon"].iloc[-1], group_a["lat"].iloc[-1], marker="s", s=45)
    ax.scatter(group_b["lon"].iloc[0], group_b["lat"].iloc[0], marker="o", s=45)
    ax.scatter(group_b["lon"].iloc[-1], group_b["lat"].iloc[-1], marker="s", s=45)

    # Hausdorff witness points and connecting segment.
    source_lon = float(witness["source_lon"])
    source_lat = float(witness["source_lat"])
    target_lon = float(witness["target_lon"])
    target_lat = float(witness["target_lat"])

    ax.scatter(source_lon, source_lat, marker="X", s=120, zorder=5, label="Hausdorff witness")
    ax.scatter(target_lon, target_lat, marker="X", s=120, zorder=5)
    ax.plot(
        [source_lon, target_lon],
        [source_lat, target_lat],
        linestyle="--",
        linewidth=1.4,
        zorder=4,
    )

    all_lat = np.concatenate(
        [
            group_a["lat"].to_numpy(dtype=float),
            group_b["lat"].to_numpy(dtype=float),
        ]
    )
    set_geographic_aspect(ax, all_lat)

    ax.set_xlabel("Longitude [deg]")
    ax.set_ylabel("Latitude [deg]")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)

    ax.set_title(
        f"Visual QC rank {int(pair_row['rank'])}: "
        f"Hausdorff = {float(pair_row['hausdorff_km']):.3f} km\n"
        f"Witness: {witness['source_flight']} -> {witness['target_flight']} "
        f"= {float(witness['witness_distance_km']):.3f} km"
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_max_pair_context(
    all_points: pd.DataFrame,
    group_a: pd.DataFrame,
    group_b: pd.DataFrame,
    pair_row: pd.Series,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))

    # All accepted 30-s trajectories as context.
    for _, group in all_points.groupby("flight_id", sort=False):
        ax.plot(group["lon"], group["lat"], linewidth=0.45, alpha=0.15)

    ax.plot(
        group_a["lon"],
        group_a["lat"],
        linewidth=2.2,
        label=f"A: {pair_row['flight_a']}",
    )
    ax.plot(
        group_b["lon"],
        group_b["lat"],
        linewidth=2.2,
        label=f"B: {pair_row['flight_b']}",
    )

    set_geographic_aspect(ax, all_points["lat"].to_numpy(dtype=float))

    ax.set_xlabel("Longitude [deg]")
    ax.set_ylabel("Latitude [deg]")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    ax.set_title(
        "Maximum Hausdorff pair in context of all 309 trajectories\n"
        f"Hausdorff = {float(pair_row['hausdorff_km']):.3f} km"
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    points = pd.read_csv(args.points, compression="infer", low_memory=False)
    points, _ = normalize_points(points)

    matrix, flight_ids = load_matrix(args.matrix, args.flight_ids)
    pairs = top_pairs(matrix, flight_ids, args.top_n)

    groups = {
        flight_id: group.reset_index(drop=True)
        for flight_id, group in points.groupby("flight_id", sort=False)
    }

    witness_rows: list[dict[str, object]] = []

    for row in pairs.itertuples(index=False):
        flight_a = str(row.flight_a)
        flight_b = str(row.flight_b)

        if flight_a not in groups or flight_b not in groups:
            raise KeyError(
                f"Trajectory points missing for pair: {flight_a}, {flight_b}"
            )

        group_a = groups[flight_a]
        group_b = groups[flight_b]

        trajectory_a = group_a[["lat", "lon"]].to_numpy(dtype=float)
        trajectory_b = group_b[["lat", "lon"]].to_numpy(dtype=float)

        witness = hausdorff_witness(trajectory_a, trajectory_b)

        pair_row = pd.Series(
            {
                "rank": row.rank,
                "flight_a": flight_a,
                "flight_b": flight_b,
                "hausdorff_km": row.hausdorff_km,
            }
        )

        output_path = (
            args.output_dir
            / f"rank_{int(row.rank):02d}_hausdorff_{float(row.hausdorff_km):.1f}km.png"
        )
        plot_pair(group_a, group_b, pair_row, witness, output_path)

        witness_rows.append(
            {
                "rank": int(row.rank),
                "flight_a": flight_a,
                "flight_b": flight_b,
                "hausdorff_km": float(row.hausdorff_km),
                **witness,
                "plot_file": str(output_path),
            }
        )

    witness_df = pd.DataFrame(witness_rows)
    witness_path = args.output_dir / "top_hausdorff_pairs_with_witness.csv"
    witness_df.to_csv(witness_path, index=False)

    # Context plot for the maximum-distance pair.
    max_row = pairs.iloc[0]
    max_a = groups[str(max_row["flight_a"])]
    max_b = groups[str(max_row["flight_b"])]
    context_path = args.output_dir / "max_pair_all_trajectories_context.png"
    plot_max_pair_context(points, max_a, max_b, max_row, context_path)

    # Count which flights repeatedly appear among the top-N extreme pairs.
    appearances = pd.concat(
        [
            pairs[["flight_a"]].rename(columns={"flight_a": "flight_id"}),
            pairs[["flight_b"]].rename(columns={"flight_b": "flight_id"}),
        ],
        ignore_index=True,
    )
    counts = (
        appearances["flight_id"]
        .value_counts()
        .rename_axis("flight_id")
        .reset_index(name="top_pair_appearances")
    )
    counts.to_csv(
        args.output_dir / "top_pair_flight_appearance_counts.csv",
        index=False,
    )

    print("\nVisual QC completed.")
    print(pairs[["rank", "flight_a", "flight_b", "hausdorff_km"]].to_string(index=False))
    print(f"\nSaved plots and tables to: {args.output_dir}")


if __name__ == "__main__":
    main()
