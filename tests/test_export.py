import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from query_engine import EXPORT_COLUMNS, format_results_csv  # noqa: E402


def sample_results():
    return [
        {
            "relation_type": "person_awarded_direct_award",
            "subject_key": "AVV. IVAN FRIONI",
            "object_key": "AGENZIA ITALIANA DEL FARMACO - AIFA",
            "period": "2024-01-01",
            "amount_if_present": "81000.0",
            "role": "",
            "source_dataset": "affidamenti-diretti",
            "source_record_id": "abc123",
            "acquisition_date": "2026-08-25",
            "fonte_url": "https://example.org/atto",
            "detail": {"private": "non deve finire nell'export"},
        },
        {
            "relation_type": "organization_awarded_direct_award",
            "subject_key": "ALFA, SRL E CONSORTI",  # virgola -> deve essere quotata
            "object_key": "ENTE PUBBLICO X",
            "period": "n.d.",
            "amount_if_present": "",
            "role": "servizio",
            "source_dataset": "affidamenti-diretti",
            "source_record_id": "def456",
            "acquisition_date": "2026-08-25",
            "fonte_url": "",
        },
    ]


def test_csv_header_matches_declared_columns():
    csv_text = format_results_csv(sample_results())
    header = csv_text.splitlines()[0]
    assert header == ",".join(EXPORT_COLUMNS)


def test_csv_quotes_fields_containing_commas():
    csv_text = format_results_csv(sample_results())
    second_data_line = csv_text.splitlines()[2]
    assert '"ALFA, SRL E CONSORTI"' in second_data_line


def test_csv_excludes_internal_detail_keys():
    csv_text = format_results_csv(sample_results())
    assert "private" not in csv_text
    assert "non deve finire" not in csv_text


def test_csv_keeps_provenance_columns_populated():
    lines = format_results_csv(sample_results()).strip().splitlines()
    assert len(lines) == 3
    first = lines[1]
    assert "affidamenti-diretti" in first
    assert "abc123" in first
    assert "https://example.org/atto" in first
