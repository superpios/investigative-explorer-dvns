import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "demo"
EDGES_JSON = DEMO_DIR / "data" / "edges.json"
META_JSON = DEMO_DIR / "data" / "meta.json"
INDEX_HTML = DEMO_DIR / "index.html"
RELATIONS_DIR = REPO_ROOT / "data" / "relations"

ALLOWED_EXTERNAL_HOSTS = ("https://github.com/", "https://www.dovevannoinostrisoldi.com")


def manifest_total():
    total = 0
    for path in RELATIONS_DIR.glob("_manifest_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        total += data.get("relations_written") or data.get("edges_written")
    return total


def test_demo_payload_exists_and_counts_match_manifests():
    assert EDGES_JSON.exists() and META_JSON.exists() and INDEX_HTML.exists()
    payload = json.loads(EDGES_JSON.read_text(encoding="utf-8"))
    meta = json.loads(META_JSON.read_text(encoding="utf-8"))
    assert len(payload["edges"]) == manifest_total()
    assert meta["total_edges"] == manifest_total()
    assert sum(meta["datasets"].values()) == manifest_total()


def test_every_edge_is_well_formed_and_resolvable():
    payload = json.loads(EDGES_JSON.read_text(encoding="utf-8"))
    types, datasets, urls = payload["types"], payload["datasets"], payload["urls"]
    for edge in payload["edges"]:
        assert len(edge) == 9
        assert 0 <= edge[0] < len(types)
        assert 0 <= edge[6] < len(datasets)
        assert -1 <= edge[8] < len(urls)
        assert edge[1] and edge[2] and edge[7]


def test_known_cases_are_present_in_public_payload():
    payload = json.loads(EDGES_JSON.read_text(encoding="utf-8"))
    subjects = {e[1] for e in payload["edges"]}
    for expected in ("AVV. IVAN FRIONI", "FANTAUZZI PAOLO GIOVANNI", "RALLO ALICE"):
        assert expected in subjects, f"caso noto mancante nella demo: {expected}"


def test_index_html_loads_no_external_resources():
    html = INDEX_HTML.read_text(encoding="utf-8")
    urls_in_quotes = [chunk for chunk in html.split('"') if chunk.startswith("http")]
    assert all(chunk.startswith(ALLOWED_EXTERNAL_HOSTS) for chunk in urls_in_quotes), \
        f"risorse esterne non ammesse: {[u for u in urls_in_quotes if not u.startswith(ALLOWED_EXTERNAL_HOSTS)]}"
    for tag_match in re.findall(r"<(?:script|link|img)[^>]*>", html):
        assert not re.search(r'src\s*=\s*["\']https?://', tag_match), \
            f"sorgente esterna trovata: {tag_match}"
        assert not re.search(r'href\s*=\s*["\']https?://', tag_match), \
            f"stylesheet/font esterni trovati: {tag_match}"
