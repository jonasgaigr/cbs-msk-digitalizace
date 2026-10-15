"""Gold-standard harvester (gold_candidates.py)."""
from pathlib import Path

import pytest

from conftest import load_script

gc = load_script("gold_candidates")
ROOT = Path(__file__).resolve().parent.parent


def para(md: str, kind: str = "p") -> "gc.Para":
    t, it, bd, marks = gc.decode(md)
    return gc.Para(0, kind, t, it, 10, marks, bold=bd)


def names(md: str, kind: str = "p") -> list[str]:
    p = para(md, kind)
    return [p.text[s:e] for s, e in gc.find_names(p)]


# ---------------------------------------------------------------- the harvester's own Markdown decoder

def test_decoder_matches_the_parser_plain_text_everywhere(ex):
    """The harvester shares no code with 03_excerpt.py, but must see the same text (item_verbatim lookups)."""
    n = 0
    for md in sorted((ROOT / "md").rglob("*.md")):
        _, blocks = ex.read_md(md)
        mine = [p for p in gc.read_paras(md)[0] if p.kind != "table"]
        theirs = [b for b in blocks if b.kind not in ("table", "comment")]
        assert [(p.kind, p.text) for p in mine] == [(b.kind, b.text) for b in theirs], md.name
        n += len(mine)
    assert n > 10000


# ---------------------------------------------------------------- names

@pytest.mark.parametrize("md, expected", [
    ("*Amblystegium serpens*, *B. rutabulum*, *Bryum argenteum*", ["Amblystegium serpens", "B. rutabulum",
                                                                   "Bryum argenteum"]),
    ("*Galium boreale* subsp. *boreale* (LC/C4a): 5", ["Galium boreale subsp. boreale"]),
    ("*Inocybe* sp.: 4, 6;", ["Inocybe sp."]),
    ("*Festuca rubra* agg.: 19", ["Festuca rubra agg."]),
    ("*Circaea* ×*intermedia*, *C. lutetiana*", ["Circaea ×intermedia", "C. lutetiana"]),
    ("*Carex* cf. *hartmanii*: 2", ["Carex cf. hartmanii"]),
    ("*Cirsium* ×*erucagineum* (*C. oleraceum* × *rivulare*): 25", ["Cirsium ×erucagineum"]),
    ("pilát lékařský (*Anchusa officinalis*), hvozdík (*Dianthus armeria*)", ["Anchusa officinalis",
                                                                             "Dianthus armeria"]),
])
def test_names(md, expected):
    assert names(md) == expected


@pytest.mark.parametrize("md", [
    "*Hypnum* je rod mechů",                         # lone genus without sp.
    "*B.* pallens",                                  # epithet not italic, abbreviation alone
    "*Dentario enneaphylli*-Fagetum",                # syntaxon fragment
    "*Univerzita Palackého v Olomouci*",             # capitalised italic words
    "Carex flava roste zde",                          # not italic
])
def test_not_names(md):
    assert names(md) == []


def test_table_cell_binomial_without_italics():
    assert names("Amaranthus cf. ×ozanonii |  | + |  |", "table") == ["Amaranthus cf. ×ozanonii"]


def test_rejoin_split_names():
    ps = [para("*Calystegia sepium*: 1; *Campanula*"), para("*persicifolia*: 1; *C. rotundifolia*: 2;"),
          para("*Plagiothecium laetum*, *Poly*"), para("*trichum formosum*")]
    log = gc.rejoin_split_names(ps, {"Campanula", "Calystegia"})
    assert [p.text for p in ps] == ["Calystegia sepium: 1; Campanula persicifolia: 1; C. rotundifolia: 2;",
                                    "Plagiothecium laetum, Polytrichum formosum"]
    assert len(log) == 2


def test_refs_and_contexts():
    paras = [para("1. 6370c, Obec: les."), para("*Russula mustelina*: 2; *Russula nigricans* 2; *Mycena pura*: 6, 7a;"),
             para("Na lokalitě jsme nalezli *Carex pendula*, která zde roste hojně.")]
    for k, p in enumerate(paras):
        p.idx = k
    cs = gc.harvest(paras, False)
    got = {c.name: (c.context, c.refs) for c in cs}
    assert got["Russula mustelina"] == ("list_refs", "2")
    assert got["Russula nigricans"] == ("list_refs", "2")
    assert got["Mycena pura"] == ("list_refs", "6, 7a")
    assert got["Carex pendula"][0] == "narrative"


def test_one_item_per_paragraph_is_a_list_item():
    p = para("*Cirsium rivulare*: 3, 4, 106 (FMM, rev. P. Bureš & M. Vavrinec), 108.")
    c = gc.harvest([p], False)[0]
    assert (c.context, c.refs) == ("list_refs", "3, 4, 106 (FMM, rev. P. Bureš & M. Vavrinec), 108")


def test_microhabitat_hint_names_site_and_entry():
    ps = [para("Na trase od soutoku Šumného potoka (GPS 50°10‘20.6“N 17°15‘27.8“E):"),
          para("1\\. **staré stromy u potoka**: *Orthotrichum affine*")]
    ps[1].idx = 1
    hint = gc.harvest(ps, False)[0].harvest_locality
    assert hint == "Na trase od soutoku Šumného potoka (GPS 50°10‘20.6“N 17°15‘27.8“E) › staré stromy u potoka"


def test_pdf_word_boxes_are_one_line_high():
    """4/P2 fonts carry ascent/descent metrics that make get_text('words') boxes ~73 pt high."""
    import pymupdf
    page = pymupdf.open(ROOT / "pdf" / "04-P2" / "ZMSPCBS_4_P2_1-48_WEB.pdf")[22]
    assert max(w[3] - w[1] for w in gc.words_tight(page)) < 20
