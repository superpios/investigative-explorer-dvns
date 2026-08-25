"""Motore di ricerca sul grafo delle relazioni.

Funzioni pure su SQLite/FTS5: nessuna dipendenza da HTTP, cosi' la logica
di ricerca e' testabile direttamente. Il livello server e' un involucro sottile.

Sicurezza:
- solo query parametrizzate;
- la stringa utente viene ripulita dai metacaratteri FTS5 e trasformata in
  termini prefisso (token*) prima del MATCH;
- filtri ammessi solo da liste chiuse.
"""

import csv
import io
import json
import re
import sqlite3

EXPORT_COLUMNS = [
    "relation_type", "subject_key", "object_key", "period",
    "amount_if_present", "role", "source_dataset", "source_record_id",
    "acquisition_date", "fonte_url",
]


def format_results_csv(results):
    """Serializza i risultati in CSV (RFC 4180) per l'export delle redazioni."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for record in results:
        writer.writerow({column: record.get(column, "") for column in EXPORT_COLUMNS})
    return buffer.getvalue()


ALLOWED_RELATION_TYPES = (
    "person_has_appointment",
    "person_awarded_direct_award",
    "organization_has_appointment",
    "organization_awarded_cig",
    "organization_awarded_direct_award",
    "cup_has_subject",
    "cig_linked_to_entity",
    "entity_has_spending_chapter",
    "contract_renewed",
)

MAX_LIMIT = 100
DEFAULT_LIMIT = 25

_TOKEN_CLEANER = re.compile(r"[^\wÀ-ÿ]+", re.UNICODE)


def connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


_FTS_OPERATORS = {"AND", "OR", "NOT", "NEAR"}


def build_match_expression(user_query):
    """Converte l'input utente in un'espressione FTS5 sicura di termini prefisso."""
    tokens = [_TOKEN_CLEANER.sub("", token) for token in str(user_query).split()]
    tokens = [token for token in tokens if token and token not in _FTS_OPERATORS]
    if not tokens:
        return None
    return " ".join("{}*".format(token) for token in tokens)


def search_edges(conn, user_query, relation_type=None, limit=DEFAULT_LIMIT):
    """Cerca archi per termini presenti in soggetto, oggetto o ruolo."""
    match_expr = build_match_expression(user_query)
    if not match_expr:
        return []

    sql = """
        SELECT e.id, e.relation_type, e.subject_type, e.subject_key,
               e.object_type, e.object_key, e.period, e.acquisition_date,
               e.source_dataset, e.source_record_id, e.confidence_note,
               e.amount_if_present, e.fonte_url, e.role, e.detail_json,
               bm25(edges_fts) AS rank_score
        FROM edges_fts
        JOIN edges e ON e.id = edges_fts.rowid
        WHERE edges_fts MATCH ?
    """
    params = [match_expr]

    if relation_type:
        if relation_type not in ALLOWED_RELATION_TYPES:
            raise ValueError("relation_type non ammesso")
        sql += " AND e.relation_type = ?"
        params.append(relation_type)

    try:
        capped_limit = int(limit)
    except (TypeError, ValueError):
        capped_limit = DEFAULT_LIMIT
    capped_limit = max(1, min(capped_limit, MAX_LIMIT))
    sql += " ORDER BY rank_score LIMIT ?"
    params.append(capped_limit)

    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        record = dict(row)
        record.pop("rank_score", None)
        record["detail"] = (
            json.loads(record.pop("detail_json")) if record.get("detail_json") else {}
        )
        results.append(record)
    return results


def get_stats(conn):
    conn.row_factory = sqlite3.Row
    stats = {
        "total_edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        "by_relation_type": {
            row["relation_type"]: row["n"]
            for row in conn.execute(
                "SELECT relation_type, COUNT(*) AS n FROM edges GROUP BY relation_type ORDER BY n DESC"
            )
        },
        "by_source_dataset": {
            row["source_dataset"]: row["n"]
            for row in conn.execute(
                "SELECT source_dataset, COUNT(*) AS n FROM edges GROUP BY source_dataset ORDER BY n DESC"
            )
        },
    }
    meta_row = conn.execute(
        "SELECT value FROM meta WHERE key = 'build_info'"
    ).fetchone()
    stats["build_info"] = json.loads(meta_row["value"]) if meta_row else None
    return stats
