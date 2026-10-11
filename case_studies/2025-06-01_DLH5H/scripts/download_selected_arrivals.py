#!/usr/bin/env python3
"""Obtain seven specified Frankfurt arrivals and their historical ADS-B positions.

This optional script uses OpenSky Trino and may require a browser login.
No passwords/API tokens are stored. Server performance and permissions vary.
"""
from pathlib import Path
import pandas as pd
import numpy as np
from pyopensky.trino import Trino

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "opensky"
OUT.mkdir(parents=True, exist_ok=True)

W_START = pd.Timestamp("2025-06-01T08:40:00Z")
W_STOP = pd.Timestamp("2025-06-01T09:40:00Z")
P_START = pd.Timestamp("2025-06-01T08:15:00Z")
P_STOP = pd.Timestamp("2025-06-01T09:45:00Z")
NAMES = ["OCN77", "UAL74", "AFR93RE", "DLH5H", "CFG2045", "DLH8F", "DLH447"]


def utc(s):
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s, unit="s", utc=True, errors="coerce")
    return pd.to_datetime(s, utc=True, errors="coerce")


def main():
    db = Trino()
    cache = OUT / "01_all_EDDF_arrivals_0840_0940.csv"
    if cache.exists():
        print("Using cached arrival list", cache)
        arrivals = pd.read_csv(cache)
    else:
        print("Querying all EDDF arrivals during 08:40–09:40 UTC...")
        arrivals = db.flightlist(
            start=W_START, stop=W_STOP, arrival_airport="EDDF"
        )
        if arrivals is None or arrivals.empty:
            raise SystemExit("OpenSky returned no EDDF arrival metadata")
        arrivals.to_csv(cache, index=False, encoding="utf-8-sig")

    arrivals = arrivals.copy()
    arrivals["firstseen_utc"] = utc(
        arrivals["firstseen_utc"] if "firstseen_utc" in arrivals else arrivals["firstseen"]
    )
    arrivals["lastseen_utc"] = utc(
        arrivals["lastseen_utc"] if "lastseen_utc" in arrivals else arrivals["lastseen"]
    )
    arrivals["callsign"] = arrivals["callsign"].fillna("").astype(str).str.strip().str.upper()
    arrivals["icao24"] = arrivals["icao24"].fillna("").astype(str).str.strip().str.lower()
    arrivals = arrivals[
        arrivals["lastseen_utc"].between(W_START, W_STOP)
        & arrivals["icao24"].str.fullmatch(r"[0-9a-f]{6}")
    ].dropna(subset=["firstseen_utc", "lastseen_utc"])
    selected = arrivals[arrivals["callsign"].isin(NAMES)].copy()
    selected = selected.drop_duplicates(subset=["icao24", "firstseen_utc", "lastseen_utc"])
    if selected.empty:
        raise SystemExit("None of the seven requested callsigns appears in metadata")

    print("Selected flights in arrival metadata:", len(selected))
    print(selected[["callsign", "icao24", "lastseen_utc"]].to_string(index=False))
    missing = set(NAMES) - set(selected["callsign"])
    if missing:
        print("WARNING: missing callsigns:", sorted(missing))

    frames = []
    ids = selected["icao24"].unique().tolist()
    for j in range(0, len(ids), 7):
        chunk = ids[j:j+7]
        print(f"Requesting historical points for aircraft {j+1}–{j+len(chunk)}...", flush=True)
        part = db.history(
            start=P_START, stop=P_STOP,
            icao24=chunk,
            bounds=(4.0, 49.0, 10.5, 53.0),
            selected_columns=("time", "icao24", "callsign", "lat", "lon", "lastposupdate", "baroaltitude", "geoaltitude", "heading")
        )
        if part is not None and not part.empty:
            frames.append(part)
    if not frames:
        raise SystemExit("No historical position rows returned; check Trino access/coverage")
    data = pd.concat(frames, ignore_index=True)
    data["utc"] = utc(data["time"])
    data["icao24"] = data["icao24"].fillna("").astype(str).str.strip().str.lower()
    data["callsign"] = data["callsign"].fillna("").astype(str).str.strip().str.upper()
    for k in ("lat", "lon", "lastposupdate"):
        data[k] = pd.to_numeric(data[k], errors="coerce")
    data = data.dropna(subset=["utc", "lat", "lon"])
    data = data[data["lat"].between(49, 53) & data["lon"].between(4, 10.5)]

    qa = []
    for record in selected.itertuples(index=False):
        t = data[
            (data["icao24"] == record.icao24)
            & (data["utc"] >= max(P_START, record.firstseen_utc - pd.Timedelta(minutes=10)))
            & (data["utc"] <= min(P_STOP, record.lastseen_utc + pd.Timedelta(minutes=4)))
        ].copy()
        # Guard against re-use of the same aircraft by another flight.
        if len(t):
            matches = t["callsign"].eq(record.callsign)
            if matches.sum() >= 3:
                t = t[matches | t["callsign"].eq("")].copy()
        t = t.sort_values("utc").drop_duplicates(subset=["utc", "lat", "lon"])
        pos_age = t["utc"].apply(lambda x: x.timestamp()) - t["lastposupdate"]
        t["position_age_seconds_exploratory"] = pos_age
        n_valid_age = int(pos_age.between(0, 15).sum())
        status = (
            "NEEDS_POSITION_AGE_QA" if n_valid_age < max(5, int(.8 * len(t)))
            else "AGE_RANGE_PLAUSIBLE_CHECK_OTHER_QA"
        )
        fn = f"flight_{record.callsign}_{record.icao24}_{record.lastseen_utc:%H%M}.csv"
        if len(t) >= 5:
            t.to_csv(OUT / fn, index=False, encoding="utf-8-sig")
        qa.append({
            "callsign": record.callsign,
            "icao24": record.icao24,
            "estimated_arrival_utc": record.lastseen_utc.isoformat(),
            "matched_points": len(t),
            "ages_between_0_and_15s": n_valid_age,
            "status": status if len(t) >= 5 else "INSUFFICIENT_POSITION_ROWS",
            "source_file": fn if len(t) >= 5 else "",
        })
        print(record.callsign, len(t), status)
    pd.DataFrame(qa).to_csv(OUT / "download_selected_arrivals_QA.csv", index=False, encoding="utf-8-sig")
    print("Saved arrivals and QA to", OUT)
    print("Caution: a plausible position-age range is not full trajectory validation.")

if __name__ == "__main__":
    main()
