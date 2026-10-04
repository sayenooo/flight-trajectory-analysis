from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


EARTH_RADIUS_KM = 6371.0088

# Approximate airport reference coordinates used only for quality-control flags.
ICN_LAT = 37.4602
ICN_LON = 126.4407
FRA_LAT = 50.0379
FRA_LON = 8.5622


@dataclass
class QualityCheckReport:
    input_file: str
    total_points: int
    total_flights: int
    isolated_spike_points: int
    flights_with_spikes: int
    incomplete_start_flights: int
    incomplete_end_flights: int
    qc_clean_points: int
    qc_clean_flights: int
    output_files: dict[str, str]


def haversine_km(
    lat1: np.ndarray | float,
    lon1: np.ndarray | float,
    lat2: np.ndarray | float,
    lon2: np.ndarray | float,
) -> np.ndarray:
    """Great-circle distance in kilometers."""
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def add_point_quality_flags(
    points: pd.DataFrame,
    spike_leg_threshold_km: float,
    neighbor_bridge_threshold_km: float,
) -> pd.DataFrame:
    """Add trajectory-continuity diagnostics without deleting any rows."""
    required = {
        "flight_id",
        "point_time_unix",
        "latitude",
        "longitude",
    }
    missing = required - set(points.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    flagged = points.copy()
    flagged = flagged.sort_values(["flight_id", "point_time_unix"]).reset_index(drop=True)

    grouped = flagged.groupby("flight_id", sort=False)

    flagged["prev_time"] = grouped["point_time_unix"].shift(1)
    flagged["next_time"] = grouped["point_time_unix"].shift(-1)
    flagged["prev_latitude"] = grouped["latitude"].shift(1)
    flagged["prev_longitude"] = grouped["longitude"].shift(1)
    flagged["next_latitude"] = grouped["latitude"].shift(-1)
    flagged["next_longitude"] = grouped["longitude"].shift(-1)

    flagged["delta_t_prev_sec"] = flagged["point_time_unix"] - flagged["prev_time"]

    prev_valid = flagged["prev_latitude"].notna() & flagged["prev_longitude"].notna()
    next_valid = flagged["next_latitude"].notna() & flagged["next_longitude"].notna()
    both_neighbors = prev_valid & next_valid

    flagged["distance_from_prev_km"] = np.nan
    flagged.loc[prev_valid, "distance_from_prev_km"] = haversine_km(
        flagged.loc[prev_valid, "prev_latitude"].to_numpy(),
        flagged.loc[prev_valid, "prev_longitude"].to_numpy(),
        flagged.loc[prev_valid, "latitude"].to_numpy(),
        flagged.loc[prev_valid, "longitude"].to_numpy(),
    )

    flagged["distance_to_next_km"] = np.nan
    flagged.loc[next_valid, "distance_to_next_km"] = haversine_km(
        flagged.loc[next_valid, "latitude"].to_numpy(),
        flagged.loc[next_valid, "longitude"].to_numpy(),
        flagged.loc[next_valid, "next_latitude"].to_numpy(),
        flagged.loc[next_valid, "next_longitude"].to_numpy(),
    )

    flagged["neighbor_bridge_distance_km"] = np.nan
    flagged.loc[both_neighbors, "neighbor_bridge_distance_km"] = haversine_km(
        flagged.loc[both_neighbors, "prev_latitude"].to_numpy(),
        flagged.loc[both_neighbors, "prev_longitude"].to_numpy(),
        flagged.loc[both_neighbors, "next_latitude"].to_numpy(),
        flagged.loc[both_neighbors, "next_longitude"].to_numpy(),
    )

    flagged["implied_speed_from_prev_kmh"] = np.nan
    speed_mask = prev_valid & (flagged["delta_t_prev_sec"] > 0)
    flagged.loc[speed_mask, "implied_speed_from_prev_kmh"] = (
        flagged.loc[speed_mask, "distance_from_prev_km"]
        / flagged.loc[speed_mask, "delta_t_prev_sec"]
        * 3600.0
    )

    flagged["isolated_spike"] = (
        both_neighbors
        & (flagged["distance_from_prev_km"] > spike_leg_threshold_km)
        & (flagged["distance_to_next_km"] > spike_leg_threshold_km)
        & (flagged["neighbor_bridge_distance_km"] < neighbor_bridge_threshold_km)
    )

    return flagged


def create_flight_quality_summary(
    flagged_points: pd.DataFrame,
    airport_radius_km: float,
) -> pd.DataFrame:
    """Create one quality-control summary row per flight."""
    rows: list[dict[str, object]] = []

    for flight_id, group in flagged_points.groupby("flight_id", sort=False):
        group = group.sort_values("point_time_unix")
        first = group.iloc[0]
        last = group.iloc[-1]

        start_distance_icn_km = float(
            haversine_km(
                float(first["latitude"]),
                float(first["longitude"]),
                ICN_LAT,
                ICN_LON,
            )
        )
        end_distance_fra_km = float(
            haversine_km(
                float(last["latitude"]),
                float(last["longitude"]),
                FRA_LAT,
                FRA_LON,
            )
        )

        duration_sec = float(last["point_time_unix"] - first["point_time_unix"])
        spike_count = int(group["isolated_spike"].sum())

        rows.append(
            {
                "flight_id": flight_id,
                "source_year": first["source_year"] if "source_year" in group.columns else pd.NA,
                "callsign": first["callsign"] if "callsign" in group.columns else pd.NA,
                "icao24": first["icao24"] if "icao24" in group.columns else pd.NA,
                "point_count": int(len(group)),
                "duration_sec": duration_sec,
                "duration_hr": duration_sec / 3600.0,
                "start_latitude": float(first["latitude"]),
                "start_longitude": float(first["longitude"]),
                "end_latitude": float(last["latitude"]),
                "end_longitude": float(last["longitude"]),
                "start_distance_icn_km": start_distance_icn_km,
                "end_distance_fra_km": end_distance_fra_km,
                "coordinate_spike_count": spike_count,
                "has_coordinate_spike": spike_count > 0,
                "incomplete_start": start_distance_icn_km > airport_radius_km,
                "incomplete_end": end_distance_fra_km > airport_radius_km,
            }
        )

    summary = pd.DataFrame(rows)

    summary["quality_status"] = np.select(
        [
            summary["has_coordinate_spike"]
            & (summary["incomplete_start"] | summary["incomplete_end"]),
            summary["has_coordinate_spike"],
            summary["incomplete_start"] | summary["incomplete_end"],
        ],
        [
            "spike_and_incomplete",
            "coordinate_spike",
            "incomplete_trajectory",
        ],
        default="pass_basic_qc",
    )

    return summary.sort_values(
        ["quality_status", "source_year", "flight_id"],
        na_position="last",
    ).reset_index(drop=True)


def run_quality_check(
    input_file: Path,
    output_dir: Path,
    spike_leg_threshold_km: float,
    neighbor_bridge_threshold_km: float,
    airport_radius_km: float,
) -> QualityCheckReport:
    output_dir.mkdir(parents=True, exist_ok=True)

    points = pd.read_csv(input_file)

    flagged = add_point_quality_flags(
        points,
        spike_leg_threshold_km=spike_leg_threshold_km,
        neighbor_bridge_threshold_km=neighbor_bridge_threshold_km,
    )
    summary = create_flight_quality_summary(
        flagged,
        airport_radius_km=airport_radius_km,
    )

    point_flags_path = output_dir / "point_quality_flags.csv"
    spike_candidates_path = output_dir / "spike_candidates.csv"
    flight_summary_path = output_dir / "flight_quality_summary.csv"
    incomplete_start_path = output_dir / "incomplete_start_candidates.csv"
    qc_clean_path = output_dir / "flight_points_qc_clean.csv"
    report_path = output_dir / "quality_check_report.json"

    # Keep all diagnostic columns in the flag file, but write the QC-clean dataset
    # using only the original preprocessing columns. The original input file is
    # never modified.
    qc_clean = flagged.loc[~flagged["isolated_spike"], points.columns].copy()

    flagged.to_csv(point_flags_path, index=False)
    flagged.loc[flagged["isolated_spike"]].to_csv(spike_candidates_path, index=False)
    summary.to_csv(flight_summary_path, index=False)
    summary.loc[summary["incomplete_start"]].to_csv(incomplete_start_path, index=False)
    qc_clean.to_csv(qc_clean_path, index=False)

    report = QualityCheckReport(
        input_file=str(input_file),
        total_points=int(len(flagged)),
        total_flights=int(flagged["flight_id"].nunique()),
        isolated_spike_points=int(flagged["isolated_spike"].sum()),
        flights_with_spikes=int(summary["has_coordinate_spike"].sum()),
        incomplete_start_flights=int(summary["incomplete_start"].sum()),
        incomplete_end_flights=int(summary["incomplete_end"].sum()),
        qc_clean_points=int(len(qc_clean)),
        qc_clean_flights=int(qc_clean["flight_id"].nunique()),
        output_files={
            "point_quality_flags": str(point_flags_path),
            "spike_candidates": str(spike_candidates_path),
            "flight_quality_summary": str(flight_summary_path),
            "incomplete_start_candidates": str(incomplete_start_path),
            "qc_clean_points": str(qc_clean_path),
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
            "Run second-stage trajectory quality checks and write a separate "
            "QC-clean dataset with isolated spike points removed."
        )
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("data/processed/flight_points_clean.csv"),
        help="Preprocessed point-level trajectory CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/quality"),
        help="Directory for QC outputs.",
    )
    parser.add_argument(
        "--spike-leg-threshold-km",
        type=float,
        default=100.0,
        help="Minimum distance for both legs around an isolated spike candidate.",
    )
    parser.add_argument(
        "--neighbor-bridge-threshold-km",
        type=float,
        default=50.0,
        help="Maximum direct distance between the previous and next point.",
    )
    parser.add_argument(
        "--airport-radius-km",
        type=float,
        default=50.0,
        help="Radius used to flag flights not starting near ICN or ending near FRA.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_quality_check(
        input_file=args.input_file,
        output_dir=args.output_dir,
        spike_leg_threshold_km=args.spike_leg_threshold_km,
        neighbor_bridge_threshold_km=args.neighbor_bridge_threshold_km,
        airport_radius_km=args.airport_radius_km,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
