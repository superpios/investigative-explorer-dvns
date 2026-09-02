"""Estrattore del dataset 'parti-atti' dal corpus DVNS (159.493 righe).

Produce:
  - data/processed/parti_atti_raw.csv   righe sorgente integrali + provenienza
  - data/relations/soggetti_atti__parti_atti.(csv|parquet)
    archi person_has_appointment / organization_has_appointment verso l'ente,
    classificando 'chi_ricevuto' con le stesse regole conservative dei contraenti
    (scripts/normalize/classification_rules.py). I nomi senza segnale esplicito
    NON generano arco e restano conteggiati a parte.
  - data/relations/_manifest_parti_atti.json

Caveat della fonte, riportato in ogni relazione: sono istanze fisiche di atti,
lo stesso soggetto puo' ricorrere e i conteggi non sono somme di spesa.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.resolve().parents[1]
NORMALIZE_DIR = REPO_ROOT / "scripts" / "normalize"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(NORMALIZE_DIR))

from dvns_api import fetch_page, iter_rows  # noqa: E402
from classification_rules import classify  # noqa: E402


DATASET_ID = "parti-atti"
EXPECTED_HEADERS = ["ente", "ipa", "tipo", "chi_autorizzato", "chi_ricevuto", "cf", "cig", "data", "fonte_url"]

RAW_PATH = REPO_ROOT / "data" / "processed" / "parti_atti_raw.csv"
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "soggetti_atti__parti_atti.csv"
RELATIONS_PARQUET = REPO_ROOT / "data" / "relations" / "soggetti_atti__parti_atti.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "relations" / "_manifest_parti_atti.json"

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
    "act_kind",
    "authorization_object",
    "ipa",
    "cig_if_present",
    "fonte_url",
]

CONFIDENCE_NOTE = (
    "istanza fisica di atto: lo stesso soggetto può ricorrere e i conteggi non sono somme di spesa; "
    "classificazione soggetto da regole conservative (docs/NORMALIZZAZIONE.md)"
)

PROGRESS_EVERY_PAGES = 100


def clean_cell(value):
    return "" if value is None else str(value).strip()


def build_relation(row, klass, acquisition_date):
    cells = row.get("cells") or {}
    record_id = clean_cell(row.get("sourceRowSha256")) or clean_cell(row.get("id"))
    return {
        "relation_type": "{}_has_appointment".format(klass),
        "subject_type": klass,
        "subject_key": clean_cell(cells.get("chi_ricevuto")),
        "object_type": "public_entity",
        "object_key": clean_cell(cells.get("ente")),
        "source_dataset": DATASET_ID,
        "source_record_id": record_id,
        "period": clean_cell(cells.get("data")) or "n.d.",
        "acquisition_date": acquisition_date,
        "confidence_note": CONFIDENCE_NOTE,
        "act_kind": clean_cell(cells.get("tipo")),
        "authorization_object": clean_cell(cells.get("chi_autorizzato")),
        "ipa": clean_cell(cells.get("ipa")),
        "cig_if_present": clean_cell(cells.get("cig")),
        "fonte_url": clean_cell(cells.get("fonte_url")),
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
    try:
        frame = pd.DataFrame(records)
        frame.to_parquet(path, index=False)
        return True
    except Exception as exc:
        print("avviso: parquet non scritto ({}): {}".format(path, exc))
        return False



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
    skipped_unclassified = 0
    skipped_missing_fields = 0
    pages_seen = 0
    last_source_row = 0

    for row in iter_rows(DATASET_ID, EXPECTED_HEADERS,
                         max_rows=args.max_rows, page_limit=args.page_limit):
        cells = row.get("cells") or {}
        raw_records.append({
            "record_id": clean_cell(row.get("id")),
            "source_row_sha256": clean_cell(row.get("sourceRowSha256")),
            "source_row": str(clean_cell(row.get("sourceRow"))),
            "source_urls": "; ".join(row.get("sourceUrls") or []),
            **{header: clean_cell(cells.get(header)) for header in EXPECTED_HEADERS},
        })
        last_source_row = max(last_source_row, int(raw_records[-1]["source_row"] or 0))
        if len(raw_records) // args.page_limit >= pages_seen + PROGRESS_EVERY_PAGES:
            pages_seen = len(raw_records) // args.page_limit
            print("progresso: {} righe, {} relazioni...".format(len(raw_records), len(relations)), flush=True)

        subject = clean_cell(cells.get("chi_ricevuto"))
        ente = clean_cell(cells.get("ente"))
        key = " ".join(subject.split()).upper()
        if not key or not ente or key in ("N.D.", "ND"):
            skipped_missing_fields += 1
            continue
        klass, _rule = classify(key)
        if klass is None:
            skipped_unclassified += 1
            continue
        relations.append(build_relation(row, klass, acquisition_date))

    write_csv(RAW_PATH, RAW_COLUMNS, raw_records)
    write_csv(RELATIONS_CSV, RELATION_COLUMNS, relations)
    parquet_ok = write_parquet(RELATIONS_PARQUET, relations)
    edges_by_type = dict(Counter(r["relation_type"] for r in relations))

    manifest = {
        "dataset_id": DATASET_ID,
        "expected_headers": EXPECTED_HEADERS,
        "license_status": dataset_meta.get("licenseStatus"),
        "checked_at_source": (dataset_meta.get("sourceMetadata") or {}).get("checkedAt"),
        "declared_caveats": dataset_meta.get("caveats") or [],
        "matched_rows_declared": first_page.get("matchedRows"),
        "rows_downloaded": len(raw_records),
        "last_source_row_scanned": last_source_row,
        "relations_written": len(relations),
        "edges_by_type": edges_by_type,
        "skipped_unclassified_subjects": skipped_unclassified,
        "skipped_missing_fields": skipped_missing_fields,
        "classification_reference": "docs/NORMALIZZAZIONE.md",
        "acquisition_date": acquisition_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parquet_written": parquet_ok,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("righe scaricate: {}".format(len(raw_records)))
    print("relazioni scritte: {} ({})".format(
        len(relations),
        ", ".join("{}={}".format(k, v) for k, v in sorted(edges_by_type.items())),
    ))
    print("soggetti non classificati (nessun arco): {}".format(skipped_unclassified))
    print("righe saltate per campi mancanti: {}".format(skipped_missing_fields))
    print("parquet: {}".format("si" if parquet_ok else "no"))
    print("manifest: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
