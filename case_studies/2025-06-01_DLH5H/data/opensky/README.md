# OpenSky CSV exports

This directory initially contains no raw ADS-B CSV exports from the seven arrival flights, because those files were generated on the student's Windows computer and were not attached to this conversation.

Import locally with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_local_exports.ps1
```

Expected: `flight_*.csv` files with `utc` (or `time`), `lat`, `lon` and optionally `callsign`, `icao24`, altitude and position-age fields. The importer also copies the EDDF arrival list and diagnostic CSVs when present.

Alternatively run `python scripts/download_selected_arrivals.py` with authorized Trino access.

**No flight rows are fabricated in this package.**
