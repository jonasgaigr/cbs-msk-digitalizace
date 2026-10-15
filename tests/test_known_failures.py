"""Phase 1 known failures, written as strict xfail tests on the real source strings.

Each test states the intended behaviour. It fails today; the Phase 1 fix removes its xfail mark.
"""
import csv
import re
from pathlib import Path

import pytest

from conftest import numbered_localities

ROOT = Path(__file__).resolve().parent.parent


def pairs(art, ex=None):
    """{(taxon_expanded, locality number)} of an Article."""
    num = {l["locality_id"]: l["locality_number_verbatim"] for l in art.locs}
    return {(o["taxon_expanded"], num.get(o["locality_id"], "")) for o in art.occs}


# ---------------------------------------------------------------- 1. English abstract dates "Month D, YYYY"

ABSTRACT_14_34 = ("**Abstract:** On June 29, 2024, a botanical excursion took place near the village of Staříč "
                  "(Silesia, Czech Republic).")
CZ_14_34 = ("Koncem června (29. 6.) roku 2024 proběhla pátá exkurze Moravskoslezské pobočky ČBS, jejímž úkolem bylo "
            "zmapovat vzácnější druhy.")


@pytest.mark.xfail(reason="Phase 1 #1: EN_DATE reads only '29 June 2024'")
def test_abstract_month_day_year(excerpt):
    art = excerpt(f"# Exkurze\n\n{ABSTRACT_14_34}\n\n## Seznam lokalit\n\n1. 6370c, Staříč: les.\n\n"
                  "## Seznam taxonů\n\n*Acer campestre*: 1; *Ajuga reptans*: 1;\n")
    assert art.locs[0]["event_date_start"] == "2024-06-29"


@pytest.mark.xfail(reason="Phase 1 #1: two field trips, one date each (13: 40–45)")
def test_abstract_took_place_on(excerpt):
    t = ("**Abstract:** The field trip to the Hukvaldy Castle and its surroundings took place on September 9, 2023. "
         "The second field trip led to Kelinkovice (Moravia, Czech Republic) on September 29, 2023.")
    art = excerpt(f"# Exkurze\n\n{t}\n\n## Seznam lokalit\n\n1. 6370c, Hukvaldy: les.\n\n"
                  "## Seznam taxonů\n\n*Acer campestre*: 1; *Ajuga reptans*: 1;\n")
    # two dates in one abstract: no single article date may be guessed; the locality stays undated but flagged
    assert art.locs[0]["event_date_start"] == "" and "DATE_AMBIGUOUS" in art.locs[0]["_flags"]


@pytest.mark.xfail(reason="Phase 1 #1: Czech narrative date read when it agrees with the abstract")
def test_czech_narrative_date_agrees(excerpt):
    art = excerpt(f"# Exkurze\n\n{ABSTRACT_14_34}\n\n## Úvod\n\n{CZ_14_34}\n\n## Seznam lokalit\n\n"
                  "1. 6370c, Staříč: les.\n\n## Seznam taxonů\n\n*Acer campestre*: 1; *Ajuga reptans*: 1;\n")
    assert art.locs[0]["event_date_start"] == "2024-06-29"
    assert "abstract" in " ".join(art.locs[0]["_remarks"]) and "DATE_CONFLICT" not in art.locs[0]["_flags"]


@pytest.mark.xfail(reason="Phase 1 #1: disagreement between abstract and Czech date is flagged")
def test_czech_narrative_date_conflict(excerpt):
    art = excerpt(f"# Exkurze\n\n{ABSTRACT_14_34}\n\n## Úvod\n\n{CZ_14_34.replace('29. 6.', '28. 6.')}\n\n"
                  "## Seznam lokalit\n\n1. 6370c, Staříč: les.\n\n## Seznam taxonů\n\n*Acer campestre*: 1; *Ajuga reptans*: 1;\n")
    assert "DATE_CONFLICT" in art.locs[0]["_flags"]


# ---------------------------------------------------------------- 2. all-or-nothing paragraph gating

@pytest.mark.xfail(reason="Phase 1 #2: list broken mid-item (9: 40–44)")
def test_paragraph_starting_with_tail_of_previous_item(excerpt):
    art = excerpt(numbered_localities(12) + "## Seznam taxonů\n\n"
                  "*Galeopsis bifida*: 4; *G. pubescens*: 1; *G. speciosa*: 2; *Galinsoga parviflora*:\n\n"
                  "1; *Galium boreale* subsp. *boreale* (LC/C4a): 5; *G. palustre*: 3, 11; *G. uliginosum*: 3; "
                  "*G. verum*: 5; *Geranium columbinum*: 12;\n")
    p = pairs(art)
    assert {("Galinsoga parviflora", "1"), ("Galium boreale subsp. boreale", "5"), ("Galium palustre", "11"),
            ("Geranium columbinum", "12")} <= p
    assert all(o["taxon_verbatim"] for o in art.occs)


@pytest.mark.xfail(reason="Phase 1 #2: herbarium tail continues the previous item (12: 25–30)")
def test_paragraph_starting_with_herbarium_tail(excerpt):
    art = excerpt(numbered_localities(9) + "## Seznam taxonů\n\n"
                  "*Galium aparine*: 3; *G. mollugo* agg.: 2; *G. palustre*: 7; *G. saxatile*: 5\n\n"
                  "(BRNM); *G. uliginosum*: 9; *Geranium phaeum*: 3; *G. pusillum*: 5;\n")
    assert ("Galium uliginosum", "9") in pairs(art)
    sax = [o for o in art.occs if o["taxon_expanded"] == "Galium saxatile"]
    assert len(sax) == 1 and sax[0]["herbarium"] == "BRNM"


@pytest.mark.xfail(reason="Phase 1 #2: locality numbers continue the previous item (6: 11–14)")
def test_paragraph_starting_with_number_list(excerpt):
    art = excerpt(numbered_localities(4) + "## Seznam taxonů\n\n"
                  "*Galeobdolon montanum*: 2, 3, 4; *Galium aparine*:\n\n"
                  "2, 3, 4; *Galium odoratum*: 2, 3, 4; *Geranium phaeum*: 2;\n")
    assert {("Galium aparine", "2"), ("Galium aparine", "4"), ("Galium odoratum", "3"), ("Geranium phaeum", "2")} <= pairs(art)


@pytest.mark.xfail(reason="Phase 1 #2 + #5: one irregular first item must not drop the paragraph (5: 43–46)")
def test_irregular_first_item_keeps_the_rest(excerpt):
    art = excerpt(numbered_localities(6) + "## Seznam taxonů\n\n*Lycoperdon perlatum*: 6;\n\n"
                  "*Megacollybia platyphylla* 3; *Mycena crocata*: 3; *Mycena galopus*: 2, 6; *Mycena pura*: 6;\n",
                  title="Mykologická exkurze")
    assert {("Mycena crocata", "3"), ("Mycena galopus", "6"), ("Megacollybia platyphylla", "3")} <= pairs(art)


# ---------------------------------------------------------------- 3. locality-first lists with group sub-labels

LOC_7_66 = ('76a. Moravská brána vlastní, 6473c, Zámrsky (distr. Přerov): PR Doubek, smíšený les s bohatě vyvinutým '
            'podrostem, asi 1,5 km SSV od kostela v Zámrskách, 49°31\'11"N, 17°50\'10"E – 49°31\'16"N, 17°50\'26"E, '
            '265–275 m n. m. (22. 4. 2017 \\* a 29. 5. 2017 +).')


@pytest.mark.xfail(reason="Phase 1 #3: 'játrovky' / 'mechy' sub-labels between locality and list (7: 66–69)")
def test_locality_first_with_group_sublabels(excerpt):
    art = excerpt(f"# Mechorosty\n\n## Výsledky\n\n{LOC_7_66}\n\njátrovky\n\n"
                  "*Chiloscyphus profundus* \\*, *Plagiochila porelloides* +.\n\nmechy\n\n"
                  "*Amblystegium serpens* \\*, *Ctenidium molluscum* +, *Fissidens exilis* \\* (VM), *F. taxifolius* \\*.\n")
    by = {o["taxon_expanded"]: o for o in art.occs}
    assert set(by) == {"Chiloscyphus profundus", "Plagiochila porelloides", "Amblystegium serpens",
                       "Ctenidium molluscum", "Fissidens exilis", "Fissidens taxifolius"}
    # 3b: '*' / '+' resolve to the two visit dates printed on the locality line
    assert by["Chiloscyphus profundus"]["event_date_start"] == "2017-04-22"
    assert by["Plagiochila porelloides"]["event_date_start"] == "2017-05-29"
    assert by["Fissidens exilis"]["herbarium"] == "VM"
    assert all(o["taxon_group"] == "bryophyte" for o in art.occs)


# ---------------------------------------------------------------- 4. numbered micro-habitats under one site

MICRO_2_48 = ("Na trase od soutoku Šumného a Hraničního potoka (GPS 50°10‘20.6“N 17°15‘27.8“E) a dále podél Šumného "
              "potoka v délce asi 500 m (GPS 50°10‘11.4“N 17°15‘58.2“E):\n\n"
              "1\\. **staré stromy u potoka**: *Orthotrichum affine*\n\n"
              "2\\. **příkop u cesty**: *Pellia epiphylla*\n\n"
              "4\\. **na zemi u skalky**: *Brachythecium salebrosum*, *Plagiochila asplenioides*, *Plagiomnium affine*\n")


@pytest.mark.xfail(reason="Phase 1 #4: micro-habitat entries give 0 rows (2: 48–49)")
def test_numbered_microhabitats(excerpt):
    art = excerpt(f"# Bryologická exkurze\n\n{MICRO_2_48}")
    assert len(art.occs) == 5
    desc = {o["taxon_expanded"]: next(l for l in art.locs if l["locality_id"] == o["locality_id"])["locality_description"]
            for o in art.occs}
    assert "staré stromy u potoka" in desc["Orthotrichum affine"]
    assert "na zemi u skalky" in desc["Plagiomnium affine"]


# ---------------------------------------------------------------- 5. taxon without a colon

@pytest.mark.xfail(reason="Phase 1 #5: 'Taxon 2' without ':' gives an empty-taxon row (5: 43–46, 8: 43–47)")
def test_taxon_without_colon(excerpt):
    art = excerpt(numbered_localities(6) + "## Seznam taxonů\n\n"
                  "*Russula mustelina*: 2; *Russula nigricans* 2; *Russula queletii*: 1; "
                  "*Strobillurus esculentus*: 3; *Sutorius luridiformis* 4, 5;\n")
    p = pairs(art)
    assert {("Russula nigricans", "2"), ("Sutorius luridiformis", "4"), ("Sutorius luridiformis", "5")} <= p
    flagged = [o for o in art.occs if o["taxon_expanded"] == "Russula nigricans"]
    assert flagged and "NO_COLON" in flagged[0]["_flags"]


def test_taxon_without_colon_needs_valid_locality_numbers(excerpt):
    """Guard for #5: a number that is not a locality of the article must not create a record."""
    art = excerpt(numbered_localities(3) + "## Seznam taxonů\n\n*Russula mustelina*: 2; *Russula nigricans* 17;\n")
    assert ("Russula nigricans", "17") not in pairs(art)


# ---------------------------------------------------------------- 6. names split across a paragraph break

def split_names_in_markdown() -> list[str]:
    out = []
    for p in sorted((ROOT / "md").rglob("*.md")):
        paras = re.split(r"\n\s*\n", p.read_text(encoding="utf-8"))
        for a, b in zip(paras, paras[1:]):
            if re.search(r"\*[A-Za-zÀ-ž-]+\*\s*$", a.strip()) and re.match(r"^\*[a-zà-ž]", b.strip()):
                out.append(f"{p.name}: {a.strip()[-25:]!r} | {b.strip()[:25]!r}")
    return out


@pytest.mark.xfail(reason="Phase 1 #6: 15 italic names split across paragraphs (Campanula | rotundifolia, …)")
def test_no_split_italic_names_in_markdown():
    assert split_names_in_markdown() == []


# ---------------------------------------------------------------- 7. literature tails

@pytest.mark.xfail(reason="Phase 1 #7: '– Lit.: Roleček (2002), Filippov (2009)' yields the taxon 'Filippov' (9: 54–61)")
def test_literature_tail_is_not_a_taxon(excerpt):
    art = excerpt("# Mokřadní louka\n\n## Seznam lokalit\n\nLokalita: 6370c, Slavkov: mokřadní louka.\n\n"
                  "## Cévnaté rostliny\n\n*Dactylis glomerata*, *Deschampsia cespitosa* – Lit.: Roleček (2002), "
                  "Filippov (2009), ***Epilobium palustre*** **(NT/C4a)**, *Epilobium tetragonum*\n")
    taxa = [o["taxon_expanded"] for o in art.occs]
    assert taxa == ["Dactylis glomerata", "Deschampsia cespitosa", "Epilobium palustre", "Epilobium tetragonum"]
    desch = art.occs[1]
    assert "Roleček (2002), Filippov (2009)" in " ".join(desch["_remarks"])


# ---------------------------------------------------------------- 8. invariant: no occurrence without a taxon

@pytest.mark.xfail(reason="Phase 1 #8: 36 occurrences with an empty taxon_verbatim in the current tables")
def test_no_empty_taxon_in_occurrences():
    with open(ROOT / "occurrences.csv", encoding="utf-8-sig", newline="") as f:
        empty = [r["occurrence_id"] for r in csv.DictReader(f) if not r["taxon_verbatim"].strip()]
    assert empty == []
