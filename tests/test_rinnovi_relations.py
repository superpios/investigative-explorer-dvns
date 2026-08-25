import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELATIONS_CSV = REPO_ROOT / "data" / "relations" / "contratti_rinnovati__rinnovi_proroghe.csv"
MANIFEST = REPO_ROOT / "data" / "relations" / "_manifest_rinnovi_proroghe.json"

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
    import json
    rows = read_rows(RELATIONS_CSV)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(rows) == manifest["relations_written"]
    assert len(rows) > 0


def test_every_relation_has_complete_provenance_and_caveat():
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        for field in MANDATORY_RELATION_FIELDS:
            assert row.get(field, "").strip(), f"riga {index}: campo vuoto '{field}'"
        assert row["relation_type"] == "contract_renewed"
        assert row["subject_type"] == "person"
        assert row["object_type"] == "public_entity"
        assert DATE_PATTERN.match(row["acquisition_date"])
        assert "non provano irregolarità" in row["confidence_note"], \
            f"riga {index}: caveat fonte mancante"


def test_amounts_are_kept_distinct_never_summed():
    rows = read_rows(RELATIONS_CSV)
    with open(REPO_ROOT / "data" / "processed" / "rinnovi_proroghe_raw.csv", encoding="utf-8") as handle:
        raw = list(csv.DictReader(handle))
    raw_by_sha = {r["source_row_sha256"]: r for r in raw}
    for index, row in enumerate(read_rows(RELATIONS_CSV), start=1):
        source = raw_by_sha[row["source_record_id"]]
        assert float(row["importo_primo"]) == float(source["importo_primo"].replace(",", ".")) \
            if row["importo_primo"] else True, f"riga {index}: importo_primo alterato"
        assert "importo_somma" not in row.keys() or row.get("importo_somma") is None


def test_manifest_declares_run_provenance():
    import json
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in [
        "rows_downloaded",
        "relations_written",
        "evidence_label",
        "declared_caveats",
        "checked_at_source",
        "acquisition_date",
    ]:
        assert key in manifest
    assert manifest["evidence_label"] == "needs-explanation"
    assert manifest["rows_downloaded"] == manifest["matched_rows_declared"]
