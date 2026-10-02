"""Preprocess DLH713 OpenSky trajectory exports for PCA/HDBSCAN teammates.

The provided OpenSky exports are Excel workbooks that contain CSV-like text in a
single column. Long trajectory rows may be split across several Excel rows, so
this script reconstructs each flight record, expands its `track` list into
point-level trajectory data, cleans obvious data-quality issues, and exports
clean/scaled CSV files.

Run from the project root:
    python src/preprocess.py --raw-dir . --processed-dir data/processed
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


RECORD_START_RE = re.compile(r"^[0-9a-fA-F]{6},")
YEAR_RE = re.compile(r"(20\d{2})")
POINT_RE = re.compile(
    r"\{time=(?P<time>-?\d+(?:\.\d+)?),\s*"
    r"latitude=(?P<latitude>-?\d+(?:\.\d+)?),\s*"
    r"longitude=(?P<longitude>-?\d+(?:\.\d+)?),\s*"
    r"altitude=(?P<altitude>-?\d+(?:\.\d+)?),\s*"
    r"heading=(?P<heading>-?\d+(?:\.\d+)?),\s*"
    r"onground=(?P<onground>true|false)\}",
    flags=re.IGNORECASE,
)

RAW_COLUMNS = ["icao24", "callsign", "firstseen", "lastseen", "track"]
REQUIRED_POINT_COLUMNS = ["point_time_unix", "latitude", "longitude", "altitude", "heading"]
SCALING_FEATURES = [
    "latitude",
    "longitude",
    "altitude",
    "heading",
    "time_from_start_sec",
    "route_progress",
]


@dataclass
class PreprocessingReport:
    raw_files: list[str]
    reconstructed_flights: int
    parsed_points_before_cleaning: int
    duplicated_points_removed: int
    invalid_points_removed: int
    clean_points: int
    clean_flights: int
    output_files: dict[str, str]


def find_input_files(raw_dir: Path) -> list[Path]:
    """Find DLH713 Excel exports in the selected directory tree."""
    patterns = ["DLH713_*.xlsx", "**/DLH713_*.xlsx"]
    found: list[Path] = []
    for pattern in patterns:
        found.extend(raw_dir.glob(pattern))
    unique = sorted({path.resolve() for path in found})
    if not unique:
        raise FileNotFoundError(
            f"No DLH713 Excel files found in {raw_dir}. Expected files like DLH713_2024.csv.xlsx."
        )
    return unique


def read_single_column_excel(path: Path) -> list[str]:
    """Read all non-empty single-column text fragments from an Excel export."""
    # The export is not a normal table; each row stores a CSV fragment in column A.
    raw = pd.read_excel(path, header=None, dtype=str, engine="openpyxl")
    if raw.empty:
        return []
    values = raw.iloc[:, 0].dropna().astype(str).tolist()
    return [value.strip() for value in values if value.strip()]


def reconstruct_csv_records(fragments: Iterable[str]) -> list[str]:
    """Reconstruct full CSV rows when long trajectory records were split across Excel rows."""
    records: list[str] = []
    current: list[str] = []

    for fragment in fragments:
        if fragment.startswith("icao24"):
            continue

        if RECORD_START_RE.match(fragment):
            if current:
                records.append("".join(current))
            current = [fragment]
        elif current:
            current.append(fragment)

    if current:
        records.append("".join(current))

    return records


def parse_flight_records(records: list[str], source_file: Path) -> pd.DataFrame:
    """Parse reconstructed CSV rows into one row per flight."""
    year_match = YEAR_RE.search(source_file.name)
    source_year = int(year_match.group(1)) if year_match else pd.NA

    rows: list[dict[str, object]] = []
    for record in records:
        try:
            parsed = next(csv.reader([record]))
        except csv.Error:
            continue
        if len(parsed) < len(RAW_COLUMNS):
            continue

        parsed = parsed[:4] + [",".join(parsed[4:])]
        row = dict(zip(RAW_COLUMNS, parsed))
        row["source_year"] = source_year
        row["source_file"] = source_file.name
        rows.append(row)

    flights = pd.DataFrame(rows)
    if flights.empty:
        return flights

    flights["icao24"] = flights["icao24"].astype(str).str.strip().str.lower()
    flights["callsign"] = flights["callsign"].astype(str).str.strip()
    flights["firstseen"] = pd.to_numeric(flights["firstseen"], errors="coerce").astype("Int64")
    flights["lastseen"] = pd.to_numeric(flights["lastseen"], errors="coerce").astype("Int64")
    flights = flights.dropna(subset=["icao24", "callsign", "firstseen", "lastseen", "track"])
    flights["flight_id"] = (
        flights["callsign"].astype(str)
        + "_"
        + flights["icao24"].astype(str)
        + "_"
        + flights["firstseen"].astype(str)
        + "_"
        + flights["lastseen"].astype(str)
    )
    return flights


def load_flight_table(input_files: list[Path]) -> pd.DataFrame:
    """Load and combine all flight-level records from all raw files."""
    frames: list[pd.DataFrame] = []
    for path in input_files:
        fragments = read_single_column_excel(path)
        records = reconstruct_csv_records(fragments)
        frame = parse_flight_records(records, path)
        if not frame.empty:
            frames.append(frame)

    if not frames:
        raise ValueError("No valid flight records were parsed from the input files.")

    flights = pd.concat(frames, ignore_index=True)
    flights = flights.drop_duplicates(subset=["flight_id"]).reset_index(drop=True)
    return flights


def expand_tracks(flights: pd.DataFrame) -> pd.DataFrame:
    """Expand each flight-level `track` list into point-level trajectory rows."""
    points: list[dict[str, object]] = []

    for flight in flights.itertuples(index=False):
        track_text = getattr(flight, "track")
        matches = list(POINT_RE.finditer(str(track_text)))
        for sequence_index, match in enumerate(matches):
            data = match.groupdict()
            points.append(
                {
                    "flight_id": getattr(flight, "flight_id"),
                    "source_year": getattr(flight, "source_year"),
                    "source_file": getattr(flight, "source_file"),
                    "icao24": getattr(flight, "icao24"),
                    "callsign": getattr(flight, "callsign"),
                    "firstseen_unix": int(getattr(flight, "firstseen")),
                    "lastseen_unix": int(getattr(flight, "lastseen")),
                    "raw_sequence_index": sequence_index,
                    "point_time_unix": float(data["time"]),
                    "latitude": float(data["latitude"]),
                    "longitude": float(data["longitude"]),
                    "altitude": float(data["altitude"]),
                    "heading": float(data["heading"]),
                    "onground": data["onground"].lower() == "true",
                }
            )

    if not points:
        raise ValueError("No trajectory points were parsed from the flight tracks.")

    return pd.DataFrame(points)


def clean_points(points: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean point-level trajectories while avoiding aggressive domain assumptions."""
    before = len(points)
    cleaned = points.copy()

    for column in REQUIRED_POINT_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned = cleaned.dropna(subset=REQUIRED_POINT_COLUMNS)

    # Keep only physically plausible coordinates/headings and timestamps that belong
    # to the corresponding flight interval. A small tolerance is allowed because
    # OpenSky firstseen/lastseen and track point timestamps can differ slightly.
    time_tolerance_sec = 3600
    valid_mask = (
        cleaned["latitude"].between(-90, 90)
        & cleaned["longitude"].between(-180, 180)
        & cleaned["heading"].between(0, 360)
        & (cleaned["point_time_unix"] > 0)
        & cleaned["point_time_unix"].between(
            cleaned["firstseen_unix"] - time_tolerance_sec,
            cleaned["lastseen_unix"] + time_tolerance_sec,
        )
    )
    invalid_removed = int((~valid_mask).sum())
    cleaned = cleaned.loc[valid_mask].copy()

    duplicate_subset = [
        "flight_id",
        "point_time_unix",
        "latitude",
        "longitude",
        "altitude",
        "heading",
    ]
    before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=duplicate_subset)
    duplicates_removed = before_dedup - len(cleaned)

    cleaned = cleaned.sort_values(["flight_id", "point_time_unix"]).reset_index(drop=True)
    cleaned["sequence_index"] = cleaned.groupby("flight_id").cumcount()
    cleaned["point_count"] = cleaned.groupby("flight_id")["flight_id"].transform("size")
    cleaned["first_point_time_unix"] = cleaned.groupby("flight_id")["point_time_unix"].transform("min")
    cleaned["last_point_time_unix"] = cleaned.groupby("flight_id")["point_time_unix"].transform("max")
    cleaned["time_from_start_sec"] = cleaned["point_time_unix"] - cleaned["first_point_time_unix"]
    cleaned["trajectory_duration_sec"] = cleaned["last_point_time_unix"] - cleaned["first_point_time_unix"]
    cleaned["route_progress"] = np.where(
        cleaned["trajectory_duration_sec"] > 0,
        cleaned["time_from_start_sec"] / cleaned["trajectory_duration_sec"],
        0.0,
    )
    cleaned["point_time_utc"] = pd.to_datetime(cleaned["point_time_unix"], unit="s", utc=True)
    cleaned["firstseen_utc"] = pd.to_datetime(cleaned["firstseen_unix"], unit="s", utc=True)
    cleaned["lastseen_utc"] = pd.to_datetime(cleaned["lastseen_unix"], unit="s", utc=True)
    cleaned["altitude_below_zero"] = cleaned["altitude"] < 0

    # Store integer timestamps after datetime conversion.
    for column in ["point_time_unix", "firstseen_unix", "lastseen_unix"]:
        cleaned[column] = cleaned[column].astype("int64")

    stats = {
        "parsed_points_before_cleaning": before,
        "invalid_points_removed": invalid_removed,
        "duplicated_points_removed": duplicates_removed,
    }
    return cleaned, stats


def create_scaled_dataset(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Add StandardScaler versions of numeric columns used by PCA/HDBSCAN teammates."""
    scaled = cleaned.copy()
    available_features = [col for col in SCALING_FEATURES if col in scaled.columns]
    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(scaled[available_features])
    for idx, column in enumerate(available_features):
        scaled[f"{column}_scaled"] = scaled_values[:, idx]
    return scaled


def create_flight_summary(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Summarize each reconstructed trajectory in one row per flight."""
    summary = (
        cleaned.groupby(["flight_id", "source_year", "icao24", "callsign"], as_index=False)
        .agg(
            first_point_time_utc=("point_time_utc", "min"),
            last_point_time_utc=("point_time_utc", "max"),
            point_count=("point_time_unix", "size"),
            duration_sec=("trajectory_duration_sec", "max"),
            min_latitude=("latitude", "min"),
            max_latitude=("latitude", "max"),
            min_longitude=("longitude", "min"),
            max_longitude=("longitude", "max"),
            min_altitude=("altitude", "min"),
            max_altitude=("altitude", "max"),
            below_zero_altitude_points=("altitude_below_zero", "sum"),
        )
        .sort_values(["source_year", "first_point_time_utc", "flight_id"])
        .reset_index(drop=True)
    )
    return summary


def run_preprocessing(raw_dir: Path, processed_dir: Path) -> PreprocessingReport:
    """Run the complete preprocessing pipeline and save output CSV files."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    input_files = find_input_files(raw_dir)

    flights = load_flight_table(input_files)
    points = expand_tracks(flights)
    cleaned, stats = clean_points(points)
    scaled = create_scaled_dataset(cleaned)
    summary = create_flight_summary(cleaned)

    clean_points_path = processed_dir / "flight_points_clean.csv"
    scaled_points_path = processed_dir / "flight_points_scaled.csv"
    summary_path = processed_dir / "flights_summary.csv"
    report_path = processed_dir / "preprocessing_report.json"

    cleaned.to_csv(clean_points_path, index=False)
    scaled.to_csv(scaled_points_path, index=False)
    summary.to_csv(summary_path, index=False)

    report = PreprocessingReport(
        raw_files=[str(path) for path in input_files],
        reconstructed_flights=int(flights["flight_id"].nunique()),
        parsed_points_before_cleaning=stats["parsed_points_before_cleaning"],
        duplicated_points_removed=stats["duplicated_points_removed"],
        invalid_points_removed=stats["invalid_points_removed"],
        clean_points=int(len(cleaned)),
        clean_flights=int(cleaned["flight_id"].nunique()),
        output_files={
            "clean_points": str(clean_points_path),
            "scaled_points": str(scaled_points_path),
            "flight_summary": str(summary_path),
            "report": str(report_path),
        },
    )

    report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess DLH713 OpenSky trajectory files.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("."),
        help="Directory containing DLH713_*.xlsx raw files. Default: current project root.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory where processed CSV files will be saved.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_preprocessing(args.raw_dir, args.processed_dir)
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
