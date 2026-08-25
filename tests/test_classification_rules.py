import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts" / "normalize"
sys.path.insert(0, str(SCRIPT_DIR))

from classification_rules import classify, normalize_key


PERSON_CASES = [
    ("Avv. Ivan Frioni", "per_avv"),
    ("AVV. BIANCHI ANDREA", "per_avv"),
    ("Dott. Rossi Mario", "per_dott"),
    ("DOTT.SSA VERDI LUISA", "per_dott"),
    ("Dr. Esposito Giuseppe", "per_dr"),
    ("Ing. Conti Paolo", "per_ing"),
    ("Geom. Ferrari Anna", "per_geom"),
    ("Rag. Greco Vincenzo", "per_rag"),
    ("Prof. Romano Carlo", "per_prof"),
    ("Arch. Gallo Maria", "per_arch"),
]

ORGANIZATION_CASES = [
    ("ALFA COSTRUZIONI S.R.L.", "org_srl"),
    ("BETA SERVIZI SRLS", "org_srl"),
    ("GAMMA HOLDING S.p.A.", "org_spa"),
    ("DELTA ENERGIA SAPA", "org_sapa"),
    ("EPSILON TRASPORTI S.N.C.", "org_snc"),
    ("ZETA CONSULENZE SAS", "org_sas"),
    ("ETA FACILITIES S.C.A.R.L.", "org_scarl"),
    ("SOC. COOP. TRACCIA", "org_coop_abbrev"),
    ("ASSOCIAZIONE ARCI LOCALE", "org_associazione"),
    ("FONDAZIONE SANITA Città", "org_fondazione"),
    ("CONSORZIO ACQUE POTABILI", "org_consortium"),
    ("DITTA LAVORI EDILI BIANCHI", "org_ditta_impresa"),
    ("STUDIO PROFESSIONALE ASSOCIATO KAPPA", "org_studio_prof"),
    ("SOCIETA' GENERICA DI SERVIZI", "org_societa_generica"),
]

UNCLASSIFIED_CASES = [
    ("ROSSI MARIO", "nessun_segnale_esplicito"),
    ("FRIONI IVAN", "nessun_segnale_esplicito"),
    ("CENTRO MEDICO SANTA LUCIA", "nessun_segnale_esplicito"),
    ("POLIAMBULATORIO CITTADINO", "nessun_segnale_esplicito"),
]

EMPTY_CASES = ["", "   ", "n.d.", "N.D.", None]


def test_known_person_titles_are_detected():
    for value, expected_rule in PERSON_CASES:
        klass, rule = classify(value)
        assert klass == "person", f"'{value}' doveva essere person, ottenuto {klass}"
        assert rule == expected_rule, f"'{value}': attesa regola {expected_rule}, ottenuta {rule}"


def test_known_legal_forms_are_detected():
    for value, expected_rule in ORGANIZATION_CASES:
        klass, rule = classify(value)
        assert klass == "organization", f"'{value}' doveva essere organization, ottenuto {klass}"
        assert rule == expected_rule, f"'{value}': attesa regola {expected_rule}, ottenuta {rule}"


def test_ambiguous_names_are_never_guessed():
    for value, expected_rule in UNCLASSIFIED_CASES:
        klass, rule = classify(value)
        assert klass is None, f"'{value}' NON deve essere classificato, ma è risultato {klass}"
        assert rule == expected_rule


def test_empty_values_return_none_without_rule_noise():
    for value in EMPTY_CASES:
        klass, rule = classify(value)
        assert klass is None
        assert rule == "valore_vuoto"


def test_normalize_key_is_stable():
    assert normalize_key("  Avv.   Ivan  Frioni ") == "AVV. IVAN FRIONI"
    assert normalize_key(None) == ""
