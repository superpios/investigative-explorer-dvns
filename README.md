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
- Non ridistribuisce gli snapshot grezzi di DVNS. Pubblica invece le tabelle di relazione derivate (con provenienza riga-per-riga: hash SHA-256 sorgente e URL dell'atto originale) insieme agli script che le rigenerano dal corpus pubblico: chiunque può ricostruire tutto da zero e verificarlo.

## Stato del progetto

**Fase 2 in corso — strumento interrogabile disponibile:**

- **48.109 relazioni** indicizzate a testo pieno da 5 dataset DVNS (`incarichi-nominativi-shard`, `affidamenti-diretti`, `parti-atti`, `rinnovi-proroghe`).
- Ricerca per nome, sigla ente o CIG; filtro per tipo di relazione; ogni risultato con periodo, importo quando dichiarato e link all'atto originale.
- Server **solo locale** (127.0.0.1): i dati non escono dal computer; query parametrizzate; pagina senza risorse esterne.

### Avvio rapido

```
pip install -r requirements.txt
python scripts/build_search_index.py      # costruisce l'indice dai CSV in data/relations/
python src/server.py --port 8765          # poi apri http://127.0.0.1:8765
```

Fasi completate: Fase 0 (struttura e metodo), Fase 1 (estrazione e normalizzazione).

## Usalo sul tuo computer (redazioni e ricercatori)

Nessuna registrazione, nessun dato inviato a server terzi: tutto gira in locale.

```
git clone https://github.com/superpios/investigative-explorer-dvns.git
cd investigative-explorer-dvns
pip install -r requirements.txt
python scripts/build_search_index.py
python src/server.py --port 8765
```

Poi apri `http://127.0.0.1:8765`. Per aggiornare i dati quando DVNS pubblica nuovi snapshot: rieseguire gli estrattori in `scripts/extract/` e poi `build_search_index.py`.

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
