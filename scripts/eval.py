"""Recall and precision of the excerption on the gold-standard articles.

    python scripts/eval.py                         # baseline (tests/baseline) → current tables
    python scripts/eval.py --outputs DIR           # only DIR
    python scripts/eval.py --checked tests/gold/review   # score the unreviewed packages (sanity check: P = R = 1)

Reads the reviewed review CSVs (tests/gold/checked/<article>_cp1250.csv), rebuilds the candidates with the same
deterministic harvester (gold_candidates.py) and scores any set of output tables against the reviewed truth:

  occurrence = (locality, taxon, date); a parser occurrence is a true positive when its locality, its taxon and its date
  agree with a true record of the same candidate (date not scored where the reviewer gave none).
  precision = TP / parser occurrences,  recall = TP / true occurrences,  95 % Wilson intervals.

Truth per reviewed row (is_record = 1):
  locality  'loc=' in correction (numbers or text) › parser localities if locality_ok = 1 (frozen baseline) ›
            printed refs ('refs: 3, 5') or the locality line of a list (harvest_locality) › unknown (never matches)
  taxon     'taxon=' › the baseline parser's expanded name › the printed name
  date      'date=' › baseline date if date_ok = 1 › the ARTICLE row's 'date=' › unknown (not scored)
Development and held-out articles are reported separately; groups: article, pattern, record type.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gold_candidates as gc  # noqa: E402
from common import ROOT, _cp1250_safe  # noqa: E402

YES = {"1", "a", "ano", "y", "yes", "x", "true"}
NO = {"0", "n", "ne", "no", "false"}


# ---------------------------------------------------------------- parsing the review CSV

def flag(v: str) -> bool | None:
    v = (v or "").strip().lower()
    return True if v in YES else False if v in NO else None


def parse_correction(s: str) -> dict[str, str]:
    """'loc=3, 5; date=2017-04-22; taxon=Galium boreale' → dict. Unkeyed text is kept as 'text'."""
    out = {}
    for part in re.split(r";\s*(?=\w+\s*=)", s or ""):
        m = re.match(r"^\s*(loc|date|taxon)\s*=\s*(.*?)\s*;?\s*$", part, re.I | re.S)
        if m:
            out[m.group(1).lower()] = m.group(2)
        elif part.strip():
            out["text"] = part.strip()
    return out


def loc_tokens(s: str) -> list[tuple[str, str]]:
    """'3, 5a' → [('num','3'), ('num','5a')]; anything else → [('text', s)]."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", s).strip()
    toks = [t.strip() for t in s.split(",") if t.strip()]
    if toks and all(re.fullmatch(r"\d{1,3}[a-zA-Z]{0,3}", t) for t in toks):
        return [("num", t) for t in toks]
    return [("text", s)] if s else []


# ---------------------------------------------------------------- matching

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("−", "-")).strip().lower()


def baseline_loc_key(loc: dict | None) -> tuple[str, str] | None:
    if not loc:
        return None
    if loc["locality_number_verbatim"]:
        return ("num", loc["locality_number_verbatim"])
    return ("text", loc["line_verbatim"][:80])


def loc_match(truth: tuple[str, str] | None, loc: dict | None) -> bool:
    if truth is None or loc is None:
        return False
    kind, v = truth
    if kind == "num":
        return loc["locality_number_verbatim"] == v
    hay = norm(" ".join(loc[k] for k in ("line_verbatim", "locality_description", "municipality")))
    return all(norm(part)[:60] in hay for part in v.split(" › ") if part.strip())


def taxon_match(truth: str, occ: dict) -> bool:
    got = gc.norm_name(occ["taxon_expanded"] or occ["taxon_verbatim"])
    t = gc.norm_name(truth)
    if got == t or gc.norm_name(occ["taxon_verbatim"]) == t:
        return True
    m = re.match(r"^([A-Z][a-z]?)\.\s+(.*)$", t)                 # printed abbreviation, expansion not verified
    return bool(m) and got.startswith(m.group(1)) and got.split(" ", 1)[-1] == m.group(2)


@dataclass
class Truth:
    loc: tuple[str, str] | None
    taxon: str
    date: str | None                  # None = not scored


@dataclass
class Row:
    article: str
    set: str
    cand_id: str
    pattern: str
    record_type: str
    truth: list[Truth] = field(default_factory=list)
    occs: list[dict] = field(default_factory=list)
    reviewed: bool = True
    notes: list[str] = field(default_factory=list)


def score(row: Row, locs: dict) -> dict:
    """Greedy one-to-one matching of parser occurrences to true tuples → counts incl. field checks."""
    free = list(range(len(row.truth)))
    tp = 0
    fields = {"taxon": [0, 0], "locality": [0, 0], "date": [0, 0]}
    for o in row.occs:
        loc = locs.get(o["locality_id"])
        hit = next((k for k in free if loc_match(row.truth[k].loc, loc) and taxon_match(row.truth[k].taxon, o)
                    and (row.truth[k].date is None or gc.occ_date(o, locs) == row.truth[k].date)), None)
        if hit is not None:
            free.remove(hit)
            tp += 1
        if row.truth:
            fields["taxon"][1] += 1
            fields["taxon"][0] += any(taxon_match(t.taxon, o) for t in row.truth)
            fields["locality"][1] += 1
            fields["locality"][0] += any(loc_match(t.loc, loc) for t in row.truth)
            same = [t for t in row.truth if loc_match(t.loc, loc) and t.date is not None]
            if same:
                fields["date"][1] += 1
                fields["date"][0] += any(gc.occ_date(o, locs) == t.date for t in same)
    return {"tp": tp, "n_parser": len(row.occs), "n_true": len(row.truth), "fields": fields}


# ---------------------------------------------------------------- truth from the reviewed CSV

def read_checked(path: Path) -> list[dict]:
    with open(path, encoding="cp1250", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def pattern_of(context: str, art_patterns: str, record_type: str = "") -> str:
    tags = art_patterns.split("+")
    if context == "list_refs":
        return "A"
    if context == "list":
        return next((t for t in tags if t in ("A1", "A3", "A4")), "A3")
    if context == "table":
        return "M"
    if context == "table_herbarium":
        return "H"
    if context == "heading":
        return "A2+B" if "A2" in tags else "B"
    if context == "narrative":
        return "N"
    return {"species_list": "A", "detailed_record": "B", "herbarium_revision": "H", "narrative": "N"}.get(record_type, "?")


def article_rows(art: dict, checked: list[dict], base: dict, cur: dict) -> tuple[list[Row], list[str]]:
    """Reviewed truth (from the frozen baseline package) + current parser occurrences, per candidate row."""
    warnings = []
    by_id = {r["cand_id"]: r for r in checked}
    article_date = parse_correction(by_id.get("ARTICLE", {}).get("correction", "")).get("date")
    base_c = {c.cand_id: c for c in base["cands"]}
    cur_c = {c.cand_id: c for c in cur["cands"]}
    rows = []

    def truth_for(rv: dict, base_occs: list[dict], name: str, refs: str, harvest_loc: str, context: str) -> list[Truth]:
        corr = parse_correction(rv.get("correction", ""))
        is_rec = flag(rv.get("is_record"))
        if not is_rec:
            return []
        loc_ok, date_ok = flag(rv.get("locality_ok")), flag(rv.get("date_ok"))
        corr_date = corr.get("date")

        def tdate(occ_date: str | None) -> str | None:
            if corr_date:
                return corr_date
            if date_ok and occ_date is not None:
                return occ_date
            if article_date and not date_ok:
                return article_date
            return "" if date_ok else None

        out = []
        if "loc" in corr:
            locs_true = loc_tokens(corr["loc"])
            base_taxon = next((o["taxon_expanded"] for o in base_occs if o["taxon_expanded"]), "")
            taxon = corr.get("taxon") or base_taxon or name
            for lt in locs_true or [None]:
                same = [o for o in base_occs if loc_match(lt, base["locs"].get(o["locality_id"]))]
                out.append(Truth(lt, taxon, tdate(gc.occ_date(same[0], base["locs"]) if same else None)))
            return out
        if base_occs:
            for o in base_occs:
                lt = baseline_loc_key(base["locs"].get(o["locality_id"])) if loc_ok else None
                taxon = corr.get("taxon") or o["taxon_expanded"] or o["taxon_verbatim"] or name
                out.append(Truth(lt, taxon, tdate(gc.occ_date(o, base["locs"]))))
            return out
        taxon = corr.get("taxon") or name
        if refs:
            return [Truth(lt, taxon, tdate(None)) for lt in loc_tokens(refs)]
        if harvest_loc and context == "list":
            return [Truth(("text", harvest_loc), taxon, tdate(None))]
        warnings.append(f"{art['article']} {rv['cand_id']}: record without a locality — add 'loc=' to correction")
        return [Truth(None, taxon, tdate(None))]

    for cid, c in base_c.items():
        rv = by_id.get(cid)
        if rv is None:
            warnings.append(f"{art['article']} {cid}: missing in the reviewed CSV")
            continue
        if _cp1250_safe(c.name) != rv["taxon_as_printed"]:
            warnings.append(f"{art['article']} {cid}: harvest changed ({rv['taxon_as_printed']!r} → {c.name!r})")
        rtype = (rv.get("record_type_suggested") or "").split(" | ")[0]
        row = Row(art["article"], art["set"], cid, pattern_of(c.context, art["patterns"], rtype), rtype)
        row.reviewed = flag(rv.get("is_record")) is not None
        row.truth = truth_for(rv, c.occs, c.name, c.refs, c.harvest_locality, c.context)
        row.occs = list(cur_c[cid].occs) if cid in cur_c else []
        rows.append(row)

    # parser-only rows of the baseline (P…) and rows the reviewer added (M…)
    cur_orphans = list(cur["orphans"])

    def take_orphans(pred) -> list[dict]:
        hit = [o for o in cur_orphans if pred(o)]
        for o in hit:
            cur_orphans.remove(o)
        return hit

    for o in base["orphans"]:
        rv = by_id.get(o["_cand_id"])
        if rv is None:
            continue
        rtype = (rv.get("record_type_suggested") or o["record_type"]).split(" | ")[0]
        row = Row(art["article"], art["set"], o["_cand_id"], pattern_of("", art["patterns"], rtype), rtype)
        row.reviewed = flag(rv.get("is_record")) is not None
        row.truth = truth_for(rv, [o], o["taxon_verbatim"], "", "", "")
        key = (gc.norm_name(o["taxon_verbatim"]), o["item_verbatim"])
        row.occs = take_orphans(lambda x: (gc.norm_name(x["taxon_verbatim"]), x["item_verbatim"]) == key)
        rows.append(row)
    for rv in checked:
        if not rv["cand_id"].startswith("M") or not rv["taxon_as_printed"].strip():
            continue
        rtype = (rv.get("record_type_suggested") or "").split(" | ")[0]
        row = Row(art["article"], art["set"], rv["cand_id"], pattern_of("", art["patterns"], rtype), rtype)
        rv = dict(rv, is_record=rv.get("is_record") or "1")
        row.truth = truth_for(rv, [], rv["taxon_as_printed"].strip(), "", "", "")
        row.occs = take_orphans(lambda x: any(taxon_match(t.taxon, x) for t in row.truth))
        rows.append(row)
    if cur_orphans:                                     # new parser rows that nobody reviewed: false positives
        row = Row(art["article"], art["set"], "unreviewed", "?", "?")
        row.occs = cur_orphans
        row.notes.append(f"{len(cur_orphans)} parser occurrences not linked to any reviewed row")
        rows.append(row)
    return rows, warnings


# ---------------------------------------------------------------- report

def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(k: int, n: int) -> str:
    if not n:
        return "–"
    lo, hi = wilson(k, n)
    return f"{k / n:.1%} ({k}/{n}; {lo:.0%}–{hi:.0%})"


def aggregate(rows: list[Row], locs_by_article: dict) -> dict:
    tot = {"tp": 0, "n_parser": 0, "n_true": 0, "fields": {f: [0, 0] for f in ("taxon", "locality", "date")},
           "unreviewed": 0}
    for r in rows:
        s = score(r, locs_by_article[r.article])
        tot["tp"] += s["tp"]
        tot["n_parser"] += s["n_parser"]
        tot["n_true"] += s["n_true"]
        for f, (ok, n) in s["fields"].items():
            tot["fields"][f][0] += ok
            tot["fields"][f][1] += n
        tot["unreviewed"] += not r.reviewed
    return tot


def table(title: str, groups: dict[str, list[Row]], locs_by_article: dict) -> list[str]:
    L = [f"#### {title}", "", "| group | precision | recall | taxon ok | locality ok | date ok | unreviewed rows |",
         "|---|---|---|---|---|---|---:|"]
    for g, rows in groups.items():
        a = aggregate(rows, locs_by_article)
        f = a["fields"]
        L.append(f"| {g} | {fmt(a['tp'], a['n_parser'])} | {fmt(a['tp'], a['n_true'])} | {fmt(*f['taxon'])} | "
                 f"{fmt(*f['locality'])} | {fmt(*f['date'])} | {a['unreviewed']} |")
    return L + [""]


def evaluate(outputs: Path, checked_dir: Path, only: list[str] | None = None) -> tuple[list[Row], dict, list[str]]:
    genera = gc.known_genera()
    rows, locs_by_article, warnings = [], {}, []
    for art in gc.read_config():
        if only and art["article"] not in only:
            continue
        path = checked_dir / f"{art['article']}_cp1250.csv"
        if not path.exists():
            warnings.append(f"{art['article']}: no reviewed CSV in {checked_dir}")
            continue
        base = gc.build(art, ROOT / "tests" / "baseline", genera)
        cur = gc.build(art, outputs, genera)
        r, w = article_rows(art, read_checked(path), base, cur)
        rows += r
        warnings += w
        locs_by_article[art["article"]] = cur["locs"]
    return rows, locs_by_article, warnings


def report(label: str, rows: list[Row], locs_by_article: dict) -> list[str]:
    L = [f"### {label}", ""]
    for st in ("dev", "heldout"):
        sub = [r for r in rows if r.set == st]
        if not sub:
            continue
        name = {"dev": "Development set", "heldout": "Held-out set"}[st]
        by_art, by_pat, by_type = defaultdict(list), defaultdict(list), defaultdict(list)
        for r in sub:
            by_art[r.article].append(r)
            by_pat[r.pattern].append(r)
            by_type[r.record_type or "?"].append(r)
        all_rows = {"all": sub}
        L += table(f"{name} — total", all_rows, locs_by_article)
        L += table(f"{name} — per article", dict(sorted(by_art.items())), locs_by_article)
        L += table(f"{name} — per pattern", dict(sorted(by_pat.items())), locs_by_article)
        L += table(f"{name} — per record type", dict(sorted(by_type.items())), locs_by_article)
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", type=Path, nargs="*", default=[ROOT / "tests" / "baseline", ROOT],
                    help="output directories to score (default: baseline, then the current tables)")
    ap.add_argument("--checked", type=Path, default=gc.GOLD / "checked")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path, default=gc.GOLD / "eval_report.md")
    args = ap.parse_args()
    L = ["## Gold-standard evaluation", "",
         "Occurrence = locality + taxon + date (date not scored where the reviewer gave none). Precision = correct "
         "parser occurrences / parser occurrences; recall = correct parser occurrences / true occurrences. "
         "Percentages with (k/n; 95 % Wilson interval). Generated by `scripts/eval.py` from "
         f"`{args.checked.resolve().relative_to(ROOT).as_posix()}`.", ""]
    all_warnings = []
    for d in args.outputs:
        rows, locs, warnings = evaluate(d, args.checked, args.only)
        label = "baseline (tests/baseline)" if d.resolve() == (ROOT / "tests" / "baseline").resolve() else \
            ("current tables" if d.resolve() == ROOT.resolve() else str(d))
        L += report(label, rows, locs)
        all_warnings = warnings
    if all_warnings:
        L += ["### Review warnings", ""] + [f"- {w}" for w in all_warnings] + [""]
    text = "\n".join(L) + "\n"
    print(text)
    args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
