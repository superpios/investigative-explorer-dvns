#!/usr/bin/env python3
"""Fail-closed checks after a daily refresh.

Verifies required relation CSVs exist, are non-empty, and have required columns
used by the investigative pipeline adapter.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "data" / "relations"

REQUIRED = {
    "awards__affidamenti_diretti.csv": {
        "min_rows": 1,
        # pipeline adapt uses awards with subject/object keys; keep flexible
        "any_columns": ["subject_key", "object_key", "source_dataset"],
    },
    "cig_ente__affidamenti_diretti.csv": {
        "min_rows": 1,
        "any_columns": ["subject_key", "object_key", "source_dataset"],
    },
    "persona_incarico_ente__incarichi_nominativi_shard.csv": {
        "min_rows": 1,
        "any_columns": ["subject_key", "object_key", "source_dataset"],
    },
}


def main() -> int:
    errors: list[str] = []
    for name, spec in REQUIRED.items():
        path = REL / name
        if not path.exists():
            errors.append(f"missing file: {name}")
            continue
        if path.stat().st_size < 10:
            errors.append(f"empty or tiny file: {name}")
            continue
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = 0
            for _ in reader:
                rows += 1
                if rows >= spec["min_rows"]:
                    # count rest quickly
                    for _ in reader:
                        rows += 1
                    break
        if rows < spec["min_rows"]:
            errors.append(f"{name}: only {rows} data rows (min {spec['min_rows']})")
        missing = [c for c in spec["any_columns"] if c not in headers]
        if missing:
            errors.append(f"{name}: missing columns {missing}; have {headers[:12]}")
        print(f"OK {name}: rows>={rows} bytes={path.stat().st_size}")

    if errors:
        print("[fail-closed] validate_refresh FAILED:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1
    print("validate_refresh: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
