import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AWARDS_CSV = REPO_ROOT / "data" / "relations" / "awards__affidamenti_diretti.csv"
RAW_CSV = REPO_ROOT / "data" / "processed" / "affidamenti_diretti_raw.csv"
CLASSIFICATION_CSV = REPO_ROOT / "data" / "processed" / "contraenti_classificazione.csv"
MANIFEST = REPO_ROOT / "data" / "relations" / "_manifest_contraenti.json"

MANDATORY_RELATION_FIELDS = [
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
]
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_rows(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def raw_sha_index():
    rows = read_rows(RAW_CSV)
    return {row["source_row_sha256"] for row in rows}


def test_awards_file_exists_and_matches_manifest():
    import json
    rows = read_rows(AWARDS_CSV)
    assert rows is not None, "eseguire prima classify_contraenti.py senza --dry-run"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(rows) == manifest["edges_written"]
    assert sum(manifest["edges_by_type"].values()) == manifest["edges_written"]


def test_every_edge_has_complete_provenance_and_valid_values():
    for index, row in enumerate(read_rows(AWARDS_CSV), start=1):
        for field in MANDATORY_RELATION_FIELDS:
            assert row.get(field, "").strip(), f"riga {index}: campo vuoto '{field}'"
        assert row["relation_type"] in (
            "person_awarded_direct_award",
            "organization_awarded_direct_award",
        ), f"riga {index}"
        assert row["subject_type"] == row["relation_type"].split("_")[0], f"riga {index}"
        assert row["object_type"] == "public_entity", f"riga {index}"
        assert DATE_PATTERN.match(row["acquisition_date"]), f"riga {index}"
        assert "NORMALIZZAZIONE.md" in row["confidence_note"], f"riga {index}"


def test_no_invented_edges_every_hash_exists_in_raw_source():
    known_shas = raw_sha_index()
    assert known_shas, "file raw vuoto o assente"
    for index, row in enumerate(read_rows(AWARDS_CSV), start=1):
        sha = row["source_record_id"]
        assert sha in known_shas, f"riga {index}: hash {sha} assente dal raw - arco inventato!"


def test_classification_table_covers_every_classified_subject():
    classification = {}
    for row in read_rows(CLASSIFICATION_CSV):
        classification[row["contraente_key"]] = row["classificazione"]
    for index, row in enumerate(read_rows(AWARDS_CSV), start=1):
        key = row["subject_key"]
        assert key in classification, f"riga {index}: soggetto '{key}' non in anagrafica classificazione"
        assert classification[key] == row["subject_type"], f"riga {index}: classe disallineata"


def test_known_person_case_from_api_probe_is_classified():
    rows = read_rows(CLASSIFICATION_CSV)
    frioni = [r for r in rows if r["contraente_key"] == "AVV. IVAN FRIONI"]
    assert frioni, "caso noto 'Avv. Ivan Frioni' mancante dall'anagrafica"
    assert frioni[0]["classificazione"] == "person"
