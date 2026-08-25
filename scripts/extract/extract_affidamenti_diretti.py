"""Estrattore del dataset 'affidamenti-diretti' dal corpus DVNS.

Produce:
  - data/processed/affidamenti_diretti_raw.csv   righe sorgente integrali + provenienza
  - data/relations/cig_ente__affidamenti_diretti.(csv|parquet)
    relazioni cig_linked_to_entity conforme a schemas/relation.schema.json
  - data/relations/_manifest_affidamenti_diretti.json  provenienza dell'esecuzione

Nota metodologica: il legame contraente->organizzazione/persona NON viene emesso
qui perche' richiede regole di classificazione documentate (fase normalize).
Vengono estratti solo i collegamenti certi presenti nella riga.
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


DATASET_ID = "affidamenti-diretti"
EXPECTED_HEADERS = ["ente", "ipa", "cig", "contraente", "cf", "importo", "oggetto", "data", "url"]

RAW_PATH = REPO_ROOT / "data" / "processed" / "affidamenti_diretti_raw.csv"
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "cig_ente__affidamenti_diretti.csv"
RELATIONS_PARQUET = REPO_ROOT / "data" / "relations" / "cig_ente__affidamenti_diretti.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "relations" / "_manifest_affidamenti_diretti.json"

RAW_COLUMNS = [
    "record_id",
    "source_row_sha256",
    "source_row",
    "source_urls",
] + EXPECTED_HEADERS

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
    "amount_if_present",
    "ipa",
    "source_url",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
    cig = clean_cell(cells.get("cig"))
    ente = clean_cell(cells.get("ente"))
    data = clean_cell(cells.get("data"))
    amount = parse_amount(cells.get("importo"))
    notes = [
        "riga sorgente con copertura dichiarata incompleta su importi/contraenti/date",
    ]
    if not DATE_PATTERN.match(data):
        notes.append("data assente o fuori formato: periodo non determinabile dalla riga")
    record_id = clean_cell(row.get("sourceRowSha256")) or clean_cell(row.get("id"))
    return {
        "relation_type": "cig_linked_to_entity",
        "subject_type": "cig",
        "subject_key": cig,
        "object_type": "public_entity",
        "object_key": ente,
        "source_dataset": DATASET_ID,
        "source_record_id": record_id,
        "period": data if data else "n.d.",
        "acquisition_date": acquisition_date,
        "confidence_note": "; ".join(notes),
        "amount_if_present": amount,
        "ipa": clean_cell(cells.get("ipa")),
        "source_url": clean_cell(cells.get("url")),
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
    parser.add_argument("--max-rows", type=int, default=None,
                        help="numero massimo di righe sorgente da scaricare")
    parser.add_argument("--page-limit", type=int, default=100)
    args = parser.parse_args()

    acquisition_date = datetime.now(timezone.utc).date().isoformat()

    first_page = fetch_page(DATASET_ID, page_limit=min(args.page_limit, 100))
    dataset_meta = first_page.get("dataset", {})
    pagination_meta = first_page.get("pagination") or {}

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

        cig = flat["cig"]
        ente = flat["ente"]
        if not cig or not ente or cig.lower() == "n.d.":
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
        "rows_skipped_missing_cig_or_ente": skipped,
        "acquisition_date": acquisition_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parquet_written": parquet_ok,
        "relation_type_emitted": "cig_linked_to_entity",
        "contraente_edge_deferred": "classificazione persona/organizzazione rimandata alla fase normalize",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("righe scaricate: {}".format(len(raw_records)))
    print("relazioni scritte: {}".format(len(relations)))
    print("righe saltate (cig/ente mancante): {}".format(skipped))
    print("parquet: {}".format("si" if parquet_ok else "no (pandas/pyarrow non disponibili)"))
    print("manifest: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
