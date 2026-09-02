"""Estrattore del dataset 'rinnovi-proroghe' dal corpus DVNS.

Produce:
  - data/processed/rinnovi_proroghe_raw.csv   righe sorgente integrali + provenienza
  - data/relations/contratti_rinnovati__rinnovi_proroghe.(csv|parquet)
    relazioni contract_renewed conforme a schemas/relation.schema.json
  - data/relations/_manifest_rinnovi_proroghe.json

Il dataset porta evidenceLabel 'needs-explanation' e il caveat della fonte:
rinnovi, proroghe o piu' incarichi NON provano irregolarita'. Il caveat viene
riportato dentro ogni relazione emessa. Gli importi restano separati
(primo/ultimo): non vengono mai sommati ne' annualizzati.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from dvns_api import fetch_page, iter_rows  # noqa: E402


DATASET_ID = "rinnovi-proroghe"
EXPECTED_HEADERS = [
    "id", "priorita", "ente", "ipa", "nome", "n_atti", "tipo", "oggetto",
    "importo_primo", "importo_ultimo", "importo_somma", "importo_annuo",
    "dal", "al", "periodi", "url", "fonte", "note",
]

RAW_PATH = REPO_ROOT / "data" / "processed" / "rinnovi_proroghe_raw.csv"
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "contratti_rinnovati__rinnovi_proroghe.csv"
RELATIONS_PARQUET = REPO_ROOT / "data" / "relations" / "contratti_rinnovati__rinnovi_proroghe.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "relations" / "_manifest_rinnovi_proroghe.json"

RAW_COLUMNS = ["record_id", "source_id", "source_row_sha256", "source_row", "source_urls"] + EXPECTED_HEADERS

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
    "renewal_kind",
    "n_atti",
    "dal",
    "al",
    "importo_primo",
    "importo_ultimo",
    "priorita",
    "ipa",
    "fonte_url",
    "note_source",
]

CONFIDENCE_NOTE = (
    "dalla fonte: rinnovi, proroghe o più incarichi non provano irregolarità "
    "(evidence label: needs-explanation); importi primo/ultimo tenuti distinti, mai sommati o annualizzati"
)


def clean_cell(value):
    return "" if value is None else str(value).strip()


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
    record_id = clean_cell(row.get("sourceRowSha256")) or clean_cell(row.get("id"))
    return {
        "relation_type": "contract_renewed",
        "subject_type": "person",
        "subject_key": clean_cell(cells.get("nome")),
        "object_type": "public_entity",
        "object_key": clean_cell(cells.get("ente")),
        "source_dataset": DATASET_ID,
        "source_record_id": record_id,
        "period": "{} -> {}".format(clean_cell(cells.get("dal")) or "n.d.", clean_cell(cells.get("al")) or "in corso/n.d."),
        "acquisition_date": acquisition_date,
        "confidence_note": CONFIDENCE_NOTE,
        "renewal_kind": clean_cell(cells.get("tipo")),
        "n_atti": clean_cell(cells.get("n_atti")),
        "dal": clean_cell(cells.get("dal")),
        "al": clean_cell(cells.get("al")),
        "importo_primo": parse_amount(cells.get("importo_primo")),
        "importo_ultimo": parse_amount(cells.get("importo_ultimo")),
        "priorita": clean_cell(cells.get("priorita")),
        "ipa": clean_cell(cells.get("ipa")),
        "fonte_url": clean_cell(cells.get("url")),
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
    skipped = 0
    for row in iter_rows(DATASET_ID, EXPECTED_HEADERS,
                         max_rows=args.max_rows, page_limit=args.page_limit):
        cells = row.get("cells") or {}
        flat = {
            "record_id": clean_cell(row.get("id")),
            "source_id": clean_cell(cells.get("id")),
            "source_row_sha256": clean_cell(row.get("sourceRowSha256")),
            "source_row": str(clean_cell(row.get("sourceRow"))),
            "source_urls": "; ".join(row.get("sourceUrls") or []),
        }
        for header in EXPECTED_HEADERS:
            flat[header] = clean_cell(cells.get(header))
        raw_records.append(flat)

        if not flat["nome"] or not flat["ente"]:
            skipped += 1
            continue
        relations.append(build_relation(row, acquisition_date))

    write_csv(RAW_PATH, RAW_COLUMNS, raw_records)
    write_csv(RELATIONS_CSV, RELATION_COLUMNS, relations)
    parquet_ok = write_parquet(RELATIONS_PARQUET, relations)

    manifest = {
        "dataset_id": DATASET_ID,
        "expected_headers": EXPECTED_HEADERS,
        "license_status": dataset_meta.get("licenseStatus"),
        "evidence_label": dataset_meta.get("evidenceLabel"),
        "checked_at_source": (dataset_meta.get("sourceMetadata") or {}).get("checkedAt"),
        "declared_caveats": dataset_meta.get("caveats") or [],
        "matched_rows_declared": first_page.get("matchedRows"),
        "rows_downloaded": len(raw_records),
        "relations_written": len(relations),
        "rows_skipped_missing_nome_or_ente": skipped,
        "acquisition_date": acquisition_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parquet_written": parquet_ok,
        "relation_type_emitted": "contract_renewed",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("righe scaricate: {}".format(len(raw_records)))
    print("relazioni scritte: {}".format(len(relations)))
    print("righe saltate: {}".format(skipped))
    print("parquet: {}".format("si" if parquet_ok else "no"))
    print("manifest: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
