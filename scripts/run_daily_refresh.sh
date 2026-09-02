#!/usr/bin/env bash
# Daily refresh of Explorer relations from DVNS public API.
# Fail-closed: any required extract/test failure aborts without claiming success.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-full}"   # full | smoke
export PYTHONUNBUFFERED=1

echo "==> Explorer daily refresh (mode=$MODE)"
echo "    root=$ROOT"
date -u +"    started_utc=%Y-%m-%dT%H:%M:%SZ"

if [[ "$MODE" == "smoke" ]]; then
  MAX_ROWS=30
  PAGE=15
else
  MAX_ROWS=""
  PAGE=100
fi

run_extract() {
  local script="$1"
  shift
  echo "==> extract: $script $*"
  python3 "scripts/extract/$script" "$@"
}

# --- Required for pipeline DVNS ---
if [[ -n "$MAX_ROWS" ]]; then
  run_extract extract_affidamenti_diretti.py --max-rows "$MAX_ROWS" --page-limit "$PAGE"
  run_extract extract_incarichi_nominativi_shard.py --max-rows "$MAX_ROWS" --page-limit "$PAGE"
else
  run_extract extract_affidamenti_diretti.py --page-limit "$PAGE"
  run_extract extract_incarichi_nominativi_shard.py --page-limit "$PAGE"
fi

echo "==> normalize: classify_contraenti"
python3 scripts/normalize/classify_contraenti.py

# --- Optional datasets (non-blocking for pipeline core, but fail if script crashes) ---
if [[ "${SKIP_OPTIONAL:-0}" != "1" ]]; then
  if [[ -n "$MAX_ROWS" ]]; then
    run_extract extract_rinnovi_proroghe.py --max-rows "$MAX_ROWS" --page-limit "$PAGE" || {
      echo "::warning::rinnovi extract failed (optional)"; true
    }
  else
    run_extract extract_rinnovi_proroghe.py --page-limit "$PAGE" || {
      echo "::warning::rinnovi extract failed (optional)"; true
    }
  fi
fi

echo "==> validate required relation files"
python3 scripts/validate_refresh.py

echo "==> pytest (offline + relation checks)"
python3 -m pytest tests/test_classification_rules.py tests/test_schemas.py tests/test_awards_relations.py tests/test_incarichi_relations.py -q

echo "==> write refresh stamp"
python3 - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
root = Path(".")
rel = root / "data" / "relations"
required = [
    "awards__affidamenti_diretti.csv",
    "cig_ente__affidamenti_diretti.csv",
    "persona_incarico_ente__incarichi_nominativi_shard.csv",
]
stamp = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "required_files": {},
}
for name in required:
    p = rel / name
    stamp["required_files"][name] = {
        "exists": p.exists(),
        "bytes": p.stat().st_size if p.exists() else 0,
    }
out = rel / "_refresh_stamp.json"
out.write_text(json.dumps(stamp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("stamp:", out)
PY

date -u +"==> done_utc=%Y-%m-%dT%H:%M:%SZ"
