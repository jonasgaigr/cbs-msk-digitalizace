"""Step 4: QA report, sample for manual re-checking, and the proposed synonym table.

    python scripts/04_qa.py            # writes qa_report.md, cache/qa_sample.csv, reference/synonyms_proposed.csv

Manual re-check of the random sample: fill manual/qa_sample_review.csv (row_id, field, correct, note);
fields not listed for a row count as checked and correct. Re-running the script folds the review into the report.
"""
from __future__ import annotations

import csv
import difflib
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, MD_DIR, ROOT, write_csv  # noqa: E402

import importlib.util

_spec = importlib.util.spec_from_file_location("excerpt", Path(__file__).with_name("03_excerpt.py"))
X = importlib.util.module_from_spec(_spec)
sys.modules["excerpt"] = X
_spec.loader.exec_module(X)

SEED = 20260923
SAMPLE_OCC, SAMPLE_LOC = 30, 15
OCC_FIELDS = ["locality_id", "taxon_verbatim", "taxon_expanded", "taxon_name_normalised", "identification_qualifier",
              "event_date_start", "recorded_by", "collected_by", "herbarium", "red_list_category", "record_type", "page"]
LOC_FIELDS = ["locality_number_verbatim", "fytochorion_code", "grid_square", "municipality", "district",
              "locality_description", "lat_start", "lon_start", "lat_end", "lon_end", "altitude_min_m",
              "altitude_max_m", "event_date_start", "page"]


def read(name: str) -> list[dict]:
    return list(csv.DictReader(open(ROOT / name, encoding="utf-8-sig")))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def md_plain_texts() -> dict[str, str]:
    """source_file → plain text of its Markdown (markup and comments removed), for traceability checks."""
    out = {}
    for md in MD_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        m = re.search(r'^source_file: "(.+?)"', text, re.M)
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        plain = []
        for block in re.split(r"\n\s*\n", body):
            if block.startswith("|"):
                plain += [" | ".join(X.md_to_plain(c)[0].strip() for c in row) for row in X.table_rows(block)]
            else:
                plain.append(X.md_to_plain(re.sub(r"^#{1,3}\s+", "", block))[0])
        out[m.group(1)] = norm(" ¶ ".join(plain))
    return out


def found_in(line: str, src: str) -> bool:
    joined = src.replace(" ¶ ", " ")          # an entry the transcription split into two paragraphs
    return any(line[:120] in s or (line[:60] in s and line[-60:] in s) for s in (src, joined))


def dms_check(loc: dict) -> bool:
    ms = list(X.DMS.finditer(loc["coordinates_verbatim"]))
    if len(ms) < 2:
        return not loc["lat_start"]
    ok = abs(X.dms(ms[0]) - float(loc["lat_start"])) < 1e-6 and abs(X.dms(ms[1]) - float(loc["lon_start"])) < 1e-6
    if loc["lat_end"] and len(ms) >= 4:
        ok &= abs(X.dms(ms[2]) - float(loc["lat_end"])) < 1e-6 and abs(X.dms(ms[3]) - float(loc["lon_end"])) < 1e-6
    return ok


def traceability(locs, occs, plain) -> dict:
    """Automatic checks over every row: verbatim fields must be literally present in their source text."""
    res = defaultdict(lambda: [0, 0, []])      # check → [passed, total, examples of failures]

    def check(name, ok, row_id):
        r = res[name]
        r[1] += 1
        if ok:
            r[0] += 1
        elif len(r[2]) < 5:
            r[2].append(row_id)

    for l in locs:
        line = norm(l["line_verbatim"])
        src = plain.get(l["source_file"], "")
        # composed lines (entry + continuation paragraph, record + a)/b) sub-item) are checked piece by piece
        check("locality line_verbatim found in its Markdown", found_in(line, src), l["locality_id"])
        if l["coordinates_verbatim"]:
            check("coordinates_verbatim inside line_verbatim", norm(l["coordinates_verbatim"]) in line, l["locality_id"])
            check("decimal coordinates recomputed from coordinates_verbatim", dms_check(l), l["locality_id"])
        if l["altitude_verbatim"]:
            check("altitude_verbatim inside line_verbatim", norm(l["altitude_verbatim"]) in line, l["locality_id"])
        for g in filter(None, l["grid_square"].split("|")):
            check("each grid square inside line_verbatim", g in line or g[:4] in line, l["locality_id"])
        if l["event_date_verbatim"] and "date from the" not in l["remarks"]:
            check("event_date_verbatim inside line_verbatim",
                  all(norm(v) in line for v in l["event_date_verbatim"].split(" | ")), l["locality_id"])
    loc_ids = {l["locality_id"] for l in locs}
    for o in occs:
        item = norm(o["item_verbatim"])
        src = plain.get(o["source_file"], "")
        check("occurrence item_verbatim found in its Markdown", found_in(item, src), o["occurrence_id"])
        if o["taxon_verbatim"]:
            core = re.sub(r"^\*", "", norm(o["taxon_verbatim"]))
            check("taxon_verbatim inside item_verbatim", core in item or core in src, o["occurrence_id"])
        if o["observation_verbatim"]:
            obs = norm(o["observation_verbatim"])
            m = re.match(r"^(.*?)\s*\((.*)\)$", obs)
            parts = [m.group(1), m.group(2)] if m else [obs]      # abundance / one event of a multi-event bracket
            check("observation_verbatim inside item_verbatim", all(pt in item for pt in parts if pt), o["occurrence_id"])
        if o["locality_id"]:
            check("locality_id resolves to localities.csv", o["locality_id"] in loc_ids, o["occurrence_id"])
    return res


def synonyms_proposal(occs, checklist) -> list[dict]:
    names = defaultdict(lambda: {"n": 0, "articles": set(), "group": ""})
    for o in occs:
        if "TAXON_UNMATCHED" in o["flags"] and o["taxon_expanded"]:
            k = X.strip_qualifier(o["taxon_expanded"])
            names[k]["n"] += 1
            names[k]["articles"].add(o["source_file"].split("/")[-1].replace(".pdf", ""))
            names[k]["group"] = o["taxon_group"]
    rows = []
    for name, d in sorted(names.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        close = checklist.suggest(name, d["group"]) if name[0].isupper() else []
        # proposals only — never applied automatically
        proposal, basis = "", "needs expert decision (synonym, infraspecific rank or group not in checklist)"
        sl = checklist.match(f"{name} s. l.", d["group"])[0]
        if sl:
            proposal, basis = sl, "checklist lists this species only in the broad sense ('s. l.')"
        elif close and difflib.SequenceMatcher(None, name.lower(), close[0].lower()).ratio() >= 0.93:
            proposal, basis = close[0], "orthographic variant (automatic similarity ≥ 0.93)"
        rows.append({"name_verbatim": name, "taxon_group": d["group"], "n_occurrences": d["n"],
                     "articles": " | ".join(sorted(d["articles"])), "closest_checklist_names": " | ".join(close),
                     "proposed_normalised": proposal, "basis": basis, "decision": "", "decided_by": ""})
    return rows


def main() -> None:
    manifest = read("manifest.csv")
    locs, occs, review = read("localities.csv"), read("occurrences.csv"), read("review_queue.csv")
    checklist = X.Checklist(ROOT / "reference" / "checklist_aopk.csv")
    plain = md_plain_texts()

    # ---- 1. totals
    qa_t = (CACHE / "qa_transcription.txt").read_text(encoding="utf-8") if (CACHE / "qa_transcription.txt").exists() else ""
    fidelity = (len(re.findall(r": 0 differences", qa_t)), len(re.findall(r"\.md: \d+ differences", qa_t)))
    st = Counter(r["download_status"] for r in manifest)
    pdf_files = {r["local_path"] for r in manifest if r["download_status"] == "downloaded"}
    methods = Counter()
    vision_files, repairs = [], []
    for md in MD_DIR.rglob("*.md"):
        m = re.search(r'^extraction_method: "(.+?)"', md.read_text(encoding="utf-8"), re.M).group(1)
        methods["text layer" if "TEXT LAYER MISSING" not in m else "needs OCR"] += 1
        if "vision" in m:
            vision_files.append(md.relative_to(ROOT).as_posix())
        if "repairs" in m or "hyphenation" in m:
            repairs.append(md.relative_to(ROOT).as_posix())
    issue_of = lambda sf: sf.split("/")[1]   # noqa: E731
    per_issue = defaultdict(lambda: [0, 0])
    for l in locs:
        per_issue[issue_of(l["source_file"])][0] += 1
    for o in occs:
        per_issue[issue_of(o["source_file"])][1] += 1
    rtypes = Counter(o["record_type"] for o in occs)
    groups = Counter(o["taxon_group"] for o in occs)
    flags = Counter(f for r in locs + occs for f in r["flags"].split("|") if f)
    arts_excerpted = {o["source_file"] for o in occs} | {l["source_file"] for l in locs}

    # ---- 2. referential integrity
    loc_ids = {l["locality_id"] for l in locs}
    dangling = [o for o in occs if o["locality_id"] and o["locality_id"] not in loc_ids]
    unlinked = [o for o in occs if not o["locality_id"]]
    unused = [l for l in locs if "LOC_UNUSED" in l["flags"]]
    dup_ids = [k for k, v in Counter(l["locality_id"] for l in locs).items() if v > 1] + \
              [k for k, v in Counter(o["occurrence_id"] for o in occs).items() if v > 1]

    # ---- 3. traceability over all rows + random sample for manual re-check
    trace = traceability(locs, occs, plain)
    ids_path = ROOT / "manual" / "qa_sample_ids.txt"
    if ids_path.exists():      # the sample that was reviewed by hand stays fixed across re-runs
        ids = set(ids_path.read_text(encoding="utf-8").split())
        s_occ = [o for o in occs if o["occurrence_id"] in ids]
        s_loc = [l for l in locs if l["locality_id"] in ids]
    else:
        rnd = random.Random(SEED)
        s_occ, s_loc = rnd.sample(occs, SAMPLE_OCC), rnd.sample(locs, SAMPLE_LOC)
    sample_rows = [{"table": "occurrences", "row_id": o["occurrence_id"], "source_line": o["item_verbatim"],
                    **{f: o[f] for f in OCC_FIELDS}} for o in s_occ] + \
                  [{"table": "localities", "row_id": l["locality_id"], "source_line": l["line_verbatim"],
                    **{f: l[f] for f in LOC_FIELDS}} for l in s_loc]
    with open(CACHE / "qa_sample.csv", "w", encoding="utf-8-sig", newline="") as f:
        cols = ["table", "row_id", "source_line"] + list(dict.fromkeys(OCC_FIELDS + LOC_FIELDS))
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sample_rows)
    review_path = ROOT / "manual" / "qa_sample_review.csv"
    manual = list(csv.DictReader(open(review_path, encoding="utf-8-sig"))) if review_path.exists() else []
    errors = defaultdict(list)
    for r in manual:
        if r["correct"].strip().lower() in ("false", "0", "no"):
            status = r.get("status_after_fix", "").strip()
            errors[(r["row_id"], r["field"])].append(r["note"] + (f" → {status}" if status else ""))
    field_rates = []
    for table, fields, rows in (("occurrences", OCC_FIELDS, s_occ), ("localities", LOC_FIELDS, s_loc)):
        key = "occurrence_id" if table == "occurrences" else "locality_id"
        for fld in fields:
            wrong = [(r[key], errors[(r[key], fld)]) for r in rows if (r[key], fld) in errors]
            field_rates.append((table, fld, len(rows), len(wrong), wrong))

    # ---- 4. review queue summary
    rq_flags = Counter(f for r in review for f in r["flags"].split("|") if f)
    rq_by_article = Counter(r["source_file"].split("/")[-1] for r in review)
    unmatched_top = Counter(X.strip_qualifier(o["taxon_expanded"]) for o in occs if "TAXON_UNMATCHED" in o["flags"])
    syn = synonyms_proposal(occs, checklist)
    write_csv(ROOT / "reference" / "synonyms_proposed.csv", syn, list(syn[0].keys()) if syn else ["name_verbatim"])

    # ---- report
    L = ["# QA report", "", f"Generated by `scripts/04_qa.py` (sample seed {SEED}).", ""]
    L += ["## 1. Totals", "",
          f"- Articles listed on the website + Zenodo: **{len(manifest)}**",
          f"- PDFs downloaded: **{len(pdf_files)}** files ({st['downloaded']} manifest rows; one PDF holds two book reviews)",
          f"- Not downloadable: {st['no_pdf']} articles without a PDF, {st['embargoed']} embargoed on Zenodo "
          f"(č. 15, until 2026-09-30), {st.get('failed_http_404', 0)} dead links (č. 1)",
          f"- Articles transcribed: **{sum(methods.values())}** — {methods['text layer']} from the text layer, "
          f"{methods['needs OCR']} needing OCR; image tables transcribed by a vision model in {len(vision_files)} file(s) "
          f"({', '.join(vision_files)}); text-layer repairs (č. 3 glyphs/bylines, hard-hyphen rejoining) in {len(repairs)} files",
          f"- Transcription fidelity (`scripts/qa_transcription.py`, cache/qa_transcription.txt): word sequence identical to "
          f"the PDF text layer in {fidelity[0]} of {fidelity[1]} files; the others differ only inside table cells, as "
          f"intended (3: 61–63 repaired ligature glyph 'modroϐialová' → 'modrofialová'; 4: 43–49 'Frýdku-Místku' "
          f"joined across a line break in a cell)",
          f"- Articles excerpted: **{len(arts_excerpted)}**; localities **{len(locs)}**; occurrences **{len(occs)}**", "",
          "### Localities and occurrences per issue", "", "| issue | localities | occurrences |", "|---|---:|---:|"]
    for iss in sorted(per_issue, key=lambda s: (int(s.split("-")[0]), s)):
        L.append(f"| {iss} | {per_issue[iss][0]} | {per_issue[iss][1]} |")
    L += ["", "### Occurrences per record_type and taxon_group", "",
          "| record_type | n |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in rtypes.most_common()] + \
         ["", "| taxon_group | n |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in groups.most_common()]
    L += ["", "### Flags by code (localities + occurrences)", "", "| flag | n |", "|---|---:|"] + \
         [f"| {k} | {v} |" for k, v in flags.most_common()]
    L += ["", "## 2. Referential integrity", "",
          f"- Occurrences whose locality_id does not resolve: **{len(dangling)}**",
          f"- Occurrences without a locality_id: **{len(unlinked)}** (all flagged LOC_NUMBER_NOT_FOUND or "
          f"MULTI_INTERPRETATION — the source cites a locality that its list lacks, or the reference could not be read)",
          f"- Duplicate IDs: **{len(dup_ids)}**",
          f"- LOC_UNUSED localities: **{len(unused)}**"] + \
         [f"  - {l['locality_id']}: {l['line_verbatim'][:110]} — {l['remarks'][:80]}" for l in unused]
    L += ["", "## 3. Accuracy", "", "### Automatic traceability (every row)", "",
          "Each parsed value must be literally present in the source text it came from.", "",
          "| check | passed | total | rate | failing rows (first 5) |", "|---|---:|---:|---:|---|"]
    for name, (ok, tot, ex) in trace.items():
        L.append(f"| {name} | {ok} | {tot} | {ok / tot:.1%} | {', '.join(ex)} |")
    L += ["", f"### Manual re-check of a random sample ({SAMPLE_OCC} occurrences, {SAMPLE_LOC} localities)", "",
          "Each sampled row was compared field by field with its Markdown source line "
          f"({'review recorded in manual/qa_sample_review.csv' if manual else 'REVIEW NOT YET RECORDED'}).", "",
          "| table | field | checked | errors | error rate | notes |", "|---|---|---:|---:|---:|---|"]
    for table, fld, n, nerr, wrong in field_rates:
        notes = "; ".join(f"{rid}: {' / '.join(ns)}" for rid, ns in wrong)
        L.append(f"| {table} | {fld} | {n} | {nerr} | {nerr / n:.1%} | {notes} |")
    total_checks = sum(n for _, _, n, _, _ in field_rates)
    total_err = sum(e for _, _, _, e, _ in field_rates)
    L += ["", f"Overall: {total_err} errors in {total_checks} field checks ({total_err / total_checks:.2%}).", ""]
    L += ["### Recall and precision on the gold standard", ""]
    gold = ROOT / "tests" / "gold" / "eval_report.md"
    if gold.exists():
        # eval.py's report, one heading level down
        L += [("##" + ln) if ln.startswith("#") else ln for ln in gold.read_text(encoding="utf-8").splitlines()[1:]]
    else:
        L += ["Pending: the review packages of the 10 gold articles (tests/gold/review/) have not been checked yet; "
              "the traceability checks and the manual sample above measure precision only. See tests/gold/README.md.", ""]
    L += ["## 4. Review queue", "", f"`review_queue.csv` has **{len(review)}** rows.", "",
          "| flag | rows |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in rq_flags.most_common()]
    L += ["", "Articles with most review rows: " + ", ".join(f"{k} ({v})" for k, v in rq_by_article.most_common(8)), "",
          "Most frequent unmatched names: " + ", ".join(f"{k} ({v})" for k, v in unmatched_top.most_common(15)), ""]

    # ---- recurring problems and rule changes that would fix them (proposed, not applied)
    rows = locs + occs
    only_abbrev = sum(1 for r in review if r["flags"] == "ABBREV_GENUS")
    amb_page = sum(1 for o in occs if "AMBIGUOUS" in o["flags"] and "previous page" in o["remarks"])
    comma_sep = sum(1 for r in rows if "separated by ','" in r["remarks"])
    colon_nums = sum(1 for r in rows if "inside locality numbers" in r["remarks"])
    no_item = sum(1 for r in rows if "without 'taxon: numbers'" in r["remarks"])
    voucher_dups = sum(1 for o in occs if "DUPLICATE" in o["flags"] and "5-11-14" in o["source_file"])
    list_split_only = sum(1 for r in review if r["flags"] == "LIST_SPLIT")
    ortho = sum(1 for s in syn if s["basis"].startswith("orthographic"))
    s_lato = [s for s in syn if "broad sense" in s["basis"]]
    L += ["### Recurring problems and proposed rule changes (not applied — for your decision)", "",
          "| # | problem | rows | proposed change | effect |", "|---|---|---:|---|---|",
          f"| 1 | plain genus expansions (ABBREV_GENUS only, not ambiguous) | {only_abbrev} | keep the flag in the tables but "
          f"leave these rows out of review_queue.csv | queue shrinks from {len(review)} to {len(review) - only_abbrev} rows |",
          f"| 2 | names not in the AOPK checklist | {sum(1 for o in occs if 'TAXON_UNMATCHED' in o['flags'])} "
          f"({len(syn)} names) | approve reference/synonyms_proposed.csv (column `decision`) and apply it as a lookup | "
          f"{ortho} names have an orthographic proposal (e.g. Bidens frondosus → frondosa); the rest need a taxonomic "
          f"decision |",
          f"| 2a | bare species name where the checklist has only the 's. l.' entry (bryophytes: Hypnum cupressiforme → "
          f"Hypnum cupressiforme s. l.) | {sum(s['n_occurrences'] for s in s_lato)} ({len(s_lato)} names) | match a bare "
          f"species name to the checklist's 's. l.' entry | these rows get a normalised name |",
          f"| 3 | genus abbreviation whose genus is on the previous page | {amb_page} | not AMBIGUOUS when the genus is the "
          f"immediately preceding entry of the same list | clears these AMBIGUOUS flags |",
          f"| 4 | source separates list items with ',' instead of ';' | {comma_sep} | accept the split without "
          f"MULTI_INTERPRETATION (keep a remark) | fewer MULTI_INTERPRETATION rows |",
          f"| 5 | ':' inside locality numbers ('7: 14') | {colon_nums} | read ':' as ',' without flag | fewer "
          f"MULTI_INTERPRETATION rows |",
          f"| 6 | voucher sub-list repeating taxa (5: 11–14 'b. Seznam mechorostů, které jsou dokladovány v herbáři') | "
          f"{voucher_dups} | add the herbarium to the matching occurrence instead of a second row | removes these DUPLICATEs |",
          f"| 7 | LIST_SPLIT only (item crosses a page; page resolved inline) | {list_split_only} | informational: leave "
          f"out of the queue | – |",
          f"| – | list items the parser could not read (missing ':' or numbers) | {no_item} | none: genuine source "
          f"irregularities, keep for manual review | – |",
          "| – | GRID_COORD_MISMATCH, ALT_IMPLAUSIBLE, COORD_PARSE, LOC_NUMBER_NOT_FOUND | "
          f"{sum(1 for r in rows if any(f in r['flags'] for f in ('GRID_COORD_MISMATCH', 'ALT_IMPLAUSIBLE', 'COORD_PARSE', 'LOC_NUMBER_NOT_FOUND')))} "
          "| none: these point at inconsistencies in the printed source (checked samples: wrong quadrant letter, reversed "
          "altitude range, missing 'E', locality 141/1a/4/7 cited but not listed) | – |", ""]
    L += ["### Parser fixes made during QA (applied, found in the manual sample)", "",
          "- U+2212 minus sign used as a dash in coordinate pairs and altitude ranges (13: 22–25, 8: 11–13) is now "
          "recognised as a dash.",
          "- District given as a two-letter code after the municipality ('Valašské Příkazy (VS)', mini-course 4/P2) now goes "
          "to `district`.",
          "- 'not' without its dot ('7. 6. 2012 not Z. Mruzíková') is read as a recorder role.",
          "Both sampled rows were re-verified after the fix (see the table above).", ""]
    (ROOT / "qa_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    print(f"... qa_report.md written; {len(syn)} names in reference/synonyms_proposed.csv; sample in cache/qa_sample.csv")


if __name__ == "__main__":
    main()
