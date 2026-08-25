"""Classificazione conservativa dei contraenti di 'affidamenti-diretti'.

Consuma le righe RAW gia' scaricate (nessuna nuova chiamata API) e produce:
  - data/processed/contraenti_classificazione.csv   anagrafica delle chiavi classificate
  - data/relations/awards__affidamenti_diretti.(csv|parquet)
    archi person_awarded_direct_award / organization_awarded_direct_award
  - data/relations/_manifest_contraenti.json

--dry-run calcola e stampa solo la distribuzione delle classificazioni,
senza scrivere alcun file di relazione.
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
sys.path.insert(0, str(SCRIPT_DIR))

from classification_rules import RULE_EMPTY, RULE_UNRESOLVED, classify, normalize_key  # noqa: E402


RAW_PATH = REPO_ROOT / "data" / "processed" / "affidamenti_diretti_raw.csv"
CLASSIFICATION_PATH = REPO_ROOT / "data" / "processed" / "contraenti_classificazione.csv"
AWARDS_CSV = REPO_ROOT / "data" / "relations" / "awards__affidamenti_diretti.csv"
AWARDS_PARQUET = REPO_ROOT / "data" / "relations" / "awards__affidamenti_diretti.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "relations" / "_manifest_contraenti.json"

AWARD_COLUMNS = [
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
    "regola_classificazione",
]

CONFIDENCE_NOTE = (
    "classificazione contraente da regole conservative documentate in docs/NORMALIZZAZIONE.md; "
    "i nomi non classificati non generano arco"
)


def parse_amount(value):
    text = str(value or "").strip().replace(",", ".")
    if not text or text.lower() in ("n.d.", "nd"):
        return ""
    try:
        return repr(round(float(text), 2))
    except ValueError:
        return ""


def load_raw_rows():
    with RAW_PATH.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_classification_table(rows):
    occurrences = Counter()
    rules_seen = {}
    for row in rows:
        key = normalize_key(row.get("contraente"))
        if not key:
            continue
        klass, rule = classify(key)
        if klass is None:
            klass_display = "non_classificato"
        else:
            klass_display = klass
        occurrences[(key, klass_display, rule)] += 1
        rules_seen.setdefault((key, klass_display), rule)

    table = []
    for (key, klass_display, rule), count in sorted(occurrences.items()):
        table.append({
            "contraente_key": key,
            "classificazione": klass_display,
            "regola": rule,
            "occorrenze": count,
        })
    return table


def summarize(table):
    by_class = Counter()
    by_rule = Counter()
    for entry in table:
        by_class[entry["classificazione"]] += entry["occorrenze"]
        by_rule[entry["regola"]] += entry["occorrenze"]
    return by_class, by_rule


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra solo la distribuzione, non scrive relazioni")
    args = parser.parse_args()

    rows = load_raw_rows()
    acquisition_date = datetime.now(timezone.utc).date().isoformat()

    table = build_classification_table(rows)
    by_class, by_rule = summarize(table)

    print("--- DISTRIBUZIONE CLASSI (su occorrenze riga) ---")
    for klass in ("person", "organization", "non_classificato"):
        print("{:>18}: {}".format(klass, by_class.get(klass, 0)))
    print("")
    print("--- DISTRIBUZIONE REGOLE ---")
    for rule, count in sorted(by_rule.items(), key=lambda item: -item[1]):
        print("{:>28}: {}".format(rule, count))

    unclassified_examples = [
        entry["contraente_key"] for entry in table
        if entry["classificazione"] == "non_classificato"
    ]
    print("")
    print("--- ESEMPI NON CLASSIFICATI (primi 15) ---")
    for example in unclassified_examples[:15]:
        print(example)

    if args.dry_run:
        return

    CLASSIFICATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CLASSIFICATION_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "contraente_key", "classificazione", "regola", "occorrenze",
        ])
        writer.writeheader()
        for entry in table:
            writer.writerow(entry)

    edges = []
    for row in rows:
        key = normalize_key(row.get("contraente"))
        klass, rule = classify(key)
        ente = " ".join(str(row.get("ente") or "").split()).upper()
        if klass is None or not key or not ente:
            continue
        edges.append({
            "relation_type": "{}_awarded_direct_award".format(klass),
            "subject_type": klass,
            "subject_key": key,
            "object_type": "public_entity",
            "object_key": ente,
            "source_dataset": "affidamenti-diretti",
            "source_record_id": row.get("source_row_sha256") or row.get("record_id"),
            "period": row.get("data") or "n.d.",
            "acquisition_date": acquisition_date,
            "confidence_note": CONFIDENCE_NOTE,
            "amount_if_present": parse_amount(row.get("importo")),
            "ipa": row.get("ipa") or "",
            "source_url": row.get("url") or "",
            "regola_classificazione": rule,
        })

    AWARDS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AWARDS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AWARD_COLUMNS)
        writer.writeheader()
        for edge in edges:
            writer.writerow(edge)

    try:
        import pandas as pd
        pd.DataFrame(edges, columns=AWARD_COLUMNS).to_parquet(AWARDS_PARQUET, index=False)
        parquet_ok = True
    except ImportError:
        parquet_ok = False

    manifest = {
        "dataset_id": "affidamenti-diretti",
        "input_file": str(RAW_PATH.relative_to(REPO_ROOT)),
        "rows_input": len(rows),
        "distinct_contraenti": len(table),
        "class_person_occurrences": by_class.get("person", 0),
        "class_organization_occurrences": by_class.get("organization", 0),
        "class_unclassified_occurrences": by_class.get("non_classificato", 0),
        "edges_written": len(edges),
        "edges_by_type": dict(Counter(e["relation_type"] for e in edges)),
        "rules_reference": "scripts/normalize/classification_rules.py + docs/NORMALIZZAZIONE.md",
        "acquisition_date_source_data": rows[0].get("url", "") != "",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parquet_written": parquet_ok,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("archi scritti: {} ({})".format(
        len(edges),
        ", ".join("{}={}".format(k, v) for k, v in manifest["edges_by_type"].items()),
    ))
    print("manifest: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
