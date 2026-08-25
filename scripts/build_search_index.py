"""Costruisce l'indice di ricerca SQLite/FTS5 dalle tabelle di relazione.

Consuma esclusivamente i CSV gia' presenti in data/relations/ (nessuna rete),
li normalizza in una tabella unica 'edges' con indice full-text e registra
nel database le informazioni di costruzione (provenienza dell'indice stesso).

Il database prodotto NON viene versionato: si ricostruisce con questo script.
"""

import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELATIONS_DIR = REPO_ROOT / "data" / "relations"
DB_PATH = REPO_ROOT / "data" / "search" / "explorer.db"

SOURCE_TABLES = [
    {
        "file": "persona_incarico_ente__incarichi_nominativi_shard.csv",
        "fonte_field": "fonte_url",
        "amount_field": "importo_if_present",
        "role_fields": ["role"],
        "detail_fields": ["note_source"],
    },
    {
        "file": "cig_ente__affidamenti_diretti.csv",
        "fonte_field": "source_url",
        "amount_field": "amount_if_present",
        "role_fields": [],
        "detail_fields": [],
    },
    {
        "file": "awards__affidamenti_diretti.csv",
        "fonte_field": "source_url",
        "amount_field": "amount_if_present",
        "role_fields": [],
        "detail_fields": ["regola_classificazione"],
    },
    {
        "file": "soggetti_atti__parti_atti.csv",
        "fonte_field": "fonte_url",
        "amount_field": None,
        "role_fields": ["act_kind", "authorization_object"],
        "detail_fields": [],
    },
    {
        "file": "contratti_rinnovati__rinnovi_proroghe.csv",
        "fonte_field": "fonte_url",
        "amount_field": None,
        "role_fields": ["renewal_kind"],
        "detail_fields": ["n_atti", "dal", "al", "importo_primo", "importo_ultimo", "priorita", "note_source"],
    },
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY,
    relation_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_key TEXT NOT NULL,
    period TEXT,
    acquisition_date TEXT,
    source_dataset TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    confidence_note TEXT,
    amount_if_present TEXT,
    fonte_url TEXT,
    role TEXT,
    detail_json TEXT,
    source_file TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS edges_fts USING fts5(
    subject_key, object_key, role, content=''
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def sha256_of_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source_table(config):
    path = RELATIONS_DIR / config["file"]
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records = []
        for row in reader:
            role_parts = [
                row[field] for field in config["role_fields"] if row.get(field)
            ]
            detail = {
                field: row[field]
                for field in config["detail_fields"]
                if row.get(field)
            }
            records.append({
                "relation_type": row["relation_type"],
                "subject_type": row["subject_type"],
                "subject_key": row["subject_key"],
                "object_type": row["object_type"],
                "object_key": row["object_key"],
                "period": row.get("period", ""),
                "acquisition_date": row.get("acquisition_date", ""),
                "source_dataset": row["source_dataset"],
                "source_record_id": row["source_record_id"],
                "confidence_note": row.get("confidence_note", ""),
                "amount_if_present": row.get(config["amount_field"], "") if config["amount_field"] else "",
                "fonte_url": row.get(config["fonte_field"], ""),
                "role": " — ".join(role_parts),
                "detail_json": json.dumps(detail, ensure_ascii=False) if detail else None,
                "source_file": config["file"],
            })
    return path, records


def insert_records(conn, records):
    cursor = conn.cursor()
    for record in records:
        cursor.execute(
            """INSERT INTO edges (relation_type, subject_type, subject_key,
                                   object_type, object_key, period, acquisition_date,
                                   source_dataset, source_record_id, confidence_note,
                                   amount_if_present, fonte_url, role, detail_json,
                                   source_file)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record["relation_type"], record["subject_type"], record["subject_key"],
                record["object_type"], record["object_key"], record["period"],
                record["acquisition_date"], record["source_dataset"],
                record["source_record_id"], record["confidence_note"],
                record["amount_if_present"], record["fonte_url"], record["role"],
                record["detail_json"], record["source_file"],
            ),
        )
        cursor.execute(
            "INSERT INTO edges_fts(rowid, subject_key, object_key, role) VALUES (?,?,?,?)",
            (cursor.lastrowid, record["subject_key"], record["object_key"], record["role"]),
        )


def main():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from query_engine import get_stats

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA_SQL)

    build_info = {"built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sources": []}
    total = 0
    for config in SOURCE_TABLES:
        path, records = load_source_table(config)
        insert_records(conn, records)
        total += len(records)
        build_info["sources"].append({
            "file": config["file"],
            "rows": len(records),
            "sha256": sha256_of_file(path),
        })
        print("{:>60}: {:>6} righe".format(config["file"], len(records)))

    build_info["total_edges"] = total
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('build_info', ?)",
        (json.dumps(build_info, ensure_ascii=False),),
    )
    conn.commit()

    stats = get_stats(conn)
    conn.close()

    print("")
    print("--- STATISTICHE INDICE ---")
    print("totale archi: {}".format(stats["total_edges"]))
    for relation_type, count in stats["by_relation_type"].items():
        print("{:>40}: {}".format(relation_type, count))
    print("")
    print("database: {}".format(DB_PATH))


if __name__ == "__main__":
    main()
