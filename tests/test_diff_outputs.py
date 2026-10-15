"""diff_outputs.py matches rows on source text, so renumbering is an ID change, not removed + added."""
import csv

from conftest import load_script

diff = load_script("diff_outputs")

LOC_COLS = ["locality_id", "source_file", "line_verbatim", "locality_number_verbatim", "flags"]
OCC_COLS = ["occurrence_id", "locality_id", "source_file", "item_verbatim", "observation_verbatim", "taxon_verbatim",
            "event_date_start", "flags"]


def write(d, locs, occs):
    d.mkdir()
    for name, cols, rows in (("localities.csv", LOC_COLS, locs), ("occurrences.csv", OCC_COLS, occs)):
        with open(d / name, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)


def loc(lid, line, num):
    return dict(locality_id=lid, source_file="a.pdf", line_verbatim=line, locality_number_verbatim=num, flags="")


def occ(oid, lid, item, date="", taxon="X y"):
    return dict(occurrence_id=oid, locality_id=lid, source_file="a.pdf", item_verbatim=item, observation_verbatim="",
                taxon_verbatim=taxon, event_date_start=date, flags="")


def run(tmp_path, old, new):
    write(tmp_path / "old", *old)
    write(tmp_path / "new", *new)
    ol, oo, _ = diff.load(tmp_path / "old")
    nl, no, _ = diff.load(tmp_path / "new")
    maps = ({r["locality_id"]: k for k, r in ol.items()}, {r["locality_id"]: k for k, r in nl.items()})
    return diff.compare(ol, nl, "locality_id"), diff.compare(oo, no, "occurrence_id", maps)


def test_renumbered_ids_are_id_changes(tmp_path):
    old = ([loc("L1", "1. Obec: les", "1"), loc("L2", "2. Obec: louka", "2")],
           [occ("O1", "L1", "*A b*: 1, 2"), occ("O2", "L2", "*A b*: 1, 2")])
    new = ([loc("L1", "1. Obec: les", "1"), loc("L9", "2. Obec: louka", "2")],
           [occ("O7", "L1", "*A b*: 1, 2"), occ("O8", "L9", "*A b*: 1, 2")])
    (ls, lf, _), (os_, of, _) = run(tmp_path, old, new)
    assert ls["a.pdf"] == {"id_changed": 1}
    assert os_["a.pdf"] == {"id_changed": 2}
    assert not lf and not of


def test_added_removed_and_changed_fields(tmp_path):
    old = ([loc("L1", "1. Obec: les", "1")], [occ("O1", "L1", "*A b*: 1"), occ("O2", "L1", "*C d*: 1")])
    new = ([loc("L1", "1. Obec: les", "1")], [occ("O1", "L1", "*A b*: 1", date="2024-06-29"),
                                              occ("O3", "L1", "*E f*: 1")])
    _, (os_, of, ex) = run(tmp_path, old, new)
    assert os_["a.pdf"] == {"added": 1, "removed": 1, "changed": 1}
    assert of["a.pdf"] == {"event_date_start": 1}


def test_repeated_source_text_is_matched_in_order(tmp_path):
    rows = [occ("O1", "", "*A b*: 99"), occ("O2", "", "*A b*: 99")]
    _, (os_, _, _) = run(tmp_path, ([], rows), ([], rows[:1]))
    assert os_["a.pdf"] == {"removed": 1}
