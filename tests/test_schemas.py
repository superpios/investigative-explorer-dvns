import json
from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"

EXPECTED_ENTITY_TYPES = [
    "person",
    "organization",
    "public_entity",
    "cig",
    "cup",
    "spending_chapter",
]

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


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_entities_registry_contains_canonical_types():
    registry = load("entities.json")
    types = [e["type"] for e in registry["entities"]]
    assert types == EXPECTED_ENTITY_TYPES
    for entity in registry["entities"]:
        assert entity["source_datasets"], f"entità senza fonti: {entity['type']}"


def test_relation_schema_declares_all_mandatory_fields():
    schema = load("relation.schema.json")
    for field in MANDATORY_RELATION_FIELDS:
        assert field in schema["required"], f"campo obbligatorio mancante: {field}"
        assert field in schema["properties"], f"proprietà non definita: {field}"


def test_relation_schema_entity_types_match_registry():
    registry = load("entities.json")
    schema = load("relation.schema.json")
    expected = set(EXPECTED_ENTITY_TYPES)
    assert set(schema["properties"]["subject_type"]["enum"]) == expected
    assert set(schema["properties"]["object_type"]["enum"]) == expected
