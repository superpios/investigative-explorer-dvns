# Limiti

Documento obbligatorio per l'uso responsabile dello strumento. Descrive ciò che Investigative Explorer non può e non deve fare.

## Limiti metodologici

1. **Un collegamento nei dati non è una prova di responsabilità.** Ogni relazione mostrata è un fatto documentato in una fonte pubblica; l'interpretazione spetta alla redazione che verifica.
2. **I perimetri contabili restano separati.** SIOPE, IRPEF, CPT, costi previsti, debiti e pagamenti osservati non vengono mai sommati né confrontati tra loro.
3. **Le omonimie non vengono risolte automaticamente.** Due occorrenze dello stesso nome corrispondono a due record, non necessariamente alla stessa persona. Lo strumento non applica deduplicazione aggressiva dei nomi.
4. **L'assenza di un collegamento non è un risultato.** Se due entità non risultano collegate, può dipendere dalla copertura parziale delle fonti.
5. **La copertura è parziale per costruzione.** Dei 79 dataset integrati da DVNS, 57 sono interrogabili; delle 13,3 milioni di righe sorgente, circa 338.782 sono pubbliche.

## Limiti specifici delle fonti (verificati agosto 2026)

- **ANAC CIG 2025**: snapshot aggregato di screening; non consente ricerca live per CIG o fornitore.
- **Collegamenti CIG → aggiudicatario**: numericamente limitati (`vincitori-cig`: 120 righe; `cig-aggiudicatari-extra`: 2.391 righe). Il grafo degli appalti è quindi molto più sparso dell'intero BDNCP ANAC.
- **`opencup-soggetti`**: 54.323 righe interrogabili ma prive di fonti puntuali collegate; da usare solo dopo verifica di copertura.
- **`opencup-progetti-bulk`** (11,9 milioni di record): catalog-only, non interrogabile via API o MCP.

## Trattamento delle persone

- Le persone presenti nei dati sono titolari di incarichi pubblici documentati da fonti ufficiali: viene trattato esclusivamente il ruolo pubblico, mai la sfera personale.
- Nessun arricchimento con dati provenienti da social network, anagrafi private o altre fonti non ufficiali.
- Chi si riconosce nei dati e rileva un errore può segnalarlo tramite issue sul repository: la segnalazione viene verificata contro la fonte primaria e, se fondata, il record viene corretto o annotato.
- Riferimento normativo: trattamento a finalità giornalistica ai sensi dell'art. 85 GDPR; si veda anche [docs/LEGAL_AND_ETHICS.md](https://github.com/Italian-Builders-Org/DoveVannoINostriSoldi/blob/main/docs/LEGAL_AND_ETHICS.md) del progetto madre.

## Regola di esposizione dei risultati

Ogni output dello strumento deve riportare: dataset sorgente, identificativo del record originale, periodo di riferimento, data di acquisizione, limiti della fonte. In assenza anche di uno solo di questi elementi, il risultato non viene pubblicato.
