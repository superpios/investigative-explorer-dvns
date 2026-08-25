# Metodologia

Come vengono costruiti i collegamenti tra entità. Il principio guida è: **nessun collegamento che non sia dimostrabile dai dati sorgente**.

## Pipeline

dataset sorgente DVNS → extract → normalize → validate → data/relations/

1. **Estrazione** (`scripts/extract/`): ogni script legge un dataset sorgente e produce una tabella di relazione tipizzata (persona→incarico→ente, CIG→aggiudicatario, CUP→soggetto, ecc.). Gli script sono *fail-closed*: se lo schema del file di input cambia rispetto a quanto dichiarato, l'esecuzione si interrompe senza produrre output.
2. **Normalizzazione** (`scripts/normalize/`): pulizia conservativa dei nomi (maiuscole/minuscole, spazi multipli, caratteri di controllo). Nessuna deduplicazione aggressiva: due nomi simili restano entità distinte.
3. **Validazione** (`scripts/validate/` + `tests/`): presenza dei campi obbligatori, coerenza delle date, esistenza della provenienza. I test falliscono se manca anche uno solo degli elementi richiesti.
4. **Controllo manuale**: dopo ogni estrazione viene verificato un campione di 20–30 righe contro la fonte originale.

## Campi obbligatori di ogni relazione

| Campo | Significato |
| --- | --- |
| `relation_type` | Tipo di relazione secondo `schemas/relation.schema.json` |
| `source_dataset` | ID del dataset sorgente nel catalogo DVNS |
| `source_record_id` | Identificativo o hash del record originale |
| `period` | Periodo di riferimento del dato |
| `acquisition_date` | Data di acquisizione dello snapshot |
| `confidence_note` | Nota su copertura e limiti della fonte per quel record |

Una tabella di relazione priva di uno qualsiasi di questi campi non è valida e non entra in `data/relations/`.

## Entità canoniche

Le sei entità collegabili sono definite in `schemas/entities.json`: `person`, `organization`, `public_entity`, `cig`, `cup`, `spending_chapter`. Ogni nodo del grafo appartiene a una di queste classi; ogni arco porta con sé la provenienza completa.

## Riproducibilità

- Le pipeline sono deterministiche: a parità di input producono output identici.
- Ogni rilascio delle tabelle di relazione registra la versione del corpus DVNS utilizzata (hash del rilascio e data).
- L'aggiornamento segue il ciclo di pubblicazione degli snapshot DVNS: si scarica il nuovo snapshot, si riesegue la pipeline, si confrontano gli output con il rilascio precedente prima di pubblicare.

## Cosa non fa questa metodologia

- Non inferisce relazioni non presenti nei dati (nessun matching fuzzy tra persone, nessun collegamento societario dedotto).
- Non attribuisce punteggi di affidabilità soggettivi: la nota `confidence_note` descrive limiti oggettivi della fonte, non giudizi.
