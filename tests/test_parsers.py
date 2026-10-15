"""Value parsers of 03_excerpt.py on real source strings (expected values = the verified baseline rows)."""
import pytest

KRTOMIL = ('3. 76a. Moravská brána vlastní, 6571d, Křtomil (distr. Přerov): okraj pole při cestě jižně od Lipové u '
           'severního okraje lesa Ochozy, asi 1,2 km JZ od obecního úřadu v obci Křtomil, 49°24\'10,1"N, 17°36\'48,6"E '
           '− 49°24\'02,2"N, 17°36\'51,8"E, 310−325 m n. m.')                                # 13: 22–25, U+2212


# ---------------------------------------------------------------- coordinates

def test_coords_segment_with_unicode_minus(ex):
    co = ex.parse_coords(KRTOMIL)
    assert co["geometry_type"] == "segment"
    assert (co["lat_start"], co["lon_start"], co["lat_end"], co["lon_end"]) == \
        ("49.402806", "17.613500", "49.400611", "17.614389")
    assert co["coordinates_verbatim"] in KRTOMIL and not co["flags"]


def test_coords_point_with_primes(ex):
    co = ex.parse_coords("okolí železniční stanice Valašské Příkazy, 49°09′57″N, 18°03′51″E, 460 m n. m.")
    assert (co["geometry_type"], co["lat_start"], co["lon_start"]) == ("point", "49.165833", "18.064167")


def test_coords_typographic_quotes(ex):                                       # 2: 52–53
    co = ex.parse_coords("Váňův kámen, vápencová skála, 49°35‘27,3“N, 18°7‘47,6“E, 420 m n. m.")
    assert (co["lat_start"], co["lon_start"]) == ("49.590917", "18.129889")


def test_coords_mezi_a_is_a_segment(ex):                                      # 10: 'mezi … a …'
    co = ex.parse_coords('mezi 50°13\'20,1"N, 17°36\'59,5"E a 50°13\'15,7"N, 17°36\'56,7"E, 325–350 m n. m.')
    assert co["geometry_type"] == "segment" and co["lat_end"] == "50.221028"
    assert "'mezi … a …' read as start–end" in co["remarks"]


def test_coords_two_pairs_without_dash_are_flagged(ex):                      # 4/P2 locality 86
    co = ex.parse_coords("od památníku zemřelých (49°11′14″N, 18°03′58″E) po samotu U Samečků (49°12′37″N, 18°04′42″E)")
    assert co["geometry_type"] == "point" and "MULTI_INTERPRETATION" in co["flags"]


def test_coords_degree_without_pair_is_a_parse_flag(ex):
    assert ex.parse_coords("49°24'N")["flags"] == ["COORD_PARSE"]


def test_coords_out_of_area(ex):
    assert "COORD_OUT_OF_AREA" in ex.parse_coords("51°00′00″N, 17°00′00″E")["flags"]


def test_kfme_square(ex):
    assert ex.kfme_square(49.402806, 17.6135)[0] == "6571d"
    assert ex.kfme_square(49.165833, 18.064167)[0] == "6874a"


# ---------------------------------------------------------------- altitude

def test_altitude_after_coordinates_unicode_minus(ex):
    alt, _ = ex.pick_altitude(KRTOMIL, ex.parse_coords(KRTOMIL)["span"])
    assert (alt["altitude_min_m"], alt["altitude_max_m"], alt["altitude_verbatim"]) == (310, 325, "310−325 m n. m.")


@pytest.mark.parametrize("text, lo, hi", [
    ("Hranice: ústí Hranické propasti, cca 300 m n. m. (49°31′54″N, 17°45′01″E)", 300, 300),
    ("podél červené turistické trasy – u sjezdovek, 1040–1110 m n. m. (50°07′35″N, 17°08′58″E)", 1040, 1110),
    ("Praděd, 1 491 m n. m.", 1491, 1491),
])
def test_altitude_forms(ex, text, lo, hi):
    alt, _ = ex.pick_altitude(text, ex.parse_coords(text)["span"])
    assert (alt["altitude_min_m"], alt["altitude_max_m"]) == (lo, hi)
    assert alt["altitude_verbatim"] in text


def test_altitude_ignores_bracketed_hill_height(ex):
    alt, _ = ex.pick_altitude("pod vrchem Radhošť (1129 m n. m.), 520 m n. m.", None)
    assert alt["altitude_min_m"] == 520


def test_altitude_reversed_range_is_implausible(ex):
    alt, _ = ex.pick_altitude("svah, 450–420 m n. m.", None)
    assert alt["flags"] == ["ALT_IMPLAUSIBLE"]


# ---------------------------------------------------------------- dates

@pytest.mark.parametrize("text, start, end", [
    ("13. VI. 2014, vedoucí: M. Hroneš", "2014-06-13", "2014-06-13"),
    ("(22. 4. 2017)", "2017-04-22", "2017-04-22"),
    ("7.–9. 6. 2013", "2013-06-07", "2013-06-09"),
    ("13. a 27. 6. 2015", "2015-06-13", "2015-06-27"),
    ("19. 5. 2012 leg. J. Kocián", "2012-05-19", "2012-05-19"),
])
def test_dates_czech(ex, text, start, end):
    d = ex.parse_dates(text)
    assert (d["event_date_start"], d["event_date_end"]) == (start, end)
    for part in d["event_date_verbatim"].split(" | "):
        assert part in text


def test_date_without_year_takes_the_hint(ex):
    d = ex.parse_dates("28. 3.", year_hint=2020)
    assert d["event_date_start"] == "2020-03-28" and d["remarks"]


def test_partial_month_year(ex):
    assert ex.parse_dates("VIII. 1894", partial=True)["event_date_start"] == "1894-08"


def test_impossible_date_is_flagged(ex):
    assert ex.parse_dates("31. 2. 2015")["flags"] == ["DATE_PARSE"]


def test_english_date_day_month_year(ex):                                    # the form EN_DATE reads today
    m = ex.EN_DATE.search("A field trip took place on 29 June 2024.")
    assert m and m.group(0) == "29 June 2024"


# ---------------------------------------------------------------- locality header / grid squares

def test_header_phytochorion_grid_district(ex):
    h = ex.parse_header("76a. Moravská brána vlastní, 6571d, Křtomil (distr. Přerov)")
    assert (h["fytochorion_code"], h["grid_square"], h["municipality"], h["district"]) == \
        (["76a"], "6571d", "Křtomil", "Přerov")


def test_header_district_code(ex):
    h = ex.parse_header("6874a, Valašské Příkazy (VS)")
    assert (h["grid_square"], h["municipality"], h["district"]) == ("6874a", "Valašské Příkazy", "VS")


def test_header_cadastral_area(ex):
    h = ex.parse_header("Loučná nad Desnou (k. ú. Kouty nad Desnou)")
    assert (h["municipality"], h["cadastral_area"]) == ("Loučná nad Desnou", "Kouty nad Desnou")


def test_header_grid_in_brackets(ex):
    h = ex.parse_header("76a. Moravská brána vlastní, distr. Nový Jičín, Štramberk (6474b)")
    assert (h["grid_square"], h["district"], h["municipality"]) == ("6474b", "Nový Jičín", "Štramberk")


@pytest.mark.parametrize("raw, squares", [("6370d/6470b", ["6370d", "6470b"]), ("6270b/d", ["6270b", "6270d"]),
                                          ("6774c/6874a", ["6774c", "6874a"])])
def test_split_grid(ex, raw, squares):
    assert ex.split_grid(raw) == squares


def test_bad_grid_is_flagged(ex):
    assert "GRID_FORMAT" in ex.parse_header("63700, Obec")["flags"]


# ---------------------------------------------------------------- persons

def test_persons_leg_rev_herb(ex):
    p = ex.persons("19. 5. 2012 leg. J. Kocián, rev. J. Chrtek, herb. Jiří Kocián")
    assert p["collected_by"] == ["J. Kocián"] and p["identified_by"] == ["rev. J. Chrtek"]
    assert p["herbarium"] == ["herb. Jiří Kocián"]


def test_persons_foto(ex):
    p = ex.persons("20. V. 2012 foto Z. Mruzíková, rev. M. Dančák")
    assert p["recorded_by"] == ["Z. Mruzíková"] and p["specimen_note"] == ["foto Z. Mruzíková"]


def test_persons_not_without_dot(ex):                                       # QA fix 2026-09-23
    assert ex.persons("7. 6. 2012 not Z. Mruzíková")["recorded_by"] == ["Z. Mruzíková"]


def test_persons_herbarium_acronym_after_name(ex):
    p = ex.persons("12. 6. 2014 leg. M. Hroneš (OL)")
    assert p["collected_by"] == ["M. Hroneš"] and p["herbarium"] == ["OL"]


# ---------------------------------------------------------------- taxon names

def test_taxon_abbreviated_genus(ex, checklist):
    g = ex.GenusMemory()
    ex.parse_taxon("Brachythecium albicans", 67, g, checklist)
    t = ex.parse_taxon("B. rutabulum", 67, g, checklist)
    assert (t.expanded, t.resolved, t.flags) == ("Brachythecium rutabulum", True, ["ABBREV_GENUS"])


def test_taxon_notes_and_brackets(ex, checklist):
    t = ex.parse_taxon("Campylium stellatum (LR-nt) (FMM, VM) [sax]", 67, ex.GenusMemory(), checklist)
    assert t.verbatim == "Campylium stellatum" and t.notes == ["LR-nt", "FMM, VM"] and t.brackets == ["sax"]


def test_taxon_protection_code_dropped(ex, checklist):
    t = ex.parse_taxon("Dactylorhiza majalis [O]", 1, ex.GenusMemory(), checklist)
    assert t.brackets == []


def test_taxon_literature_tail_goes_to_remarks(ex, checklist):
    t = ex.parse_taxon("Agrostis canina – Lit.: Duda & Šula (1964)", 1, ex.GenusMemory(), checklist)
    assert t.verbatim == "Agrostis canina" and t.remarks == ["earlier literature record: Duda & Šula (1964)"]


def test_taxon_qualifier_and_voucher(ex, checklist):
    t = ex.parse_taxon("*Carex cf. hartmanii", 1, ex.GenusMemory(), checklist)
    assert t.voucher and t.qualifier == "cf."


def test_taxon_keeps_agg_period(ex):
    assert ex.strip_final_period("Festuca rubra agg.") == "Festuca rubra agg."
    assert ex.strip_final_period("Chiloscyphus coadunatus.") == "Chiloscyphus coadunatus"


def test_checklist_match_orthography(checklist):
    assert checklist.match("Narcissus poëticus", "vascular_plant")[0] == checklist.match("Narcissus poeticus", "")[0]


def test_classify_notes(ex):
    n = ex.classify_notes(["LC/C4a", "BRNM", "cult.", "LR-nt"])
    assert n["red_list_category"] == ["LC/C4a"] and n["herbarium"] == ["BRNM"] and n["status_note"] == ["cult."]
