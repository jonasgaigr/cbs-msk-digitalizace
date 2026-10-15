"""Download the AOPK taxon checklists (portal23.nature.cz/redlist/v_nd_taxon_category.php)
for vascular plants, bryophytes, lichens and fungi → reference/checklist_aopk.csv (+ cp1250 copy).

The portal keeps the group filter in the PHP session: one POST sets it, then GET pages by offset.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import ROOT, write_csv  # noqa: E402

BASE = "https://portal23.nature.cz/redlist/v_nd_taxon_category.php"
GROUPS = {"5": "vascular_plant", "4": "bryophyte", "3": "lichen", "2": "fungus"}
PAGE = 1000
COLUMNS = ["taxon_group", "scientific_name", "author", "czech_name", "family", "portal_group", "portal_row"]


def parse_rows(html: str) -> tuple[list[list[str]], list[list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    taxa, sources = [], []
    for tr in soup.find_all("tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td", recursive=False)]
        if len(tds) == 6 and tds[0].isdigit():
            taxa.append(tds)
        elif len(tds) in (3, 4) and re.match(r"^\d+\s*>$", tds[0].replace("\xa0", " ")):
            sources.append(tds)
    return taxa, sources


def fetch_group(code: str) -> tuple[list[list[str]], list[list[str]]]:
    s = common._session
    common._wait("portal23.nature.cz")
    r = s.post(BASE + "?akce=seznam&opener=&vztazne_id=0",
               data={"promka": "", "refSearch": "", "skupina": code, "pagesizeX": str(PAGE), "but_action": "Vyhledat"},
               timeout=180)
    r.raise_for_status()
    taxa, sources = parse_rows(r.text)
    offset = PAGE
    while True:
        rr = common.get(BASE, params={"akce": "seznam", "opener": "", "vztazne_id": "0", "order": "",
                                      "orderhow": "ASC", "frompage": str(offset)})
        rr.raise_for_status()
        page, _ = parse_rows(rr.text)
        if not page:
            break
        taxa.extend(page)
        print(f"  group {code}: {len(taxa)} rows", flush=True)
        if len(page) < PAGE:
            break
        offset += PAGE
    return taxa, sources


def main() -> None:
    out_rows, src_lines = [], []
    for code, group in GROUPS.items():
        taxa, sources = fetch_group(code)
        groups_seen = {t[5] for t in taxa}
        print(f"{group}: {len(taxa)} taxa; portal groups in result: {groups_seen}")
        for t in taxa:
            out_rows.append(dict(zip(COLUMNS, [group, t[1], t[2], t[3], t[4], t[5], t[0]])))
        for srow in sources:
            src_lines.append(f"{group}\t" + "\t".join(x.replace("\r\n", " ") for x in srow))
    ref = ROOT / "reference"
    write_csv(ref / "checklist_aopk.csv", out_rows, COLUMNS)
    (ref / "checklist_aopk_sources.tsv").write_text("\n".join(src_lines), encoding="utf-8")
    print(f"{len(out_rows)} rows written")


if __name__ == "__main__":
    main()
