"""Step 2: transcribe article PDFs (text layer, PyMuPDF) into Markdown, one file per PDF.

    python scripts/02_transcribe.py                    # all downloaded PDFs in manifest.csv
    python scripts/02_transcribe.py --only 10-43-52    # PDFs whose file name contains any given substring

Output: md/<issue folder>/<pdf stem>.md with YAML front matter and <!-- page N --> markers
(N = printed page number). Per-file notes go to cache/transcribe_log.jsonl.

Transcription rules (faithful; no corrections):
- reading order = PDF content-stream order; pieces of one visual line are merged
- running headers (journal line, folio, section label in the top band) are dropped; folio feeds the page markers
- paragraphs rebuilt from geometry: short previous line, indentation change, vertical gap, list labels, headings
- soft hyphens (U+00AD) at line end are rejoined; hard hyphens / dashes at line end are kept and joined without
  space, except in PDFs that hyphenate with "-" (č. 3, parts of č. 7): there a line-end "-" before a lower-case
  continuation is removed unless the hyphenated word occurs mid-line elsewhere (cache/hyphen_vocab.json)
- text-layer repairs: č. 3 ligature glyphs (U+03D0/U+03D4 → f) and scrambled small-caps bylines (BYLINE_CIPHER)
- output is Unicode NFC
- italic → *…*, bold → **…**, superscript → <sup>…</sup>; NBSP and tabs become single spaces
- images without text → <!-- image --> comment (not transcribed)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import unicodedata
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, MD_DIR, ROOT  # noqa: E402

# hand transcriptions of images that carry text (tables), by a vision model: manual/<folder>/<stem>.p<page>.img<k>.md
MANUAL_DIR = ROOT / "manual"

HEADER_BAND = 62.0          # pt from top: running header zone
FOOTER_BAND = 40.0          # pt from bottom
FULL_LINE_TOL = 25.0        # a line ending within this of the right margin is "full"
INDENT_MIN = 8.0
HEADER_TEXT = re.compile(r"^(Zprávy Moravskoslezské pobočky.*|\d{1,3}|[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9 ,.–-]{2,40})$")
# labels that open a new paragraph: "12.\t…", "1. 76b. Tršická…", "74a. Vidnavsko…" (not dates like "25. 12. 2020")
UC = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
LIST_LABEL = re.compile(
    rf"^\s*(?:\d{{1,3}}[a-z]?\.\s*\t"
    rf"|\d{{1,3}}[a-z]?\.\s+(?=\d{{2}}[a-z]?\.\s+[{UC}])"
    rf"|\d{{2}}[a-z]?\.\s+(?=[{UC}][a-záčďéěíňóřšťúůýž]))"
)
# private-use / replacement characters or "(cid:N)" mean a broken text layer
GARBLED = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + chr(0xFFFD) + "]" + r"|\(cid:\d+\)")
# table-of-contents line: "Title<TAB>page" (right-aligned page number) ends its paragraph
TOC_LINE_END = re.compile(r"\t\s*\d{1,3}\s*$")
# manual line breaks inside spans (Word exports) are layout, not content
LINEBREAK_CHARS = {c: " " for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x2028, 0x2029)}

# ---- text-layer repairs (confirmed after the full-scale stop; logged per file in extraction_method)
# č. 3: the fi/fl ligature's "f" is encoded as U+03D0 / U+03D4 ("speciϐický", "grandiϔlorum")
GLYPH_FIX = {0x03D0: "f", 0x03D4: "f"}
# č. 3: author bylines set in a small-caps font whose lower-case letters carry a scrambled encoding
# ("Ċęė KĔĈĎġē" = "(P)etr Kocián"); derived from and checked against the manifest authors
BYLINE_CIPHER = str.maketrans({
    "Ć": "a", "ć": "b", "Ĉ": "c", "Į": "č", "ĉ": "d", "Ċ": "e", "Ķ": "ě", "Ď": "i", "Ń": "í", "Đ": "k",
    "đ": "l", "Ē": "m", "ē": "n", "Ĕ": "o", "ĕ": "p", "ė": "r", "ţ": "ř", "Ę": "s", "ŧ": "š", "ę": "t",
    "Ě": "u", "ě": "v", "Ğ": "y", "ż": "ý", "ğ": "z", "Ĵ": "é", "č": "h", "ġ": "á", "ƭ": "&",
})
BYLINE_MARK = set("ĆćĈĮĉĊĶĎŃĐđĒēĔĕėţĘŧęĚĞżğĴġƭ")
HYPHEN_VOCAB_PATH = CACHE / "hyphen_vocab.json"
# per-document state, reset in transcribe()
DOC = {"repairs": Counter(), "authors": set(), "hard_hyphens": False, "hyphen_log": []}


def repair_span(text: str) -> str:
    """Apply GLYPH_FIX everywhere and BYLINE_CIPHER to scrambled small-caps spans."""
    n = sum(text.count(chr(c)) for c in GLYPH_FIX)
    if n:
        DOC["repairs"]["ligature glyph → f"] += n
        text = text.translate(GLYPH_FIX)
    if sum(c in BYLINE_MARK for c in text) >= 2 and not re.search(r"[a-z]", text):
        decoded = text.translate(BYLINE_CIPHER)
        # small caps lose case: take the capitalisation of matching manifest author names
        words = {w.lower(): w for w in DOC["authors"]}
        decoded = re.sub(r"[^\W\d_]+", lambda m: words.get(m.group(0).lower(), m.group(0)), decoded)
        DOC["repairs"]["scrambled small-caps span decoded"] += 1
        return decoded
    return text


def hyphen_vocab() -> set[str]:
    """Words printed with an internal hyphen mid-line anywhere in the corpus, plus hyphenated checklist names."""
    if HYPHEN_VOCAB_PATH.exists():
        return set(json.loads(HYPHEN_VOCAB_PATH.read_text(encoding="utf-8")))
    vocab: set[str] = set()
    for pdf in sorted((ROOT / "pdf").rglob("*.pdf")):
        with pymupdf.open(pdf) as doc:
            for pg in doc:
                for line in pg.get_text("text").splitlines():
                    vocab.update(w.lower() for w in re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)+", line.translate(GLYPH_FIX)))
    checklist = ROOT / "reference" / "checklist_aopk.csv"
    if checklist.exists():
        for r in csv.DictReader(open(checklist, encoding="utf-8-sig")):
            vocab.update(w.lower() for w in re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)+", r["scientific_name"]))
    HYPHEN_VOCAB_PATH.write_text(json.dumps(sorted(vocab), ensure_ascii=False), encoding="utf-8")
    return vocab


def uses_hard_hyphenation(doc) -> bool:
    """True when the PDF hyphenates words at line ends with '-' rather than a soft hyphen (č. 3, parts of č. 7)."""
    soft = hard = 0
    for pg in doc:
        lines = pg.get_text("text").splitlines()
        for a, b in zip(lines, lines[1:]):
            a = a.rstrip()
            if a.endswith("\xad"):
                soft += 1
            elif re.search(r"[a-záčďéěíňóřšťúůýž]-$", a) and re.match(r"\s*[a-záčďéěíňóřšťúůýž]", b):
                hard += 1
    return hard >= 3 and hard > soft


@dataclass
class Run:
    text: str
    italic: bool = False
    bold: bool = False
    sup: bool = False
    raw: bool = False  # already Markdown (page markers)

    def style(self):
        return (self.italic, self.bold, self.sup, self.raw)


@dataclass
class Line:
    runs: list[Run]
    x0: float
    x1: float
    y0: float
    y1: float
    size: float
    page: int  # printed page number
    pidx: int = 0  # PDF page index

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def table(self) -> bool:
        """Pseudo-line carrying a whole Markdown table."""
        return bool(self.runs) and self.runs[0].raw

    @property
    def all_bold(self) -> bool:
        vis = [r for r in self.runs if r.text.strip()]
        return bool(vis) and all(r.bold for r in vis)

    @property
    def all_italic(self) -> bool:
        vis = [r for r in self.runs if r.text.strip()]
        return bool(vis) and all(r.italic for r in vis)


@dataclass
class Para:
    kind: str                     # p | h1 | h2 | h3 | image
    lines: list[Line] = field(default_factory=list)
    runs: list[Run] = field(default_factory=list)
    hanging: bool = False
    page: int = 0                 # image paragraphs: printed page and 1-based image index
    img: int = 0


def span_style(span) -> tuple[bool, bool, bool]:
    font = span["font"]
    italic = bool(span["flags"] & 2) or bool(re.search(r"(Italic|Oblique|-It\b|It$|BoldIt)", font))
    bold = bool(span["flags"] & 16) or "Bold" in font or "Black" in font or "Semibold" in font
    sup = bool(span["flags"] & 1)
    return italic, bold, sup


def _inside(bbox, rect, tol: float = 1.0) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return rect[0] - tol <= cx <= rect[2] + tol and rect[1] - tol <= cy <= rect[3] + tol


def _cell_runs(lines: list[dict], cell) -> list[Run]:
    """Runs of the spans whose centre lies in the cell; lines joined with a space or a hyphen join."""
    out: list[Run] = []
    for ln in lines:
        spans = [s for s in ln["spans"] if s["text"].strip() and _inside(s["bbox"], cell)]
        if not spans:
            continue
        if out:
            tail = out[-1]
            if tail.text.rstrip().endswith("\xad"):
                tail.text = tail.text.rstrip()[:-1]
            elif not re.search(r"\S[-–]$", tail.text.rstrip()):
                out.append(Run(" "))
        for s in spans:
            it, bd, sp = span_style(s)
            out.append(Run(repair_span(s["text"].translate(LINEBREAK_CHARS)), it, bd, sp))
    return out


def page_tables(page, dict_blocks) -> list[tuple[tuple, str]]:
    """Ruled tables on the page as (bbox, Markdown). Sideways tables are turned to reading orientation."""
    try:
        found = page.find_tables().tables
    except Exception:  # noqa: BLE001 — table detection is best effort
        return []
    lines = [l for b in dict_blocks if b["type"] == 0 for l in b["lines"]]
    # on /Rotate pages, table geometry is in rotated space but text boxes are not
    unrot = (lambda r: tuple(pymupdf.Rect(r) * page.derotation_matrix)) if page.rotation else (lambda r: tuple(r))
    out = []
    for t in found:
        grid = []
        for row in t.rows:
            grid.append([render(_cell_runs(lines, unrot(c)), "cell") if c else "" for c in row.cells])
        filled_rows = sum(1 for r in grid if sum(1 for c in r if c.strip()) >= 2)
        if len(grid) < 3 or t.col_count < 2 or filled_rows < 3 or (t.bbox[2] - t.bbox[0]) < 150:
            continue
        bbox = unrot(t.bbox)
        dirs = Counter(tuple(round(v) for v in l["dir"]) for l in lines if _inside(l["bbox"], bbox))
        main_dir = dirs.most_common(1)[0][0] if dirs else (1, 0)
        if page.rotation == 0 and main_dir == (0, -1):      # text reads bottom→top: printed columns are page rows
            grid = [list(r) for r in zip(*reversed(grid))]
        elif page.rotation == 0 and main_dir == (0, 1):     # text reads top→bottom
            grid = [list(r) for r in reversed(list(zip(*grid)))]
        width = max(len(r) for r in grid)
        grid = [r + [""] * (width - len(r)) for r in grid]
        md = ["| " + " | ".join(c.replace("|", r"\|") for c in grid[0]) + " |",
              "|" + "---|" * width]
        md += ["| " + " | ".join(c.replace("|", r"\|") for c in r) + " |" for r in grid[1:]]
        out.append((bbox, "\n".join(md)))
    return out


def page_lines(page) -> tuple[list[Line], list[str], int]:
    """Body lines in stream order (same-baseline pieces merged), header texts, image count.

    Ruled tables become single pseudo-lines (Line.table) holding their Markdown, placed where
    the table's first line was in the stream.
    """
    height = page.rect.height
    raw: list[tuple[list[Run], tuple, float]] = []
    images = 0
    blocks = page.get_text("dict")["blocks"]
    tables = page_tables(page, blocks)
    placed: set[int] = set()
    for block in blocks:
        if block["type"] == 1:
            w, h = block["bbox"][2] - block["bbox"][0], block["bbox"][3] - block["bbox"][1]
            if w > 40 and h > 40 and not any(_inside(block["bbox"], tb) for tb, _ in tables):
                images += 1
            continue
        for ln in block["lines"]:
            ti = next((k for k, (tb, _) in enumerate(tables) if _inside(ln["bbox"], tb)), None)
            if ti is not None:
                if ti not in placed:
                    placed.add(ti)
                    raw.append(([Run(tables[ti][1], raw=True)], tables[ti][0], 0.0))
                continue
            runs, sizes = [], []
            for s in ln["spans"]:
                if not s["text"]:
                    continue
                it, bd, sp = span_style(s)
                runs.append(Run(repair_span(s["text"].translate(LINEBREAK_CHARS)), it, bd, sp))
                sizes += [s["size"]] * len(s["text"].strip())
            if runs:
                raw.append((runs, ln["bbox"], statistics.mode(sizes) if sizes else 0.0))
    # running header/footer pieces are classified one by one, before any merging
    header: list[str] = []
    kept = []
    for runs, bbox, size in raw:
        if runs[0].raw:
            kept.append((runs, bbox, size))
            continue
        text = re.sub(r"\s+", " ", "".join(r.text for r in runs)).strip()
        # line tops only: some Word PDFs report very tall line boxes (3/P1 header box ends at 80 pt)
        in_band = bbox[1] < HEADER_BAND - 7 or bbox[1] > height - FOOTER_BAND
        if in_band and (not text or HEADER_TEXT.match(text)):
            if text:
                header.append(text)
            continue
        kept.append((runs, bbox, size))
    # merge pieces sharing a baseline (tabs split a visual line into several PyMuPDF lines)
    merged: list[list] = []
    for runs, bbox, size in kept:
        if merged and not runs[0].raw and not merged[-1][0][0].raw:
            prev = merged[-1]
            if abs(prev[1][1] - bbox[1]) < 3.0 and bbox[0] >= prev[1][2] - 1.0:
                if prev[0] and not prev[0][-1].text.endswith((" ", "\t")):
                    prev[0].append(Run(" "))
                prev[0].extend(runs)
                prev[1] = (prev[1][0], min(prev[1][1], bbox[1]), bbox[2], max(prev[1][3], bbox[3]))
                prev[2] = max(prev[2], size)
                continue
        merged.append([list(runs), tuple(bbox), size])
    body = [Line(runs, bbox[0], bbox[2], bbox[1], bbox[3], size, 0)
            for runs, bbox, size in merged if "".join(r.text for r in runs).strip()]
    return body, header, images


def folio_of(header: list[str]) -> int | None:
    nums = [int(h) for h in header if re.fullmatch(r"\d{1,3}", h)]
    return nums[0] if len(nums) == 1 else None


def printed_pages(folios: list[int | None]) -> tuple[list[int], list[str]]:
    """Fill printed page numbers: consistent offset from detected folios; report disagreements."""
    notes = []
    offsets = [f - i for i, f in enumerate(folios) if f is not None]
    if not offsets:
        return [], ["no printed folios detected"]
    off = Counter(offsets).most_common(1)[0][0]
    out = []
    for i, f in enumerate(folios):
        if f is not None and f - i != off:
            notes.append(f"pdf page {i + 1}: printed folio {f} ≠ expected {i + off}")
        out.append(i + off)
    missing = [i + off for i, f in enumerate(folios) if f is None]
    if missing:
        notes.append(f"folio not printed/detected on pages {missing} (numbered by offset)")
    return out, notes


# ---------------------------------------------------------------- paragraph assembly

def is_heading(line: Line, body_size: float) -> str | None:
    if not line.all_bold or line.all_italic:
        return None
    text = line.text.strip()
    if len(text) > 160 or len(re.findall(r"[^\W\d_]", text)) < 2:
        return None
    if line.size >= body_size + 4:
        return "h1"
    return "h2" if line.size >= 14 else "h3"


def line_is_full(line: Line, left: float, right: float) -> bool:
    """Reaches the right margin and is long (a right-aligned signature is not a full line)."""
    return line.x1 >= right - FULL_LINE_TOL and (line.x1 - line.x0) > 0.5 * (right - left)


def starts_list_entry(line: Line, prev: Line) -> bool:
    """'*Taxon name*: …' after a line that did not end with a list separator (one-entry-per-line lists)."""
    first = next((r for r in line.runs if r.text.strip()), None)
    if first is None or not first.italic:
        return False
    plain = re.sub(r"\s+", " ", line.text.replace("\xad", "")).strip()
    # "Genus species [subsp. x] [agg.|s. str.|sp.] [(note)]:" — a name of at most ~8 words, then a colon
    m = re.match(rf"^[{UC}×][\w×.\- ]{{2,80}}?(?:\s*\([^)]*\))?:(?:\s|$)", plain)
    return bool(m) and len(m.group(0).split()) <= 9 and not prev.text.rstrip().endswith((";", ","))


def build_paragraphs(lines: list[Line], body_size: float, left: float, right: float) -> list[Para]:
    paras: list[Para] = []
    cur: Para | None = None
    prev: Line | None = None
    spacing = []
    for a, b in zip(lines, lines[1:]):
        d = b.y0 - a.y0
        if 0 < d < 3 * body_size:
            spacing.append(d)
    line_gap = statistics.median(spacing) if spacing else body_size * 1.2

    for ln in lines:
        if ln.table:                     # a whole table: its own block, breaks any running paragraph
            paras.append(Para("table", lines=[ln]))
            cur, prev = None, None
            continue
        head = is_heading(ln, body_size)
        new = True
        if cur is not None and prev is not None:
            prev_full = line_is_full(prev, left, right)
            gap = ln.y0 - prev.y0
            big_gap = gap > 1.45 * 1.2 * max(ln.size, prev.size) or gap < -2 * line_gap
            if cur.kind.startswith("h"):
                new = not (head == cur.kind and abs(ln.size - prev.size) < 0.6 and not big_gap)
            elif head or big_gap or LIST_LABEL.match(ln.text) or starts_list_entry(ln, prev):
                new = True
            elif not prev_full or TOC_LINE_END.search(prev.text):
                new = True
            else:
                first = cur.lines[0]
                if len(cur.lines) == 1:
                    if ln.x0 > first.x0 + INDENT_MIN:
                        cur.hanging = True
                    new = False
                else:
                    cont_x = cur.lines[1].x0     # where this paragraph's continuation lines sit
                    if cur.hanging:
                        new = ln.x0 < cont_x - INDENT_MIN
                    else:
                        new = abs(ln.x0 - cont_x) > INDENT_MIN
        if new:
            cur = Para(head or "p")
            paras.append(cur)
        cur.lines.append(ln)
        prev = ln
    return paras


def hard_hyphen_break(prev_text: str, next_runs: list[Run]) -> bool:
    """In PDFs hyphenating with '-', a line-end hyphen before a lower-case continuation is a word break,
    unless the hyphenated word is printed mid-line elsewhere (compound: Vidnavsko-osoblažská, flos-cuculi)."""
    if not DOC["hard_hyphens"] or not prev_text.endswith("-"):
        return False
    nxt = "".join(r.text for r in next_runs).lstrip()
    w1 = re.search(r"([^\W\d_]+)-$", prev_text)
    w2 = re.match(r"([^\W\d_]+)", nxt)
    if not w1 or not w2 or not w2.group(1)[0].islower():
        return False
    word = f"{w1.group(1)}-{w2.group(1)}"
    compound = word.lower() in DOC["vocab"]
    DOC["hyphen_log"].append(f"{word} → {'kept' if compound else w1.group(1) + w2.group(1)}")
    return not compound


def join_runs(lines: list[Line]) -> list[Run]:
    """Concatenate the runs of a paragraph's lines, rejoining hyphenation."""
    out: list[Run] = []
    for i, ln in enumerate(lines):
        runs = [Run(r.text, r.italic, r.bold, r.sup, r.raw) for r in ln.runs]
        # whitespace-only runs at a line boundary would break style continuity (*Fragaria* *moschata*)
        while len(runs) > 1 and not runs[0].text.strip():
            runs.pop(0)
        while len(out) > 1 and not out[-1].raw and not out[-1].text.strip(" \t\xa0"):
            out.pop()
        if i and out:
            tail = out[-1]
            stripped = tail.text.rstrip(" \t\xa0")
            marker = None
            if ln.page != lines[i - 1].page:
                marker = Run(f"<!-- page {ln.page} -->", raw=True)
            if stripped.endswith("\xad") or hard_hyphen_break(stripped, runs):
                tail.text = stripped[:-1]
                if marker:  # keep the split word intact; marker goes after it
                    first = runs[0]
                    m = re.match(r"^(\S*)(.*)$", first.text, re.S)
                    runs[0:1] = [Run(m[1], first.italic, first.bold, first.sup), Run(" "), marker,
                                 Run(m[2], first.italic, first.bold, first.sup)]
            elif re.search(r"\S[-–]$", stripped) and tail.text == stripped:
                if marker:
                    runs.insert(0, marker)
            else:
                tail.text = stripped
                sep_style = runs[0].style() == tail.style() and not tail.raw
                sep = Run(" ", tail.italic, tail.bold, tail.sup) if sep_style else Run(" ")
                out.append(sep)
                if marker:
                    out.extend([marker, Run(" ")])
        out.extend(runs)
    return out


MD_ESCAPE = str.maketrans({"*": r"\*", "_": r"\_", "`": r"\`"})


def render(runs: list[Run], kind: str) -> str:
    # normalise whitespace inside runs, merge same-style neighbours
    norm: list[Run] = []
    for r in runs:
        t = r.text if r.raw else re.sub(r"[\t\xa0 ]+", " ", r.text.replace("\xad", ""))
        if not t:
            continue
        if norm and norm[-1].style() == r.style() and not r.raw:
            norm[-1].text += t
        else:
            norm.append(Run(t, r.italic, r.bold, r.sup, r.raw))
    # a plain space typeset between two italic words belongs to the italic phrase (*Poa nemoralis*)
    i = 1
    while i < len(norm) - 1:
        a, ws, b = norm[i - 1], norm[i], norm[i + 1]
        if not ws.raw and not ws.text.strip() and a.style() == b.style() and not a.raw:
            a.text += ws.text + b.text
            del norm[i:i + 2]
        else:
            i += 1
    parts = []
    in_heading = kind.startswith("h")
    for r in norm:
        if r.raw:
            parts.append(r.text)
            continue
        t = r.text.translate(MD_ESCAPE)
        if not t.strip():
            parts.append(t)
            continue
        lead = t[: len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        core = t.strip()
        if r.sup:
            core = f"<sup>{core}</sup>"
        bold = r.bold and not in_heading
        if r.italic and bold:
            core = f"***{core}***"
        elif r.italic:
            core = f"*{core}*"
        elif bold:
            core = f"**{core}**"
        parts.append(lead + core + trail)
    text = re.sub(r" {2,}", " ", "".join(parts)).strip()
    if kind == "p":
        text = re.sub(r"^(\d{1,3})\.(?=\s)", r"\1\\.", text)      # keep printed numbers (no list renumbering)
        text = re.sub(r"^([#>+-])", r"\\\1", text)
    return text


# ---------------------------------------------------------------- document

def transcribe(pdf_path: Path, meta: dict) -> tuple[str, dict]:
    doc = pymupdf.open(pdf_path)
    DOC.update(repairs=Counter(), hyphen_log=[], hard_hyphens=uses_hard_hyphenation(doc),
               authors=set(re.findall(r"[^\W\d_]+", meta.get("authors", ""))))
    if DOC["hard_hyphens"] and "vocab" not in DOC:
        DOC["vocab"] = hyphen_vocab()
    pages, headers, images, folios = [], [], [], []
    garbled_chars = total_chars = 0
    for pg in doc:
        body, header, n_img = page_lines(pg)
        pages.append(body)
        headers.append(header)
        images.append(n_img)
        folios.append(folio_of(header))
        txt = "".join(l.text for l in body)
        total_chars += len(txt)
        garbled_chars += len(GARBLED.findall(txt))
    printed, notes = printed_pages(folios)
    if not printed:  # no folios at all: number from the manifest start page
        start = int(re.match(r"\d+", meta.get("pages") or "1")[0])
        printed = [start + i for i in range(len(pages))]
    all_lines = []
    for i, body in enumerate(pages):
        for ln in body:
            ln.page = printed[i]
            ln.pidx = i
        all_lines.extend(body)

    sizes = Counter()
    for ln in all_lines:
        if not ln.table:
            sizes[round(ln.size * 2) / 2] += len(ln.text)
    body_size = sizes.most_common(1)[0][0] if sizes else 12.0
    xs = [round(ln.x0) for ln in all_lines if abs(ln.size - body_size) < 1.5]
    x1s = sorted(ln.x1 for ln in all_lines if abs(ln.size - body_size) < 1.5)

    stats = {"pages": len(pages), "images": sum(images), "header_lines_dropped": sum(len(h) for h in headers)}
    # margins per page parity (mirrored layouts have different left margins on odd/even pages)
    by_parity: dict[int, list[Line]] = {0: [], 1: []}
    for i, body in enumerate(pages):
        by_parity[i % 2].extend(body)
    margins = {}
    for par, ls in by_parity.items():
        bl = [l for l in ls if abs(l.size - body_size) < 1.5]
        if bl:
            left = Counter(round(l.x0) for l in bl).most_common(1)[0][0]
            right = sorted(l.x1 for l in bl)[int(len(bl) * 0.95)]
            margins[par] = (left, right)
    default_margins = (min(xs or [50]), max(x1s or [540]))

    def margin(pidx: int) -> tuple[float, float]:
        return margins.get(pidx % 2) or margins.get(0) or default_margins

    def continues_across(prev: Para | None, first: Para, pidx: int) -> bool:
        """Does the first paragraph of page pidx continue the last paragraph of the previous page?"""
        if not prev or prev.kind != "p" or first.kind != "p" or not prev.lines:
            return False
        last, fl = prev.lines[-1], first.lines[0]
        if not line_is_full(last, *margin(last.pidx)) or LIST_LABEL.match(fl.text) or starts_list_entry(fl, last):
            return False
        rel = fl.x0 - margin(pidx)[0]
        if len(prev.lines) > 1:
            cont_rel = prev.lines[1].x0 - margin(prev.lines[1].pidx)[0]
            return rel >= cont_rel - INDENT_MIN if prev.hanging else abs(rel - cont_rel) <= INDENT_MIN
        first_rel = prev.lines[0].x0 - margin(prev.lines[0].pidx)[0]
        return rel <= INDENT_MIN or rel > first_rel + INDENT_MIN

    # paragraphs are built per page (margins differ on mirrored pages), then joined across page breaks;
    # a joined paragraph gets its page marker inline (see join_runs)
    paras: list[Para] = []
    for i, body in enumerate(pages):
        left, right = margin(i)
        page_paras = build_paragraphs(body, body_size, left, right)
        prev_text = next((p for p in reversed(paras) if p.kind not in ("marker", "image")), None)
        if page_paras and continues_across(prev_text, page_paras[0], i):
            prev_text.lines.extend(page_paras[0].lines)
            page_paras = page_paras[1:]
        else:
            paras.append(Para("marker", runs=[Run(f"<!-- page {printed[i]} -->", raw=True)]))
        paras.extend(page_paras)
        paras.extend(Para("image", page=printed[i], img=k + 1) for k in range(images[i]))

    md_blocks = []
    vision_pages: list[int] = []
    for p in paras:
        if p.kind == "marker":
            md_blocks.append(p.runs[0].text)
        elif p.kind == "table":
            md_blocks.append(p.lines[0].runs[0].text)
        elif p.kind == "image":
            manual = MANUAL_DIR / pdf_path.parent.name / f"{pdf_path.stem}.p{p.page}.img{p.img}.md"
            if manual.exists():
                vision_pages.append(p.page)
                src = manual.relative_to(ROOT).as_posix()
                md_blocks.append(f"<!-- begin: image p. {p.page} #{p.img} transcribed by vision model, "
                                 f"not from the text layer ({src}) -->")
                md_blocks.append(manual.read_text(encoding="utf-8").strip())
                md_blocks.append("<!-- end: image transcription -->")
            else:
                md_blocks.append("<!-- image (no text layer; not transcribed) -->")
        else:
            text = render(join_runs(p.lines), p.kind)
            if not text:
                continue
            prefix = {"h1": "# ", "h2": "## ", "h3": "### "}.get(p.kind, "")
            md_blocks.append(prefix + text)
    # canonical composition only (e.g. "C" + combining caron → "Č"); no compatibility folding
    body_md = unicodedata.normalize("NFC", "\n\n".join(md_blocks))

    garbled_ratio = garbled_chars / total_chars if total_chars else 1.0
    method = f"text layer (PyMuPDF {pymupdf.VersionBind})"
    if vision_pages:
        method += f"; image tables on p. {', '.join(map(str, sorted(set(vision_pages))))} transcribed by vision model"
    if DOC["repairs"]:
        method += "; text-layer repairs: " + ", ".join(f"{k} ×{v}" for k, v in DOC["repairs"].items())
    removed = sum(1 for h in DOC["hyphen_log"] if not h.endswith("kept"))
    if DOC["hard_hyphens"]:
        method += f"; line-end '-' hyphenation rejoined ×{removed} (kept as compounds ×{len(DOC['hyphen_log']) - removed})"
    stats["hyphen_joins"] = DOC["hyphen_log"]
    if total_chars == 0 or garbled_ratio > 0.01:
        method += " — TEXT LAYER MISSING/GARBLED, needs OCR"
    stats.update({"chars": total_chars, "garbled_ratio": round(garbled_ratio, 4), "body_font_size": body_size,
                  "folio_notes": notes, "printed_pages": f"{printed[0]}–{printed[-1]}" if printed else ""})
    fm = front_matter(meta, method, printed)
    return fm + "\n" + body_md + "\n", stats


def yaml_str(v) -> str:
    v = "" if v is None else str(v)
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(meta: dict, method: str, printed: list[int]) -> str:
    fields = [
        ("title", meta["title"]), ("authors", meta["authors"]), ("issue", meta["issue_no"]),
        ("supplement", meta.get("supplement", "")), ("year", meta["year"]), ("pages", meta["pages"]),
        ("citation", meta["citation"]), ("pdf_url", meta["pdf_url"]), ("zenodo_doi", meta.get("zenodo_doi", "")),
        ("source_file", meta["local_path"]), ("extraction_method", method),
    ]
    lines = ["---"] + [f"{k}: {yaml_str(v)}" for k, v in fields]
    extra = meta.get("_also")
    if extra:
        lines.append("also_contains:")
        lines += [f"  - {yaml_str(t)}" for t in extra]
    lines.append("---")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="substrings of PDF file names to process")
    args = ap.parse_args()
    rows = [r for r in csv.DictReader(open(ROOT / "manifest.csv", encoding="utf-8-sig"))
            if r["download_status"] == "downloaded" and r["local_path"]]
    by_path: dict[str, dict] = {}
    for r in rows:
        if r["local_path"] in by_path:
            by_path[r["local_path"]].setdefault("_also", []).append(r["title"])
        else:
            by_path[r["local_path"]] = dict(r)
    log_path = CACHE / "transcribe_log.jsonl"
    done = 0
    with open(log_path, "a", encoding="utf-8") as log:
        for path, meta in by_path.items():
            if args.only and not any(s in Path(path).name for s in args.only):
                continue
            pdf = ROOT / path
            md_text, stats = transcribe(pdf, meta)
            folder = Path(path).parent.name
            out = MD_DIR / folder / (pdf.stem + ".md")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md_text, encoding="utf-8")
            stats.update({"pdf": path, "md": out.relative_to(ROOT).as_posix()})
            log.write(json.dumps(stats, ensure_ascii=False) + "\n")
            print(f"{out.relative_to(ROOT).as_posix()}: {stats['pages']} pp, {stats['chars']} chars, "
                  f"{stats['images']} images, garbled {stats['garbled_ratio']}, notes {stats['folio_notes']}")
            done += 1
    print(f"{done} files transcribed")


if __name__ == "__main__":
    main()
