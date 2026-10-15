"""Inventory of record formats: for every record-candidate article, count record-like signals in its
Markdown and compare with what 03_excerpt.py extracted. Articles with many signals but few rows use
a format the confirmed rules do not cover.

    python scripts/inventory_formats.py        # after: python scripts/03_excerpt.py --all
Writes cache/format_inventory.csv and prints the table.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, MD_DIR, ROOT  # noqa: E402

import importlib.util

_spec = importlib.util.spec_from_file_location("excerpt", Path(__file__).with_name("03_excerpt.py"))
X = importlib.util.module_from_spec(_spec)
sys.modules["excerpt"] = X
_spec.loader.exec_module(X)

SIGNALS = {
    "coords": X.DMS,
    "grid": re.compile(r"\b\d{4}[a-d]\b"),
    "phyto_start": re.compile(r"^\d{1,2}[a-z]?\\?\.\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-zá-ž]+", re.M),
    "dated_leg_not": re.compile(r"\b\d{4}\s*,?\s*(?:leg|not|obs|det|foto)\b|\b(?:leg|not|obs)\.\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]\."),
    "taxon_numbers": re.compile(r"^\*[A-Z][^*]+\*[^:\n]{0,40}:\s*\d", re.M),
    "table_rows": re.compile(r"^\| ", re.M),
    "loc_dash_list": re.compile(r"^\d{1,2}\s*[–-]\s+\S", re.M),
}


def main() -> None:
    manifest = {r["local_path"]: r for r in csv.DictReader(open(ROOT / "manifest.csv", encoding="utf-8-sig"))
                if r["download_status"] == "downloaded"}
    locs = Counter(r["source_file"] for r in csv.DictReader(open(ROOT / "localities.csv", encoding="utf-8-sig")))
    occs = Counter(r["source_file"] for r in csv.DictReader(open(ROOT / "occurrences.csv", encoding="utf-8-sig")))
    rows = []
    for path, meta in manifest.items():
        if not X.is_record_candidate(meta):
            continue
        md = MD_DIR / Path(path).parent.name / (Path(path).stem + ".md")
        text = md.read_text(encoding="utf-8")
        sig = {k: len(rx.findall(text)) for k, rx in SIGNALS.items()}
        heads = [h.strip() for h in re.findall(r"^#{2,3} (.+)$", text, re.M)][:12]
        rows.append({"article": X.article_key(meta), "section": meta["section"], "title": meta["title"][:70],
                     "localities": locs[path], "occurrences": occs[path], **sig, "headings": " / ".join(heads),
                     "md": md.relative_to(ROOT).as_posix()})
    cols = list(rows[0].keys())
    with open(CACHE / "format_inventory.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['article']:16} loc={r['localities']:3} occ={r['occurrences']:4} | coords={r['coords']:3} grid={r['grid']:3} "
              f"phyto={r['phyto_start']:3} dated={r['dated_leg_not']:3} tx:n={r['taxon_numbers']:3} tab={r['table_rows']:3} "
              f"dash={r['loc_dash_list']:2} | {r['title'][:45]}")


if __name__ == "__main__":
    main()
