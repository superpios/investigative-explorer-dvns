"""Regole di classificazione conservativa dei contraenti.

Classificano il valore della colonna 'contraente' in 'person', 'organization'
o None (non classificato). La classe non classificata NON produce alcun arco:
e' l'applicazione diretta del principio di fail-closed metodologico.

Le regole sono deterministiche, ordinate e ispezionabili; ogni classificazione
riporta l'identificativo della regola che l'ha prodotta.
"""

import re


ORGANIZATION_LEGAL_FORMS = [
    ("org_srl", re.compile(r"\bS\.?\s?R\.?L\.?S?\.?(?=\b|\s|$)")),
    ("org_spa", re.compile(r"\bS\.?\s?P\.?A\.?(?=\b|\s|$)")),
    ("org_sapa", re.compile(r"\bS\.?\s?A\.?P\.?A\.?(?=\b|\s|$)")),
    ("org_snc", re.compile(r"\bS\.?\s?N\.?C\.?(?=\b|\s|$)")),
    ("org_sas", re.compile(r"\bS\.?\s?A\.?S\.?(?=\b|\s|$)")),
    ("org_scarl", re.compile(r"\bS\.?\s?C\.?\s?A\.?R\.?L\.?(?=\b|\s|$)")),
    ("org_scrle", re.compile(r"\bS\.?\s?C\.?\s?R\.?L\.?E\.?(?=\b|\s|$)")),
    ("org_scrl", re.compile(r"\bS\.?\s?C\.?\s?R\.?L\.?(?=\b|\s|$)")),
    ("org_cooperativa", re.compile(r"\bCOOPERATIV[AE]\b")),
    ("org_coop_abbrev", re.compile(r"(?<![A-Z])COOP\.(?![A-Z])")),
    ("org_associazione", re.compile(r"\bASSOCIAZIONE\b|\bASS\.\s")),
    ("org_fondazione", re.compile(r"\bFONDAZIONE\b")),
    ("org_consortium", re.compile(r"\bCONSORZIO\b")),
    ("org_ditta_impresa", re.compile(r"\bDITTA\b\s|\bIMPRESA\b\s")),
    ("org_studio_prof", re.compile(r"\bSTUDIO\s+PROFESSIONALE\b|\bSTUDIO\s+ASSOCIATO\b")),
    ("org_societa_generica", re.compile(r"\bSOCIET(?:À|A'|A)(?=\s)")),
]

TITLE_RULE_IDS = {
    "AVV": "per_avv",
    "AVVOCATO": "per_avv",
    "DOTT": "per_dott",
    "DOTTORE": "per_dott",
    "DOTTSSA": "per_dott",
    "DOTTORESSA": "per_dott",
    "DR": "per_dr",
    "DRA": "per_dr",
    "ING": "per_ing",
    "INGEGNERE": "per_ing",
    "GEOM": "per_geom",
    "GEOMETRA": "per_geom",
    "RAG": "per_rag",
    "RAGIONIERE": "per_rag",
    "PROF": "per_prof",
    "PROFSSA": "per_prof",
    "PROFESSORE": "per_prof",
    "ARCH": "per_arch",
    "ARCHITETTO": "per_arch",
    "NOTAIO": "per_notaio",
}

EMPTY_VALUES = {"", "N.D.", "ND", "NULLO", "ANONIMO"}

RULE_EMPTY = "valore_vuoto"
RULE_UNRESOLVED = "nessun_segnale_esplicito"


def normalize_key(value):
    """Chiave stabile: trim, collasso spazi, maiuscole."""
    return " ".join(str(value or "").split()).upper()


def classify(contraente):
    """Restituisce (classe, regola) senza mai inferire oltre i segnali espliciti."""
    key = normalize_key(contraente)

    if not key or key in EMPTY_VALUES:
        return None, RULE_EMPTY

    first_token = key.split(" ", 1)[0].replace(".", "")
    if first_token in TITLE_RULE_IDS:
        return "person", TITLE_RULE_IDS[first_token]

    for rule_id, pattern in ORGANIZATION_LEGAL_FORMS:
        if pattern.search(key):
            return "organization", rule_id

    return None, RULE_UNRESOLVED
