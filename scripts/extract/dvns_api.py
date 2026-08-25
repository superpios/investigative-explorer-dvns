"""Client di sola lettura per le API pubbliche di DoveVannoINostriSoldi.

Regole operative: pausa tra le richieste, User-Agent identificativo,
validazione fail-closed dello schema prima di accettare qualsiasi riga.
"""

import json
import time
import urllib.error
import urllib.request


BASE_URL = "https://www.dovevannoinostrisoldi.com/api/dati"
USER_AGENT = (
    "investigative-explorer-dvns/0.1 "
    "(uso civico e giornalistico; https://github.com/superpios/investigative-explorer-dvns)"
)
REQUEST_PAUSE_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 60


class SchemaChangedError(RuntimeError):
    """Sollevata quando gli header del dataset non coincidono con quelli attesi."""


def fetch_page(dataset_id, page_limit=100, cursor=None):
    url = "{}/{}?limit={}".format(BASE_URL, dataset_id, page_limit)
    if cursor:
        url = url + "&cursor=" + cursor
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_schema(payload, expected_headers):
    dataset = payload.get("dataset", {})
    headers = tuple(dataset.get("headers", []))
    if headers != tuple(expected_headers):
        raise SchemaChangedError(
            "schema di '{}' cambiato: atteso {}, trovato {}".format(
                dataset.get("id"), tuple(expected_headers), headers
            )
        )


def iter_rows(dataset_id, expected_headers, max_rows=None, page_limit=100):
    """Itera le righe del dataset seguendo i cursor restituiti dall'API.

    Si interrompe senza inventare nulla se: lo schema cambia, una pagina
    arriva malformata o viene raggiunto max_rows.
    """
    cursor = None
    collected = 0
    while True:
        payload = fetch_page(dataset_id, page_limit=page_limit, cursor=cursor)
        validate_schema(payload, expected_headers)
        rows = payload.get("rows") or []
        if not rows:
            return
        for row in rows:
            yield row
            collected += 1
            if max_rows is not None and collected >= max_rows:
                return
        pagination = payload.get("pagination") or {}
        cursor = pagination.get("nextCursor")
        if not cursor or pagination.get("exhausted"):
            return
        time.sleep(REQUEST_PAUSE_SECONDS)
