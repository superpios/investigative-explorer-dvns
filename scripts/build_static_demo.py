"""Costruisce la demo pubblica statica (ricerca lato browser).

Genera la cartella demo/ con:
  - data/edges.json      archi compatti + tabelle di lookup (tipi, dataset, url deduplicati)
  - index.html           interfaccia di ricerca senza alcuna dipendenza esterna

Il sito risultante e' pubblicabile su qualsiasi hosting statico (es. GitHub
Pages): niente backend, niente log, la ricerca avviene nel browser del
visitatore sui dati gia' pubblici della repository.

Riusa gli stessi CSV delle relazioni validati dai test (nessuna nuova rete).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_search_index import SOURCE_TABLES, load_source_table  # noqa: E402


DEMO_DIR = REPO_ROOT / "demo"


def build_payload():
    relation_types, datasets, urls = [], [], []
    type_index, dataset_index, url_index = {}, {}, {}
    edges = []

    for config in SOURCE_TABLES:
        _path, records = load_source_table(config)
        for record in records:
            rt = record["relation_type"]
            if rt not in type_index:
                type_index[rt] = len(relation_types)
                relation_types.append(rt)
            ds = record["source_dataset"]
            if ds not in dataset_index:
                dataset_index[ds] = len(datasets)
                datasets.append(ds)
            url = record.get("fonte_url") or ""
            if url not in url_index:
                if url:
                    url_index[url] = len(urls)
                    urls.append(url)
                else:
                    url_index[url] = -1
            edges.append([
                type_index[rt],
                record["subject_key"],
                record["object_key"],
                record.get("period", ""),
                record.get("amount_if_present", "") or "",
                record.get("role", "") or "",
                dataset_index[ds],
                record["source_record_id"],
                url_index[url],
            ])

    return {
        "payload": {
            "types": relation_types,
            "datasets": datasets,
            "urls": urls,
            "edges": edges,
        },
        "dataset_counts": {name: sum(1 for e in edges if e[6] == idx)
                           for name, idx in dataset_index.items()},
    }


def main():
    result = build_payload()
    payload = result["payload"]

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    (DEMO_DIR / "data").mkdir(exist_ok=True)

    out_path = DEMO_DIR / "data" / "edges.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_edges": len(payload["edges"]),
        "datasets": result["dataset_counts"],
    }
    (DEMO_DIR / "data" / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    size_kb = out_path.stat().st_size // 1024
    print("archi scritti: {}".format(len(payload["edges"])))
    print("file: {} ({} KB)".format(out_path.relative_to(REPO_ROOT), size_kb))
    for name, count in meta["datasets"].items():
        print("{:>40}: {}".format(name, count))


if __name__ == "__main__":
    main()
