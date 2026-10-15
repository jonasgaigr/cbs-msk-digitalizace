"""Step 3: excerpt localities and occurrences from the transcribed Markdown.

    python scripts/03_excerpt.py --all                     # every record-bearing article
    python scripts/03_excerpt.py --only 2021-10-43-52 …    # selected PDF stems

Record patterns (confirmed at checkpoints 0–3 and after the full-scale stop):
  A   numbered locality list ("1. 76b. Tršická…, 6370c, Hlubočky (distr. Olomouc): …", "1 – Loučná (k. ú. X): …",
      "1\\. 6475b, Kozlovice, …") + species lists citing the numbers ("*Taxon* (notes): 2, 15a (BRNM) [sax]; …")
  A1  single-locality appendix ("### Lokalita" or a lone locality): unnumbered list items go to that locality
  A2  locality keyed by name ("Bernartice | 74a. …"), records "Bernartice (26. 5., JESM), …" under a taxon heading
  A3  locality-first: a record-style locality paragraph followed by a list of taxa for it
  A4  flat species list with no locality information: one locality derived from the article (flagged)
  B   floristic notes: taxon heading (bold-italic paragraph, ## heading, or the article's single taxon), record
      paragraphs "74a. Name, 5771d, Obec (distr. X): …" / "5771c, Obec: …" / "76a. …, distr. X, Obec (6474b): …",
      optional a)/b) sub-localities, one occurrence per dated event; inline "***Taxon***: 74b, 6074b, …" records
  M   species × locality matrix tables ("Taxon / Lokalita | 1 | 2 …" with "+")
  H   herbarium revision tables (columns lokalita / datum / leg. …)
Never excerpted: commentaries, captions, running text (checkpoint 1, Q13). Protection status is never taken
from the articles (checkpoint 3, Q3).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MD_DIR, ROOT, write_csv  # noqa: E402

LOC_COLS = [
    "locality_id", "source_file", "citation", "page", "locality_number_verbatim", "line_verbatim",
    "fytochorion_code", "fytochorion_name", "grid_square", "municipality", "district", "cadastral_area",
    "locality_description", "habitat", "coordinates_verbatim", "lat_start", "lon_start", "lat_end", "lon_end",
    "geometry_type", "altitude_min_m", "altitude_max_m", "altitude_verbatim", "event_date_start",
    "event_date_end", "event_date_verbatim", "recorders_verbatim", "remarks", "flags",
]
OCC_COLS = [
    "occurrence_id", "locality_id", "source_file", "citation", "page", "item_verbatim",
    "observation_verbatim", "locality_numbers_verbatim", "taxon_verbatim", "taxon_expanded",
    "genus_abbreviation_resolved", "taxon_name_normalised", "taxon_group", "identification_qualifier",
    "abundance_verbatim", "phenology_verbatim", "habitat_verbatim", "event_date_start", "event_date_end",
    "event_date_verbatim", "recorded_by", "collected_by", "identified_by", "herbarium", "specimen_note",
    "record_type", "red_list_category", "red_list_regional", "protection_status", "status_note",
    "is_new_record_claim", "remarks", "flags",
]
REVIEW_COLS = ["table", "row_id", "source_file", "page", "line_verbatim", "flags", "parsed_values",
               "suggested_fix", "question_for_me"]

AREA = (48.8, 50.5, 16.7, 18.9)          # lat min/max, lon min/max (confirmed at checkpoint 3)
SEGMENT_MAX_KM = 2.0
ALT_RANGE = (150, 1500)
THIS_YEAR = date.today().year

UC = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
LC = "a-záčďéěíňóřšťúůýž"
ROMAN_RX = "XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I"
ROMAN = {r: i for i, r in enumerate(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"], 1)}
DMS = re.compile(r"(\d{1,2})\s*°\s*(\d{1,2})\s*[′'’‘]\s*(\d{1,2}(?:[,.]\d+)?)\s*(?:[″\"”“]|′′|''|’’)\s*([NSEW])")
ALT = re.compile(r"(?:(?:přibližně|cca|asi|ca\.)\s+)?(\d[\d ]{1,4}?)(?:\s*[–−-]\s*(\d[\d ]{1,4}?))?\s*m\s*n\.\s*m\.?")
DATE = re.compile(rf"\b(\d{{1,2}})\.\s*(?:(?:a|–|−|-)\s*(\d{{1,2}})\.\s*)?({ROMAN_RX}|\d{{1,2}})\.\s*(\d{{4}})\b")
DATE_NOYEAR = re.compile(rf"(?<![\d.])(\d{{1,2}})\.\s*({ROMAN_RX}|\d{{1,2}})\.(?!\s*\d)")
MONTH_YEAR = re.compile(rf"(?<![\d.]\s)(?<!\d\.)\b({ROMAN_RX})\.\s*(\d{{4}})\b")
EN_MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"], 1)}
EN_DATE = re.compile(r"\b(\d{1,2})(?:\s*[–-]\s*(\d{1,2}))?\s+(" + "|".join(EN_MONTHS) + r")\s+(\d{4})\b")
PHYTO = re.compile(r"^(\d{1,2}[a-z]?)\.\s+(\S.*)$")
GRID = re.compile(r"^\d{4}[a-d]?$")
LOC_ENTRY = re.compile(r"^(\d{1,3})([a-z]?|[A-Z]?)(?:\.\s+|\s*[–−-]\s+)(.*)$", re.S)
NAME_KEY_ENTRY = re.compile(r"^([^|:()]{2,60}?)\s*\|\s*(.+)$", re.S)
PHYTO_FIRST = re.compile(rf"^\d{{1,2}}[a-z]?\.\s+[{UC}][^,]*,\s*\d{{4}}")           # "75. Jesenické podhůří, 6372b"
RECORD_START = re.compile(rf"^\d{{1,2}}[a-z]?\.\s+[{UC}][{LC}]")
GRID_START = re.compile(rf"^\d{{4}}[a-d]?(?:/\d{{4}}[a-d]?)?,\s+[{UC}]")
SUBITEM = re.compile(r"^([a-z])\)\s+")
KNOWN_HERBARIA = {"BRNM", "BRNU", "BRNL", "CB", "CHOM", "FMM", "GM", "HOMP", "HR", "JESM", "JIC", "LIM", "LIT", "MJ",
                  "MMI", "MP", "MZ", "NJM", "OL", "OLM", "OMJ", "OP", "OSM", "OSTR", "OVMB", "PL", "PR", "PRA", "PRC",
                  "ROZ", "SUM", "VM", "ZMT", "KHMS", "MMH", "PRM", "BRA", "SAV", "SLO", "KRA", "KRAM", "WRSL", "W", "WU"}
HERB_TOKEN = re.compile(r"^(?:[A-Z]{2,6}|herb\.\s+\S.*)$")
INITIALS = re.compile(r"^[A-ZČŘŠŽ][A-Za-zČŘŠŽ]?$")
REDLIST = re.compile(r"^(?:(?:EX|EW|RE|CR|EN|VU|NT|LC|DD|NE)\s*(?:/\s*[ACR]\d[a-z]?(?:\s*[a-z])?)?|[AC]\d[a-z]?(?:\s*[a-z])?)$")
CULT = re.compile(r"^(kult\.|cult\.|subspont\.|adv\.|zplaň\.|vysaz\.|pěst\.)$", re.I)
PERSON_ROLE = re.compile(r"^(not\.?(?=\s)|obs\.|foto|leg\.|det\.|rev\.|conf\.|herb\.)\s*(.+)$")
LITERATURE = re.compile(rf"^[{UC}][^()]*?\b(1[89]\d\d|20[0-4]\d)[a-z]?(?:\s*:\s*[\d–-]+)?$")
LOC_SECTION = re.compile(r"(Přehled|Seznam)\s+lokalit|^Lokalit[ay]\b", re.I)
SPECIES_SECTION = re.compile(r"(Přehled|Seznam)\s+(?:\w+\s+){0,2}(taxonů|druhů|hub|mechorostů|lišejníků|rostlin)"
                             r"|Floristický přehled", re.I)
GROUP_HEADINGS = {"cévnaté rostliny": "vascular_plant", "mechorosty": "bryophyte", "lišejníky": "lichen",
                  "houby": "fungus", "mechy": "bryophyte", "játrovky": "bryophyte", "hlevíky": "bryophyte"}
RESULTS_SECTION = re.compile(r"^Výsledky\b|poznámky k jednotlivým|Přehled nálezů|^Nálezy|Nové lokality", re.I)
RLTABLE_SECTION = re.compile(r"ohrožených taxonů", re.I)
EXCURSION_WORDS = re.compile(r"field trip|excursion|\btrip\b|exkurz|vycházk", re.I)
LOC_REF = r"\d{1,3}(?:[a-z]{1,3}|[A-Z])?(?:\s*\([^)]*\))?(?:\s*\[[^\]]*\])?"   # 15a, 5sv, 3A
SPECIES_ITEM = re.compile(rf"^\*?[{UC}{LC}×][^:]{{1,120}}?:\s*{LOC_REF}(?:\s*[,:]\s*{LOC_REF})*\s*\.?$")
TAXON_ONLY_ITEM = re.compile(rf"^\*?(?:[{UC}×][{LC}ë-]+|[{UC}][{LC}]?\.)(?:\s+[^:;]{{0,120}})?$")
NEW_CLAIM = re.compile(r"\b(nov[ýáé] (pro|druh|údaj|lokalit)|poprvé (zjištěn|nalezen|zaznamenán)|first record)", re.I)
SKIP_SECTIONS = {"EDITORIAL", "VÝROČNÍ ZPRÁVA", "RŮZNÉ", "PERSONALIA", "HISTORIE"}
SKIP_TITLES = re.compile(r"Výroční zpráva|Publikace členů|Nová kniha|ve fotografii|Informační materiály"
                         r"|\b(číslo|ročník|Sedmička)$|jubileu|Opustila|vzpomínka|– \d+ let$"
                         r"|\(\*?\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\s*[–-]\s*†?\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\)$"
                         r"|^(Mgr|Ing|RNDr|Doc|Prof)\.|narozeninám|^Tomáš Svěrák$|Zpráva o hospodaření", re.I)


# ---------------------------------------------------------------- Markdown → blocks

@dataclass
class Block:
    kind: str                  # h1 h2 h3 p table comment
    md: str
    text: str = ""
    ital: list[bool] = field(default_factory=list)
    bold: list[bool] = field(default_factory=list)
    marks: list[tuple[int, int]] = field(default_factory=list)   # (offset in text, page) inline markers
    page: int = 0

    def page_at(self, offset: int) -> int:
        p = self.page
        for off, pg in self.marks:
            if off <= offset:
                p = pg
        return p

    def spans_pages(self, a: int, b: int) -> bool:
        return any(a < off < b for off, _ in self.marks)

    @property
    def starts_italic(self) -> bool:
        i = next((k for k, c in enumerate(self.text) if c.strip() and c != "*"), None)
        return i is not None and self.ital[i]

    @property
    def all_bold(self) -> bool:
        vis = [b for b, c in zip(self.bold, self.text) if c.strip() and c not in ":."]
        return bool(vis) and all(vis)


MARKER = re.compile(r"<!--\s*page\s+(\d+)\s*-->")


def md_to_plain(md: str) -> tuple[str, list[bool], list[bool], list[tuple[int, int]]]:
    chars, ital, bold, marks = [], [], [], []
    i, it, bd, n = 0, False, False, len(md)
    while i < n:
        if md.startswith("<!--", i):
            j = md.find("-->", i)
            j = n if j < 0 else j + 3
            m = MARKER.match(md, i)
            if m:
                marks.append((len(chars), int(m.group(1))))
            i = j
            if chars and chars[-1] == " " and i < n and md[i] == " ":
                i += 1
            continue
        if md.startswith("<sup>", i) or md.startswith("</sup>", i):
            i = md.find(">", i) + 1
            continue
        c = md[i]
        if c == "\\" and i + 1 < n and md[i + 1] in "\\*_`.#>+-[]()!|":
            chars.append(md[i + 1]); ital.append(it); bold.append(bd); i += 2
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
        chars.append(c); ital.append(it); bold.append(bd); i += 1
    return "".join(chars), ital, bold, marks


def read_md(path: Path) -> tuple[dict, list[Block]]:
    text = path.read_text(encoding="utf-8")
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(": ")
            fm[k.strip()] = v.strip().strip('"')
        text = text[m.end():]
    blocks, page = [], 0
    for raw in re.split(r"\n\s*\n", text):
        raw = raw.strip()
        if not raw:
            continue
        mm = MARKER.fullmatch(raw)
        if mm:
            page = int(mm.group(1))
            continue
        if raw.startswith("<!--"):
            blocks.append(Block("comment", raw, page=page))
            continue
        if raw.startswith("|"):
            blocks.append(Block("table", raw, text=raw, page=page))
            continue
        kind, content = "p", raw
        hm = re.match(r"^(#{1,3})\s+(.*)$", raw, re.S)
        if hm:
            kind, content = f"h{len(hm.group(1))}", hm.group(2)
        t, it, bd, marks = md_to_plain(content)
        blocks.append(Block(kind, raw, t, it, bd, marks, page))
        if marks:
            page = marks[-1][1]
    return fm, blocks


def table_rows(md: str) -> list[list[str]]:
    rows = []
    for line in md.splitlines():
        if re.fullmatch(r"\|(---\|)+", line.strip()):
            continue
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        rows.append([c.strip() for c in cells])
    return rows


# ---------------------------------------------------------------- value parsers

def dms(m: re.Match) -> float:
    v = int(m.group(1)) + int(m.group(2)) / 60 + float(m.group(3).replace(",", ".")) / 3600
    return -v if m.group(4) in "SW" else v


def haversine(la1, lo1, la2, lo2) -> float:
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def parse_coords(text: str) -> dict:
    """All DMS pairs in text → point / segment. Returns fields + flags + span (start, end)."""
    out = {"coordinates_verbatim": "", "lat_start": "", "lon_start": "", "lat_end": "", "lon_end": "",
           "geometry_type": "none", "flags": [], "span": None, "remarks": []}
    ms = list(DMS.finditer(text))
    if not ms:
        if re.search(r"\d+\s*°", text):
            out["flags"].append("COORD_PARSE")
        return out
    pairs, i = [], 0
    while i < len(ms):
        if i + 1 < len(ms) and ms[i].group(4) in "NS" and ms[i + 1].group(4) in "EW":
            pairs.append((ms[i], ms[i + 1]))
            i += 2
        else:
            out["flags"].append("COORD_PARSE")
            i += 1
    if not pairs:
        return out
    out["span"] = (pairs[0][0].start(), pairs[-1][1].end())
    out["coordinates_verbatim"] = text[out["span"][0]:out["span"][1]]
    lat, lon = dms(pairs[0][0]), dms(pairs[0][1])
    out.update(lat_start=f"{lat:.6f}", lon_start=f"{lon:.6f}", geometry_type="point")
    if len(pairs) == 2:
        between = text[pairs[0][1].end():pairs[1][0].start()]
        mezi = re.fullmatch(r"\s+a\s+", between) and re.search(r"\bmezi\s*$", text[:pairs[0][0].start()])
        if mezi:
            out["remarks"].append("'mezi … a …' read as start–end")
        if re.fullmatch(r"\s*[–−-]\s*", between) or mezi:
            lat2, lon2 = dms(pairs[1][0]), dms(pairs[1][1])
            out.update(lat_end=f"{lat2:.6f}", lon_end=f"{lon2:.6f}", geometry_type="segment")
            if haversine(lat, lon, lat2, lon2) > SEGMENT_MAX_KM:
                out["flags"].append("COORD_SEGMENT_LONG")
        else:
            out["flags"].append("MULTI_INTERPRETATION")
            out["remarks"].append("two coordinate pairs not joined by a dash; first pair used as point")
    elif len(pairs) > 2:
        out["flags"].append("MULTI_INTERPRETATION")
        out["remarks"].append(f"{len(pairs)} coordinate pairs; first used as point")
    pts = [(lat, lon)] + ([(float(out["lat_end"]), float(out["lon_end"]))] if out["lat_end"] else [])
    if any(not (AREA[0] <= la <= AREA[1] and AREA[2] <= lo <= AREA[3]) for la, lo in pts):
        out["flags"].append("COORD_OUT_OF_AREA")
    return out


def kfme_square(lat: float, lon: float) -> tuple[str, float]:
    """KFME quadrant (e.g. 6370c) of a WGS84 point, and approx. distance (km) to the quadrant edge."""
    ry, cx = (56.0 - lat) * 10, (lon - (5 + 40 / 60)) * 6
    row, col = int(ry), int(cx)
    fy, fx = ry - row, cx - col
    q = "ab"[fx >= 0.5] if fy < 0.5 else "cd"[fx >= 0.5]
    qy, qx = (fy * 2) % 1, (fx * 2) % 1
    edge_km = min(min(qy, 1 - qy) * 0.05 * 111.2, min(qx, 1 - qx) * (10 / 60) / 2 * 111.2 * math.cos(math.radians(lat)))
    return f"{row:02d}{col:02d}{q}", edge_km


def inside_parens(text: str, pos: int) -> bool:
    return text[:pos].count("(") > text[:pos].count(")")


def alt_value(s: str) -> int:
    return int(s.replace(" ", ""))


def pick_altitude(text: str, coords_span) -> tuple[dict, tuple[int, int] | None]:
    """Altitude after the coordinates; else the last one before them (not a bracketed hill height)."""
    out = {"altitude_min_m": "", "altitude_max_m": "", "altitude_verbatim": "", "flags": []}
    cands = [m for m in ALT.finditer(text) if not inside_parens(text, m.start())]
    if coords_span:
        after = [m for m in cands if m.start() >= coords_span[1]]
        before = [m for m in cands if m.end() <= coords_span[0]]
        pick = after[0] if after else (before[-1] if before else None)
    else:
        pick = cands[-1] if cands else None
    if not pick:
        return out, None
    lo = alt_value(pick.group(1))
    hi = alt_value(pick.group(2)) if pick.group(2) else lo
    out.update(altitude_min_m=lo, altitude_max_m=hi, altitude_verbatim=pick.group(0).strip())
    if lo > hi or lo < ALT_RANGE[0] or hi > ALT_RANGE[1]:
        out["flags"].append("ALT_IMPLAUSIBLE")
    return out, (pick.start(), pick.end())


def iso(d: int, mth: int, y: int) -> str | None:
    try:
        dt = date(y, mth, d)
    except ValueError:
        return None
    return dt.isoformat() if 1800 <= y <= THIS_YEAR else None


def month_no(tok: str) -> int:
    return ROMAN.get(tok) or int(tok)


def parse_dates(text: str, year_hint: int | None = None, partial: bool = False) -> dict:
    """Dates in text: '7. VI. 2013', '25. 4. 2014', '7.–9. 6. 2013', '13. a 27. 6. 2015'; with partial=True also
    'VIII. 1894' / a leading year; with year_hint also '28. 3.' (year then taken from the article header)."""
    out = {"event_date_start": "", "event_date_end": "", "event_date_verbatim": "", "flags": [], "remarks": []}
    found = []
    for m in DATE.finditer(text):
        mo, y = month_no(m.group(3)), int(m.group(4))
        found.append((iso(int(m.group(1)), mo, y), m.group(0)))
        if m.group(2):
            found.append((iso(int(m.group(2)), mo, y), ""))
    if not found and partial:
        for m in MONTH_YEAR.finditer(text):
            y, mo = int(m.group(2)), ROMAN[m.group(1)]
            found.append((f"{y:04d}-{mo:02d}" if 1800 <= y <= THIS_YEAR else None, m.group(0)))
        if not found:
            m = re.match(r"^\s*(?:vše\s+)?(1[89]\d\d|20[0-4]\d)\b(?!\s*[:)])", text)
            if m:
                found.append((m.group(1) if int(m.group(1)) <= THIS_YEAR else None, m.group(1)))
    if not found and year_hint:
        for m in DATE_NOYEAR.finditer(text):
            v = iso(int(m.group(1)), month_no(m.group(2)), year_hint)
            if v:
                found.append((v, m.group(0)))
                out["remarks"].append(f"year {year_hint} from the article header/methods")
    if not found:
        return out
    if any(v is None for v, _ in found):
        out["flags"].append("DATE_PARSE")
    ok = sorted(v for v, _ in found if v)
    out["event_date_verbatim"] = " | ".join(v for _, v in found if v)
    if ok:
        out["event_date_start"], out["event_date_end"] = ok[0], ok[-1]
    return out


def split_top(text: str, sep: str) -> list[tuple[int, str]]:
    """Split on sep outside () and []; returns (start offset, piece)."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        depth += c in "(["
        depth -= c in ")]"
        if c == sep and depth == 0:
            parts.append((start, text[start:i]))
            start = i + 1
    parts.append((start, text[start:]))
    return parts


def persons(paren: str) -> dict:
    out = {"recorded_by": [], "collected_by": [], "identified_by": [], "specimen_note": [], "herbarium": [],
           "remarks": []}
    rest = DATE.sub("", paren)
    rest = MONTH_YEAR.sub("", rest)
    rest = re.sub(r"^\s*(?:vše\s*)?(?:1[89]\d\d|20[0-4]\d)?\s*", "", rest).strip(" ,")
    for part in re.split(r",\s*(?=(?:not\.|obs\.|foto|leg\.|det\.|rev\.|conf\.|herb\.))", rest):
        part = part.strip(" ,")
        if not part:
            continue
        ut = re.search(r"\s+ut\s+(.+)$", part)
        if ut:
            out["remarks"].append(f"ut {ut.group(1)}")
            part = part[:ut.start()]
        m = PERSON_ROLE.match(part)
        if not m:
            if HERB_TOKEN.match(part):
                out["herbarium"].append(part)
            else:
                out["remarks"].append(f"in brackets: {part}")
            continue
        role, who = m.group(1), m.group(2).strip()
        hm = re.search(r"[,(]\s*([A-Z]{2,6})\)?\s*$", who)
        if hm and hm.group(1) in KNOWN_HERBARIA:
            out["herbarium"].append(hm.group(1))
            who = who[:hm.start()].strip(" ,(")
        if role in ("not.", "not", "obs."):
            out["recorded_by"].append(who)
        elif role == "foto":
            out["recorded_by"].append(who)
            out["specimen_note"].append(f"foto {who}")
        elif role == "leg.":
            out["collected_by"].append(who)
        elif role == "herb.":
            out["herbarium"].append(f"herb. {who}")
        else:
            out["identified_by"].append(f"{role} {who}")
    return out


# ---------------------------------------------------------------- taxa

class Checklist:
    def __init__(self, path: Path):
        self.by_norm: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.by_czech: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.names_by_group: dict[str, list[str]] = defaultdict(list)
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            self.by_norm[self.norm(r["scientific_name"])].append((r["scientific_name"], r["taxon_group"]))
            if r["czech_name"]:
                self.by_czech[r["czech_name"].strip().lower()].append((r["scientific_name"], r["taxon_group"]))
            self.names_by_group[r["taxon_group"]].append(r["scientific_name"])

    @staticmethod
    def norm(name: str) -> str:
        """Whitespace, hybrid-sign spacing and diaeresis (poëticus = poeticus) are orthography only."""
        name = re.sub(r"\s+", " ", name.strip())
        name = name.replace("ë", "e").replace("ï", "i").replace("ü", "u")
        return re.sub(r"×\s+", "×", name)

    def match(self, name: str, prefer: str) -> tuple[str, str, str]:
        """(normalised name, group, remark) or ('', '', '')."""
        n = self.norm(name)
        tries = [(n, "")]
        if re.search(r"\bs\. ?str\.", n):
            tries.append((re.sub(r"\s*\bs\. ?str\.", "", n), "matched after removing 's. str.'"))
        # trailing author citation ("Celastrus orbiculatus Thunb.")
        toks = n.split()
        while len(toks) > 2 and (toks[-1][0].isupper() or toks[-1] in ("et", "ex", "&")) and toks[-1] not in ("×",):
            toks = toks[:-1]
            tries.append((" ".join(toks), "matched without the author citation"))
        for cand, remark in tries:
            hits = self.by_norm.get(cand)
            if hits:
                hit = next((h for h in hits if h[1] == prefer), hits[0])
                return hit[0], hit[1], remark
        return "", "", ""

    def match_czech(self, name: str) -> tuple[str, str, str]:
        hits = self.by_czech.get(re.sub(r"\s+", " ", name.strip().lower()), [])
        sci = {h[0] for h in hits}
        if len(sci) == 1:
            return hits[0][0], hits[0][1], "matched via the Czech name (AOPK checklist)"
        return "", "", ("Czech name ambiguous in checklist: " + "; ".join(sorted(sci))) if sci else ""

    def suggest(self, name: str, group: str) -> list[str]:
        pool = self.names_by_group.get(group) or []
        return difflib.get_close_matches(self.norm(name), pool, n=2, cutoff=0.85)


QUALIFIER = re.compile(r"(?:^|\s)(cf\.|aff\.|\?)(?=\s|$)")


def strip_qualifier(name: str) -> str:
    return re.sub(r"\s+", " ", QUALIFIER.sub(" ", name)).strip()


@dataclass
class TaxonName:
    verbatim: str
    expanded: str
    resolved: bool | None          # None = not abbreviated
    qualifier: str
    notes: list[str]               # (…) after the name
    brackets: list[str]            # […] after the name (substrate / host)
    voucher: bool                  # leading '*'
    czech: bool
    flags: list[str]
    remarks: list[str]


class GenusMemory:
    """Resolve 'C. canescens' from the preceding full genus with the same initial."""

    def __init__(self):
        self.history: list[tuple[str, int]] = []

    def remember(self, genus: str, page: int):
        self.history.append((genus, page))

    def resolve(self, abbr: str, page: int, checklist: Checklist, rest: str) -> tuple[str, list[str], list[str]]:
        flags, remarks = ["ABBREV_GENUS"], []
        cands = [(g, p) for g, p in reversed(self.history) if g.startswith(abbr)]
        if not cands:
            return "", flags + ["AMBIGUOUS"], ["no preceding genus with this initial"]
        genus, gpage = cands[0]
        last_genus = self.history[-1][0] if self.history else ""
        if not last_genus.startswith(abbr):
            flags.append("AMBIGUOUS")
            remarks.append(f"preceding entry is {last_genus}; expanded to the last genus starting '{abbr}'")
        elif gpage != page:
            flags.append("AMBIGUOUS")
            remarks.append("genus given on the previous page")
        others = [g for g, _ in cands[1:] if g != genus]
        full = f"{genus} {rest}".strip()
        if others and not checklist.match(strip_qualifier(full), "")[0]:
            alt = [f"{g} {rest}" for g in dict.fromkeys(others) if checklist.match(strip_qualifier(f"{g} {rest}"), "")[0]]
            if alt:
                flags.append("AMBIGUOUS")
                remarks.append(f"'{full}' not in checklist but {alt[0]} is")
        return genus, flags, remarks


PROTECTION_CODE = re.compile(r"^(?:KO|SO|O|§\s*[123])$")
ABBREV_END = re.compile(r"\b(agg|sp|spp|str|l|lat|var|subsp|ssp|f|cf|aff|coll|sect|ser|nothosubsp|hybr)\.$")


def strip_final_period(s: str) -> str:
    """Drop a sentence-final '.' but keep the one closing 'agg.', 'sp.', 's. str.' …"""
    s = s.strip().rstrip(",;").strip()
    return s if ABBREV_END.search(s) else s.rstrip(".").strip()


def parse_taxon(raw: str, page: int, genera: GenusMemory, checklist: Checklist) -> TaxonName:
    raw = strip_final_period(raw)
    voucher = raw.startswith("*")
    raw = raw.lstrip("*").strip()
    lit_remarks = []
    lm = re.search(r"\s+[–-]\s+Lit\.:?\s*(.+)$", raw)          # "Agrostis canina – Lit.: Duda & Šula (1964)"
    if lm:
        lit_remarks.append(f"earlier literature record: {lm.group(1).strip()}")
        raw = raw[:lm.start()].strip()
    notes, brackets = [], []
    while True:  # trailing (NT/C3) (OL) (cult.) [sax]
        m = re.search(r"\s*(\(([^()]*)\)|\[([^\[\]]*)\])\s*$", raw)
        if not m:
            break
        if m.group(2) is not None:
            notes.insert(0, m.group(2).strip())
        elif not PROTECTION_CODE.match(m.group(3).strip()):     # [SO], [§2]: protection is never taken over
            brackets.insert(0, m.group(3).strip())
        raw = raw[:m.start()].strip()
    q = QUALIFIER.search(raw)
    qualifier = q.group(1) if q else ""
    flags, remarks = [], list(lit_remarks)
    czech = bool(raw) and raw[0].islower()
    m = re.match(r"^([A-Z][a-z]{0,2})\.\s+(.*)$", raw)
    if m:
        genus, f, r = genera.resolve(m.group(1), page, checklist, m.group(2))
        flags += f
        remarks += r
        expanded = f"{genus} {m.group(2)}".strip() if genus else ""
        resolved = bool(genus)
    else:
        expanded, resolved = raw, None
        g = re.match(r"^([A-Z][a-zë-]+)\b", raw)
        if g:
            genera.remember(g.group(1), page)
    return TaxonName(raw, expanded, resolved, qualifier, notes, brackets, voucher, czech, flags, remarks)


def classify_notes(notes: list[str]) -> dict:
    out = {"red_list_category": [], "herbarium": [], "status_note": [], "recorded_by": [], "remarks": []}
    for n in notes:
        tokens = [t.strip() for t in n.split(",")]
        if REDLIST.match(n.replace(" ", "") if "/" in n else n):
            out["red_list_category"].append(n)
        elif CULT.match(n):
            out["status_note"].append(n)
        elif all(t in KNOWN_HERBARIA or re.fullmatch(r"[A-Z]{3,6}", t) or t.startswith("herb.") for t in tokens):
            out["herbarium"].append(", ".join(tokens))
        elif all(INITIALS.match(t) for t in tokens):
            out["recorded_by"].append(", ".join(tokens))
        else:
            out["remarks"].append(f"note: ({n})")
    return out


def taxon_heading(block: Block) -> tuple[str, str] | None:
    """A heading/paragraph that names a taxon: '*Buglossoides arvensis* agg.', '*Celastrus orbiculatus* Thunb. – jesenec…',
    'Nové lokality *Corispermum pallasii* na …'. Returns (verbatim, name for matching)."""
    t = block.text
    runs, cur, cur_it = [], "", None
    for c, it in zip(t, block.ital):
        if cur_it is None or it == cur_it:
            cur += c
        else:
            runs.append((cur, cur_it))
            cur = c
        cur_it = it
    if cur:
        runs.append((cur, cur_it))
    italic = [r.strip() for r, it in runs if it and r.strip()]
    if not italic:
        return None
    if block.starts_italic:
        head = re.split(r"\s+[–-]\s+|\s*\((?:obr|Obr|fig)", t)[0].strip()
        if not re.match(rf"^[{UC}][{LC}ë-]+\s+[×]?[{LC}ë-]+", head):
            return None
        words = []
        for r, it in runs:
            for w in r.split():
                if it or w in ("subsp.", "var.", "agg.", "s.", "str.", "l.", "f.", "×", "sect.", "ser."):
                    words.append(w)
                else:
                    break
            else:
                continue
            break
        return head, " ".join(words)
    # one italic binomial inside a heading
    bins = [r for r in italic if re.fullmatch(rf"[{UC}][{LC}ë-]+\s+[×]?[{LC}ë-]+(?:\s+(?:subsp\.|var\.)\s+[{LC}-]+)?", r)]
    if len(bins) == 1 and block.kind != "p":
        return bins[0], bins[0]
    return None


# ---------------------------------------------------------------- article model

@dataclass
class Article:
    key: str
    source_file: str
    citation: str
    section: str
    locs: list[dict] = field(default_factory=list)
    occs: list[dict] = field(default_factory=list)
    log: Counter = field(default_factory=Counter)
    notes: list[str] = field(default_factory=list)
    loc_by_number: dict[str, dict] = field(default_factory=dict)
    loc_by_name: dict[str, dict] = field(default_factory=dict)
    used_ids: set[str] = field(default_factory=set)
    seq_loc: int = 0
    record_type: str = "species_list"

    def drop_loc(self, loc: dict) -> None:
        """Undo new_loc (used when a wrapped entry is merged with its continuation paragraph)."""
        self.locs.remove(loc)
        self.used_ids.discard(loc["locality_id"])
        for index in (self.loc_by_number, self.loc_by_name):
            for k in [k for k, v in index.items() if v is loc]:
                del index[k]

    def new_loc(self, number: str | None, page: int, line: str) -> dict:
        if number:
            m = re.match(r"(\d+)([A-Za-z]*)", number)
            lid = f"{self.key}_L{int(m.group(1)):03d}{m.group(2)}"
        else:
            self.seq_loc += 1
            lid = f"{self.key}_L{self.seq_loc:03d}"
            while lid in self.used_ids:
                lid = f"{self.key}_LX{self.seq_loc:03d}"
                self.seq_loc += 1
        loc = {c: "" for c in LOC_COLS}
        loc.update(locality_id=lid, source_file=self.source_file, citation=self.citation, page=page,
                   locality_number_verbatim=number or "", line_verbatim=line)
        loc["_flags"], loc["_remarks"] = [], []
        if lid in self.used_ids:
            loc["_flags"].append("DUPLICATE")
            loc["locality_id"] = lid = f"{lid}_{len(self.locs)}"
        self.used_ids.add(lid)
        self.locs.append(loc)
        if number:
            self.loc_by_number[number] = loc
        return loc

    def new_occ(self, loc: dict | None, page: int, item: str, record_type: str | None = None) -> dict:
        occ = {c: "" for c in OCC_COLS}
        occ.update(occurrence_id=f"{self.key}_O{len(self.occs) + 1:04d}", locality_id=loc["locality_id"] if loc else "",
                   source_file=self.source_file, citation=self.citation, page=page, item_verbatim=item,
                   record_type=record_type or self.record_type)
        occ["_flags"], occ["_remarks"] = [], []
        self.occs.append(occ)
        return occ


def article_key(meta: dict) -> str:
    supp = f"P{meta['supplement']}" if meta.get("supplement") else ""
    pages = (meta.get("pages") or "").split(" ")[0].replace("–", "-")
    return f"ZMSP{meta['issue_no']}{supp}_{pages}"


COUNTRIES = {"polská republika", "polsko", "slovensko", "slovenská republika", "rakousko", "německo",
             "česká republika"}


def split_grid(p: str) -> list[str]:
    """'6370d/6470b' → both; '6270b/d' → 6270b, 6270d."""
    out = []
    for s in re.split(r"\s*/\s*", p.strip()):
        if re.fullmatch(r"[a-d]", s) and out:
            out.append(out[-1][:4] + s)
        else:
            out.append(s)
    return out


def parse_header(head: str) -> dict:
    """Text before the locality colon → phytochorion, grid, municipality, district, cadastral area."""
    out = {"fytochorion_code": [], "fytochorion_name": [], "grid_square": "", "municipality": "", "district": "",
           "cadastral_area": "", "flags": [], "remarks": []}
    rest = []
    for _, p in split_top(head, ","):
        p = p.strip()
        if not p:
            continue
        if not rest and not out["grid_square"] and p.lower() in COUNTRIES:
            out["remarks"].append(f"country: {p}")
            continue
        if not out["grid_square"] and re.fullmatch(r"\d{4}[a-d]?(?:\s*/\s*(?:\d{4}[a-d]?|[a-d]))*", p):
            squares = split_grid(p)
            out["grid_square"] = "|".join(squares)
            if not all(GRID.match(s) for s in squares):
                out["flags"].append("GRID_FORMAT")
            continue
        if not out["grid_square"] and not rest and re.match(r"^\d{1,2}[a-z]?\.\s+\D", p):
            for ph in re.split(r"\s*/\s*(?=\d{1,2}[a-z]?\.\s)", p):
                m = PHYTO.match(ph)
                if m:
                    out["fytochorion_code"].append(m.group(1))
                    out["fytochorion_name"].append(m.group(2).strip())
        elif not out["grid_square"] and not rest and not out["fytochorion_code"] and re.fullmatch(r"\d{1,2}[a-z]?", p):
            out["fytochorion_code"].append(p)             # "74b, 6074b, Bělá …" (code without name)
            out["fytochorion_name"].append("")
        elif not out["grid_square"] and not rest and re.match(r"^\d{4}", p):
            squares = split_grid(p)
            out["grid_square"] = "|".join(squares)
            if not all(GRID.match(s) for s in squares):
                out["flags"].append("GRID_FORMAT")
        elif re.match(r"^distr\.\s+", p):
            out["district"] = p.split(None, 1)[1].strip()
        else:
            rest.append(p)
    muni = ", ".join(rest)
    dm = re.search(r"\((?:distr\.|okres)\s*([^)]+)\)", muni) or re.search(r"\(([A-Z]{2})\)\s*$", muni)
    if dm:
        out["district"] = dm.group(1).strip()
        muni = (muni[:dm.start()] + muni[dm.end():]).strip()
    km = re.search(r"\(?\bk\.\s?ú\.\s*([^,()]+)\)?", muni)
    if km:
        out["cadastral_area"] = km.group(1).strip()
        muni = (muni[:km.start()] + muni[km.end():]).strip()
    gm = re.search(r"\((\d{4}[a-d]?(?:/\d{4}[a-d]?|/[a-d])?)\)", muni)
    if gm and not out["grid_square"]:
        squares = split_grid(gm.group(1))
        out["grid_square"] = "|".join(squares)
        muni = (muni[:gm.start()] + muni[gm.end():]).strip()
    out["municipality"] = re.sub(r"\s{2,}", " ", muni).strip(" ,")
    if not out["grid_square"]:
        out["remarks"].append("no grid square in header")
    return out


def split_header(rest: str) -> tuple[str, str, bool]:
    """(header, body, had_colon). Without a colon: leading phytochorion/grid parts + the next part are the header."""
    head, colon, body = rest.partition(":")
    if colon and len(head) < 160 and not DMS.search(head):
        return head, body, True
    parts = split_top(rest, ",")
    k = 0
    while k < len(parts) and (re.match(r"^\s*\d{1,2}[a-z]?\.\s+\D", parts[k][1]) or re.match(r"^\s*\d{4}", parts[k][1])
                              or re.fullmatch(r"\s*\d{1,2}[a-z]?\s*", parts[k][1])):
        k += 1
    if len(parts) <= k + 1:
        return "", rest, False                               # a name only ("Mokřad v Bělé")
    cut = parts[k + 1][0]
    return rest[:cut - 1], rest[cut:], False


def slice_block(b: Block, a: int, e: int) -> Block:
    return Block(b.kind, b.md, b.text[a:e], b.ital[a:e], b.bold[a:e],
                 [(o - a, p) for o, p in b.marks if a <= o < e], b.page_at(a))


def merge_blocks(a: Block, b: Block) -> Block:
    """An entry and its continuation paragraph (the transcription broke a wrapped entry in two)."""
    marks = list(a.marks)
    if b.page != a.page_at(len(a.text)):
        marks.append((len(a.text) + 1, b.page))
    marks += [(o + len(a.text) + 1, p) for o, p in b.marks]
    return Block("p", a.md + "\n" + b.md, a.text + " " + b.text, a.ital + [False] + b.ital,
                 a.bold + [False] + b.bold, marks, a.page)


def split_entries(b: Block) -> list[Block]:
    """'4 – výchozy pískovce … 5 – trávník …' printed as one paragraph → one block per numbered entry."""
    m0 = LOC_ENTRY.match(b.text)
    if not m0:
        return [b]
    expected = int(m0.group(1)) + 1
    cuts = []
    for m in re.finditer(r"(?<=[)\w.])\s+(\d{1,3})([a-z]?)\s[–-]\s(?=[^\d\s])", b.text):
        if int(m.group(1)) == expected:
            cuts.append(m.start() + 1)
            expected += 1
    if not cuts:
        return [b]
    bounds = [0] + cuts + [len(b.text)]
    return [slice_block(b, bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]


CONTINUATION = re.compile(rf"^(?:\(|\d[\d ,]*\s*m\s*n\.|\d{{1,2}}°|[{LC}])")


def grid_check(loc: dict) -> None:
    """Coordinates outside the stated KFME quadrant (more than 150 m inside another one)."""
    if not loc["lat_start"] or not loc["grid_square"]:
        return
    stated = loc["grid_square"].split("|")
    pts = [(float(loc["lat_start"]), float(loc["lon_start"]))]
    if loc["lat_end"]:
        pts.append((float(loc["lat_end"]), float(loc["lon_end"])))
    for la, lo in pts:
        sq, edge = kfme_square(la, lo)
        if not any(sq == s or (len(s) == 4 and sq[:4] == s) for s in stated) and edge > 0.15:
            loc["_flags"].append("GRID_COORD_MISMATCH")
            loc["_remarks"].append(f"coordinates fall in {sq}")
            return


def fill_locality(loc: dict, header: dict, body: str, ctx_phyto=None) -> str:
    """Fill fields from header parts and the text after the colon. Returns the tail after coordinates/altitude."""
    codes, names = header["fytochorion_code"], header["fytochorion_name"]
    if not codes and ctx_phyto:
        codes, names = ctx_phyto
        loc["_remarks"].append("phytochorion from group heading")
    loc.update(fytochorion_code="|".join(codes), fytochorion_name="|".join(names), grid_square=header["grid_square"],
               municipality=header["municipality"], district=header["district"], cadastral_area=header["cadastral_area"])
    loc["_flags"] += header["flags"]
    loc["_remarks"] += header["remarks"]
    co = parse_coords(body)
    for k in ("coordinates_verbatim", "lat_start", "lon_start", "lat_end", "lon_end", "geometry_type"):
        loc[k] = co[k]
    loc["_flags"] += co["flags"]
    loc["_remarks"] += co["remarks"]
    alt, aspan = pick_altitude(body, co["span"])
    for k in ("altitude_min_m", "altitude_max_m", "altitude_verbatim"):
        loc[k] = alt[k]
    loc["_flags"] += alt["flags"]
    ends = [s for s in (co["span"][0] if co["span"] else None, aspan[0] if aspan else None) if s is not None]
    desc_end = min(ends) if ends else len(body)
    desc = body[:desc_end].strip(" ,;(")
    if not ends:
        desc = re.split(r",\s*(?=(?:leg|not|obs|vedoucí)\b)", desc)[0]
        desc = DATE.split(desc)[0].strip(" ,;") if DATE.search(desc) else desc
    loc["locality_description"] = desc
    tail_start = max([e for e in (co["span"][1] if co["span"] else None, aspan[1] if aspan else None) if e] or [len(desc)])
    grid_check(loc)
    return body[tail_start:]


# ---------------------------------------------------------------- article excerption

class Excerptor:
    def __init__(self, md_path: Path, meta: dict, checklist: Checklist):
        self.fm, self.blocks = read_md(md_path)
        self.meta = meta
        self.cl = checklist
        self.art = Article(article_key(meta), meta["local_path"], meta["citation"], meta.get("section", ""))
        title = meta.get("title", "")
        if re.search(r"herbář|herbarium", title, re.I):
            self.art.record_type = "herbarium_revision"
        self.group = "vascular_plant"
        self.event_date = None          # (start, end, verbatim, source)
        self.year_hint = None
        self.star_note = ""
        self.title_taxon = None
        self._article_context()

    # ---- article-level context
    def _article_context(self):
        for b in self.blocks:
            t = b.text
            if b.kind == "p" and re.match(r"^Taxonomické pojetí", t) and re.search(r"bryo|mechorost", t, re.I):
                self.group = "bryophyte"
            if b.kind == "p" and re.match(r"^datum:", t) and not self.event_date:
                seg = re.split(r"\s*•\s*", t[len("datum:"):])[0]
                d = parse_dates(seg)
                if d["event_date_start"]:
                    self.event_date = (d["event_date_start"], d["event_date_end"], seg.strip(), "article header 'datum:'")
                    self.year_hint = int(d["event_date_start"][:4])
            if b.kind == "p" and t.startswith("Abstract:") and EXCURSION_WORDS.search(t) and not self.event_date:
                ds = list(EN_DATE.finditer(t))
                if len(ds) == 1:
                    m = ds[0]
                    mo = EN_MONTHS[m.group(3)]
                    d1 = iso(int(m.group(1)), mo, int(m.group(4)))
                    d2 = iso(int(m.group(2)), mo, int(m.group(4))) if m.group(2) else d1
                    self.event_date = (d1, d2, m.group(0), "abstract")
            m = re.search(r"\bvše\s+(?:v\s+)?rok[u]?\s+(\d{4})", t)
            if m and not self.year_hint:
                self.year_hint = int(m.group(1))
            m = re.search(r"hvězdičkou\s*\(\*\)\s*jsou\s+dokladován\w*\s+v\s+herbáři\w*\s+([^.]+)", t)
            if m:
                self.star_note = f"voucher (*): dokladováno v herbáři {m.group(1).strip()}"
            if b.kind == "h1" and not self.title_taxon:
                th = taxon_heading(Block("h2", b.md, b.text, b.ital, b.bold, b.marks, b.page))
                if th:
                    self.title_taxon = th

    # ---- main pass
    def run(self) -> Article:
        mode, ctx_phyto, ctx_country = None, None, ""
        genera = GenusMemory()
        cur_taxon = None                 # (verbatim, match name, categories)
        parent = None                    # floristic record waiting for a)/b) sub-items
        single_loc = None                # the current unnumbered locality (A1)
        rl_table: dict[str, tuple[str, str, str]] = {}
        blocks = self.blocks
        consumed: set[int] = set()
        deferred_tables: list[tuple[Block, list[list[str]]]] = []
        last_entry = None                # (block, locality) of the last locality entry, for continuations
        self.loc_singular, self.last_num, self.prev_num = False, None, None
        for i, b in enumerate(blocks):
            if i in consumed or b.kind == "comment":
                continue
            if b.kind == "h1":
                continue
            # ---- headings and bold pseudo-headings ("**Seznam lokalit**:")
            pseudo = b.kind == "p" and b.all_bold and len(b.text) < 90 and not b.starts_italic
            if b.kind in ("h2", "h3") or pseudo:
                h = b.text.strip().rstrip(":").strip()
                hl = re.sub(r"^[a-z]\.\s+", "", h.lower())
                hl = re.sub(r"\s*\([^)]*\)", "", hl).strip(" :")          # "Játrovky (Marchantiophyta)"
                th = taxon_heading(b)
                if LOC_SECTION.search(h):
                    mode, ctx_phyto, ctx_country, single_loc = "loc", None, "", None
                    self.loc_singular = bool(re.match(r"^Lokalita\b", h, re.I))
                    self.last_num, last_entry = None, None
                elif hl in GROUP_HEADINGS:
                    mode, self.group, genera = "species", GROUP_HEADINGS[hl], GenusMemory()
                elif RLTABLE_SECTION.search(h):
                    mode = "rltable"
                elif SPECIES_SECTION.search(h):
                    mode, genera = "species", GenusMemory()
                elif th:
                    mode, cur_taxon, parent = "records", (th[0], th[1], []), None
                elif RESULTS_SECTION.search(h):
                    mode = "records"
                elif mode == "loc" and (b.kind == "h3" or pseudo):
                    m = re.match(r"^(\d{1,2}[a-z]?\.\s.*?)$", h)
                    if m:
                        codes, names = [], []
                        for ph in re.split(r"\s*/\s*(?=\d{1,2}[a-z]?\.\s)", m.group(1)):
                            pm = PHYTO.match(ph.strip())
                            if pm:
                                codes.append(pm.group(1))
                                names.append(pm.group(2).strip())
                        ctx_phyto = (codes, names)
                    elif re.search(rf"[{UC}{LC}]{{3}}", h):
                        ctx_country, ctx_phyto = h, None
                elif b.kind == "h2" or (b.kind == "h3" and mode not in ("species", "records")):
                    mode = None
                self.art.log[f"heading→{mode}"] += 1
                continue

            # ---- tables: matrices and herbarium tables anywhere; red-list table in its section
            if b.kind == "table":
                rows = table_rows(b.text)
                hdr = [md_to_plain(c)[0].strip().lower() for c in rows[0]] if rows else []
                if mode == "rltable":
                    for r in rows[1:]:
                        if len(r) == 4:
                            rl_table[md_to_plain(r[0])[0].strip()] = (r[1], r[2], r[3])
                elif hdr and re.match(r"taxon|druh", hdr[0]) and sum(bool(re.fullmatch(r"\d{1,3}[a-z]?", c)) for c in hdr[1:]) >= 2:
                    deferred_tables.append((b, rows))     # after the locality list, which may come later
                elif any("lokalita" in c for c in hdr) and any(c.startswith(("datum", "leg")) for c in hdr):
                    self.herbarium_table(b, rows, hdr)
                continue

            t = b.text
            # ---- inline-taxon records ("***Agrimonia procera***: 74b, 6074b, Bělá (distr. Opava): …") in any section
            inline = re.match(r"^(.{3,120}?):\s+(?=\d{1,2}[a-z]?,\s*\d{4}|\d{1,2}[a-z]?\.\s+[A-Z]|\d{4}[a-d]?,)", t)
            if b.kind == "p" and inline and b.bold and b.bold[0] and b.starts_italic:
                name = inline.group(1).strip()
                body_block = Block("p", b.md, t[inline.end():], b.ital[inline.end():], b.bold[inline.end():],
                                   [(o - inline.end(), p) for o, p in b.marks], b.page)
                self.record(body_block, (name, strip_qualifier(name), []), None, line=t)
                self.art.log["pattern B: inline-taxon record"] += 1
                continue
            # ---- a numbered list of localities outside a "Seznam lokalit" section ("1\. 6475b, Kozlovice, …")
            if mode is None and b.kind == "p" and re.match(r"^\d{1,3}[a-z]?\.\s+(?:\d{4}[a-d]?(?:/\S+)?,|\d{1,2}[a-z]?\.\s+[A-Z])", t) \
                    and not self.title_taxon:
                mode, ctx_phyto, ctx_country, single_loc = "loc", None, "", None
                self.art.log["numbered locality list without heading"] += 1
            # ---- single-taxon article: its "Lokalita:" entry is a floristic record of the title taxon
            if mode == "loc" and b.kind == "p" and self.title_taxon and self.loc_singular \
                    and (RECORD_START.match(t) or GRID_START.match(t)) and not re.match(r"^\d{1,3}[a-z]?\.\s+\d", t):
                parent = self.record(b, self.title_taxon_ctx(), None)
                self.art.log["pattern B: record of the title taxon"] += 1
                continue
            # ---- locality lists (a species list may follow directly, without its own heading)
            if mode == "loc" and b.kind == "p":
                if SPECIES_ITEM.match(split_top(t, ";")[0][1].strip()) and not LOC_ENTRY.match(t):
                    mode, genera = "species", GenusMemory()
                elif single_loc is not None and self.is_taxon_list(b, allow_single=True):
                    self.species_paragraph(b, genera, single_loc)     # list right under a single locality
                    continue
                else:
                    if last_entry is not None and CONTINUATION.match(t) and len(t) < 250 \
                            and not LOC_ENTRY.match(t) and (DMS.search(t) or ALT.search(t)):
                        # the transcription split a wrapped entry: re-parse the entry with its continuation
                        prev_block, prev_loc = last_entry
                        self.art.drop_loc(prev_loc)
                        for sub_loc in [l for l in self.art.locs if l.get("_parent") is prev_loc]:
                            self.art.drop_loc(sub_loc)
                        self.last_num = self.prev_num
                        entries = [merge_blocks(prev_block, b)]
                        self.art.log["entry merged with its continuation paragraph"] += 1
                    else:
                        entries = split_entries(b)
                        if len(entries) > 1:
                            self.art.log["paragraph split into several numbered entries"] += 1
                    for eb in entries:
                        loc = self.locality_entry(eb, ctx_phyto, ctx_country)
                        if loc is not None:
                            last_entry = (eb, loc)
                            if not loc["locality_number_verbatim"]:
                                single_loc = loc
                    continue

            # ---- species lists
            if mode == "species" and b.kind == "p":
                self.species_paragraph(b, genera, single_loc)
                continue

            # ---- floristic records (records section, or record-shaped paragraphs anywhere else)
            if b.kind == "p":
                if b.bold and b.bold[0] and b.starts_italic and (mode == "records" or len(t) < 120):
                    n = 0
                    while n < len(t) and (b.bold[n] or not t[n].strip()):
                        n += 1
                    name = t[:n].strip()
                    cats = [c.strip() for c in t[n:].strip().split(",")] if t[n:].strip() else []
                    cur_taxon, parent, mode = (name, strip_qualifier(name), cats), None, "records"
                    self.art.log["pattern B: taxon header"] += 1
                    continue
                sm = SUBITEM.match(t)
                if sm and parent is not None:
                    self.record(b, cur_taxon or self.title_taxon_ctx(), parent, sub=sm)
                    continue
                recordish = bool(DMS.search(t) or re.search(r"\b\d{4}[a-d]\b|\((?:distr\.|okres)|\(\d{1,2}\.\s*\S+\s*\d{4}", t))
                if (RECORD_START.match(t) or GRID_START.match(t)) and recordish:
                    nxt = next((j for j in range(i + 1, len(blocks)) if blocks[j].kind != "comment"), None)
                    if nxt is not None and self.is_taxon_list(blocks[nxt]):
                        loc = self.record_locality_only(b)
                        self.species_paragraph(blocks[nxt], GenusMemory(), loc, record_type="species_list")
                        consumed.add(nxt)
                        self.art.log["pattern A3: locality-first list"] += 1
                        continue
                    if mode not in ("records",) and not (cur_taxon or self.title_taxon):
                        if not (DMS.search(t) or re.search(r"\(\d{1,2}\.\s*\S+\s*\d{4}", t)):
                            self.art.log["record-shaped paragraph skipped (no taxon, no data)"] += 1
                            continue
                    parent = self.record(b, cur_taxon or self.title_taxon_ctx(), None)
                    continue
                if mode == "records" and cur_taxon and self.art.loc_by_name and self.name_key_records(b, cur_taxon):
                    continue
                self.art.log["paragraph skipped (narrative/commentary/caption)"] += 1

        for b, rows in deferred_tables:
            self.matrix(b, rows, GenusMemory())
        self.finish(rl_table)
        return self.art

    def title_taxon_ctx(self):
        return (self.title_taxon[0], self.title_taxon[1], []) if self.title_taxon else None

    # ---- A: locality entries
    def locality_entry(self, b: Block, ctx_phyto, ctx_country) -> dict | None:
        t = b.text
        number, rest = None, t
        m = LOC_ENTRY.match(t)
        nk = NAME_KEY_ENTRY.match(t)
        continues_numbering = bool(m) and self.last_num is not None and int(m.group(1)) == self.last_num + 1
        if m and (not PHYTO_FIRST.match(t) or continues_numbering):
            number, rest = m.group(1) + m.group(2), m.group(3)
            self.prev_num, self.last_num = self.last_num, int(m.group(1))
        elif nk and not m:
            rest = nk.group(2)
        elif not (m or DMS.search(t) or re.search(r"\((?:distr\.|okres)", t) or GRID_START.match(t)):
            self.art.log["loc-section paragraph skipped"] += 1
            return None
        loc = self.art.new_loc(number, b.page, t)
        if nk and not number:
            loc["locality_number_verbatim"] = nk.group(1).strip()
            self.art.loc_by_name[nk.group(1).strip()] = loc
            loc["_remarks"].append("locality keyed by name")
        if b.marks:
            loc["_flags"].append("LIST_SPLIT")
        head, body, had_colon = split_header(rest)
        if not had_colon and head:
            loc["_remarks"].append("no colon: first part read as municipality")
        header = parse_header(head) if head else {"fytochorion_code": [], "fytochorion_name": [], "grid_square": "",
                                                    "municipality": "", "district": "", "cadastral_area": "",
                                                    "flags": [], "remarks": ["name-only locality"]}
        tail = fill_locality(loc, header, body, ctx_phyto)
        if ctx_country and ctx_country != "Česká republika":
            loc["_remarks"].append(f"country: {ctx_country} (group heading)")
        dt = parse_dates(tail or body, self.year_hint)
        for k in ("event_date_start", "event_date_end", "event_date_verbatim"):
            loc[k] = dt[k]
        loc["_flags"] += dt["flags"]
        loc["_remarks"] += dt["remarks"]
        rm = re.search(r"\b(vedoucí|leg\.|not\.|obs\.)", tail)
        if rm:
            loc["recorders_verbatim"] = re.split(r",\s*\d{1,2}\.\s", tail[rm.start():])[0].strip(" .,")
        if number:
            self.sub_localities(loc, number, body)
        self.art.log["pattern A: locality entry"] += 1
        return loc

    def sub_localities(self, parent: dict, number: str, body: str) -> None:
        """'(5s – severní strana hradeb, 49°37'17,3"N, 18°13'38,3"E; 5sv – …)' inside entry 5 → localities 5s, 5sv."""
        subs = list(re.finditer(rf"(?<![\w]){re.escape(number)}([a-z]{{1,3}})\s+[–-]\s+([^;()]+?)(?=;|\))", body))
        if len(subs) < 2:
            return
        for m in subs:
            code = number + m.group(1)
            loc = self.art.new_loc(code, parent["page"], parent["line_verbatim"])
            loc["_parent"] = parent
            for k in ("fytochorion_code", "fytochorion_name", "grid_square", "municipality", "district", "cadastral_area",
                      "altitude_min_m", "altitude_max_m", "altitude_verbatim", "event_date_start", "event_date_end",
                      "event_date_verbatim", "recorders_verbatim"):
                loc[k] = parent[k]
            co = parse_coords(m.group(2))
            for k in ("coordinates_verbatim", "lat_start", "lon_start", "lat_end", "lon_end", "geometry_type"):
                loc[k] = co[k]
            loc["_flags"] += co["flags"]
            desc = m.group(2)[:co["span"][0]].strip(" ,") if co["span"] else m.group(2).strip()
            loc["locality_description"] = f"{parent['locality_description']}: {desc}".strip(": ")
            loc["_remarks"].append(f"sub-locality defined within locality {number}")
            grid_check(loc)
        # the parent's own coordinates are the sub-localities' ones
        for k in ("coordinates_verbatim", "lat_start", "lon_start", "lat_end", "lon_end"):
            parent[k] = ""
        parent["geometry_type"] = "none"
        parent["_flags"] = [f for f in parent["_flags"] if f not in ("MULTI_INTERPRETATION", "COORD_OUT_OF_AREA")]
        parent["_remarks"] = [r for r in parent["_remarks"] if "coordinate pairs" not in r]
        parent["_remarks"].append("coordinates given per sub-locality (" + ", ".join(number + s.group(1) for s in subs) + ")")

    # ---- A: species lists
    def is_taxon_list(self, b: Block, allow_single: bool = False) -> bool:
        if b.kind != "p" or not b.starts_italic:
            return False
        items = [p.strip() for _, p in split_top(b.text, ";")]
        if len(items) < 2:
            items = [p.strip() for _, p in split_top(b.text, ",")]
        items = [re.sub(r"\s+[–-]\s+Lit\..*$", "", x).rstrip(".") for x in items if x.strip(" .")]
        return (len(items) >= 2 or (allow_single and len(items) == 1)) and all(TAXON_ONLY_ITEM.match(x) for x in items)

    def species_paragraph(self, b: Block, genera: GenusMemory, single_loc: dict | None, record_type: str | None = None):
        t = b.text
        items = split_top(t, ";")
        first = items[0][1].strip()
        with_refs = bool(SPECIES_ITEM.match(re.split(r",\s+(?=\*?[A-Z][a-zë]*\.?\s)", first)[0].strip()) or SPECIES_ITEM.match(first))
        if not with_refs:
            if not self.is_taxon_list(b, allow_single=single_loc is not None):
                self.art.log["species-section paragraph skipped (commentary/signature)"] += 1
                return
            if len(items) < 2:
                items = split_top(t, ",")
            loc = single_loc or self.derived_locality(b)
        for off, raw_item in items:
            # items the source separated by ',' instead of ';' ("P. formosum: 1 (FMM), P. juniperinum: 1 (FMM)")
            sub = [(0, raw_item)]
            if with_refs:
                # also Czech-name lists run together without any separator ("…: 1, 3, 4, 5 ryzec plstnatý: 1, 2")
                cuts = [m.start() + (1 if m.group(0).startswith(",") else 0) for m in re.finditer(
                    rf",?\s+(?=\*?(?:[A-Z][a-zë]*\.?|[{LC}]+)\s+[^:,;()]{{2,60}}:\s*\d)", raw_item)
                    if m.start() > raw_item.find(":")]
                if cuts:
                    bounds = [0] + cuts + [len(raw_item)]
                    sub = [(bounds[k], raw_item[bounds[k]:bounds[k + 1]].rstrip(",")) for k in range(len(bounds) - 1)]
            for soff, item in sub:
                item_s = item.strip()
                if not item_s or item_s == ".":
                    continue
                start = off + soff + (len(item) - len(item.lstrip()))
                end = off + soff + len(item)
                page = b.page_at(start)
                split_flag = b.spans_pages(start, end)
                if with_refs:
                    self.species_item(item_s, page, genera, split_flag, len(sub) > 1, record_type)
                else:
                    self.list_taxon(strip_final_period(item_s), page, genera, loc, split_flag, record_type)
        self.art.log["pattern A: species-list paragraph"] += 1

    def apply_taxon(self, occ: dict, taxon: TaxonName):
        occ["taxon_verbatim"] = taxon.verbatim
        occ["taxon_expanded"] = taxon.expanded
        occ["genus_abbreviation_resolved"] = "" if taxon.resolved is None else str(taxon.resolved).lower()
        occ["identification_qualifier"] = taxon.qualifier
        occ["_flags"] += taxon.flags
        occ["_remarks"] += taxon.remarks
        name = strip_qualifier(taxon.expanded) if taxon.expanded else ""
        if taxon.czech:
            norm, grp, remark = self.cl.match_czech(name)
        else:
            norm, grp, remark = self.cl.match(name, self.group) if name else ("", "", "")
        occ["taxon_name_normalised"] = norm
        occ["taxon_group"] = grp or self.group
        if remark:
            occ["_remarks"].append(remark)
        if not norm:
            occ["_flags"].append("TAXON_UNMATCHED")
            occ["_suggest"] = self.cl.suggest(name, self.group) if name and not taxon.czech else []
        notes = classify_notes(taxon.notes)
        occ["red_list_category"] = "; ".join(notes["red_list_category"])
        occ["herbarium"] = "; ".join(notes["herbarium"])
        occ["status_note"] = "; ".join(notes["status_note"])
        occ["recorded_by"] = "; ".join(notes["recorded_by"])
        occ["_remarks"] += notes["remarks"]
        if taxon.brackets:
            occ["habitat_verbatim"] = "; ".join(taxon.brackets)
        if taxon.voucher:
            occ["specimen_note"] = self.star_note or "voucher (*)"

    def species_item(self, item: str, page: int, genera: GenusMemory, split_flag: bool, resplit: bool, record_type):
        tm = re.match(r"^(.+?):\s*(\d.*)$", item)
        if not tm:
            occ = self.art.new_occ(None, page, item, record_type)
            occ["_flags"].append("MULTI_INTERPRETATION")
            occ["_remarks"].append("list item without 'taxon: numbers'")
            return
        taxon = parse_taxon(tm.group(1), page, genera, self.cl)
        refs_raw = tm.group(2).rstrip(" .")
        weird = ":" in refs_raw
        refs = []
        for _, rp in split_top(refs_raw, ","):
            for piece in (rp.split(":") if weird else [rp]):
                piece = piece.strip()
                if not piece:
                    continue
                rm = re.match(r"^(\d{1,3}(?:[a-z]{1,3}|[A-Z])?)\s*(?:\(([^)]*)\))?\s*(?:\[([^\]]*)\])?$", piece)
                refs.append((rm.group(1), rm.group(2), rm.group(3)) if rm else (None, piece, None))
        for num, paren, brack in refs:
            loc = self.art.loc_by_number.get(num) if num else None
            occ = self.art.new_occ(loc, page, item, record_type)
            occ["locality_numbers_verbatim"] = refs_raw
            self.apply_taxon(occ, taxon)
            if paren:
                pn = classify_notes([paren])
                for k in ("herbarium", "status_note", "recorded_by"):
                    occ[k] = "; ".join(filter(None, [occ[k]] + pn[k]))
                occ["red_list_category"] = "; ".join(filter(None, [occ["red_list_category"]] + pn["red_list_category"]))
                occ["_remarks"] += pn["remarks"]
            if brack:
                occ["habitat_verbatim"] = "; ".join(filter(None, [occ["habitat_verbatim"], brack]))
            if num is None:
                occ["_flags"].append("MULTI_INTERPRETATION")
                occ["_remarks"].append(f"locality reference not parsed: '{paren}'")
            elif loc is None:
                occ["_flags"].append("LOC_NUMBER_NOT_FOUND")
                occ["_remarks"].append(f"locality {num} not in the locality list")
            if weird:
                occ["_flags"].append("MULTI_INTERPRETATION")
                occ["_remarks"].append(f"':' inside locality numbers '{refs_raw}' (read as comma)")
            if resplit:
                occ["_flags"].append("MULTI_INTERPRETATION")
                occ["_remarks"].append("list items separated by ',' instead of ';' in the source")
            if split_flag:
                occ["_flags"].append("LIST_SPLIT")
            if NEW_CLAIM.search(item):
                occ["is_new_record_claim"] = "true"

    def list_taxon(self, item: str, page: int, genera: GenusMemory, loc: dict | None, split_flag: bool, record_type):
        taxon = parse_taxon(item, page, genera, self.cl)
        occ = self.art.new_occ(loc, page, item, record_type)
        self.apply_taxon(occ, taxon)
        if split_flag:
            occ["_flags"].append("LIST_SPLIT")

    def derived_locality(self, b: Block) -> dict:
        """A4: flat species list with no locality in the article → one locality derived from the article."""
        loc = next((l for l in self.art.locs if "LOC_DERIVED_FROM_NARRATIVE" in l["_flags"]), None)
        if loc:
            return loc
        loc = self.art.new_loc(None, b.page, self.meta.get("title", ""))
        loc["locality_description"] = self.meta.get("title", "")
        loc["_flags"].append("LOC_DERIVED_FROM_NARRATIVE")
        loc["_remarks"].append("locality = the site named in the article title (no locality list in the article)")
        return loc

    # ---- M / H tables
    def matrix(self, b: Block, rows: list[list[str]], genera: GenusMemory):
        hdr = [md_to_plain(c)[0].strip() for c in rows[0]]
        for r in rows[1:]:
            name = md_to_plain(r[0])[0].strip() if r else ""
            if not name:
                continue
            taxon = parse_taxon(name, b.page, genera, self.cl)
            row_text = " | ".join(md_to_plain(c)[0].strip() for c in r)
            for col, cell in zip(hdr[1:], r[1:]):
                cell = md_to_plain(cell)[0].strip()
                if not cell:
                    continue
                loc = self.art.loc_by_number.get(col)
                occ = self.art.new_occ(loc, b.page, row_text)
                occ["locality_numbers_verbatim"] = col
                self.apply_taxon(occ, taxon)
                if cell != "+":
                    occ["_remarks"].append(f"table cell: {cell}")
                if loc is None:
                    occ["_flags"].append("LOC_NUMBER_NOT_FOUND")
                    occ["_remarks"].append(f"locality {col} not in the locality list")
        self.art.log["pattern M: matrix table"] += 1

    def herbarium_table(self, b: Block, rows: list[list[str]], hdr: list[str]):
        col = {}
        for k, h in enumerate(hdr):
            if h.startswith("ohrožení"):
                col["rl"] = k
            elif h.startswith("latinské jméno") and "herbář" in h:
                col["label_name"] = k
            elif h.startswith("latinské jméno"):
                col.setdefault("name", k)
            elif h.startswith("české jméno"):
                col.setdefault("czech", k)
            elif h.startswith("lokalita"):
                col["loc"] = k
            elif h.startswith("datum"):
                col["date"] = k
            elif h.startswith("leg"):
                col["leg"] = k
            elif h.startswith("poznámka"):
                col["note"] = k
        genera = GenusMemory()
        for r in rows[1:]:
            cells = [md_to_plain(c)[0].strip() for c in r] + [""] * len(hdr)
            name = cells[col["name"]] if "name" in col else cells[col.get("label_name", 0)]
            if not name:
                continue
            row_text = " | ".join(cells[:len(hdr)])
            loc = self.art.new_loc(None, b.page, row_text)
            loc["locality_description"] = cells[col["loc"]] if "loc" in col else ""
            loc["_remarks"].append("locality as written on the herbarium label ([…] = editor's clarification)")
            dt = parse_dates(cells[col["date"]], partial=True) if "date" in col else parse_dates("")
            occ = self.art.new_occ(loc, b.page, row_text, "herbarium_revision")
            self.apply_taxon(occ, parse_taxon(name, b.page, genera, self.cl))
            for k in ("event_date_start", "event_date_end", "event_date_verbatim"):
                occ[k] = dt[k]
            occ["_flags"] += dt["flags"]
            if "leg" in col:
                occ["collected_by"] = cells[col["leg"]]
            if "rl" in col and cells[col["rl"]] not in ("", "-", "–"):
                occ["red_list_category"] = cells[col["rl"]]
            if "label_name" in col and cells[col["label_name"]]:
                occ["_remarks"].append(f"name on label: {cells[col['label_name']]}")
            if "note" in col and cells[col["note"]]:
                occ["_remarks"].append(f"note: {cells[col['note']]}")
            occ["specimen_note"] = "herbarium specimen (herbarium named in the article title)"
        self.art.log["pattern H: herbarium table"] += 1

    # ---- B: floristic records
    def record_locality_only(self, b: Block) -> dict:
        head, body, had_colon = split_header(b.text)
        loc = self.art.new_loc(None, b.page, b.text)
        header = parse_header(head)
        tail = fill_locality(loc, header, body)
        dt = parse_dates(tail, self.year_hint)
        for k in ("event_date_start", "event_date_end", "event_date_verbatim"):
            loc[k] = dt[k]
        return loc

    def record(self, b: Block, taxon_ctx, parent, sub=None, line: str | None = None):
        """Pattern B record or a)/b) sub-item. Returns parent context when the record ends with ':'."""
        if sub is None:
            head, body, _ = split_header(b.text)
            header = parse_header(head)
            if body.strip().endswith(":") or not body.strip():
                alt, _ = pick_altitude(body, None)
                return {"header": header, "desc": body.strip().rstrip(":").strip(), "alt": alt if alt["altitude_verbatim"] else None,
                        "line": line or b.text, "subs": []}
            self.make_record(b, taxon_ctx, header, body, line or b.text, None)
            return None
        body = b.text[sub.end():]
        occs = self.make_record(b, taxon_ctx, parent["header"], body, parent["line"] + " " + b.text, parent)
        parent["subs"].append(occs)
        vse = [o for occ_list in parent["subs"] for o in occ_list if o.get("_vse")]
        if vse:
            src = vse[-1]
            for occ_list in parent["subs"]:
                for o in occ_list:
                    if not o["event_date_verbatim"]:
                        for k in ("event_date_start", "event_date_end", "event_date_verbatim", "recorded_by",
                                  "collected_by", "identified_by", "specimen_note"):
                            o[k] = src[k]
                        o["_remarks"].append("date/persons from '(vše …)' of a sibling sub-item")
        return parent

    def make_record(self, b: Block, taxon_ctx, header, body, line, parent_ctx) -> list[dict]:
        loc = self.art.new_loc(None, b.page, line)
        if b.marks:
            loc["_flags"].append("LIST_SPLIT")
        tail = fill_locality(loc, header, body)
        if parent_ctx:
            if parent_ctx["desc"]:
                loc["locality_description"] = (parent_ctx["desc"] + ": " + loc["locality_description"]).strip(": ")
            if not loc["altitude_verbatim"] and parent_ctx["alt"]:
                for k in ("altitude_min_m", "altitude_max_m", "altitude_verbatim"):
                    loc[k] = parent_ctx["alt"][k]
                loc["_remarks"].append("altitude from parent record")
        occs = []
        for obs_text, paren, extra_remarks in split_observations(tail):
            literature = bool(paren) and not parse_dates(paren, partial=True)["event_date_verbatim"] and LITERATURE.match(paren.strip())
            occ = self.art.new_occ(loc, b.page_at(0), line, "historical_literature" if literature else
                                   ("herbarium_revision" if self.art.record_type == "herbarium_revision" else "detailed_record"))
            occ["observation_verbatim"] = (obs_text + (f" ({paren})" if paren else "")).strip()
            occ["abundance_verbatim"] = obs_text
            occ["_remarks"] += extra_remarks
            if taxon_ctx:
                verb, match_name, cats = taxon_ctx
                taxon = TaxonName(verb, verb, None, (QUALIFIER.search(verb).group(1) if QUALIFIER.search(verb) else ""),
                                  [], [], False, False, [], [])
                self.apply_taxon(occ, taxon)
                if match_name != verb and "TAXON_UNMATCHED" in occ["_flags"]:
                    norm, grp, remark = self.cl.match(strip_qualifier(match_name), self.group)
                    if norm:
                        occ["_flags"].remove("TAXON_UNMATCHED")
                        occ["taxon_name_normalised"], occ["taxon_group"] = norm, grp
                        occ["_remarks"].append("matched without the author citation")
                if len(cats) >= 2 and cats[1] not in ("–", "-"):
                    occ["red_list_category"] = cats[1]
                if len(cats) >= 3 and cats[2] not in ("–", "-"):
                    occ["red_list_regional"] = cats[2]
            else:
                occ["_flags"].append("MULTI_INTERPRETATION")
                occ["_remarks"].append("record without a preceding taxon header")
            if literature:
                occ["_remarks"].append(f"literature: {paren}")
            elif paren:
                dt = parse_dates(paren, self.year_hint, partial=True)
                for k in ("event_date_start", "event_date_end", "event_date_verbatim"):
                    occ[k] = dt[k]
                occ["_flags"] += dt["flags"]
                ps = persons(paren)
                for k in ("recorded_by", "collected_by", "identified_by", "specimen_note", "herbarium"):
                    occ[k] = " | ".join(filter(None, [occ[k]] + ps[k])) if k == "herbarium" else " | ".join(ps[k])
                occ["_remarks"] += ps["remarks"]
                if re.match(r"^\s*vše\b", paren):
                    occ["_vse"] = True
            if b.marks:
                occ["_flags"].append("LIST_SPLIT")
            if NEW_CLAIM.search(line):
                occ["is_new_record_claim"] = "true"
            occs.append(occ)
        self.art.log["pattern B: record locality"] += 1
        return occs

    def name_key_records(self, b: Block, taxon_ctx) -> bool:
        """A2: 'Bernartice (26. 5., JESM), Česká Ves bazén (4.6., JESM), …' under a taxon heading."""
        items = [p.strip().rstrip(".") for _, p in split_top(b.text, ",")]
        parsed = []
        for it in items:
            m = re.match(r"^(.+?)\s*\(([^()]*)\)$", it)
            if not m:
                return False
            parsed.append((m.group(1).strip(), m.group(2)))
        if not parsed or not any(n in self.art.loc_by_name for n, _ in parsed):
            return False
        for name, paren in parsed:
            loc = self.art.loc_by_name.get(name)
            occ = self.art.new_occ(loc, b.page, b.text, "detailed_record")
            occ["observation_verbatim"] = f"{name} ({paren})"
            occ["locality_numbers_verbatim"] = name
            verb, match_name, _ = taxon_ctx
            self.apply_taxon(occ, TaxonName(verb, verb, None, "", [], [], False, False, [], []))
            if match_name != verb and "TAXON_UNMATCHED" in occ["_flags"]:
                norm, grp, _r = self.cl.match(match_name, self.group)
                if norm:
                    occ["_flags"].remove("TAXON_UNMATCHED")
                    occ["taxon_name_normalised"], occ["taxon_group"] = norm, grp
            dt = parse_dates(paren, self.year_hint)
            for k in ("event_date_start", "event_date_end", "event_date_verbatim"):
                occ[k] = dt[k]
            occ["_remarks"] += dt["remarks"]
            herbs = [p.strip() for p in paren.split(",") if p.strip() in KNOWN_HERBARIA]
            occ["herbarium"] = "; ".join(herbs)
            if loc is None:
                occ["_flags"].append("LOC_NUMBER_NOT_FOUND")
                occ["_remarks"].append(f"locality '{name}' not in the locality list")
        self.art.log["pattern A2: name-keyed records"] += 1
        return True

    # ---- post-processing
    def finish(self, rl_table):
        art = self.art
        used = {o["locality_id"] for o in art.occs if o["locality_id"]}
        for loc in art.locs:
            if loc["locality_id"] not in used:
                loc["_flags"].append("LOC_UNUSED")
            if not loc["event_date_verbatim"] and self.event_date and art.record_type != "herbarium_revision" \
                    and "LOC_DERIVED_FROM_NARRATIVE" not in loc["_flags"] and not self._has_record_occs(loc):
                loc["event_date_start"], loc["event_date_end"], loc["event_date_verbatim"], src = self.event_date
                loc["_remarks"].append(f"date from the {src} (whole excursion)")
        for occ in art.occs:
            if rl_table and occ["taxon_expanded"] in rl_table:
                _prot, nat, reg = rl_table[occ["taxon_expanded"]]   # protection ignored (checkpoint 3, Q3)
                if nat and nat not in ("-", "–"):
                    occ["red_list_category"] = nat
                if reg and reg not in ("-", "–"):
                    occ["red_list_regional"] = reg
                occ["_remarks"].append("red-list categories from the article's table")
        seen = {}
        for occ in art.occs:
            k = (occ["locality_id"], occ["taxon_expanded"], occ["event_date_verbatim"], occ["observation_verbatim"],
                 occ["herbarium"], occ["habitat_verbatim"])
            if occ["locality_id"] and k in seen:
                occ["_flags"].append("DUPLICATE")
                occ["_remarks"].append(f"same as {seen[k]}")
            else:
                seen[k] = occ["occurrence_id"]

    def _has_record_occs(self, loc) -> bool:
        return any(o["locality_id"] == loc["locality_id"] and o["record_type"] in ("detailed_record", "historical_literature")
                   for o in self.art.occs)


def split_observations(tail: str) -> list[tuple[str, str, list[str]]]:
    """', dva jedinci (25. 4. 2014 not. X), pět rostlin (…); 15 ex. (…)' → [(abundance, bracket, remarks)].
    A bracket with several ';'-separated dated events yields one observation per event; undated parts
    following an event are kept as its remarks."""
    tail = tail.strip(" ,.;")
    if not tail:
        return [("", "", [])]
    out, pos = [], 0
    for m in re.finditer(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", tail):
        content = m.group(1)
        dated = parse_dates(content, partial=True)["event_date_verbatim"]
        if not dated and not LITERATURE.match(content.strip()):
            continue  # a note in brackets, not an observation
        text = tail[pos:m.start()].strip(" ,.;")
        parts = [p.strip() for _, p in split_top(content, ";")]
        events: list[tuple[str, list[str]]] = []
        for p in parts:
            if parse_dates(p, partial=True)["event_date_verbatim"] or not events:
                events.append((p, []))
            else:
                events[-1][1].append(f"also in brackets: {p}")
        for p, rem in events:
            out.append((text, p, rem))
        pos = m.end()
    rest = tail[pos:].strip(" ,.;")
    if rest:
        out.append((rest, "", []))
    return out or [(tail, "", [])]


# ---------------------------------------------------------------- review queue

QUESTIONS = {
    "AMBIGUOUS": "Is the genus expansion right?",
    "TAXON_UNMATCHED": "Name not in the AOPK checklist — synonym, typo or keep as is?",
    "LOC_NUMBER_NOT_FOUND": "The list refers to a locality that the locality list lacks.",
    "COORD_PARSE": "Coordinates could not be parsed cleanly.",
    "COORD_OUT_OF_AREA": "Outside 48.8–50.5 N, 16.7–18.9 E — correct?",
    "COORD_SEGMENT_LONG": "Start–end pair more than 2 km apart — correct?",
    "ALT_IMPLAUSIBLE": "Altitude outside 150–1500 m or min > max.",
    "GRID_FORMAT": "Grid square not in ####x format.",
    "GRID_COORD_MISMATCH": "Coordinates are not in the stated grid square.",
    "DATE_PARSE": "Date could not be parsed or is implausible.",
    "MULTI_INTERPRETATION": "More than one reading is possible — see remarks.",
    "DUPLICATE": "Duplicate row.",
    "OCR_SUSPECT": "Doubtful character(s) in the source.",
    "LOC_DERIVED_FROM_NARRATIVE": "Locality taken from the article title — acceptable?",
}


def review_row(table: str, row: dict, line: str, parsed: dict, suggest: list[str] | None) -> dict:
    flags = row["flags"].split("|")
    fixes, qs = [], []
    for f in flags:
        if f == "TAXON_UNMATCHED" and suggest:
            fixes.append("closest checklist name(s): " + "; ".join(suggest))
        if f == "ABBREV_GENUS":
            fixes.append(f"expanded as '{row.get('taxon_expanded', '')}'")
        if QUESTIONS.get(f):
            qs.append(QUESTIONS[f])
    return {"table": table, "row_id": row.get("occurrence_id") or row.get("locality_id"), "source_file": row["source_file"],
            "page": row["page"], "line_verbatim": line, "flags": row["flags"],
            "parsed_values": json.dumps(parsed, ensure_ascii=False), "suggested_fix": " | ".join(dict.fromkeys(fixes)),
            "question_for_me": " ".join(dict.fromkeys(qs)) + (f" Remarks: {row['remarks']}" if row["remarks"] and qs else "")}


# ---------------------------------------------------------------- main

def is_record_candidate(meta: dict) -> bool:
    if meta.get("section", "").rstrip(":") in SKIP_SECTIONS:
        return False
    return not SKIP_TITLES.search(meta.get("title", ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="substrings of PDF stems to process")
    ap.add_argument("--all", action="store_true", help="process every record-bearing article")
    args = ap.parse_args()
    if not args.only and not args.all:
        ap.error("give --only STEM... or --all")
    checklist = Checklist(ROOT / "reference" / "checklist_aopk.csv")
    manifest = {}
    for r in csv.DictReader(open(ROOT / "manifest.csv", encoding="utf-8-sig")):
        if r["download_status"] == "downloaded" and r["local_path"] not in manifest:
            manifest[r["local_path"]] = r
    all_locs, all_occs, review, logs = [], [], [], []
    for path, meta in manifest.items():
        stem = Path(path).stem
        if args.only and not any(s in stem for s in args.only):
            continue
        if args.all and not is_record_candidate(meta):
            continue
        md = MD_DIR / Path(path).parent.name / f"{stem}.md"
        if not md.exists():
            continue
        art = Excerptor(md, meta, checklist).run()
        for loc in art.locs:
            loc["flags"] = "|".join(dict.fromkeys(loc.pop("_flags")))
            loc["remarks"] = "; ".join(dict.fromkeys(loc.pop("_remarks")))
            all_locs.append(loc)
            if loc["flags"]:
                parsed = {k: loc[k] for k in ("fytochorion_code", "grid_square", "municipality", "lat_start", "lon_start",
                                             "lat_end", "lon_end", "altitude_verbatim", "event_date_verbatim") if loc[k]}
                review.append(review_row("localities", loc, loc["line_verbatim"], parsed, None))
        for occ in art.occs:
            suggest = occ.pop("_suggest", None)
            occ.pop("_vse", None)
            occ["flags"] = "|".join(dict.fromkeys(occ.pop("_flags")))
            occ["remarks"] = "; ".join(dict.fromkeys(occ.pop("_remarks")))
            all_occs.append(occ)
            if occ["flags"]:
                parsed = {k: occ[k] for k in ("taxon_expanded", "taxon_name_normalised", "locality_id",
                                             "locality_numbers_verbatim", "observation_verbatim", "event_date_verbatim",
                                             "recorded_by") if occ[k]}
                review.append(review_row("occurrences", occ, occ["item_verbatim"], parsed, suggest))
        logs.append((art, meta))
        print(f"{art.key}: {len(art.locs)} localities, {len(art.occs)} occurrences; {dict(art.log)}")
    write_csv(ROOT / "localities.csv", all_locs, LOC_COLS)
    write_csv(ROOT / "occurrences.csv", all_occs, OCC_COLS)
    write_csv(ROOT / "review_queue.csv", review, REVIEW_COLS)
    write_extraction_log(logs, all_locs, all_occs, manifest)
    fl = Counter(f for r in all_locs + all_occs for f in r["flags"].split("|") if f)
    print(f"\n{len(all_locs)} localities, {len(all_occs)} occurrences, {len(review)} review rows")
    print("flags:", dict(fl.most_common()))


RULES_AND_DEVIATIONS = """## Parsing rules and deviations (summary)

Record patterns (letters used per article below): **A** numbered locality list + species lists citing the numbers;
**A1** single-locality appendix; **A2** locality keyed by name; **A3** locality paragraph followed by its taxon list;
**A4** flat species list with no locality information (locality derived from the article title, flagged
LOC_DERIVED_FROM_NARRATIVE); **B** floristic-note records (one occurrence per dated event); **M** species × locality
matrix tables; **H** herbarium revision tables. Details in the docstring of `scripts/03_excerpt.py`.

Rules confirmed at the checkpoints and applied throughout:
- Only structured lists and record paragraphs are excerpted; commentaries, captions and running text never are.
- The printed locality number is the key; a lone "75. Jesenické podhůří, 6372b, …" is a phytochorion, not locality 75
  (unless the number continues the list's numbering).
- Protection status is never taken from the articles (column left empty; bracketed [SO]/[§2] codes are dropped).
- Red-list categories: national in `red_list_category`, regional in `red_list_regional` (added column).
- One occurrence per dated observation; the exact observation text is in `observation_verbatim` (added column).
- Excursion localities without their own date take the date of the article header line "datum: …" or, failing that,
  the single date of the English abstract (remark "date from the …"). A date without year ("28. 3.") takes the year of
  that header or of a methods statement "vše rok 2020" (remark).
- Floristic records without a taxon heading take the article title's single taxon when there is exactly one.
- Taxon names: exact match to the AOPK checklist after orthographic normalisation (spaces, ×, diaeresis; 's. str.' and
  author citations dropped for matching only). Czech-only names (fungus exhibition 4: 25–27) are matched through the
  checklist's Czech names when unique. No synonym resolution: see reference/synonyms_proposed.csv.
- Coordinate bounds for COORD_OUT_OF_AREA: 48.8–50.5 N, 16.7–18.9 E. Extra flag GRID_COORD_MISMATCH (coordinates more
  than 150 m inside another KFME quadrant than the one printed).

Deviations and repairs (all logged):
- Transcription: č. 3 ligature glyphs (U+03D0/U+03D4 → f) and scrambled small-caps bylines were repaired; line-end hard
  hyphens in č. 3 / parts of č. 7 were rejoined (each decision in cache/transcribe_log.jsonl); image tables in 3/P1
  pp. 39–40 were transcribed by a vision model (manual/03-P1/).
- A locality entry that the transcription split into two paragraphs is re-joined before parsing; two dash entries printed
  in one paragraph are split; sub-localities defined inside an entry ("5s – …; 5sv – …") become their own rows.
- Matrix tables are processed after the article's locality list, which in č. 2 is printed after the tables.
- 2: 54–55+vi: the colour plate "vi" is numbered 56 in the page markers (no printed folio).
"""


def write_extraction_log(logs, locs, occs, manifest) -> None:
    lines = ["# Extraction log", "",
             "Per-article record counts, the parsing patterns that produced them, and deviations from the rules.", "",
             RULES_AND_DEVIATIONS, "## Per-article counts", ""]
    done = {art.source_file for art, _ in logs}
    for art, meta in logs:
        fl = Counter(f for r in locs + occs if r["source_file"] == art.source_file for f in r["flags"].split("|") if f)
        lines += [f"### {art.key} — {meta['title']}", "",
                  f"- source: `{art.source_file}`; section: {art.section or '–'}; default record type: {art.record_type}",
                  f"- localities: {len(art.locs)}; occurrences: {len(art.occs)}",
                  "- blocks by pattern: " + ", ".join(f"{k}: {v}" for k, v in sorted(art.log.items())),
                  "- flags: " + (", ".join(f"{k} {v}" for k, v in fl.most_common()) or "none")]
        if not art.locs and not art.occs:
            lines.append("- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)")
        lines += [f"- note: {n}" for n in art.notes]
        lines.append("")
    skipped = [m for p, m in manifest.items() if p not in done]
    lines += ["## Articles not excerpted (no records by type)", ""]
    lines += [f"- {article_key(m)} — {m['title']} ({m.get('section') or 'no section'})" for m in skipped]
    (ROOT / "extraction_log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
