import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "normalize"))

from classification_rules import classify  # noqa: E402

RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "soggetti_atti__parti_atti.csv"
RAW_CSV = REPO_ROOT / "data" / "processed" / "parti_atti_raw.csv"
MANIFEST = REPO_ROOT / "data" / "relations" / "_manifest_parti_atti.json"

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
    assert path.exists(), f"file mancante: {path.name}"
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_relations_file_exists_and_matches_manifest():
    rows = read_rows(RELATIONS_CSV)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(rows) == manifest["relations_written"]
    assert sum(manifest["edges_by_type"].values()) == manifest["relations_written"]
    assert manifest["rows_downloaded"] == manifest["matched_rows_declared"]


def test_every_relation_has_complete_provenance_and_caveat():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        for field in MANDATORY_RELATION_FIELDS:
            assert row.get(field, "").strip(), f"riga {index}: campo vuoto '{field}'"
        assert DATE_PATTERN.match(row["acquisition_date"]), f"riga {index}"
        assert "istanza fisica di atto" in row["confidence_note"], f"riga {index}"
        assert row["object_type"] == "public_entity"


def test_subject_classification_is_reproducible_and_never_invented():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        klass, _rule = classify(row["subject_key"])
        assert klass == row["subject_type"], \
            f"riga {index}: classificazione non riproducibile ({row['subject_key']})"
        expected_type = "{}_has_appointment".format(klass)
        assert row["relation_type"] == expected_type, f"riga {index}"


def test_emitted_edges_equal_full_reclassification_of_raw():
    rows = read_rows(RELATIONS_CSV)
    raw = read_rows(RAW_CSV)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    recomputed = 0
    for source in raw:
        key = " ".join((source.get("chi_ricevuto") or "").split()).upper()
        ente = (source.get("ente") or "").strip()
        if not key or not ente or key in ("N.D.", "ND"):
            continue
        klass, _rule = classify(key)
        if klass is not None:
            recomputed += 1
    assert recomputed == manifest["relations_written"]
    assert len(rows) == recomputed
