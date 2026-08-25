import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from query_engine import connect, get_stats, search_edges, build_match_expression  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "search" / "explorer.db"
RELATIONS_DIR = REPO_ROOT / "data" / "relations"


@pytest.fixture(scope="module")
def conn():
    assert DB_PATH.exists(), "indice assente: eseguire scripts/build_search_index.py"
    return connect(DB_PATH)


def manifest_total():
    total = 0
    for manifest_path in RELATIONS_DIR.glob("_manifest_*.json"):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        total += data.get("relations_written") or data.get("edges_written")
    return total


def test_stats_total_matches_sum_of_manifests(conn):
    stats = get_stats(conn)
    expected = manifest_total()
    assert stats["total_edges"] == expected, f"indice {stats['total_edges']} != manifest {expected}"
    assert sum(stats["by_relation_type"].values()) == expected
    assert stats["build_info"]["sources"], "build_info senza sorgenti"


def test_search_finds_known_person_award_case(conn):
    hits = search_edges(conn, "FRIONI")
    assert hits, "caso noto AVV. IVAN FRIONI non trovato"
    hit = hits[0]
    assert hit["relation_type"] == "person_awarded_direct_award"
    assert hit["source_dataset"] == "affidamenti-diretti"
    assert hit["fonte_url"].startswith("https://")


def test_search_finds_known_repeated_appointment_case(conn):
    hits = search_edges(conn, "RALLO ALICE")
    assert len(hits) >= 2, "i due incarichi consecutivi di RALLO ALICE devono emergere entrambi"


def test_search_finds_known_renewal_case(conn):
    hits = search_edges(conn, "FANTAUZZI", relation_type="contract_renewed")
    assert hits, "caso noto FANTAUZZI non trovato tra i rinnovi"
    assert "->" in hits[0]["period"]


def test_search_by_entity_abbreviation(conn):
    hits = search_edges(conn, "AIFA")
    assert hits, "ricerca per sigla ente senza risultati"
    assert all("aifa" in (h["object_key"] or "").lower() for h in hits), \
        "tutti i risultati devono riferirsi all'Agenzia Italiana del Farmaco - AIFA"


def test_fts_injection_attempt_is_harmless(conn):
    before = get_stats(conn)["total_edges"]
    malicious = '"; DROP TABLE edges; --'
    hits = search_edges(conn, malicious)
    after = get_stats(conn)["total_edges"]
    assert after == before > 0
    assert isinstance(hits, list)


def test_empty_or_noise_queries_return_empty_list(conn):
    assert search_edges(conn, "") == []
    assert search_edges(conn, "   ") == []
    assert search_edges(conn, "!!! ???") == []


def test_limit_is_capped_even_when_user_asks_more(conn):
    hits = search_edges(conn, "SRL", limit=9999)
    assert 0 < len(hits) <= 100


def test_invalid_relation_type_is_rejected(conn):
    with pytest.raises(ValueError):
        search_edges(conn, "FRIONI", relation_type="DROP TABLE edges")


def test_match_expression_strips_fts_metacharacters():
    assert build_match_expression('rossi "AND" (mario)') == "rossi* mario*"
    expr = build_match_expression('a"b NEAR/10 c^')
    assert expr == "ab* NEAR10* c*"
    assert build_match_expression("dott ssa verdi") == "dott* ssa* verdi*"
