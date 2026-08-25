"""Estrattore del dataset 'incarichi-nominativi-shard' dal corpus DVNS.

Produce:
  - data/processed/incarichi_nominativi_shard_raw.csv   righe sorgente integrali + provenienza
  - data/relations/persona_incarico_ente__incarichi_nominativi_shard.(csv|parquet)
    relazioni person_has_appointment conforme a schemas/relation.schema.json
  - data/relations/_manifest_incarichi_nominativi_shard.json  provenienza dell'esecuzione

Nota metodologica: il nominativo resta identificativo verbatim senza deduplicazione
(vedi docs/LIMITI.md, omonimie). Il legame incarico->CIG non viene emesso qui perche'
la colonna cig in questo dataset ha copertura quasi nulla.
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from dvns_api import fetch_page, iter_rows  # noqa: E402


DATASET_ID = "incarichi-nominativi-shard"
EXPECTED_HEADERS = [
    "ente", "ipa", "cf_ente", "tipo", "nominativo", "cf_piva",
    "oggetto", "cig", "importo_euro", "data", "fonte_url", "note",
]

RAW_PATH = REPO_ROOT / "data" / "processed" / "incarichi_nominativi_shard_raw.csv"
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "persona_incarico_ente__incarichi_nominativi_shard.csv"
RELATIONS_PARQUET = REPO_ROOT / "data" / "relations" / "persona_incarico_ente__incarichi_nominativi_shard.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "relations" / "_manifest_incarichi_nominativi_shard.json"

RAW_COLUMNS = ["record_id", "source_row_sha256", "source_row", "source_urls"] + EXPECTED_HEADERS

RELATION_COLUMNS = [
    "relation_type",
    "subject_type",
    "subject_key",
    "object_type",
    "object_key",
    "source_dataset",
    "source_record_id",
    "period",
    "acquisition_date",
    "confidence_note",
    "role",
    "importo_if_present",
    "ipa",
    "fonte_url",
    "note_source",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OVERLAP_NOTE = (
    "dataset shard potenzialmente sovrapposto a nominativi-incarichi: "
    "non sommare righe o importi con altri dataset di incarichi"
)


def clean_cell(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_amount(value):
    text = clean_cell(value).replace(",", ".")
    if not text or text.lower() in ("n.d.", "nd"):
        return ""
    try:
        return repr(round(float(text), 2))
    except ValueError:
        return ""


def build_relation(row, acquisition_date):
    cells = row.get("cells") or {}
    nominativo = clean_cell(cells.get("nominativo"))
    ente = clean_cell(cells.get("ente"))
    data = clean_cell(cells.get("data"))
    record_id = clean_cell(row.get("sourceRowSha256")) or clean_cell(row.get("id"))
    return {
        "relation_type": "person_has_appointment",
        "subject_type": "person",
        "subject_key": nominativo,
        "object_type": "public_entity",
        "object_key": ente,
        "source_dataset": DATASET_ID,
        "source_record_id": record_id,
        "period": data if data else "n.d.",
        "acquisition_date": acquisition_date,
        "confidence_note": OVERLAP_NOTE,
        "role": clean_cell(cells.get("oggetto")),
        "importo_if_present": parse_amount(cells.get("importo_euro")),
        "ipa": clean_cell(cells.get("ipa")),
        "fonte_url": clean_cell(cells.get("fonte_url")),
        "note_source": clean_cell(cells.get("note")),
    }


def write_csv(path, columns, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def write_parquet(path, records):
    try:
        import pandas as pd
    except ImportError:
        return False
    frame = pd.DataFrame(records, columns=RELATION_COLUMNS)
    frame.to_parquet(path, index=False)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--page-limit", type=int, default=100)
    args = parser.parse_args()

    acquisition_date = datetime.now(timezone.utc).date().isoformat()

    first_page = fetch_page(DATASET_ID, page_limit=min(args.page_limit, 100))
    dataset_meta = first_page.get("dataset", {})

    raw_records = []
    relations = []
    skipped = 0
    for row in iter_rows(
        DATASET_ID,
        EXPECTED_HEADERS,
        max_rows=args.max_rows,
        page_limit=args.page_limit,
    ):
        cells = row.get("cells") or {}
        flat = {"record_id": clean_cell(row.get("id"))}
        flat["source_row_sha256"] = clean_cell(row.get("sourceRowSha256"))
        flat["source_row"] = str(clean_cell(row.get("sourceRow")))
        flat["source_urls"] = "; ".join(row.get("sourceUrls") or [])
        for header in EXPECTED_HEADERS:
            flat[header] = clean_cell(cells.get(header))
        raw_records.append(flat)

        if not flat["nominativo"] or not flat["ente"]:
            skipped += 1
            continue
        relations.append(build_relation(row, acquisition_date))

    write_csv(RAW_PATH, RAW_COLUMNS, raw_records)
    write_csv(RELATIONS_CSV, RELATION_COLUMNS, relations)
    parquet_ok = write_parquet(RELATIONS_PARQUET, relations)

    manifest = {
        "dataset_id": DATASET_ID,
        "api_endpoint": "{}/{}".format("https://www.dovevannoinostrisoldi.com/api/dati", DATASET_ID),
        "expected_headers": EXPECTED_HEADERS,
        "license_status": dataset_meta.get("licenseStatus"),
        "checked_at_source": (dataset_meta.get("sourceMetadata") or {}).get("checkedAt"),
        "declared_caveats": dataset_meta.get("caveats") or [],
        "matched_rows_declared": first_page.get("matchedRows"),
        "rows_downloaded": len(raw_records),
        "relations_written": len(relations),
        "rows_skipped_missing_nominativo_or_ente": skipped,
        "acquisition_date": acquisition_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parquet_written": parquet_ok,
        "relation_type_emitted": "person_has_appointment",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("righe scaricate: {}".format(len(raw_records)))
    print("relazioni scritte: {}".format(len(relations)))
    print("righe saltate (nominativo/ente mancante): {}".format(skipped))
    print("parquet: {}".format("si" if parquet_ok else "no"))
    print("manifest: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
