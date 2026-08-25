import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "persona_incarico_ente__incarichi_nominativi_shard.csv"
MANIFEST = REPO_ROOT / "data" / "relations" / "_manifest_incarichi_nominativi_shard.json"

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


def test_relations_file_exists_and_is_not_empty():
    rows = read_rows(RELATIONS_CSV)
    assert rows is not None, "eseguire prima extract_incarichi_nominativi_shard.py"
    assert len(rows) > 0


def test_every_relation_has_complete_provenance():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        for field in MANDATORY_RELATION_FIELDS:
            assert row.get(field, "").strip(), f"riga {index}: campo obbligatorio vuoto '{field}'"


def test_person_appointment_values_are_valid():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        assert row["relation_type"] == "person_has_appointment", f"riga {index}"
        assert row["subject_type"] == "person", f"riga {index}"
        assert row["object_type"] == "public_entity", f"riga {index}"
        assert DATE_PATTERN.match(row["acquisition_date"]), f"riga {index}"
        assert row["source_dataset"] == "incarichi-nominativi-shard"
        assert "sovrapposto" in row["confidence_note"], f"riga {index}: caveat sovrapposizione mancante"


def test_manifest_declares_run_provenance():
    import json
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in [
        "rows_downloaded",
        "relations_written",
        "rows_skipped_missing_nominativo_or_ente",
        "acquisition_date",
        "checked_at_source",
        "declared_caveats",
    ]:
        assert key in manifest, f"manifest senza '{key}'"
    assert manifest["rows_downloaded"] > 0
