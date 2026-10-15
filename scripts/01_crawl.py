"""Step 1: crawl ms-cbs.cz issue pages + Zenodo community msp-cbs, download PDFs, write manifest.csv.

Usage:
    python scripts/01_crawl.py                 # parse cached pages, download missing PDFs
    python scripts/01_crawl.py --refresh       # re-fetch index/issue pages and Zenodo metadata first
    python scripts/01_crawl.py --no-download   # parse only, write manifest without downloading

Resumable: existing PDFs are skipped (their sha256 is still recorded).
"""
from __future__ import annotations

import argparse

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, PDF_DIR, ROOT, cached_text, download, get, normalise_url, sha256, write_csv  # noqa: E402

INDEX_URL = "https://www.ms-cbs.cz/zpravy-moravskoslezske-pobocky-cbs/"
ISSUE_URL_PATTERN = "https://www.ms-cbs.cz/zpravy-moravskoslezske-pobocky-cbs-c-{n}/"
ZENODO_API = "https://zenodo.org/api/communities/msp-cbs/records"
SKIP_PDF = re.compile(r"(pokyny-pro-autory|pravidla-pro-psani-rukopisu)", re.I)
JOURNAL = "Zprávy Moravskoslezské pobočky ČBS"

MANIFEST_COLUMNS = [
    "issue_no", "year", "supplement", "authors", "title", "citation", "pages",
    "source_page_url", "pdf_url", "zenodo_doi", "local_path", "sha256", "download_status",
    # additions (agreed at checkpoint 0 / explained at checkpoint 1)
    "citation_source", "section", "toc_page", "pdf_pages", "remarks",
]


@dataclass
class Entry:
    issue_no: int
    year: int | None
    supplement: int | None
    authors: str = ""
    title: str = ""
    citation: str = ""
    pages: str = ""
    source_page_url: str = ""
    pdf_url: str = ""
    zenodo_doi: str = ""
    local_path: str = ""
    sha256: str = ""
    download_status: str = ""
    citation_source: str = ""
    section: str = ""
    toc_page: str = ""
    pdf_pages: str = ""
    remarks: list[str] = field(default_factory=list)
    zenodo_file_md5: str = ""

    def row(self) -> dict:
        d = asdict(self)
        d["remarks"] = "; ".join(dict.fromkeys(self.remarks))
        d["supplement"] = "" if self.supplement is None else self.supplement
        d["year"] = "" if self.year is None else self.year
        return {k: d[k] for k in MANIFEST_COLUMNS}


# ---------------------------------------------------------------- text helpers

def clean(s: str) -> str:
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


def dash(s: str) -> str:
    return re.sub(r"\s*[-‒–—]\s*", "–", s.strip())


TOC_PAGE = re.compile(r"\s*(?:[.…]\s*){3,}\s*(\d+)\s*$")
HEADING = re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ ]+:?$")
TOC_HEADER = re.compile(r"^Zprávy Moravskoslezské pobočky ČBS č\.\s*\d+")
CITATION = re.compile(r"^Zprávy Moravskoslezské pobočky ČBS\s+(\d+)\s*:\s*(?P<pages>[^,]+?)\s*,\s*(?P<year>\d{4})\s*$")
STOP = re.compile(r"^(Ukázka|Vydáno s finanční podporou)")
FILE_PAGES = [
    re.compile(r"^ZMSP(?:CBS)?_(?P<year>\d{4})-(?P<issue>\d+)[-_](?P<p1>\d+)(?:-(?P<p2>\d+))?(?P<extra>\+\w+)?$"),
    re.compile(r"^ZMSP(?:CBS)?_(?P<issue>\d+)_P(?P<supp>\d)_(?P<p1>\d+)-(?P<p2>\d+)"),
]


def pages_from_filename(url: str) -> str:
    stem = Path(url.split("?")[0]).stem
    for rx in FILE_PAGES:
        m = rx.match(stem)
        if m:
            p = m["p1"] + (f"–{m['p2']}" if m["p2"] else "")
            if m.groupdict().get("extra"):
                p += m["extra"].replace("+", " + ")
            return p
    return ""


# ---------------------------------------------------------------- HTML → lines

@dataclass
class Line:
    text: str
    pdfs: list[str]
    bold: bool


def html_lines(container: Tag, base: str) -> list[Line]:
    """Split a WordPress entry-content into logical lines (<br> and blocks), keeping <a> atomic."""
    lines: list[Line] = []
    cur: list[tuple[str, bool]] = []
    pdfs: list[str] = []

    def flush():
        nonlocal cur, pdfs
        text = clean("".join(t for t, _ in cur))
        if text:
            visible = [(t, b) for t, b in cur if t.strip()]
            lines.append(Line(text, pdfs, all(b for _, b in visible)))
        cur, pdfs = [], []

    def walk(node, bold: bool):
        for child in node.children:
            if isinstance(child, NavigableString):
                cur.append((str(child), bold))
            elif isinstance(child, Tag):
                if child.name == "br":
                    flush()
                elif child.name == "a":
                    href = child.get("href", "")
                    if href.lower().split("?")[0].endswith(".pdf") and not SKIP_PDF.search(href):
                        pdfs.append(normalise_url(href, base))
                    cur.append((child.get_text(" "), bold or child.find(["strong", "b"]) is not None))
                elif child.name in ("script", "style", "img"):
                    continue
                elif child.name in ("p", "div", "figure", "table", "tr", "li", "h1", "h2", "h3", "h4", "ul", "ol"):
                    flush()
                    walk(child, bold)
                    flush()
                else:
                    walk(child, bold or child.name in ("strong", "b"))

    walk(container, False)
    flush()
    return lines


# ---------------------------------------------------------------- page parsers

def parse_supplement(lines: list[Line], issue: dict, url: str) -> list[Entry]:
    """Supplement pages carry one 'Doporučená citace' paragraph."""
    idx = next((i for i, l in enumerate(lines) if l.text.startswith("Doporučená citace")), None)
    if idx is None:
        return []
    cit_line = lines[idx + 1] if idx + 1 < len(lines) else Line("", [], False)
    pdfs = [p for l in lines for p in l.pdfs]
    citation = re.sub(r"\s*\[\s*Full text.*$", "", cit_line.text).strip()
    citation = re.sub(r"\s+([.,])", r"\1", citation)
    e = Entry(issue["issue_no"], issue["year"], issue["supplement"], source_page_url=url,
              citation=citation, citation_source="page", section="PŘÍLOHA")
    m = re.match(r"^(?P<authors>.+?)\s*\((?P<year>\d{4})\):\s*(?P<title>.+?)\s*–\s*Zprávy Moravskoslezské pobočky .*?"
                 r"(?P<issue>\d+),\s*Příloha\s*(?P<supp>\d+):\s*(?P<pages>[\d–-]+)", citation)
    if m:
        e.authors, e.title, e.pages = m["authors"], m["title"].rstrip(" ."), dash(m["pages"])
    else:
        e.title = issue.get("subtitle", "")
        e.remarks.append("recommended citation not parsed")
    if pdfs:
        e.pdf_url = pdfs[0]
    return [e]


def parse_toc(lines: list[Line], issue: dict, url: str) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    stray: list[str] = []
    started = False
    section = ""
    pending: Line | None = None

    def new_entry(title_line: Line, author_line: Line | None) -> Entry:
        title = title_line.text
        toc = ""
        m = TOC_PAGE.search(title)
        if m:
            toc, title = m.group(1), title[: m.start()].rstrip(" .…")
        e = Entry(issue["issue_no"], issue["year"], issue["supplement"], source_page_url=url,
                  title=clean(title), section=section.rstrip(":").strip(), toc_page=toc)
        if author_line:
            e.authors = author_line.text.rstrip(":").strip().rstrip(",")
        if title_line.pdfs:
            e.pdf_url = title_line.pdfs[0]
            if len(set(title_line.pdfs)) > 1:
                e.remarks.append("several PDF links on title line: " + " ".join(title_line.pdfs[1:]))
        entries.append(e)
        return e

    for ln in lines:
        t = ln.text
        if not started:
            if t == "OBSAH" or (HEADING.match(t) and t.rstrip(":") != "OBSAH"):
                started = True
            else:
                continue
        if t == "OBSAH" or TOC_HEADER.match(t):
            continue
        if STOP.match(t):
            break
        if HEADING.match(t):
            if pending:
                stray.append(pending.text)
                pending = None
            section = t
            continue
        m = CITATION.match(t)
        if m:
            if entries and not entries[-1].citation:
                entries[-1].citation = t
                entries[-1].citation_source = "page"
            else:
                stray.append(t)
            continue
        if ln.pdfs:
            new_entry(ln, pending)
            pending = None
        elif pending is None:
            pending = ln
        else:
            new_entry(ln, pending)
            pending = None
    if pending:
        if pending.bold:
            e = new_entry(pending, None)
            e.remarks.append("no author line on issue page")
        else:
            stray.append(pending.text)
    return entries, stray


def parse_issue_page(issue: dict) -> tuple[list[Entry], list[str]]:
    url = issue["url"]
    ec = BeautifulSoup(cached_text(url, refresh=ARGS.refresh), "html.parser").select_one("div.entry-content")
    if ec is None:
        return [], ["no entry-content found"]
    lines = html_lines(ec, url)
    if any(l.text.startswith("Doporučená citace") for l in lines):
        return parse_supplement(lines, issue, url), []
    return parse_toc(lines, issue, url)


def parse_index() -> list[dict]:
    soup = BeautifulSoup(cached_text(INDEX_URL, refresh=ARGS.refresh), "html.parser")
    table = next(t for t in soup.find_all("table") if "PŘEHLED ČÍSEL" in t.get_text())
    issues = []
    for a in table.find_all("a", href=True):
        label = clean(a.get_text(" "))
        m = re.match(r"č\.\s*(\d+)/(\d{4}),?\s*(?:Příloha\s*(\d+))?", label)
        if not m:
            print(f"WARNING: unparsed index label {label!r}")
            continue
        cell = a.find_parent("td")
        subtitle = clean(cell.get_text(" ").replace(a.get_text(" "), "")) if cell else ""
        issues.append({
            "label": label, "url": normalise_url(a["href"], INDEX_URL),
            "issue_no": int(m[1]), "year": int(m[2]),
            "supplement": int(m[3]) if m[3] else None, "subtitle": subtitle,
        })
    return issues


# ---------------------------------------------------------------- Zenodo

def zenodo_records() -> list[dict]:
    out, page = [], 1
    zdir = CACHE / "zenodo"
    zdir.mkdir(parents=True, exist_ok=True)
    while True:
        path = zdir / f"community_page{page}.json"
        if path.exists() and not ARGS.refresh:
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            r = get(ZENODO_API, params={"size": 25, "page": page, "sort": "newest"})
            r.raise_for_status()
            data = r.json()
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        hits = data["hits"]["hits"]
        out.extend(hits)
        if not hits or len(out) >= data["hits"]["total"]:
            return out
        page += 1


def zenodo_info(h: dict) -> dict:
    md = h["metadata"]
    j = md.get("journal") or {}
    files = []
    for f in h.get("files") or []:
        link = (f.get("links") or {}).get("self") or f"https://zenodo.org/records/{h['id']}/files/{f['key']}?download=1"
        files.append({"key": f["key"], "url": link, "md5": (f.get("checksum") or "").replace("md5:", "")})
    authors = []
    for c in md.get("creators", []):
        name = c["name"]
        if "," in name:
            last, first = [x.strip() for x in name.split(",", 1)]
            name = f"{first} {last}"
        authors.append(name)
    return {
        "id": h["id"], "doi": h.get("doi", ""), "html": h["links"].get("self_html", f"https://zenodo.org/records/{h['id']}"),
        "title": md.get("title", ""), "volume": j.get("volume", ""), "pages": dash(j.get("pages", "")),
        "year": int(md["publication_date"][:4]) if md.get("publication_date") else None,
        "access": md.get("access_right", ""), "embargo": md.get("embargo_date", ""),
        "authors": ", ".join(authors), "files": files,
    }


def apply_zenodo(e: Entry, z: dict) -> None:
    e.zenodo_doi = z["doi"]
    if not e.pages and z["pages"]:
        e.pages = z["pages"]
    if not e.citation:
        e.citation = f"{JOURNAL} {z['volume']}: {z['pages']}, {z['year']}"
        e.citation_source = "zenodo"
    if not e.pdf_url:
        pdf_files = [f for f in z["files"] if f["key"].lower().endswith(".pdf")]
        if pdf_files:
            e.pdf_url, e.zenodo_file_md5 = pdf_files[0]["url"], pdf_files[0]["md5"]
            e.remarks.append(f"PDF from Zenodo (file {pdf_files[0]['key']})")
        elif z["access"] == "embargoed":
            e.download_status = "embargoed"
            e.remarks.append(f"Zenodo embargo until {z['embargo']}")
        else:
            e.remarks.append(f"Zenodo record has no PDF file (access={z['access']})")


def printed_folios(doc) -> tuple[int, int] | None:
    """Printed page number of first and last PDF page (a bare 1–3 digit line at top or bottom).

    Returns None unless both are found and they span exactly the PDF's page count.
    """
    def folio(page) -> int | None:
        lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        nums = [int(l) for l in lines[:2] + lines[-2:] if re.fullmatch(r"\d{1,3}", l)]
        return nums[0] if len(set(nums)) == 1 else None

    f1, fn = folio(doc[0]), folio(doc[-1])
    if f1 is None or fn is None or fn - f1 + 1 != doc.page_count:
        return None
    return f1, fn


# ---------------------------------------------------------------- main

def folder_for(e: Entry) -> str:
    return f"{e.issue_no:02d}" + (f"-P{e.supplement}" if e.supplement else "")


def local_name(e: Entry) -> str:
    name = Path(e.pdf_url.split("?")[0]).name
    if name == "content":  # Zenodo API link …/files/<key>/content
        name = e.pdf_url.rstrip("/").split("/")[-2]
    return name


def main() -> None:
    issues = parse_index()
    known = {(i["issue_no"], i["supplement"]) for i in issues}
    # issues newer than the index table: probe the URL pattern (page may exist without being linked)
    n = max(i["issue_no"] for i in issues) + 1
    while True:
        url = ISSUE_URL_PATTERN.format(n=n)
        r = get(url)
        # WordPress may redirect a missing slug to a "similar" post, so require the exact URL
        if r.status_code != 200 or r.url.rstrip("/") != url.rstrip("/"):
            break
        issues.append({"label": f"č. {n} (not in index table)", "url": url, "issue_no": n, "year": None,
                       "supplement": None, "subtitle": "", "unlisted": True})
        n += 1

    entries: list[Entry] = []
    log: list[str] = []
    for iss in issues:
        found, stray = parse_issue_page(iss)
        if iss.get("unlisted"):
            for e in found:
                e.remarks.append("issue page not linked from PŘEHLED ČÍSEL")
        log.append(f"{iss['label']}: {len(found)} entries, {sum(1 for e in found if e.pdf_url)} with PDF link"
                   + (f"; stray lines: {stray}" if stray else ""))
        entries.extend(found)

    # ---- Zenodo: DOIs for website PDFs, fallback PDFs, and records not listed on the site
    zrecs = [zenodo_info(h) for h in zenodo_records()]
    used: set[str] = set()
    for e in entries:
        if e.supplement:
            continue
        cands = [z for z in zrecs if z["volume"] == str(e.issue_no) and z["doi"] not in used]
        fname = local_name(e) if e.pdf_url else ""
        z = (next((z for z in cands if fname and any(f["key"] == fname for f in z["files"])), None)
             or next((z for z in cands if norm_title(z["title"]) == norm_title(e.title)), None))
        if z:
            used.add(z["doi"])
            apply_zenodo(e, z)
    issue_years = {i["issue_no"]: i["year"] for i in issues if i["year"]}
    for z in zrecs:
        if z["doi"] in used or not z["volume"].isdigit():
            continue
        vol = int(z["volume"])
        e = Entry(vol, issue_years.get(vol) or z["year"], None, authors=z["authors"], title=z["title"],
                  source_page_url=z["html"], section="")
        e.remarks.append("listed on Zenodo only" + ("" if (vol, None) in known else " (issue not in PŘEHLED ČÍSEL)"))
        apply_zenodo(e, z)
        entries.append(e)
        used.add(z["doi"])
        log.append(f"Zenodo-only record added: č. {vol} {z['title'][:60]} ({z['doi']})")

    # ---- year for issues known only via Zenodo / unlisted page
    for e in entries:
        if e.year is None:
            e.year = issue_years.get(e.issue_no)

    # ---- pages, citation fallbacks, consistency remarks
    for e in entries:
        m = CITATION.match(e.citation) if e.citation_source == "page" else None
        cit_pages = dash(m["pages"]) if m else ""
        file_pages = pages_from_filename(e.pdf_url) if e.pdf_url else ""
        if cit_pages:
            e.pages = cit_pages
        elif not e.pages:
            e.pages = file_pages or e.toc_page
        if file_pages and cit_pages and file_pages.split(" ")[0] != cit_pages:
            e.remarks.append(f"file name pages {file_pages} ≠ citation pages {cit_pages}")
        if e.toc_page and e.pages and e.pages.split("–")[0].split(" ")[0] != e.toc_page:
            e.remarks.append(f"TOC page {e.toc_page} ≠ start page {e.pages}")
        if not e.citation and not e.supplement and e.pages:
            e.citation = f"{JOURNAL} {e.issue_no}: {e.pages}, {e.year}"
            e.citation_source = "constructed"
        if e.issue_no == 1:
            e.remarks.append("index lists č. 1/2012; issue page says 'č. 1 (2011)', file names use 2011")

    # ---- shared PDFs
    by_url: dict[str, list[Entry]] = {}
    for e in entries:
        if e.pdf_url:
            by_url.setdefault(e.pdf_url, []).append(e)
    for url, es in by_url.items():
        if len(es) > 1:
            for e in es:
                others = [o.title[:50] for o in es if o is not e]
                e.remarks.append("PDF shared with: " + " | ".join(others))

    # ---- download
    for e in entries:
        if not e.pdf_url:
            if not e.download_status:
                e.download_status = "no_pdf"
            continue
        dest = PDF_DIR / folder_for(e) / local_name(e)
        e.local_path = dest.relative_to(ROOT).as_posix()
        if ARGS.no_download:
            e.download_status = "exists" if dest.exists() else "not_downloaded"
            if dest.exists():
                e.sha256 = sha256(dest)
        else:
            try:
                status, digest = download(e.pdf_url, dest)
            except RuntimeError as err:
                status, digest = "failed", ""
                e.remarks.append(str(err))
            e.download_status, e.sha256 = status, digest
            print(f"{status:10} {e.local_path}", flush=True)
        if e.download_status == "exists":
            e.download_status = "downloaded"  # stable value across reruns
        elif e.download_status.startswith("http_"):
            e.download_status = "failed_" + e.download_status
        if dest.exists():
            try:
                with pymupdf.open(dest) as doc:
                    e.pdf_pages = str(doc.page_count)
                    folios = printed_folios(doc)
            except Exception as err:  # noqa: BLE001
                e.download_status = "failed"
                e.remarks.append(f"PDF unreadable: {err}")
                folios = None
            # printed folios on first and last page win over file name / TOC (checked at checkpoint 1)
            if folios:
                f1, fn = folios
                printed = f"{f1}–{fn}" if fn != f1 else str(f1)
                if e.pages.split(" ")[0] != printed:
                    e.remarks.append(f"pages corrected from printed folios (was {e.pages})")
                    e.pages = printed
                    if e.citation_source == "constructed":
                        e.citation = f"{JOURNAL} {e.issue_no}: {e.pages}, {e.year}"
                    elif e.citation_source in ("page", "zenodo"):
                        e.remarks.append("citation pages differ from printed folios")
            if e.zenodo_file_md5:
                import hashlib
                if hashlib.md5(dest.read_bytes()).hexdigest() != e.zenodo_file_md5:
                    e.remarks.append("MD5 mismatch with Zenodo checksum")
            # single printed page but multi-page PDF → end page from page count (checkpoint 0, Q3)
            if e.pdf_pages and re.fullmatch(r"\d+", e.pages or "") and int(e.pdf_pages) > 1:
                start = int(e.pages)
                e.pages = f"{start}–{start + int(e.pdf_pages) - 1}"
                e.remarks.append("end page derived from PDF page count")
                if e.citation_source == "constructed":
                    e.citation = f"{JOURNAL} {e.issue_no}: {e.pages}, {e.year}"

    # ---- write
    out = ROOT / "manifest.csv"
    write_csv(out, [e.row() for e in entries], MANIFEST_COLUMNS)
    (CACHE / "crawl_log.txt").write_text("\n".join(log), encoding="utf-8")
    print("\n".join(log))
    print(f"\n{len(entries)} manifest rows written to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-fetch index, issue pages and Zenodo metadata")
    ap.add_argument("--no-download", action="store_true")
    ARGS = ap.parse_args()
    main()
