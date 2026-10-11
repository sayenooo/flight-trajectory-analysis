#!/usr/bin/env python3
"""Plot seven nearby EDDF arrivals from verified local CSV export paths.

Exploratory display: ADS-B position-age validation remains a separate QA task.
Reads from <case>/data/opensky/flight_*.csv; does not require Internet.
"""
import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

CASE_ROOT = Path(__file__).resolve().parents[1]
STYLE = {
    "DLH5H": ("#df2739", 4.0, "09:13:52"),
    "AFR93RE": ("#2171b5", 1.9, "09:13:29"),
    "CFG2045": ("#2aa35a", 1.9, "09:16:18"),
    "DLH8F": ("#f18a1b", 1.9, "09:17:13"),
    "UAL74": ("#9061bc", 1.9, "09:09:22"),
    "DLH447": ("#159fa5", 1.9, "09:18:55"),
    "OCN77": ("#8c4f2e", 1.9, "09:07:21"),
}

def get_times(s):
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s, unit="s", utc=True, errors="coerce")
    return pd.to_datetime(s, utc=True, errors="coerce")


def identify_flight(file):
    # Supported previous exports: flight_01_DLH5H.csv and
    # flight_DLH5H_3c65d8_0913.csv.
    stem = file.stem.upper()
    for callsign in STYLE:
        patterns = (
            rf"^FLIGHT_\d+_{re.escape(callsign)}$",
            rf"^FLIGHT_{re.escape(callsign)}(?:_|$)",
        )
        if any(re.search(pat, stem) for pat in patterns):
            return callsign
    return None


def read_route(file, callsign):
    df = pd.read_csv(file, low_memory=False)
    time_col = next((c for c in ("utc", "time") if c in df.columns), None)
    if time_col is None or not {"lat", "lon"}.issubset(df.columns):
        raise ValueError(f"Missing time/lat/lon columns in {file.name}")
    df["utc"] = get_times(df[time_col])
    for key in ("lat", "lon"):
        df[key] = pd.to_numeric(df[key], errors="coerce")
    df = df.dropna(subset=["utc", "lat", "lon"])
    df = df[
        (df["utc"] >= pd.Timestamp("2025-06-01T08:15:00Z"))
        & (df["utc"] <= pd.Timestamp("2025-06-01T09:45:00Z"))
        & df["lon"].between(4.0, 10.5)
        & df["lat"].between(49.0, 53.0)
    ].copy()
    if "callsign" in df.columns:
        c = df["callsign"].fillna("").astype(str).str.strip().str.upper()
        if (c == callsign).sum() >= 2:
            df = df[(c == callsign) | c.eq("")]
    return df.drop_duplicates(subset=["utc", "lat", "lon"]).sort_values("utc")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=CASE_ROOT / "data" / "opensky")
    ap.add_argument("--output", type=Path, default=CASE_ROOT / "figures" / "7_flights_vs_DLH5H.png")
    args = ap.parse_args()
    files = sorted(args.data_dir.glob("flight_*.csv"))
    latest = {}
    for file in files:
        callsign = identify_flight(file)
        if callsign is not None:
            latest[callsign] = file

    routes = {}
    manifest = []
    print(f"CSV files detected: {len(files)}")
    for callsign in STYLE:
        file = latest.get(callsign)
        if file is None:
            print(f"MISSING {callsign}: import local exports first")
            continue
        df = read_route(file, callsign)
        if len(df) < 5:
            print(f"SKIP {callsign}: only {len(df)} valid plotted points")
            continue
        routes[callsign] = df
        manifest.append({
            "callsign": callsign,
            "plotted_points": len(df),
            "observed_first_utc": df["utc"].min().isoformat(),
            "observed_last_utc": df["utc"].max().isoformat(),
            "source_file": file.name,
            "position_age_verified": False,
        })
        print(f"{callsign}: {len(df)} plotted points <- {file.name}")

    if "DLH5H" not in routes:
        raise SystemExit("DLH5H CSV missing; run scripts/import_local_exports.ps1")
    if len(routes) < 2:
        raise SystemExit("Need at least one comparison CSV alongside DLH5H")

    fig, axes = plt.subplots(1, 2, figsize=(18.4, 8.0))
    fig.subplots_adjust(left=.065, right=.96, bottom=.215, top=.85, wspace=.18)
    fig.suptitle("Frankfurt Arrival Trajectories | 1 June 2025", fontsize=18, fontweight="bold")
    fig.text(.5, .89, "OpenSky historical ADS-B | selected arrivals near DLH5H", ha="center", fontsize=11)
    handles = []
    for callsign, df in routes.items():
        color, width, arr = STYLE[callsign]
        segment_id = df["utc"].diff().dt.total_seconds().fillna(0).gt(60).cumsum()
        for _, part in df.groupby(segment_id):
            if len(part) < 2:
                continue
            for ax in axes:
                ax.plot(part["lon"], part["lat"], c=color, linewidth=width,
                        alpha=1 if callsign == "DLH5H" else .86,
                        zorder=10 if callsign == "DLH5H" else 3)
        handles.append(Line2D([0], [0], color=color, lw=width, label=f"{callsign} ({arr} UTC)"))

    for ax in axes:
        ax.scatter(8.5622, 50.038, marker="x", c="black", s=70, linewidths=2, zorder=20)
        ax.annotate("FRA", (8.5622, 50.038), xytext=(5, 5), textcoords="offset points", fontweight="bold")
        ax.grid(alpha=.25, ls="--")
        ax.set_xlabel("Longitude (degrees east)")
        ax.set_ylabel("Latitude (degrees north)")
        ax.set_aspect(1 / np.cos(np.deg2rad(51)), adjustable="box")
    axes[0].set_xlim(4.5, 9.8)
    axes[0].set_ylim(49.3, 52.3)
    axes[0].set_title("All selected approach routes")
    axes[1].set_xlim(6.0, 9.3)
    axes[1].set_ylim(49.55, 51.35)
    axes[1].set_title("Western approach close-up")

    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .095),
               ncol=4, frameon=False, fontsize=10)
    fig.text(.5, .032,
             "Time/coordinate-validated ADS-B plots; position-update age NOT independently verified. "
             "Different tracks do not prove ATC or weather causation.",
             ha="center", fontsize=9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=200, facecolor="white")
    plt.close(fig)
    pd.DataFrame(manifest).to_csv(args.data_dir / "plot_manifest.csv", index=False)
    print(f"Saved: {args.output}")
    print(f"Plotted {len(routes)}/7 requested callsigns")
    if len(routes) < 7:
        print("CAUTION: Missing routes were omitted; import all seven CSVs before final team submission.")

if __name__ == "__main__":
    main()
