# Fonti

Elenco dei dataset utilizzati, con stato e condizioni di riuso. I conteggi provengono dal registro ufficiale DVNS (`docs/INTEGRATED_SOURCE_LEDGER.md`) e sono stati verificati ad agosto 2026; vanno ricontrollati a ogni aggiornamento del corpus.

## Canali di accesso ai dati

| Canale | Indirizzo | Uso previsto |
| --- | --- | --- |
| Server MCP pubblico (sola lettura) | `https://www.dovevannoinostrisoldi.com/api/mcp` | Prototyping e query puntuali (`list_datasets`, `query_dataset`) |
| API HTTP | `https://www.dovevannoinostrisoldi.com/api/dati/<id>` | Estrazioni mirate e paginazione |
| Repository DVNS | snapshot in `src/data/generated/` e script ETL | Estrazioni bulk riproducibili |

## Dataset relazionali prioritari

| ID dataset | Titolo | Righe | Note |
| --- | --- | ---: | --- |
| `parti-atti` | Soggetti negli atti | 159.493 | Il più esteso asset relazionale soggetto ↔ atti |
| `opencup-soggetti` | Soggetti titolari OpenCUP | 54.323 | Righe interrogabili ma senza fonti puntuali collegate |
| `incarichi-nominativi-shard` | Incarichi nominativi: fonti estese | 39.685 | Base per le relazioni persona → incarico → ente |
| `openbdap-capitoli-2024-2026` | Capitoli OpenBDAP 2024–2026 | 17.792 | Capitoli di spesa statale |
| `cig-ministeri` | CIG di ministeri e Presidenza | 14.824 | Appalti ministeriali |
| `procurement-partecipate` | Affidamenti delle partecipate | 11.115 | Affidamenti societarie partecipate |
| `affidamenti-diretti` | Affidamenti diretti | 6.506 | Base principale per l'analisi degli aggiudicatari |
| `procurement-atti-mimit` | Atti di acquisto MIMIT | 5.789 | — |
| `cig-aggiudicatari-extra` | CIG e aggiudicatari: lotti supplementari | 2.391 | Collegamenti aggiuntivi CIG → aggiudicatario |
| `nominativi-incarichi` | Incarichi nominativi | 1.633 | — |
| `rinnovi-proroghe` | Rinnovi e proroghe | 440 | Base per il segnale «rinnovi ripetuti» |
| `consulenze-legali` | Consulenze legali | 352 | — |
| `consulenze-pnrr` | Consulenze PNRR | 213 | — |
| `vincitori-cig` | Vincitori collegati ai CIG | 120 | Copertura molto parziale: vedi LIMITI |

## Dataset di contesto (server MCP)

Oltre al corpus integrato, il server MCP espone dataset di riferimento utili all'abbinamento entità: `ipa_enti` e `ipa_struttura` (anagrafica enti), `mef_partecipazioni` (partecipazioni pubbliche), `consulenti_incarichi` (statistiche nazionali su incarichi), `pnrr_asili` (progetti, gare e aggiudicatari per CUP).

## Condizioni di riuso

- Quasi tutti i dataset integrati presentano `licenseStatus: not-declared`: lo stato è un caveat di riuso dichiarato da DVNS stesso. Questo repository pubblica pertanto schemi, codice, hash degli input e procedure di riesecuzione anziché ridistribuire righe grezze.
- Fanno eccezione i dataset Consip (`consip-winners-*`, CC BY 4.0), per cui la redistribuzione è consentita con attribuzione.
- A ogni nuova estrazione va registrata in questa pagina la data del rilascio DVNS utilizzato.
