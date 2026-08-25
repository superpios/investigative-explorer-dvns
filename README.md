# Investigative Explorer · DVNS

Strumento di ricerca e navigazione relazionale sui dati della spesa pubblica italiana aggregati dal progetto [DoveVannoINostriSoldi](https://github.com/Italian-Builders-Org/DoveVannoINostriSoldi) (DVNS).

Permette di partire da una persona, una società, un CIG, un CUP o un ente pubblico e ricostruire i collegamenti documentati nei dati pubblici, ciascuno corredato di fonte, periodo di riferimento, data di acquisizione e limiti dichiarati.

## Cosa fa

- Ricerca unificata su nomi, CIG, CUP ed enti nei dataset pubblici integrati da DVNS.
- Ricostruzione delle relazioni esistenti nei dati: persona → incarico → ente, CIG → aggiudicatario → importo, CUP → soggetto titolare.
- Vista a grafo leggera con pannello di dettaglio per ogni nodo e arco.
- Export CSV/JSON di ogni sessione di ricerca.

## Cosa non fa

- Non stabilisce responsabilità, illeciti o sprechi: ogni risultato è formulato come «merita verifica».
- Non somma né mescola perimetri contabili diversi (SIOPE, IRPEF, CPT, costi previsti e debiti restano separati).
- Non inventa collegamenti assenti nei dati sorgente.
- Non ridistribuisce il corpus DVNS al di fuori delle condizioni di riuso dichiarate: pubblica schemi, codice e procedure di riesecuzione.

## Stato del progetto

**Fase 1 in corso** — prime relazioni estratte dal corpus DVNS e pubblicate:

- `affidamenti-diretti`: 6.506 righe sorgente → **6.484 relazioni CIG→ente** in `data/relations/` (CSV + Parquet + manifest di provenienza, verifica a campione superata).
- Prossimo dataset: `incarichi-nominativi-shard` → relazioni persona→incarico→ente.

## Documentazione

| File | Contenuto |
| --- | --- |
| [docs/METODOLOGIA.md](docs/METODOLOGIA.md) | Come vengono costruiti i collegamenti |
| [docs/LIMITI.md](docs/LIMITI.md) | Limiti metodologici e interpretativi |
| [docs/FONTI.md](docs/FONTI.md) | Dataset utilizzati, stato e condizioni di riuso |

## Struttura del repository

```
docs/               metodologia, limiti, fonti
data/
  raw/              snapshot originali DVNS (sola lettura, non versionati)
  processed/        dati normalizzati intermedi
  relations/        tabelle di relazione (output principale)
scripts/
  extract/          estrazione relazioni dai dataset sorgente
  normalize/        pulizia leggera dei nomi e dei campi
  validate/         controlli di integrità e provenienza
schemas/            entità canoniche e schemi delle relazioni
src/                backend di consultazione (fase successiva)
tests/              controlli automatici
```

## Requisiti

- Python 3.11+
- Dipendenze: `pip install -r requirements.txt`
- Test: `pytest`

## Progetto collegato

- **Generator di piste investigative** (`investigative-leads-generator`): consuma le tabelle di relazione prodotte da questo repository secondo lo schema in `schemas/`.

## Licenza

GNU Affero General Public License v3.0 — vedere [LICENSE](LICENSE).
