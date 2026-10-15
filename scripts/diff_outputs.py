"""Compare two sets of excerption outputs (localities / occurrences / review queue), per article.

    python scripts/diff_outputs.py                          # tests/baseline/ → current tables
    python scripts/diff_outputs.py --old A --new B --show 5 --article 2018-7-66-69

Rows are matched on their source text, not on their IDs, so a renumbered row is reported as an ID change and not as
"removed + added":
  locality    = (source_file, line_verbatim, locality_number_verbatim, k-th repeat)
  occurrence  = (source_file, item_verbatim, observation_verbatim, key of its locality, k-th repeat)
For every matched row the fields whose value changed are counted. ID changes are listed separately (rule: IDs stay
stable unless the source text changed).
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT  # noqa: E402

ID_FIELDS = {"locality_id", "occurrence_id"}


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def keyed(rows: list[dict], base) -> dict[tuple, dict]:
    """Key each row by base(row) plus its repeat number among rows with the same base key."""
    seen: Counter = Counter()
    out = {}
    for r in rows:
        b = base(r)
        out[b + (seen[b],)] = r
        seen[b] += 1
    return out


def loc_base(r: dict) -> tuple:
    return (r["source_file"], r["line_verbatim"], r["locality_number_verbatim"])


def load(d: Path) -> tuple[dict, dict, list[dict]]:
    locs = keyed(read(d / "localities.csv"), loc_base)
    loc_key_by_id = {r["locality_id"]: k for k, r in locs.items()}

    def occ_base(r: dict) -> tuple:
        lk = loc_key_by_id.get(r["locality_id"], ("",))
        return (r["source_file"], r["item_verbatim"], r["observation_verbatim"], lk[1:])

    occs = keyed(read(d / "occurrences.csv"), occ_base)
    return locs, occs, read(d / "review_queue.csv")


def compare(old: dict, new: dict, id_field: str, loc_id_maps=None):
    """→ per article: Counter(added, removed, changed, id_changed), Counter(field), examples."""
    stats: dict[str, Counter] = defaultdict(Counter)
    fields: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    for k in old.keys() - new.keys():
        stats[k[0]]["removed"] += 1
        examples[k[0]].append(f"- removed {old[k][id_field]}: {short(old[k])}")
    for k in new.keys() - old.keys():
        stats[k[0]]["added"] += 1
        examples[k[0]].append(f"+ added {new[k][id_field]}: {short(new[k])}")
    for k in old.keys() & new.keys():
        o, n = old[k], new[k]
        diff = [c for c in n if c in o and c not in ID_FIELDS and o[c] != n[c]]
        if loc_id_maps and "locality_id" in diff:
            # a renamed locality is an ID change, not a different locality
            old_loc_key, new_loc_key = loc_id_maps[0].get(o["locality_id"]), loc_id_maps[1].get(n["locality_id"])
            if old_loc_key == new_loc_key:
                diff.remove("locality_id")
        if o[id_field] != n[id_field]:
            stats[k[0]]["id_changed"] += 1
        if diff:
            stats[k[0]]["changed"] += 1
            for c in diff:
                fields[k[0]][c] += 1
            examples[k[0]].append(f"~ {n[id_field]}: " + "; ".join(f"{c}: {o[c]!r} → {n[c]!r}" for c in diff))
    return stats, fields, examples


def short(r: dict) -> str:
    if "taxon_verbatim" in r:
        return f"{r['taxon_verbatim']!r} @ {r['locality_id'] or '–'} | {r['item_verbatim'][:90]!r}"
    return repr(r["line_verbatim"][:110])


def flag_counts(rows: list[dict]) -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        for f in r["flags"].split("|"):
            if f:
                out[r["source_file"]][f] += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", type=Path, default=ROOT / "tests" / "baseline")
    ap.add_argument("--new", type=Path, default=ROOT)
    ap.add_argument("--article", nargs="*", help="substrings of source_file to restrict the report to")
    ap.add_argument("--show", type=int, default=0, help="example rows per article and table")
    ap.add_argument("--out", type=Path, help="also write the report to this file")
    args = ap.parse_args()

    old_locs, old_occs, old_rq = load(args.old)
    new_locs, new_occs, new_rq = load(args.new)
    maps = ({r["locality_id"]: k for k, r in old_locs.items()}, {r["locality_id"]: k for k, r in new_locs.items()})
    tables = [("localities", *compare(old_locs, new_locs, "locality_id")),
              ("occurrences", *compare(old_occs, new_occs, "occurrence_id", maps))]
    old_rq_n, new_rq_n = Counter(r["source_file"] for r in old_rq), Counter(r["source_file"] for r in new_rq)
    old_fl = flag_counts(list(old_locs.values()) + list(old_occs.values()))
    new_fl = flag_counts(list(new_locs.values()) + list(new_occs.values()))

    def wanted(a: str) -> bool:
        return not args.article or any(s in a for s in args.article)

    articles = sorted({a for _, st, _, _ in tables for a in st} | {a for a in old_rq_n | new_rq_n
                                                                  if old_rq_n[a] != new_rq_n[a]}
                      | {a for a in old_fl.keys() | new_fl.keys() if old_fl.get(a) != new_fl.get(a)})
    articles = [a for a in articles if wanted(a)]
    lines = [f"# Output diff: {args.old} → {args.new}", "",
             f"Totals: localities {len(old_locs)} → {len(new_locs)}, occurrences {len(old_occs)} → {len(new_occs)}, "
             f"review rows {len(old_rq)} → {len(new_rq)}", "",
             f"Articles with any change: {len(articles)}", ""]
    if articles:
        lines += ["| article | loc +/−/~ | loc id Δ | occ +/−/~ | occ id Δ | queue | changed fields |",
                  "|---|---|---:|---|---:|---|---|"]
    for a in articles:
        cells = []
        flds = Counter()
        for name, st, fl, _ in tables:
            s = st.get(a, Counter())
            cells += [f"+{s['added']} −{s['removed']} ~{s['changed']}", str(s["id_changed"])]
            flds.update({f"{name[:3]}.{k}": v for k, v in fl.get(a, {}).items()})
        q = f"{old_rq_n[a]} → {new_rq_n[a]}" if old_rq_n[a] != new_rq_n[a] else str(new_rq_n[a])
        lines.append(f"| {Path(a).name} | " + " | ".join(cells) + f" | {q} | "
                     + ", ".join(f"{k} {v}" for k, v in flds.most_common()) + " |")
    flag_delta = Counter()
    for a in articles:
        flag_delta.update(new_fl.get(a, Counter()))
        flag_delta.subtract(old_fl.get(a, Counter()))
    flag_delta = {k: v for k, v in flag_delta.items() if v}
    if flag_delta:
        lines += ["", "Flag changes: " + ", ".join(f"{k} {v:+d}" for k, v in sorted(flag_delta.items()))]
    if args.show:
        for a in articles:
            lines += ["", f"## {Path(a).name}"]
            for name, _, _, ex in tables:
                if ex.get(a):
                    lines += [f"{name}:"] + [f"    {e}" for e in ex[a][:args.show]]
                    if len(ex[a]) > args.show:
                        lines.append(f"    … {len(ex[a]) - args.show} more")
    report = "\n".join(lines) + "\n"
    print(report)
    if args.out:
        args.out.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
