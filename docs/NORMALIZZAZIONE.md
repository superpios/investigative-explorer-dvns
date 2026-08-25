# Normalizzazione — classificazione dei contraenti

Documento di riferimento per la fase `normalize` applicata al dataset `affidamenti-diretti`. Le regole sono implementate in `scripts/normalize/classification_rules.py`, sono deterministiche e ogni classificazione riporta l'identificativo della regola che l'ha prodotta.

## Principio

**Nessuna inferenza oltre i segnali espliciti.** Un nome contraente viene classificato solo se contiene un segnale inequivocabile; in caso contrario resta `non_classificato` e **non genera alcun arco** nel grafo. La classificazione mancata non è un errore: è il comportamento corretto.

## Regole persona

Il primo token del nome normalizzato (punti rimossi) deve coincidere con un titolo professionale:

| Regola | Titoli riconosciuti |
| --- | --- |
| `per_avv` | AVV., AVVOCATO |
| `per_dott` | DOTT., DOTTORE, DOTT.SSA, DOTTORESSA |
| `per_dr` | DR., DRA |
| `per_ing` | ING., INGEGNERE |
| `per_geom` | GEOM., GEOMETRA |
| `per_rag` | RAG., RAGIONIERE |
| `per_prof` | PROF., PROF.SSA, PROFESSORE |
| `per_arch` | ARCH., ARCHITETTO |
| `per_notaio` | NOTAIO |

## Regole organizzazione

Il nome deve contenere una forma giuridica o denominazione sociale esplicita:

| Regola | Segnale |
| --- | --- |
| `org_srl` / `org_spa` / `org_sapa` / `org_snc` / `org_sas` | forme societarie di capitali e persone, con o senza punti |
| `org_scarl` / `org_scrle` / `org_scrl` | cooperative sociali |
| `org_cooperativa` | COOPERATIVA / COOPERATIVO |
| `org_coop_abbrev` | COOP. abbreviato |
| `org_associazione` | ASSOCIAZIONE, ASS. |
| `org_fondazione` | FONDAZIONE |
| `org_consortium` | CONSORZIO |
| `org_ditta_impresa` | DITTA, IMPRESA seguiti da spazio |
| `org_studio_prof` | STUDIO PROFESSIONALE, STUDIO ASSOCIATO |
| `org_societa_generica` | SOCIETÀ / SOCIETA' / SOCIETA |

## Cosa NON viene classificato (deliberatamente)

- Nomi senza alcun segnale (`ROSSI MARIO`, `CENTRO MEDICO SANTA LUCIA`, `ACCENTURE`): potrebbero essere persone o società; non si indovina.
- Ditte individuali nella forma `X DI COGNOME NOME` (es. `A72 DI CHIORLIN`): pattern frequente nei dati ma ambiguo; eventuale regola dedicata va discussa e documentata prima dell'attivazione.
- Frammenti testuali derivati dai documenti sorgente (`AFFIDATARIO DICHIARA E GARANTISCE…`).
- Valori vuoti, `n.d.`, `NULLO`, `ANONIMO`.

## Chiavi normalizzate

La chiave del soggetto è: testo originale → trim → collasso spazi multipli → maiuscole. Nessuna ulteriore manipolazione (niente rimozione accenti o punteggiatura): due grafie diverse restano due chiavi distinte, coerentemente con la regola anti-omonimia di docs/LIMITI.md.

## Esito della prima applicazione (agosto 2026)

Su 6.506 righe di `affidamenti-diretti`: 171 occorrenze classificate persona, 1.471 organizzazione, 4.213 valori vuoti/`n.d.`, ~651 nomi reali lasciati deliberatamente non classificati. Archi emessi: 1.642, tutti verificati contro l'hash SHA-256 della riga sorgente dal test `test_no_invented_edges_every_hash_exists_in_raw_source`.
