"""Gold-standard review packages: every italic taxon-like name of a gold article, checked against the parser output.

    python scripts/gold_candidates.py                 # all articles of tests/gold/gold_articles.csv
    python scripts/gold_candidates.py --only ZMSP7_66-69

For each gold article this writes
  tests/gold/review/<article>.pdf          the original PDF, every candidate highlighted and labelled with its cand_id
                                           (green = the parser produced an occurrence for it, red = it did not,
                                            grey = literature / front matter / caption, i.e. out of scope)
  tests/gold/review/<article>_cp1250.csv   one row per candidate (Windows-1250, ';'), pre-filled from the parser output

The harvester is deliberately over-inclusive and independent of the parser's rules (it shares no code with
03_excerpt.py): it takes every italic name that looks like a taxon — "Genus epithet", abbreviated "B. rutabulum",
"Genus sp.", infraspecific ranks, hybrids — rejoins names that the transcription split across a paragraph break, and
records the name's page, its source line and the nearest locality context. Table cells are taken when they start with
a binomial even if not italic. Czech-only names are not harvested: the reviewer adds them in the block at the end.

Parser occurrences are linked to candidates by taxon text and position; parser rows that no candidate explains are
added as "P…" rows so that every parser occurrence of the article is reviewed (precision).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MD_DIR, ROOT, _cp1250_safe  # noqa: E402

GOLD = ROOT / "tests" / "gold"
REVIEW_COLS = ["cand_id", "page", "taxon_as_printed", "source_line", "parser_occurrence_id", "parser_locality",
               "parser_date", "record_type_suggested", "is_record", "locality_ok", "date_ok", "correction", "note",
               "colour", "harvest_locality"]
MISSED_ROWS = 25

UC = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
LC = "a-záčďéěíňóřšťúůýžëäöü"
RANK = r"(?:subsp\.|ssp\.|var\.|f\.|nothosubsp\.|nothovar\.|sect\.|ser\.|subg\.)"
TAIL = r"(?:agg\.|s\.\s?l\.|s\.\s?str\.|s\.\s?lat\.|sp\.|spp\.)"
GENUS = rf"[{UC}][{LC}]+(?:-[{LC}]+)?"
ABBR = rf"[{UC}][{LC}]?\."
EPI = rf"[{LC}][{LC}-]*[{LC}](?![{LC}-])"
LOCREF = r"\d{1,3}(?:[a-z]{1,3}|[A-Z])?"
REFS = re.compile(rf"^\s*(?:\([^()]*\)\s*|\[[^\[\]]*\]\s*)*:?\s*({LOCREF}(?:\s*\([^()]*\))?(?:\s*\[[^\]]*\])?"
                  rf"(?:\s*[,:]\s*{LOCREF}(?:\s*\([^()]*\))?(?:\s*\[[^\]]*\])?)*)\s*(?=[;.]|$)")
LITERATURE_HEAD = re.compile(r"^(Použité zdroje|Literatura|Citovaná literatura|Zdroje|References)\b", re.I)
FRONT_PARA = re.compile(r"^(Abstract|Keywords|Key words|Klíčová slova|Taxonomické pojetí|Nomenklatura)\b|e-mail", re.I)
CAPTION = re.compile(r"^(Obr\.|Obrázek|Fig\.|Tab\.|Tabulka)\s*\d*", re.I)
LOCALITY_LIKE = re.compile(r"\d+\s*°\s*\d+\s*[′'’‘]|\b\d{4}[a-d]\b|\((?:distr\.|okres)|^\d{1,3}[a-z]?(?:\.|\s[–-])\s+\S")
MARKER = re.compile(r"<!--\s*page\s+(\d+)\s*-->")


# ---------------------------------------------------------------- Markdown → plain text with italic mask

def decode(md: str) -> tuple[str, list[bool], list[bool], list[tuple[int, int]]]:
    """Markdown inline → (plain text, italic and bold flag per char, [(offset, page)] for inline page markers).
    Same plain text as the transcription's Markdown (comments and <sup> dropped, escapes resolved)."""
    out, ital, bold, marks = [], [], [], []
    i, it, bd, n = 0, False, False, len(md)
    while i < n:
        if md.startswith("<!--", i):
            j = md.find("-->", i)
            j = n if j < 0 else j + 3
            m = MARKER.match(md, i)
            if m:
                marks.append((len(out), int(m.group(1))))
            i = j
            if out and out[-1] == " " and i < n and md[i] == " ":
                i += 1
            continue
        if md.startswith("<sup>", i) or md.startswith("</sup>", i):
            i = md.find(">", i) + 1
            continue
        c = md[i]
        if c == "\\" and i + 1 < n and md[i + 1] in "\\*_`.#>+-[]()!|":
            out.append(md[i + 1])
            ital.append(it)
            bold.append(bd)
            i += 2
            continue
        if md.startswith("***", i):
            it, bd, i = not it, not bd, i + 3
            continue
        if md.startswith("**", i):
            bd, i = not bd, i + 2
            continue
        if c == "*":
            it, i = not it, i + 1
            continue
        out.append(c)
        ital.append(it)
        bold.append(bd)
        i += 1
    return "".join(out), ital, bold, marks


@dataclass
class Para:
    idx: int
    kind: str                        # h1 h2 h3 p table
    text: str
    ital: list[bool]
    page: int
    marks: list[tuple[int, int]] = field(default_factory=list)
    section: str = ""                # text of the last h2/h3
    zone: str = "body"               # front / literature / caption / title / body
    bold: list[bool] = field(default_factory=list)

    def page_at(self, off: int) -> int:
        p = self.page
        for o, pg in self.marks:
            if o <= off:
                p = pg
        return p


def table_text(md: str) -> tuple[str, list[bool]]:
    """Rows as 'cell | cell | …' (cells decoded), one row per line, separator rows dropped."""
    rows_t, rows_i = [], []
    for line in md.splitlines():
        if re.fullmatch(r"\|(---\|)+", line.strip()):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        t, it = [], []
        for k, c in enumerate(cells):
            ct, ci, _, _ = decode(c)
            ct_s = ct.strip()
            lead = len(ct) - len(ct.lstrip())
            if k:
                t.append(" | ")
                it += [False] * 3
            t.append(ct_s)
            it += ci[lead:lead + len(ct_s)]
        rows_t.append("".join(t))
        rows_i.append(it)
    text = "\n".join(rows_t)
    ital = []
    for k, ri in enumerate(rows_i):
        ital += ri + ([False] if k < len(rows_i) - 1 else [])
    return text, ital


def read_paras(md_path: Path) -> tuple[list[Para], int]:
    """Paragraphs as the transcription wrote them; returns them and the first printed page (PDF page index 0)."""
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        text = text[m.end():]
    first = MARKER.search(text)
    first_page = int(first.group(1)) if first else 1
    paras, page, section, zone_lit, seen_h2 = [], first_page, "", False, False
    for raw in re.split(r"\n\s*\n", text):
        raw = raw.strip()
        if not raw:
            continue
        mm = MARKER.fullmatch(raw)
        if mm:
            page = int(mm.group(1))
            continue
        if raw.startswith("<!--"):
            continue
        if raw.startswith("|"):
            t, it = table_text(raw)
            p = Para(len(paras), "table", t, it, page, [], section)
        else:
            kind, content = "p", raw
            hm = re.match(r"^(#{1,3})\s+(.*)$", raw, re.S)
            if hm:
                kind, content = f"h{len(hm.group(1))}", hm.group(2)
            t, it, bd, marks = decode(content)
            p = Para(len(paras), kind, t, it, page, marks, section, bold=bd)
            if marks:
                page = marks[-1][1]
        if p.kind in ("h2", "h3"):
            section = p.text.strip()
            if p.kind == "h2" or LITERATURE_HEAD.match(section):
                zone_lit = bool(LITERATURE_HEAD.match(section))
            seen_h2 = seen_h2 or p.kind == "h2"
            p.section = section
        if p.kind == "h1" or (p.kind == "h3" and not seen_h2 and paras and paras[-1].kind == "h1"):
            p.zone = "title"
        elif zone_lit:
            p.zone = "literature"
        elif p.kind == "p" and (FRONT_PARA.search(p.text[:40]) or re.match(r"^\d\)\s", p.text)
                                or (not seen_h2 and re.search(r"\bCZ-\d{3}\s?\d{2}\b", p.text))):
            p.zone = "front"
        elif p.kind == "p" and CAPTION.match(p.text):
            p.zone = "caption"
        paras.append(p)
    return paras, first_page


def known_genera() -> set[str]:
    with open(ROOT / "reference" / "checklist_aopk.csv", encoding="utf-8-sig", newline="") as f:
        return {r["scientific_name"].split()[0] for r in csv.DictReader(f) if r["scientific_name"]}


def rejoin_split_names(paras: list[Para], genera: set[str]) -> list[str]:
    """A paragraph ending in an italic word followed by a paragraph starting with a lowercase italic word is one name
    broken by the transcription (*Campanula* | *rotundifolia*, *Poly* | *trichum formosum*). Joined with a space when
    the first part is a known genus, without one otherwise. Returns a log of the joins."""
    log, k = [], 0
    while k < len(paras) - 1:
        a, b = paras[k], paras[k + 1]
        ta, tb = a.text.rstrip(), b.text.lstrip()
        if a.kind == b.kind == "p" and ta and tb and a.ital[len(ta) - 1] and re.match(rf"[{LC}]", tb) \
                and b.ital[len(b.text) - len(tb)]:
            last = re.search(rf"([{UC}][{LC}-]*)$", ta)
            if last:
                sep = " " if last.group(1) in genera else ""
                lead = len(b.text) - len(tb)
                marks = list(a.marks)
                if b.page != a.page_at(len(ta)):
                    marks.append((len(ta) + len(sep), b.page))
                marks += [(o - lead + len(ta) + len(sep), pg) for o, pg in b.marks]
                a.text = ta + sep + tb
                a.ital = a.ital[:len(ta)] + [True] * len(sep) + b.ital[lead:]
                a.bold = a.bold[:len(ta)] + [False] * len(sep) + b.bold[lead:]
                a.marks = marks
                log.append(f"p.{a.page}: '{last.group(1)}' + '{tb.split()[0]}' joined {'with' if sep else 'without'} space")
                del paras[k + 1]
                continue
        k += 1
    for i, p in enumerate(paras):
        p.idx = i
    return log


# ---------------------------------------------------------------- candidates

@dataclass
class Cand:
    para: Para
    start: int
    end: int
    name: str
    context: str = ""                # list_refs / list / table / heading / narrative / out-of-scope zone
    refs: str = ""
    source_line: str = ""
    harvest_locality: str = ""
    page: int = 0
    cand_id: str = ""
    occs: list[dict] = field(default_factory=list)

    @property
    def colour(self) -> str:
        if self.occs:
            return "green"
        return "grey" if self.para.zone != "body" else "red"


NOT_EPI = r"(?!(?:sp|spp|agg|subsp|ssp|var|cf|aff|s|str|lat|l|f|sect|ser)\.)"
NAME = re.compile(rf"(?P<g>{GENUS}|{ABBR})(?:\s+(?:cf\.\s*|aff\.\s*)?×?\s*{NOT_EPI}(?P<e>{EPI}))?"
                  rf"(?:\s+{RANK}\s+{NOT_EPI}{EPI})*(?:\s+(?P<t>{TAIL}))?(?:\s+×\s*{NOT_EPI}{EPI})?")


def find_names(p: Para) -> list[tuple[int, int]]:
    """Spans of taxon-like names: first letter and epithet italic (in tables also a plain cell starting with a
    binomial); a lone genus only with 'sp.' / 'agg.' …; a lone abbreviation never. A name in brackets right after
    another name ("Cirsium ×erucagineum (C. oleraceum × rivulare)") belongs to it and is skipped."""
    t, it = p.text, p.ital
    spans = []
    for m in NAME.finditer(t):
        s, e = m.start(), m.end()
        if s and (t[s - 1].isalnum() or t[s - 1] in "-'’"):
            continue
        has_epi = m.group("e") is not None
        if p.kind == "table":
            cell_start = s == 0 or t[max(0, s - 3):s] == " | " or t[s - 1] == "\n"
            if not (it[s] or (cell_start and has_epi)):
                continue
        else:
            if not it[s]:
                continue
            if has_epi and not it[m.start("e")]:          # capitalised italic word + plain Czech text: no name
                has_epi = False
                e = m.end("g")
                tm = re.match(rf"\s+{TAIL}", t[e:])
                if tm:
                    e += tm.end()
        if not has_epi and not re.search(rf"\s{TAIL}$", t[s:e]):
            continue
        if spans and t[s - 1:s] == "(" and not t[spans[-1][1]:s - 1].strip():
            continue
        spans.append((s, e))
    return spans


def split_top(text: str, seps: str) -> list[tuple[int, int]]:
    """(start, end) of pieces separated by any char of seps outside () and []."""
    out, depth, start = [], 0, 0
    for i, c in enumerate(text):
        depth += c in "(["
        depth -= c in ")]"
        if c in seps and depth == 0:
            out.append((start, i))
            start = i + 1
    out.append((start, len(text)))
    return out


def sentence(text: str, s: int, e: int) -> tuple[int, int]:
    """Sentence around [s, e): boundaries at '. ' + capital, not after an abbreviation or an initial."""
    bounds = [0]
    for m in re.finditer(rf"[.!?]\s+(?=[{UC}„])", text):
        before = text[max(0, m.start() - 6):m.start() + 1]
        if re.search(rf"(?:\b[{UC}{LC}]{{1,3}}|\bsubsp|\bdistr|\bcca|\bresp|\bapod|\btzv|\bobr|\bsp|\bspp|\bvar|\bagg)\.$", before):
            continue
        bounds.append(m.end())
    bounds.append(len(text))
    a = max(b for b in bounds if b <= s)
    z = min(b for b in bounds if b >= e)
    return a, z


def harvest(paras: list[Para], herbarium_article: bool) -> list[Cand]:
    cands: list[Cand] = []
    last_loc = site_loc = ""
    for p in paras:
        spans = find_names(p)
        if p.zone == "body" and p.kind != "table" and LOCALITY_LIKE.search(p.text[:80]):
            head = (p.text[:spans[0][0]] if spans else p.text).strip(" :")[:110]
            if spans and re.match(r"^\d{1,3}[a-z]?\.\s", p.text) and site_loc:
                # "1. staré stromy u potoka: *Taxon*" under a site → "site › staré stromy u potoka"
                last_loc = f"{site_loc} › {re.sub(r'^\d{1,3}[a-z]?\.\s*', '', head)}"
            else:
                site_loc = last_loc = head
        listish = False
        if p.kind == "p" and spans:
            # a list: most ';'-separated pieces start with a name, or a ','-list that starts with a name or
            # follows a 'label:' ("3. skalka: *Bazzania trilobata*, *Dicranodontium denudatum*, …")
            semi = ";" in p.text
            pieces = [(a, z) for a, z in split_top(p.text, ";" if semi else ",") if p.text[a:z].strip(" .")]
            starts = {s for s, _ in spans}
            led = sum(1 for a, z in pieces if a + len(p.text[a:z]) - len(p.text[a:z].lstrip()) in starts)
            prefix = p.text[:spans[0][0]].rstrip()
            labelled = prefix.endswith(":") and len(prefix) < 120
            if semi:
                listish = led >= 2 and led >= 0.5 * len(pieces)
            elif len(prefix) <= 2 or labelled:
                listish = led + labelled >= max(1, 0.5 * len(pieces))
        for s, e in spans:
            c = Cand(p, s, e, p.text[s:e], page=p.page_at(s))
            if p.kind == "table":
                ls = p.text.rfind("\n", 0, s) + 1
                le = p.text.find("\n", e)
                c.source_line = p.text[ls:le if le >= 0 else len(p.text)]
                c.context = "table"
            elif p.kind in ("h1", "h2", "h3") or (p.kind == "p" and len(p.text) < 120 and len(spans) == 1
                                                  and p.text.strip().startswith(c.name) and p.bold[s]):
                c.source_line = p.text
                c.context = "heading"
            else:
                pieces = split_top(p.text, ";") if ";" in p.text else split_top(p.text, ",")
                a, z = next(((a, z) for a, z in pieces if a <= s < z), (0, len(p.text)))
                zr = next(z2 for a2, z2 in split_top(p.text, ";") if a2 <= s < z2 or z2 == len(p.text))
                rm = REFS.match(p.text[e:zr])
                colon_refs = bool(rm) and ":" in p.text[e:e + rm.start(1)]
                if rm and (colon_refs or listish):
                    c.refs = rm.group(1).strip()             # also "*Russula nigricans* 2" (no colon) in a list
                if colon_refs and not listish:               # one item per paragraph ("*Taxon*: 3, 4, 6.")
                    a2 = max(a2 for a2, _ in split_top(p.text, ";") if a2 <= s)
                    c.source_line = p.text[a2:zr].strip()
                    c.context = "list_refs"
                elif listish:
                    c.source_line = p.text[a:z].strip()
                    c.context = "list_refs" if c.refs else "list"
                else:
                    a, z = sentence(p.text, s, e)
                    c.source_line = p.text[a:z].strip()
                    c.context = "narrative"
            if len(c.source_line) > 400:
                k = c.source_line.find(c.name)
                c.source_line = ("…" if k > 150 else "") + c.source_line[max(0, k - 150):k + 250] + "…"
            # the locality hint is offered for list items only (refs, or the locality line the list belongs to)
            c.harvest_locality = f"refs: {c.refs}" if c.refs else (last_loc if c.context == "list" else "")
            if p.zone != "body":
                c.context = p.zone
                c.harvest_locality = ""
            cands.append(c)
    for c in cands:
        if c.context == "table" and herbarium_article:
            c.context = "table_herbarium"
    return cands


# ---------------------------------------------------------------- link parser occurrences to candidates

def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace("*", " ")
    s = re.sub(r"(?:^|\s)(?:cf\.|aff\.|\?)(?=\s|$)", " ", s)
    s = re.sub(r"\s*×\s*", " ×", s)
    return re.sub(r"\s+", " ", s).strip().rstrip(",;:").strip()


def load_outputs(d: Path, source_file: str) -> tuple[list[dict], dict[str, dict]]:
    with open(d / "occurrences.csv", encoding="utf-8-sig", newline="") as f:
        occs = [r for r in csv.DictReader(f) if r["source_file"] == source_file]
    with open(d / "localities.csv", encoding="utf-8-sig", newline="") as f:
        locs = {r["locality_id"]: r for r in csv.DictReader(f) if r["source_file"] == source_file}
    return occs, locs


def in_block(page, pages: tuple[int, int] | None) -> bool:
    return pages is None or pages[0] <= int(page) <= pages[1]


def link(cands: list[Cand], paras: list[Para], occs: list[dict]) -> list[dict]:
    """Attach each occurrence to a candidate; return the occurrences that no candidate explains."""
    by_name: dict[str, list[Cand]] = defaultdict(list)
    for c in cands:
        c.occs = []
        by_name[norm_name(c.name)].append(c)
    order = {id(c): k for k, c in enumerate(cands)}
    orphans = []
    for o in occs:
        tv = norm_name(o["taxon_verbatim"])
        if not tv:
            orphans.append(o)
            continue
        pool = by_name.get(tv) or [c for n, cs in by_name.items() for c in cs
                                   if tv.startswith(n + " ") or n.startswith(tv + " ")]
        if not pool:
            orphans.append(o)
            continue
        item = o["item_verbatim"]
        hit = None
        for c in pool:                                    # the candidate inside the occurrence's own item
            k = c.para.text.find(item) if item else -1
            while k >= 0:
                if k <= c.start < k + len(item):
                    hit = c
                    break
                k = c.para.text.find(item, k + 1)
            if hit:
                break
        if hit is None:                                   # records under a taxon heading: nearest preceding heading
            head = item[:50]
            pidx = next((p.idx for p in paras if head and head in p.text), None)
            if pidx is not None:
                before = [c for c in pool if c.para.idx <= pidx]
                hit = max(before, key=lambda c: order[id(c)]) if before else None
        if hit is None:
            same_page = [c for c in pool if str(c.page) == str(o["page"])]
            hit = same_page[0] if len(same_page) == 1 else None
        if hit is None:
            orphans.append(o)
        else:
            hit.occs.append(o)
    return orphans


# ---------------------------------------------------------------- review CSV rows

def loc_label(loc: dict | None) -> str:
    if not loc:
        return "–"
    num = loc["locality_number_verbatim"]
    where = ", ".join(x for x in (loc["municipality"], loc["locality_description"]) if x)
    return (f"{num}" if num else loc["locality_id"].rsplit("_", 1)[-1]) + (f" {where[:70]}" if where else "")


def occ_date(o: dict, locs: dict) -> str:
    if o["event_date_start"]:
        return o["event_date_start"] + (f"/{o['event_date_end']}" if o["event_date_end"] not in ("", o["event_date_start"]) else "")
    loc = locs.get(o["locality_id"])
    if loc and loc["event_date_start"]:
        d = loc["event_date_start"]
        return d + (f"/{loc['event_date_end']}" if loc["event_date_end"] not in ("", d) else "")
    return ""


def review_row(cand_id: str, page, name: str, line: str, occs: list[dict], locs: dict, context: str, colour: str,
               harvest_loc: str, record_type_default: str) -> dict:
    row = {c: "" for c in REVIEW_COLS}
    row.update(cand_id=cand_id, page=page, taxon_as_printed=name, source_line=line, colour=colour,
               harvest_locality=harvest_loc)
    if occs:
        labels = list(dict.fromkeys(loc_label(locs.get(o["locality_id"])) for o in occs))
        nums = [locs[o["locality_id"]]["locality_number_verbatim"] for o in occs if o["locality_id"] in locs]
        row["parser_occurrence_id"] = " | ".join(o["occurrence_id"] for o in occs)
        row["parser_locality"] = (", ".join(nums) if len(labels) > 1 and all(nums) else " | ".join(labels))
        row["parser_date"] = " | ".join(dict.fromkeys(occ_date(o, locs) or "–" for o in occs))
        row["record_type_suggested"] = " | ".join(dict.fromkeys(o["record_type"] for o in occs))
        row["is_record"] = "1"
        if all(o["locality_id"] for o in occs):
            row["locality_ok"] = "1"
        if all(occ_date(o, locs) for o in occs):
            row["date_ok"] = "1"
        expanded = {o["taxon_expanded"] for o in occs if o["taxon_expanded"] and o["taxon_expanded"] != name}
        notes = []
        if expanded:
            notes.append("parser read the name as " + "; ".join(sorted(expanded)))
        flags = sorted({f for o in occs for f in o["flags"].split("|") if f})
        if flags:
            notes.append("flags: " + ", ".join(flags))
        row["note"] = " · ".join(notes)
    else:
        row["record_type_suggested"] = record_type_default
        if colour == "grey":
            row["is_record"] = "0"
    return row


CONTEXT_TYPE = {"list_refs": "species_list", "list": "species_list", "table": "species_list",
                "table_herbarium": "herbarium_revision", "heading": "detailed_record", "narrative": "narrative",
                "literature": "literature", "front": "out_of_scope", "title": "out_of_scope",
                "caption": "out_of_scope"}


# ---------------------------------------------------------------- PDF highlighting

COLOURS = {"green": (0.45, 0.85, 0.45), "red": (1.0, 0.45, 0.45), "grey": (0.75, 0.75, 0.75)}
LABEL_COLOURS = {"green": (0.0, 0.42, 0.0), "red": (0.75, 0.0, 0.0), "grey": (0.35, 0.35, 0.35)}


def words_tight(page) -> list[tuple]:
    """Like get_text('words') — (x0, y0, x1, y1, text, block, line) — but with boxes from each character's baseline
    and font size: some fonts (4/P2) carry ascent/descent metrics that make word boxes several lines tall."""
    out = []
    for bi, b in enumerate(page.get_text("rawdict")["blocks"]):
        for li, ln in enumerate(b.get("lines", [])):
            cur, box = [], None
            for sp in ln["spans"]:
                size = sp["size"]
                for ch in sp["chars"]:
                    if ch["c"].isspace():
                        if cur:
                            out.append((*box, "".join(cur), bi, li))
                        cur, box = [], None
                        continue
                    x0, _, x1, _ = ch["bbox"]
                    oy = ch["origin"][1]
                    r = (x0, oy - 0.8 * size, x1, oy + 0.22 * size)
                    box = r if box is None else (min(box[0], r[0]), min(box[1], r[1]), max(box[2], r[2]), max(box[3], r[3]))
                    cur.append(ch["c"])
            if cur:
                out.append((*box, "".join(cur), bi, li))
    return out


def pdf_words(page) -> list[tuple]:
    """Words in reading order with line-end hyphenation resolved: (text variants, [rects])."""
    raw = words_tight(page)
    out, k = [], 0
    while k < len(raw):
        w = raw[k]
        text, rects = w[4], [w[:4]]
        if text.endswith(("-", "­")) and k + 1 < len(raw) and (raw[k + 1][5], raw[k + 1][6]) != (w[5], w[6]):
            nxt = raw[k + 1]
            variants = {text[:-1] + nxt[4], text + nxt[4]}
            out.append((variants, rects + [nxt[:4]]))
            k += 2
            continue
        out.append(({text}, rects))
        k += 1
    return out


def tok(s: str) -> str:
    return s.strip(",;:.()[]„“”\"'*+").replace("×", "").replace("­", "")


def locate(words: list[tuple], name: str, nth: int) -> list | None:
    target = [tok(t) for t in name.replace("×", " ").split() if tok(t)]
    if not target:
        return None
    hits = []
    k = 0
    while k < len(words):
        j, rects, ok, consumed = 0, [], True, 0
        while j < len(target):
            if k + consumed >= len(words):
                ok = False
                break
            variants, r = words[k + consumed]
            vt = {tok(v) for v in variants}
            vt.discard("")
            if not vt and j == 0:                          # a hit never starts on punctuation
                ok = False
                break
            if not vt:                                     # a lone '×' or punctuation between name words
                consumed += 1
                rects += r
                continue
            if target[j] in vt:
                rects += r
                j += 1
                consumed += 1
            elif j + 1 < len(target) and target[j] + target[j + 1] in vt:   # "×intermedia" vs "×", "intermedia"
                rects += r
                j += 2
                consumed += 1
            else:
                ok = False
                break
        if ok:
            hits.append(rects)
        k += 1
    if not hits:
        return None
    return hits[min(nth, len(hits) - 1)] if nth < len(hits) else None


def annotate(pdf_in: Path, pdf_out: Path, items: list[tuple[str, int, str, str]], first_page: int) -> set[str]:
    """items: (cand_id, printed page, name, colour). Returns the cand_ids that could not be located."""
    import pymupdf
    doc = pymupdf.open(pdf_in)
    missing, seen = set(), defaultdict(int)
    cache: dict[int, list] = {}
    for cid, page, name, colour in items:
        pidx = int(page) - first_page
        if not 0 <= pidx < len(doc):
            missing.add(cid)
            continue
        pg = doc[pidx]
        if pidx not in cache:
            cache[pidx] = pdf_words(pg)
        nth = seen[(pidx, norm_name(name))]
        seen[(pidx, norm_name(name))] += 1
        rects = locate(cache[pidx], name, nth)
        if not rects:
            missing.add(cid)
            continue
        quads = [pymupdf.Rect(r).quad for r in rects]
        h = pg.add_highlight_annot(quads)
        h.set_colors(stroke=COLOURS[colour])
        h.set_info(title=cid, content=f"{cid}: {name} ({colour})")
        h.update()
        r0 = pymupdf.Rect(rects[0])
        lab = pymupdf.Rect(r0.x0 - 1, r0.y0 - 5.2, r0.x0 + 4.2 * len(cid) + 2, r0.y0 + 0.6)
        a = pg.add_freetext_annot(lab, cid, fontsize=5, fontname="helv", text_color=LABEL_COLOURS[colour],
                                  fill_color=(1, 1, 1), border_width=0)
        a.set_opacity(0.9)
        a.set_info(title=cid)
        a.update()
    doc.save(pdf_out, garbage=3, deflate=True)
    return missing


# ---------------------------------------------------------------- main

def read_config() -> list[dict]:
    with open(GOLD / "gold_articles.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def md_path(source_file: str) -> Path:
    p = Path(source_file)
    return MD_DIR / p.parent.name / f"{p.stem}.md"


def page_block(spec: str) -> tuple[int, int] | None:
    if not spec:
        return None
    a, _, b = spec.partition("-")
    return int(a), int(b or a)


def build(art: dict, outputs: Path, genera: set[str]) -> dict:
    """Harvest + link for one gold article. → dict with candidates, orphans, localities, first page, join log."""
    paras, first_page = read_paras(md_path(art["source_file"]))
    joins = rejoin_split_names(paras, genera)
    herbarium = art["patterns"].startswith("H")
    block = page_block(art["pages"])
    cands = [c for c in harvest(paras, herbarium) if in_block(c.page, block)]
    occs, locs = load_outputs(outputs, art["source_file"])
    occs = [o for o in occs if in_block(o["page"], block)]
    orphans = link(cands, paras, occs)
    for k, c in enumerate(cands, 1):
        c.cand_id = f"c{k:03d}"
    for k, o in enumerate(orphans, 1):
        o["_cand_id"] = f"P{k:03d}"
    return {"cands": cands, "orphans": orphans, "locs": locs, "first_page": first_page, "joins": joins, "paras": paras}


def write_package(art: dict, res: dict) -> dict:
    out = GOLD / "review"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in res["cands"]:
        rows.append(review_row(c.cand_id, c.page, c.name, c.source_line, c.occs, res["locs"], c.context, c.colour,
                               c.harvest_locality, CONTEXT_TYPE.get(c.context, "")))
    for o in res["orphans"]:
        r = review_row(o["_cand_id"], o["page"], o["taxon_verbatim"] or "(no taxon)", o["item_verbatim"], [o],
                       res["locs"], "", "green", "", "")
        r["note"] = "parser row not linked to a harvested name · " + r["note"]
        rows.append(r)
    rows.sort(key=lambda r: (int(r["page"]), 0 if r["cand_id"].startswith("c") else 1, r["cand_id"]))
    end = {c: "" for c in REVIEW_COLS}
    end.update(cand_id="ARTICLE", note="optional: correction 'date=YYYY-MM-DD' = the date of every record of this "
                                       "article whose date is neither confirmed (date_ok=1) nor corrected")
    rows.append(end)
    for k in range(1, MISSED_ROWS + 1):
        r = {c: "" for c in REVIEW_COLS}
        r.update(cand_id=f"M{k:02d}")
        rows.append(r)
    path = out / f"{art['article']}_cp1250.csv"
    with open(path, "w", encoding="cp1250", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_COLS, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cp1250_safe(str(v)) for k, v in r.items()})
    items = [(c.cand_id, c.page, c.name, c.colour) for c in res["cands"]]
    items += [(o["_cand_id"], o["page"], o["taxon_verbatim"], "green") for o in res["orphans"] if o["taxon_verbatim"]]
    missing = annotate(ROOT / art["source_file"], out / f"{art['article']}.pdf", items, res["first_page"])
    if missing:
        with open(path, encoding="cp1250", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        for r in rows:
            if r["cand_id"] in missing:
                r["note"] = ("(not highlighted: text not found on the PDF page) · " + r["note"]).strip(" ·")
        with open(path, "w", encoding="cp1250", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REVIEW_COLS, delimiter=";")
            w.writeheader()
            w.writerows(rows)
    colours = defaultdict(int)
    for c in res["cands"]:
        colours[c.colour] += 1
    return {"article": art["article"], "set": art["set"], "candidates": len(res["cands"]), **colours,
            "parser_only": len(res["orphans"]), "occurrences": sum(len(c.occs) for c in res["cands"]) + len(res["orphans"]),
            "not_located": len(missing), "joins": len(res["joins"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="gold article keys")
    ap.add_argument("--outputs", type=Path, default=ROOT / "tests" / "baseline",
                    help="directory with localities.csv / occurrences.csv (default: the frozen baseline)")
    args = ap.parse_args()
    genera = known_genera()
    stats = []
    for art in read_config():
        if args.only and art["article"] not in args.only:
            continue
        stats.append(write_package(art, build(art, args.outputs, genera)))
    keys = ["article", "set", "candidates", "green", "red", "grey", "parser_only", "occurrences", "not_located", "joins"]
    print("\t".join(keys))
    for s in stats:
        print("\t".join(str(s.get(k, 0)) for k in keys))


if __name__ == "__main__":
    main()
