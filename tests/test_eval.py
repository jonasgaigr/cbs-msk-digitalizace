"""Gold-standard evaluation (eval.py)."""
from pathlib import Path

import pytest

from conftest import load_script

gc = load_script("gold_candidates")
ev = load_script("eval")
ROOT = Path(__file__).resolve().parent.parent


def test_parse_correction():
    assert ev.parse_correction("loc=3, 5; date=2017-04-22; taxon=Galium boreale") == \
        {"loc": "3, 5", "date": "2017-04-22", "taxon": "Galium boreale"}
    assert ev.parse_correction("genus is wrong") == {"text": "genus is wrong"}


def test_loc_tokens():
    assert ev.loc_tokens("3, 5a (FMM), 7") == [("num", "3"), ("num", "5a"), ("num", "7")]
    assert ev.loc_tokens("staré stromy u potoka") == [("text", "staré stromy u potoka")]


def test_wilson():
    lo, hi = ev.wilson(9, 10)
    assert 0.59 < lo < 0.60 and 0.98 < hi < 0.99


LOCS = {"L1": {"locality_id": "L1", "locality_number_verbatim": "1", "line_verbatim": "1. Obec: les",
               "locality_description": "les", "municipality": "Obec", "event_date_start": "2020-05-01",
               "event_date_end": ""},
        "L2": {"locality_id": "L2", "locality_number_verbatim": "2", "line_verbatim": "2. Obec: louka",
               "locality_description": "louka", "municipality": "Obec", "event_date_start": "", "event_date_end": ""}}


def occ(lid, taxon, exp="", date=""):
    return {"locality_id": lid, "taxon_verbatim": taxon, "taxon_expanded": exp or taxon, "event_date_start": date,
            "event_date_end": ""}


def test_score_counts_wrong_locality_as_fp_and_fn():
    row = ev.Row("a", "dev", "c001", "A", "species_list",
                 truth=[ev.Truth(("num", "1"), "Carex flava", "2020-05-01"), ev.Truth(("num", "2"), "Carex flava", None)],
                 occs=[occ("L1", "Carex flava"), occ("L1", "Carex flava")])
    s = ev.score(row, LOCS)
    assert (s["tp"], s["n_parser"], s["n_true"]) == (1, 2, 2)
    assert s["fields"]["locality"] == [2, 2] and s["fields"]["date"] == [2, 2]


def test_score_abbreviation_without_verified_expansion():
    row = ev.Row("a", "dev", "c001", "A3", "species_list", truth=[ev.Truth(("num", "1"), "B. rutabulum", None)],
                 occs=[occ("L1", "B. rutabulum", "Brachythecium rutabulum")])
    assert ev.score(row, LOCS)["tp"] == 1


def test_text_locality_matches_site_and_microhabitat():
    hint = "Na trase od soutoku Šumného potoka (GPS 50°10‘20.6“N 17°15‘27.8“E) › staré stromy u potoka"
    loc = dict(LOCS["L1"], line_verbatim="Na trase od soutoku Šumného potoka (GPS 50°10‘20.6“N 17°15‘27.8“E):",
               locality_description="staré stromy u potoka")
    assert ev.loc_match(("text", hint), loc)
    assert not ev.loc_match(("text", hint), dict(loc, locality_description="příkop u cesty"))


def unreviewed_rows(res):
    rows = [gc.review_row(c.cand_id, c.page, c.name, c.source_line, c.occs, res["locs"], c.context, c.colour,
                          c.harvest_locality, gc.CONTEXT_TYPE.get(c.context, "")) for c in res["cands"]]
    rows += [gc.review_row(o["_cand_id"], o["page"], o["taxon_verbatim"], o["item_verbatim"], [o], res["locs"], "",
                           "green", "", "") for o in res["orphans"]]
    return [{k: gc._cp1250_safe(str(v)) for k, v in r.items()} for r in rows]


@pytest.fixture(scope="module")
def small_gold():
    art = next(a for a in gc.read_config() if a["article"] == "ZMSP10_53-63")
    res = gc.build(art, ROOT / "tests" / "baseline", gc.known_genera())
    return art, res


def test_eval_of_an_unchanged_package_is_perfect(small_gold):
    art, res = small_gold
    rows, warnings = ev.article_rows(art, unreviewed_rows(res), res, res)
    a = ev.aggregate(rows, {art["article"]: res["locs"]})
    assert a["tp"] == a["n_parser"] == a["n_true"] > 0 and not warnings


def test_eval_rejected_and_missed_records(small_gold):
    art, res = small_gold
    checked = unreviewed_rows(res)
    green = next(r for r in checked if r["colour"] == "green")
    n_green = len(green["parser_occurrence_id"].split(" | "))
    green["is_record"] = "0"                                          # reviewer rejects a parser record
    red = next(r for r in checked if r["colour"] == "red")
    red.update(is_record="1", correction="loc=Vidnava; date=2020-07-02")   # and adds a missed one
    rows, _ = ev.article_rows(art, checked, res, res)
    a = ev.aggregate(rows, {art["article"]: res["locs"]})
    assert a["n_parser"] - a["tp"] == n_green
    assert a["n_true"] - a["tp"] == 1
