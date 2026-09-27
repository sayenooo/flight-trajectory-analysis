"""Basic trajectory preprocessing helpers.

This file is intentionally small. Add route-specific filtering only after
the OpenSky schema and access method are confirmed.
"""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ["time", "icao24", "latitude", "longitude"]


def validate_columns(df: pd.DataFrame) -> None:
    """Raise an error when required trajectory columns are missing."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def clean_state_vectors(df: pd.DataFrame) -> pd.DataFrame:
    """Return a minimally cleaned, time-ordered state-vector table."""
    validate_columns(df)

    cleaned = df.copy()
    cleaned = cleaned.dropna(subset=["time", "icao24", "latitude", "longitude"])
    cleaned["time"] = pd.to_datetime(cleaned["time"], unit="s", errors="coerce", utc=True)
    cleaned = cleaned.dropna(subset=["time"])
    cleaned = cleaned.sort_values(["icao24", "time"]).reset_index(drop=True)

    return cleaned
