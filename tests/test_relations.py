import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "cig_ente__affidamenti_diretti.csv"
RAW_CSV = REPO_ROOT / "data" / "processed" / "affidamenti_diretti_raw.csv"
MANIFEST = REPO_ROOT / "data" / "relations" / "_manifest_affidamenti_diretti.json"
EXPECTED_SOURCE_HEADERS = ["ente", "ipa", "cig", "contraente", "cf", "importo", "oggetto", "data", "url"]

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
ALLOWED_RELATION_TYPES = {
    "person_has_appointment",
    "organization_awarded_cig",
    "organization_awarded_direct_award",
    "cup_has_subject",
    "cig_linked_to_entity",
    "entity_has_spending_chapter",
    "contract_renewed",
}
ALLOWED_ENTITY_TYPES = {"person", "organization", "public_entity", "cig", "cup", "spending_chapter"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_rows(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_relations_file_exists_and_is_not_empty():
    rows = read_rows(RELATIONS_CSV)
    assert rows is not None, "eseguire prima scripts/extract/extract_affidamenti_diretti.py"
    assert len(rows) > 0


def test_every_relation_has_complete_provenance():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        for field in MANDATORY_RELATION_FIELDS:
            assert row.get(field, "").strip(), f"riga {index}: campo obbligatorio vuoto '{field}'"


def test_relation_values_are_valid_against_schema():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        assert row["relation_type"] in ALLOWED_RELATION_TYPES, f"riga {index}: relation_type non valido"
        assert row["subject_type"] in ALLOWED_ENTITY_TYPES, f"riga {index}: subject_type non valido"
        assert row["object_type"] in ALLOWED_ENTITY_TYPES, f"riga {index}: object_type non valido"
        assert DATE_PATTERN.match(row["acquisition_date"]), f"riga {index}: acquisition_date non valida"
        assert row["source_dataset"] == "affidamenti-diretti"


def test_raw_preservation_keeps_source_headers():
    rows = read_rows(RAW_CSV)
    assert rows is not None, "file raw mancante: rieseguire l'estrattore"
    expected = ["record_id", "source_row_sha256", "source_row", "source_urls"] + EXPECTED_SOURCE_HEADERS
    assert list(rows[0].keys()) == expected


def test_manifest_declares_run_provenance():
    import json
    assert MANIFEST.exists(), "manifest mancante: rieseguire l'estrattore"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in [
        "rows_downloaded",
        "relations_written",
        "rows_skipped_missing_cig_or_ente",
        "acquisition_date",
        "license_status",
        "checked_at_source",
    ]:
        assert key in manifest, f"manifest senza '{key}'"
    assert manifest["rows_downloaded"] > 0
