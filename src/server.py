"""Server locale di Investigative Explorer.

Vincoli di sicurezza e privacy, non opzionali:
- ascolta SOLO su 127.0.0.1: i dati restano sul computer, nessuna esposizione di rete;
- ogni query SQL e' parametrizzata;
- gli input HTTP sono limitati in lunghezza e validati contro liste chiuse;
- la pagina non carica alcuna risorsa esterna (niente CDN, niente tracker).

Avvio: python src/server.py [--port 8765]
"""

import argparse
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.resolve().parents[0]
sys.path.insert(0, str(SRC_DIR))

from query_engine import DEFAULT_LIMIT, MAX_LIMIT, connect, get_stats, search_edges  # noqa: E402


DB_PATH = REPO_ROOT / "data" / "search" / "explorer.db"
INDEX_PAGE = SRC_DIR / "static" / "index.html"

app = FastAPI(title="Investigative Explorer", version="0.2.0")


@app.get("/")
def home():
    return FileResponse(INDEX_PAGE, media_type="text/html")


@app.get("/api/search")
def api_search(
    q: str = Query(min_length=2, max_length=200),
    relation_type: str = None,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="indice assente: eseguire scripts/build_search_index.py")
    conn = connect(DB_PATH)
    try:
        return {"query": q, "results": search_edges(conn, q, relation_type=relation_type, limit=limit)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@app.get("/api/stats")
def api_stats():
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="indice assente: eseguire scripts/build_search_index.py")
    conn = connect(DB_PATH)
    try:
        return get_stats(conn)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="indirizzo di ascolto; lasciare localhost salvo esigenze documentate")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn
    print("Investigative Explorer su http://{}:{} — solo rete locale, nessun dato esposto all'esterno".format(args.host, args.port))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
