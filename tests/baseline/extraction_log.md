# Extraction log

Per-article record counts, the parsing patterns that produced them, and deviations from the rules.

## Parsing rules and deviations (summary)

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

## Per-article counts

### ZMSP2_7-15 — Floristický minikurz na Plumlovsku

- source: `pdf/02/ZMSPCBS_2013-2-7-15.pdf`; section: FLORISTICKÝ MINIKURZ; default record type: species_list
- localities: 9; occurrences: 209
- blocks by pattern: heading→None: 13, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 78, pattern A: locality entry: 9, pattern M: matrix table: 4, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 23

### ZMSP2_16-20 — Jarní aspekt suchomilných trávníků na Plumlovsku (po zavátých stopách Václava Spitznera)

- source: `pdf/02/ZMSPCBS_2013-2-16-20.pdf`; section: EXKURZE; default record type: species_list
- localities: 8; occurrences: 79
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, loc-section paragraph skipped: 2, paragraph skipped (narrative/commentary/caption): 48, pattern A: locality entry: 8, pattern M: matrix table: 2, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 6

### ZMSP2_21-24 — Bryologická exkurze do údolí Černé Ostravice

- source: `pdf/02/ZMSPCBS_2013-2-21-24.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 83
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, loc-section paragraph skipped: 1, paragraph skipped (narrative/commentary/caption): 25, paragraph split into several numbered entries: 1, pattern A: locality entry: 7, pattern M: matrix table: 2, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 5

### ZMSP2_25-28 — Bryologická vycházka aneb za mechorosty do Hostýnských vrchů

- source: `pdf/02/ZMSPCBS_2013-2-25-28.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 62
- blocks by pattern: heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 11, pattern A: locality entry: 5, pattern M: matrix table: 2, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 9

### ZMSP2_42 — Exkurze za poznáním pozdě kvetoucích kruštíků Bílých Karpat a Hlucké pahorkatiny

- source: `pdf/02/ZMSPCBS_2013-2-42.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: paragraph skipped (narrative/commentary/caption): 8
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP2_43-47 — Exkurze za termofilní flórou heřmanické sopky (jedné ze dvou posledních termoaktivních hald na Ostravsku)

- source: `pdf/02/ZMSPCBS_2013-2-43-47.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 141
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 12, pattern A: locality entry: 5, pattern M: matrix table: 3, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 5

### ZMSP2_48-49 — Bryologická exkurze do údolí Šumného a Hraničního potoka v Hrubém Jeseníku

- source: `pdf/02/ZMSPCBS_2013-2-48-49.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 5, species-section paragraph skipped (commentary/signature): 12
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP2_52-53 — Dvě nové lokality jestřábníku dvouklaného (Hieracium bifidum) ve Štramberském krasu

- source: `pdf/02/ZMSPCBS_2013-2-52-53.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 2; occurrences: 2
- blocks by pattern: heading→None: 1, paragraph skipped (narrative/commentary/caption): 9, pattern B: record locality: 2
- flags: none

### ZMSP2_54-55 — Praktické poznámky k určení: kakost nachový (Geranium purpureum)

- source: `pdf/02/ZMSPCBS_2013-2-54-55+vi.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 3, paragraph skipped (narrative/commentary/caption): 15
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP2_56-60 — Gogelova květena okresu Valašskomeziříčského – poznámky k rukopisu

- source: `pdf/02/ZMSPCBS_2013-2-56-60.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 2, heading→species: 1, paragraph skipped (narrative/commentary/caption): 10, species-section paragraph skipped (commentary/signature): 135
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_8-9 — Bryologická exkurze na vápence do okolí Teplic nad Bečvou

- source: `pdf/03/ZMSPCBS_2014-3-8-9.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 71
- blocks by pattern: entry merged with its continuation paragraph: 1, heading→None: 1, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 7, paragraph split into several numbered entries: 1, pattern A: locality entry: 5, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 3
- flags: TAXON_UNMATCHED 9

### ZMSP3_10-12 — Exkurze do botanické zahrady ve Štramberku a okolí

- source: `pdf/03/ZMSPCBS_2014-3-10-12.pdf`; section: EXKURZE; default record type: species_list
- localities: 2; occurrences: 112
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 10, paragraph split into several numbered entries: 1, pattern A: locality entry: 2, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 5

### ZMSP3_13-15 — Exkurze na javornické louky

- source: `pdf/03/ZMSPCBS_2014-3-13-15.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, paragraph skipped (narrative/commentary/caption): 23
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_16-17 — Ohlédnutí se za floristickým minikurzem – Osoblažsko 2013

- source: `pdf/03/ZMSPCBS_2014-3-16-17.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: paragraph skipped (narrative/commentary/caption): 10
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_18-20 — Exkurze „Za skrytými poklady hornického Karvinska“

- source: `pdf/03/ZMSPCBS_2014-3-18-20.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 64
- blocks by pattern: entry merged with its continuation paragraph: 2, heading→None: 1, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 11, paragraph split into several numbered entries: 2, pattern A: locality entry: 9, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 1

### ZMSP3_21-22 — Exkurze za kruštíky do Ždánického lesa

- source: `pdf/03/ZMSPCBS_2014-3-21-22.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, paragraph skipped (narrative/commentary/caption): 11
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_23-26 — Exkurze do Jeseníků

- source: `pdf/03/ZMSPCBS_2014-3-23-26.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 183
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 12, pattern A: species-list paragraph: 16, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 10, LIST_SPLIT 1, MULTI_INTERPRETATION 1

### ZMSP3_27-30 — Za flórou přehradních litorálů – Slezská Harta

- source: `pdf/03/ZMSPCBS_2014-3-27-30.pdf`; section: EXKURZE; default record type: species_list
- localities: 9; occurrences: 183
- blocks by pattern: entry merged with its continuation paragraph: 1, heading→None: 1, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 14, paragraph split into several numbered entries: 1, pattern A: locality entry: 10, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 11, COORD_PARSE 1, LIST_SPLIT 1

### ZMSP3_31-32 — Přednášky na výročním setkání Moravskoslezské pobočky ČBS (2013)

- source: `pdf/03/ZMSPCBS_2014-3-31-32.pdf`; section: PŘEDNÁŠKY; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→records: 6, paragraph skipped (narrative/commentary/caption): 10
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_33 — Determinační setkání – rod Salix

- source: `pdf/03/ZMSPCBS_2014-3-33.pdf`; section: PŘEDNÁŠKY; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: paragraph skipped (narrative/commentary/caption): 7
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_34-38 — Severní svahy vrchu Staškov – floristicky pestrá lokalita Moravskoslezských Beskyd

- source: `pdf/03/ZMSPCBS_2014-3-34-38.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 108
- blocks by pattern: heading→None: 3, heading→records: 3, heading→species: 3, paragraph skipped (narrative/commentary/caption): 46, pattern A: species-list paragraph: 1, pattern B: taxon header: 18, species-section paragraph skipped (commentary/signature): 12
- flags: TAXON_UNMATCHED 2, LOC_DERIVED_FROM_NARRATIVE 1, LIST_SPLIT 1

### ZMSP3_39-46 — Poznámky k rozšíření orchidejí na Osoblažsku

- source: `pdf/03/ZMSPCBS_2014-3-39-46.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 20; occurrences: 23
- blocks by pattern: heading→None: 4, heading→records: 3, paragraph skipped (narrative/commentary/caption): 88, pattern B: record locality: 20, pattern B: taxon header: 13
- flags: LIST_SPLIT 2, GRID_COORD_MISMATCH 1, MULTI_INTERPRETATION 1

### ZMSP3_47-49 — Několik nálezů rozchodníku španělského (Sedum hispanicum) na severovýchodě ČR

- source: `pdf/03/ZMSPCBS_2014-3-47-49.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 15; occurrences: 15
- blocks by pattern: heading→None: 6, paragraph skipped (narrative/commentary/caption): 16, pattern B: record locality: 15
- flags: none

### ZMSP3_50-53 — Výskyt tromínu prorostlého (Smyrnium perfoliatum) v Novém Jičíně

- source: `pdf/03/ZMSPCBS_2014-3-50-53.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 1
- blocks by pattern: heading→None: 3, heading→loc: 1, loc-section paragraph skipped: 3, paragraph skipped (narrative/commentary/caption): 28, pattern B: record locality: 1, pattern B: record of the title taxon: 1
- flags: none

### ZMSP3_54-56 — Invazní mech křivonožka vehnutá (Campylopus introflexus) v Havířově-Prostřední Suché

- source: `pdf/03/ZMSPCBS_2014-3-54-56.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 1
- blocks by pattern: heading→loc: 4, loc-section paragraph skipped: 20, paragraph skipped (narrative/commentary/caption): 7, pattern B: record locality: 1, pattern B: record of the title taxon: 1
- flags: none

### ZMSP3_57-60 — Určování vrb v NPR Praděd (Salix hastata subsp. vegeta, S. silesiaca, S. ×chlorophana)

- source: `pdf/03/ZMSPCBS_2014-3-57-60.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 7, paragraph skipped (narrative/commentary/caption): 25
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3_61-63 — Hledíček pobřežní (Microrrhinum litorale) – výzva ke sledování

- source: `pdf/03/ZMSPCBS_2014-3-61-63.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 12, paragraph skipped (narrative/commentary/caption): 19
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP3P1_3-48 — Výsledky floristického minikurzu Moravskoslezské pobočky ČBS po Osoblažsku (7.–9. června 2013)

- source: `pdf/03-P1/ZMSPCBS_3_P1_1-48.pdf`; section: PŘÍLOHA; default record type: species_list
- localities: 142; occurrences: 2320
- blocks by pattern: heading→None: 27, heading→loc: 7, heading→rltable: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 180, pattern A: locality entry: 142, pattern A: species-list paragraph: 573, species-section paragraph skipped (commentary/signature): 106
- flags: TAXON_UNMATCHED 30, LOC_NUMBER_NOT_FOUND 1

### ZMSP3P2_3-12 — Nálezová databáze Moravskoslezské pobočky ČBS a záznamy rostlin během pilotního projektu

- source: `pdf/03-P2/ZMSPCBS_2014-3-PRILOHA2-FINAL.pdf`; section: PŘÍLOHA; default record type: species_list
- localities: 127; occurrences: 150
- blocks by pattern: heading→None: 7, heading→species: 2, paragraph skipped (narrative/commentary/caption): 29, pattern B: inline-taxon record: 127, pattern B: record locality: 127, species-section paragraph skipped (commentary/signature): 8
- flags: TAXON_UNMATCHED 12, GRID_COORD_MISMATCH 2, COORD_PARSE 1

### ZMSP4_7-10 — Bryologická exkurze do PR Kutaný a PR Halvovský potok ve Vsetínských vrších

- source: `pdf/04/ZMSPCBS_2015-4-7-10.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→species: 5, paragraph skipped (narrative/commentary/caption): 9, species-section paragraph skipped (commentary/signature): 23
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP4_11-13 — Exkurze zaměřená na trávy

- source: `pdf/04/ZMSPCBS_2015-4-11-13.pdf`; section: EXKURZE; default record type: species_list
- localities: 8; occurrences: 81
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 12, pattern A: locality entry: 8, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 7, MULTI_INTERPRETATION 4, COORD_PARSE 1

### ZMSP4_14-18 — Botanika na sjezdovkách

- source: `pdf/04/ZMSPCBS_2015-4-14-18.pdf`; section: EXKURZE; default record type: species_list
- localities: 2; occurrences: 181
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 2, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 12

### ZMSP4_19-21 — Za zbožnou kostelní flórou a hřbitovním kvítím Oderských vrchů

- source: `pdf/04/ZMSPCBS_2015-4-19-21.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 3, paragraph skipped (narrative/commentary/caption): 16
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP4_22-24 — Exkurze „Za vrbami ve středním Pobečví a v Moravskoslezských Beskydech“

- source: `pdf/04/ZMSPCBS_2015-4-22-24.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 33
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 14, paragraph split into several numbered entries: 1, pattern A: locality entry: 6, pattern A: species-list paragraph: 4, species-section paragraph skipped (commentary/signature): 1
- flags: MULTI_INTERPRETATION 4, TAXON_UNMATCHED 1

### ZMSP4_25-27 — Zajímavé a vzácné druhy na výstavě živých hub ve Valašském Meziříčí

- source: `pdf/04/ZMSPCBS_2015-4-25-27.pdf`; section: VÝSTAVY; default record type: species_list
- localities: 9; occurrences: 274
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 15, pattern A: locality entry: 9, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 47, MULTI_INTERPRETATION 11

### ZMSP4_28-32 — Je dymnivka nízká (Corydalis pumila) součástí květeny Severomoravského kraje?

- source: `pdf/04/ZMSPCBS_2015-4-28-32.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, heading→loc: 8, heading→records: 12, loc-section paragraph skipped: 16, paragraph skipped (narrative/commentary/caption): 15
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP4_33-36 — Troskut prstnatý (Cynodon dactylon) v Ostravě

- source: `pdf/04/ZMSPCBS_2015-4-33-36.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 1
- blocks by pattern: heading→None: 2, heading→loc: 3, loc-section paragraph skipped: 20, paragraph skipped (narrative/commentary/caption): 7, pattern B: record locality: 1, pattern B: record of the title taxon: 1
- flags: none

### ZMSP4_37-38 — Lilík mochyňovitý (Nicandra physalodes) – zajímavý plevel na Novojičínsku

- source: `pdf/04/ZMSPCBS_2015-4-37-38.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 1
- blocks by pattern: heading→loc: 5, loc-section paragraph skipped: 10, paragraph skipped (narrative/commentary/caption): 6, pattern B: record locality: 1, pattern B: record of the title taxon: 1
- flags: none

### ZMSP4_39-42 — Okruh kamejky rolní (Buglossoides arvensis agg.) – výzva ke sledování

- source: `pdf/04/ZMSPCBS_2015-4-39-42.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, heading→records: 10, paragraph skipped (narrative/commentary/caption): 35, pattern B: taxon header: 1
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP4_43-49 — Herbář Viktora Navrátila v Muzeu regionu Valašsko

- source: `pdf/04/ZMSPCBS_2015-4-43-49.pdf`; section: FLORISTIKA; default record type: herbarium_revision
- localities: 59; occurrences: 59
- blocks by pattern: heading→None: 1, heading→records: 4, paragraph skipped (narrative/commentary/caption): 36, pattern B: taxon header: 5, pattern H: herbarium table: 4
- flags: TAXON_UNMATCHED 9

### ZMSP4P2_3-48 — Výsledky floristického minikurzu Moravskoslezské pobočky ČBS Horní Lideč (13.–15. června 2014)

- source: `pdf/04-P2/ZMSPCBS_4_P2_1-48_WEB.pdf`; section: PŘÍLOHA; default record type: species_list
- localities: 136; occurrences: 4668
- blocks by pattern: heading→None: 33, heading→loc: 5, heading→species: 1, loc-section paragraph skipped: 1, paragraph skipped (narrative/commentary/caption): 142, pattern A: locality entry: 136, pattern A: species-list paragraph: 740, species-section paragraph skipped (commentary/signature): 51
- flags: TAXON_UNMATCHED 23, COORD_PARSE 1, MULTI_INTERPRETATION 1, ALT_IMPLAUSIBLE 1, GRID_FORMAT 1, GRID_COORD_MISMATCH 1

### ZMSP5_11-14 — Bryologická exkurze do PR Klenov ve Vsetínských vrších

- source: `pdf/05/ZMSPCBS_2016-5-11-14.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 188
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 5, paragraph skipped (narrative/commentary/caption): 40, pattern A: locality entry: 4, pattern A: species-list paragraph: 42, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 14, DUPLICATE 9, LIST_SPLIT 1

### ZMSP5_15-17 — Exkurze do PR Obřany v Hostýnských vrších

- source: `pdf/05/ZMSPCBS_2016-5-15-17.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 59
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 13, pattern A: locality entry: 5, pattern A: species-list paragraph: 13, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 1

### ZMSP5_18-19 — Exkurze do Hranického krasu

- source: `pdf/05/ZMSPCBS_2016-5-18-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 2, paragraph skipped (narrative/commentary/caption): 10
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP5_20-26 — Mokřadní exkurze na Vidnavské mokřiny a Zábřežské louky

- source: `pdf/05/ZMSPCBS_2016-5-20-26.pdf`; section: EXKURZE; default record type: species_list
- localities: 2; occurrences: 218
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 28, pattern A: locality entry: 2, pattern A: species-list paragraph: 29, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 4

### ZMSP5_27-32 — Exkurze na rašelinné biotopy Moravskoslovenského pomezí

- source: `pdf/05/ZMSPCBS_2016-5-27-32.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 139
- blocks by pattern: heading→None: 8, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 35, pattern A: locality entry: 7, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 5, ALT_IMPLAUSIBLE 2, MULTI_INTERPRETATION 1

### ZMSP5_33-36 — Ve stopách Kiliánových – potoky Slezských Beskyd

- source: `pdf/05/ZMSPCBS_2016-5-33-36.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 171
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 15, pattern A: locality entry: 7, pattern A: species-list paragraph: 23, species-section paragraph skipped (commentary/signature): 3
- flags: TAXON_UNMATCHED 5, MULTI_INTERPRETATION 1

### ZMSP5_37-42 — Exkurze řekou Morávkou

- source: `pdf/05/ZMSPCBS_2016-5-37-42.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 133
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 28, pattern A: locality entry: 6, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 4, MULTI_INTERPRETATION 3, COORD_PARSE 1, ALT_IMPLAUSIBLE 1

### ZMSP5_43-46 — Mykologická exkurze v obci Bílá

- source: `pdf/05/ZMSPCBS_2016-5-43-46.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 72
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 1, paragraph skipped (narrative/commentary/caption): 10, pattern A: locality entry: 6, pattern A: species-list paragraph: 13, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 4, MULTI_INTERPRETATION 1

### ZMSP5_47-54 — Rod kuřinka (Spergularia) – výzva ke sledování

- source: `pdf/05/ZMSPCBS_2016-5-47-54.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→records: 23, paragraph skipped (narrative/commentary/caption): 38, pattern B: taxon header: 1
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP5_55-59 — Herbář Vladimíra Kajdoše v Muzeu Novojičínska

- source: `pdf/05/ZMSPCBS_2016-5-55-59.pdf`; section: FLORISTIKA; default record type: herbarium_revision
- localities: 47; occurrences: 47
- blocks by pattern: heading→None: 3, paragraph skipped (narrative/commentary/caption): 48, pattern H: herbarium table: 2
- flags: TAXON_UNMATCHED 1

### ZMSP6_11-14 — Exkurze do lužního lesa u Olomouce

- source: `pdf/06/ZMSPCBS_2017-6-11-14.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 206
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 5, pattern A: species-list paragraph: 28, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 4, MULTI_INTERPRETATION 1

### ZMSP6_15-19 — Floristická exkurze po vápencových ostrůvcích mezi Ostružnou a Brannou

- source: `pdf/06/ZMSPCBS_2017-6-15-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 154
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 5, pattern A: species-list paragraph: 31, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 6, MULTI_INTERPRETATION 3

### ZMSP6_20-24 — Exkurze do Grygovských kopců a Tršické pahorkatiny

- source: `pdf/06/ZMSPCBS_2017-6-20-24.pdf`; section: EXKURZE; default record type: species_list
- localities: 11; occurrences: 178
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 11, pattern A: species-list paragraph: 27, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 6, COORD_PARSE 1, MULTI_INTERPRETATION 1

### ZMSP6_25-29 — Exkurze do okolí Hlinska pod Hostýnem a Holešova

- source: `pdf/06/ZMSPCBS_2017-6-25-29.pdf`; section: EXKURZE; default record type: species_list
- localities: 11; occurrences: 220
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 11, pattern A: species-list paragraph: 30, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 4

### ZMSP6_30-33 — Exkurze po železnici a jejím okolí mezi Olomoucí a Nezamyslicemi

- source: `pdf/06/ZMSPCBS_2017-6-30-33.pdf`; section: EXKURZE; default record type: species_list
- localities: 9; occurrences: 99
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 9, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 1

### ZMSP6_34-38 — Exkurze za teplomilnou květenou Beskyd

- source: `pdf/06/ZMSPCBS_2017-6-34-38.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 310
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 23, pattern A: locality entry: 5, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 17, ALT_IMPLAUSIBLE 1, LIST_SPLIT 1

### ZMSP6_39-42 — Exkurze na hadce v okolí Raškova a Rudy nad Moravou

- source: `pdf/06/ZMSPCBS_2017-6-39-42.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 112
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 3, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 2
- flags: MULTI_INTERPRETATION 1, TAXON_UNMATCHED 1

### ZMSP6_43-47 — Bryologická exkurze do PP Lúčky-Roveňky a PP Růžděcký Vesník ve Vsetínských vrších

- source: `pdf/06/ZMSPCBS_2017-6-43-47.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 88
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 25, pattern A: locality entry: 5, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 5

### ZMSP6_48-51 — Nález kruštíku uherského (Epipactis tallosii) na Opavsku

- source: `pdf/06/ZMSPCBS_2017-6-48-51.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 3; occurrences: 5
- blocks by pattern: heading→None: 8, heading→records: 2, paragraph skipped (narrative/commentary/caption): 25, pattern B: record locality: 3, pattern B: taxon header: 2
- flags: none

### ZMSP6_52-55 — Další výskyty velbloudníku tenkokřídlého (Corispermum pallasii) v prodejnách písku na severní Moravě

- source: `pdf/06/ZMSPCBS_2017-6-52-55.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 4; occurrences: 5
- blocks by pattern: heading→None: 5, heading→records: 6, paragraph skipped (narrative/commentary/caption): 24, pattern B: record locality: 4
- flags: none

### ZMSP6_56-60 — Válečka skalní (Brachypodium rupestre) – výzva ke sledování

- source: `pdf/06/ZMSPCBS_2017-6-56-60.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 5, heading→records: 9, paragraph skipped (narrative/commentary/caption): 29
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP7_11-14 — Exkurze za jarním aspektem na Skaličku

- source: `pdf/07/ZMSP_2018-7-11-14.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 113
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 6, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 1
- flags: none

### ZMSP7_15-19 — Exkurze z Přerova-Předmostí po stopách mamutů do Lhotky

- source: `pdf/07/ZMSP_2018-7-15-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 201
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 12, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 6, ALT_IMPLAUSIBLE 1

### ZMSP7_20-24 — Exkurze údolím Bystřice u Moravského Berouna

- source: `pdf/07/ZMSP_2018-7-20-24.pdf`; section: EXKURZE; default record type: species_list
- localities: 13; occurrences: 158
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 17, pattern A: locality entry: 13, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 2

### ZMSP7_25-28 — Sjezdovky a sihly pod Lysou horou – floristicko-bryologická exkurze

- source: `pdf/07/ZMSP_2018-7-25-28.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 176
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 4, pattern A: species-list paragraph: 28, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 3, MULTI_INTERPRETATION 1, COORD_SEGMENT_LONG 1

### ZMSP7_29-33 — Lichenologická a bryologická exkurze na Kelčský Javorník v Hostýnských vrších

- source: `pdf/07/ZMSP_2018-7-29-33.pdf`; section: EXKURZE; default record type: species_list
- localities: 2; occurrences: 108
- blocks by pattern: heading→None: 4, heading→loc: 2, heading→species: 4, paragraph skipped (narrative/commentary/caption): 24, pattern A: locality entry: 2, pattern A: species-list paragraph: 39, species-section paragraph skipped (commentary/signature): 3
- flags: TAXON_UNMATCHED 5

### ZMSP7_34-37 — Smilkové pastviny na hřebeni Radhoště

- source: `pdf/07/ZMSP_2018-7-34-37.pdf`; section: EXKURZE; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 1, heading→records: 3, paragraph skipped (narrative/commentary/caption): 21
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP7_38-40 — Exkurze po historických lokalitách Spiranthes spiralis na Vsetínsku

- source: `pdf/07/ZMSP_2018-7-38-40.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 24
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→records: 3, heading→species: 2, paragraph skipped (narrative/commentary/caption): 17, pattern A: locality entry: 4, pattern A: species-list paragraph: 10, species-section paragraph skipped (commentary/signature): 1
- flags: TAXON_UNMATCHED 1

### ZMSP7_41-44 — Bryologická exkurze na vápencové skály u Černotína

- source: `pdf/07/ZMSP_2018-7-41-44.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 86
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 5, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 2
- flags: TAXON_UNMATCHED 4

### ZMSP7_45-54 — Vzácnější druhy plevelů Metylovic a okolí

- source: `pdf/07/ZMSP_2018-7-45-54.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 21; occurrences: 21
- blocks by pattern: heading→None: 6, heading→records: 6, paragraph skipped (narrative/commentary/caption): 64, pattern B: record locality: 21, pattern B: taxon header: 9
- flags: TAXON_UNMATCHED 2

### ZMSP7_55-60 — Za ruderálními pampeliškami (Taraxacum sect. Taraxacum) na Novojičínsku

- source: `pdf/07/ZMSP_2018-7-55-60.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 5; occurrences: 110
- blocks by pattern: heading→None: 9, heading→records: 2, paragraph skipped (narrative/commentary/caption): 36, pattern A3: locality-first list: 5, pattern A: species-list paragraph: 5
- flags: ABBREV_GENUS 105, TAXON_UNMATCHED 5

### ZMSP7_61-65 — Poznámky k některým zástupcům rodu kruštík ve Štramberku a okolí

- source: `pdf/07/ZMSP_2018-7-61-65.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 7; occurrences: 14
- blocks by pattern: heading→None: 5, heading→records: 6, paragraph skipped (narrative/commentary/caption): 33, pattern A3: locality-first list: 6, pattern A: species-list paragraph: 6, pattern B: record locality: 1
- flags: ABBREV_GENUS 7, MULTI_INTERPRETATION 1

### ZMSP7_66-69 — Mechorosty okolí řeky Bečvy mezi obcemi Choryně a Špičky

- source: `pdf/07/ZMSP_2018-7-66-69.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 5; occurrences: 5
- blocks by pattern: heading→None: 5, heading→records: 1, paragraph skipped (narrative/commentary/caption): 42, pattern B: record locality: 5
- flags: MULTI_INTERPRETATION 5, COORD_SEGMENT_LONG 1

### ZMSP7_70-75 — Bryologický herbář Jana Vrány

- source: `pdf/07/ZMSP_2018-7-70-75.pdf`; section: FLORISTIKA; default record type: herbarium_revision
- localities: 50; occurrences: 184
- blocks by pattern: heading→None: 8, heading→loc: 1, heading→species: 2, loc-section paragraph skipped: 2, numbered locality list without heading: 1, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 50, pattern A: species-list paragraph: 16
- flags: ABBREV_GENUS 29, TAXON_UNMATCHED 11

### ZMSP8_11-13 — Lichenologická exkurze po vápencových ostrůvcích mezi Ostružnou a Brannou

- source: `pdf/08/ZMSPCBS_2019-8-11-13.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 80
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 17, pattern A: locality entry: 4, pattern A: species-list paragraph: 13, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 23, TAXON_UNMATCHED 20

### ZMSP8_14-19 — Exkurze za masožravou rosnatkou okrouhlolistou do přírodní památky Kamenec u Frýdku-Místku

- source: `pdf/08/ZMSPCBS_2019-8-14-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 423
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→records: 2, heading→species: 4, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 4, pattern A: species-list paragraph: 31, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 132, TAXON_UNMATCHED 13, COORD_PARSE 1

### ZMSP8_20-23 — Exkurze po východních svazích Velkého Kosíře

- source: `pdf/08/ZMSPCBS_2019-8-20-23.pdf`; section: EXKURZE; default record type: species_list
- localities: 8; occurrences: 177
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 8, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 55, TAXON_UNMATCHED 7

### ZMSP8_24-28 — Exkurze do nejsevernějšího výběžku Tršické pahorkatiny

- source: `pdf/08/ZMSPCBS_2019-8-24-28.pdf`; section: EXKURZE; default record type: species_list
- localities: 16; occurrences: 234
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 16, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 86, TAXON_UNMATCHED 8, COORD_SEGMENT_LONG 1, MULTI_INTERPRETATION 1

### ZMSP8_29-33 — Exkurze na Slunečnou, nejvyšší vrchol Nízkého Jeseníku

- source: `pdf/08/ZMSPCBS_2019-8-29-33.pdf`; section: EXKURZE; default record type: species_list
- localities: 13; occurrences: 238
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 13, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 82, TAXON_UNMATCHED 5, MULTI_INTERPRETATION 2

### ZMSP8_34-39 — Údolím řeky Mohelnice – floristicko-bryologická exkurze

- source: `pdf/08/ZMSPCBS_2019-8-34-39.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 204
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 5, paragraph skipped (narrative/commentary/caption): 24, pattern A: locality entry: 7, pattern A: species-list paragraph: 44, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 40, TAXON_UNMATCHED 16, MULTI_INTERPRETATION 7

### ZMSP8_40-42 — Bryologická exkurze na nejvyšší vrchol Vsetínských vrchů

- source: `pdf/08/ZMSPCBS_2019-8-40-42.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 56
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 3, pattern A: species-list paragraph: 16, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 14, TAXON_UNMATCHED 9, MULTI_INTERPRETATION 1

### ZMSP8_43-47 — Mykologická exkurze v Moravskoslezských Beskydech: Bílá – Staré Hamry

- source: `pdf/08/ZMSPCBS_2019-8-43-47.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 160
- blocks by pattern: heading→None: 6, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 7, pattern A: species-list paragraph: 16, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 75, TAXON_UNMATCHED 15, MULTI_INTERPRETATION 2

### ZMSP8_48-53 — Poznámky k výskytu plevelů na Novojičínsku 1. Xanthium strumarium a X. albinum

- source: `pdf/08/ZMSPCBS_2019-8-48-53.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 5; occurrences: 5
- blocks by pattern: heading→None: 8, heading→records: 5, paragraph skipped (narrative/commentary/caption): 34, pattern B: record locality: 5, pattern B: taxon header: 2
- flags: none

### ZMSP8_54-57 — Poznámky k výskytu plevelů na Novojičínsku 2. Datura stramonium

- source: `pdf/08/ZMSPCBS_2019-8-54-57.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 2; occurrences: 2
- blocks by pattern: heading→None: 4, heading→records: 6, paragraph skipped (narrative/commentary/caption): 25, pattern B: record locality: 2, pattern B: taxon header: 3
- flags: none

### ZMSP8_58-60 — Nález šikouška bezlistého (Buxbaumia aphylla) ve Veřovických vrších

- source: `pdf/08/ZMSPCBS_2019-8-58-60.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 1
- blocks by pattern: heading→None: 7, heading→records: 2, paragraph skipped (narrative/commentary/caption): 27, pattern B: record locality: 1
- flags: none

### ZMSP9_11-13 — Bryologická exkurze do přírodní památky Bludný u Chvalčova v Hostýnských vrších

- source: `pdf/09/ZMSPCBS_2020-9-11-13.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 95
- blocks by pattern: heading→None: 2, heading→loc: 3, heading→species: 3, loc-section paragraph skipped: 1, paragraph skipped (narrative/commentary/caption): 14, pattern A: locality entry: 4, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 21, MULTI_INTERPRETATION 6, TAXON_UNMATCHED 5, ALT_IMPLAUSIBLE 1

### ZMSP9_14-19 — Exkurze za orchidejemi do Kateřinic

- source: `pdf/09/ZMSPCBS_2020-9-14-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 286
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 25, pattern A: locality entry: 6, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 116, TAXON_UNMATCHED 15, MULTI_INTERPRETATION 7, LOC_NUMBER_NOT_FOUND 3

### ZMSP9_20-23 — Vycházka za lišejníky a mechorosty do pohoří Králického Sněžníku

- source: `pdf/09/ZMSPCBS_2020-9-20-23.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 205
- blocks by pattern: heading→None: 2, heading→loc: 3, heading→species: 4, loc-section paragraph skipped: 1, paragraph skipped (narrative/commentary/caption): 12, pattern A: locality entry: 7, pattern A: species-list paragraph: 28, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 69, TAXON_UNMATCHED 11, MULTI_INTERPRETATION 1

### ZMSP9_24-28 — Exkurze do nejvýchodnějšího výběžku Tršické pahorkatiny

- source: `pdf/09/ZMSPCBS_2020-9-24-28.pdf`; section: EXKURZE; default record type: species_list
- localities: 13; occurrences: 177
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 21, pattern A: locality entry: 13, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 53, TAXON_UNMATCHED 3, GRID_COORD_MISMATCH 1

### ZMSP9_29-33 — Exkurze po zajímavých bezlesých enklávách aneb Z bláta do louže kolem Smradlavé

- source: `pdf/09/ZMSPCBS_2020-9-29-33.pdf`; section: EXKURZE; default record type: species_list
- localities: 8; occurrences: 183
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 26, pattern A: locality entry: 8, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 59, AMBIGUOUS 11, GRID_COORD_MISMATCH 6, TAXON_UNMATCHED 4, MULTI_INTERPRETATION 1

### ZMSP9_34-39 — Exkurze na Ondřejník

- source: `pdf/09/ZMSPCBS_2020-9-34-39.pdf`; section: EXKURZE; default record type: species_list
- localities: 10; occurrences: 502
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 28, pattern A: locality entry: 10, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 127, TAXON_UNMATCHED 35, LIST_SPLIT 9, COORD_SEGMENT_LONG 1

### ZMSP9_40-44 — Exkurze do údolí potoka Bělidlo u Domašova nad Bystřicí

- source: `pdf/09/ZMSPCBS_2020-9-40-44.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 242
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 12, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 91, TAXON_UNMATCHED 8, MULTI_INTERPRETATION 2

### ZMSP9_45-49 — Mykologická exkurze v Oderských vrších

- source: `pdf/09/ZMSPCBS_2020-9-45-49.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 226
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 3, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 89, TAXON_UNMATCHED 23, AMBIGUOUS 1

### ZMSP9_50-53 — Bryologická exkurze na Starojický kopec

- source: `pdf/09/ZMSPCBS_2020-9-50-53.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 48
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 3, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 12, TAXON_UNMATCHED 4, MULTI_INTERPRETATION 2

### ZMSP9_54-61 — Zajímavá upolínová louka u Slavkova v Oderských vrších

- source: `pdf/09/ZMSPCBS_2020-9-54-61.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 1; occurrences: 147
- blocks by pattern: heading→None: 7, heading→records: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 42, pattern A: species-list paragraph: 3, species-section paragraph skipped (commentary/signature): 33
- flags: ABBREV_GENUS 35, TAXON_UNMATCHED 10, DUPLICATE 2, AMBIGUOUS 2, LOC_DERIVED_FROM_NARRATIVE 1, LIST_SPLIT 1

### ZMSP9_62-72 — Příspěvek k poznání zajímavých polních plevelů Osoblažska – II

- source: `pdf/09/ZMSPCBS_2020-9-62-72.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 46; occurrences: 51
- blocks by pattern: heading→None: 5, heading→records: 7, paragraph skipped (narrative/commentary/caption): 52, pattern B: record locality: 46, pattern B: taxon header: 15
- flags: LIST_SPLIT 2, MULTI_INTERPRETATION 1

### ZMSP9_73-76 — Poznámky k rozšíření některých vzácnějších druhů na Osoblažsku aneb běžné druhy ne tak běžnými

- source: `pdf/09/ZMSPCBS_2020-9-73-76.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 4; occurrences: 5
- blocks by pattern: heading→None: 5, heading→records: 2, paragraph skipped (narrative/commentary/caption): 29, pattern B: record locality: 4, pattern B: taxon header: 4
- flags: none

### ZMSP10_24-28 — Exkurze do Tršické pahorkatiny v okolí Velkého Újezda

- source: `pdf/10/ZMSPCBS_2021-10-24-28.pdf`; section: –; default record type: species_list
- localities: 14; occurrences: 208
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 23, pattern A: locality entry: 14, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 73, TAXON_UNMATCHED 3, LIST_SPLIT 2, MULTI_INTERPRETATION 2

### ZMSP10_29-32 — Exkurze na louky Filena u Záhlinických rybníků

- source: `pdf/10/ZMSPCBS_2021-10-29-32.pdf`; section: –; default record type: species_list
- localities: 7; occurrences: 72
- blocks by pattern: heading→None: 2, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 7, pattern A: species-list paragraph: 6, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 14, TAXON_UNMATCHED 5, MULTI_INTERPRETATION 3

### ZMSP10_33-38 — Kukačka aneb Exkurze do lomu za léčebnou

- source: `pdf/10/ZMSPCBS_2021-10-33-38.pdf`; section: –; default record type: species_list
- localities: 9; occurrences: 209
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 26, pattern A: locality entry: 9, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 51, TAXON_UNMATCHED 4, LIST_SPLIT 3, MULTI_INTERPRETATION 2

### ZMSP10_39-42 — Bryologická exkurze do údolí potoka Trubiska

- source: `pdf/10/ZMSPCBS_2021-10-39-42.pdf`; section: –; default record type: species_list
- localities: 3; occurrences: 61
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 19, pattern A: locality entry: 3, pattern A: species-list paragraph: 13, species-section paragraph skipped (commentary/signature): 4
- flags: ABBREV_GENUS 14, TAXON_UNMATCHED 7

### ZMSP10_43-52 — Poznámky k rozšíření některých vzácnějších druhů na Osoblažsku II

- source: `pdf/10/ZMSPCBS_2021-10-43-52.pdf`; section: –; default record type: species_list
- localities: 23; occurrences: 28
- blocks by pattern: heading→None: 5, heading→records: 5, paragraph skipped (narrative/commentary/caption): 66, pattern B: record locality: 23, pattern B: taxon header: 7
- flags: GRID_COORD_MISMATCH 2

### ZMSP10_53-63 — Zajímavé druhy železniční květeny na Jesenicku

- source: `pdf/10/ZMSPCBS_2021-10-53-63.pdf`; section: –; default record type: species_list
- localities: 22; occurrences: 34
- blocks by pattern: heading→None: 6, heading→loc: 1, heading→records: 6, paragraph skipped (narrative/commentary/caption): 67, pattern A2: name-keyed records: 6, pattern A: locality entry: 22, pattern B: taxon header: 5
- flags: none

### ZMSP11_22-27 — Exkurze na Hradisko

- source: `pdf/11/ZMSPCBS_2022-11-22-27.pdf`; section: EXKURZE; default record type: species_list
- localities: 8; occurrences: 216
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 24, pattern A: locality entry: 8, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 44, TAXON_UNMATCHED 1, MULTI_INTERPRETATION 1

### ZMSP11_28-32 — Exkurze mokřadními loukami Nízkého Jeseníku mezi Ondrášovem a Domašovem nad Bystřicí

- source: `pdf/11/ZMSPCBS_2022-11-28-32.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 196
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 16, pattern A: locality entry: 12, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 68, GRID_COORD_MISMATCH 1, TAXON_UNMATCHED 1

### ZMSP11_33-38 — Bryologická exkurze za rašeliníky do osady Hutě ve Starých Hamrech

- source: `pdf/11/ZMSPCBS_2022-11-33-38.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 299
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 27, pattern A: locality entry: 4, pattern A: species-list paragraph: 39, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 87, TAXON_UNMATCHED 17, AMBIGUOUS 13, GRID_COORD_MISMATCH 1, LIST_SPLIT 1

### ZMSP11_39-42 — Bryologická exkurze do přírodní rezervace Smrdutá u Chvalčova v Hostýnských vrších

- source: `pdf/11/ZMSPCBS_2022-11-39-42.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 82
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 4, pattern A: species-list paragraph: 21, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 18, TAXON_UNMATCHED 4, MULTI_INTERPRETATION 2, ALT_IMPLAUSIBLE 1, GRID_COORD_MISMATCH 1

### ZMSP11_43-46 — Mykologická exkurze na Skalickou Strážnici, Vrchy a do údolí Morávky

- source: `pdf/11/ZMSPCBS_2022-11-43-46.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 105
- blocks by pattern: heading→None: 6, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 13, pattern A: locality entry: 3, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 42, TAXON_UNMATCHED 6, LOC_NUMBER_NOT_FOUND 2, GRID_COORD_MISMATCH 1, COORD_SEGMENT_LONG 1

### ZMSP11_47-50 — Mykologická exkurze do okolí osady Samčanka

- source: `pdf/11/ZMSPCBS_2022-11-47-50.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 225
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, loc-section paragraph skipped: 1, paragraph skipped (narrative/commentary/caption): 12, pattern A: locality entry: 5, pattern A: species-list paragraph: 15, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 116, TAXON_UNMATCHED 28, GRID_COORD_MISMATCH 2, MULTI_INTERPRETATION 2

### ZMSP11_51-62 — Zajímavé druhy železniční květeny na Jesenicku – II

- source: `pdf/11/ZMSPCBS_2022-11-51-62.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 33; occurrences: 33
- blocks by pattern: heading→None: 6, heading→records: 4, paragraph skipped (narrative/commentary/caption): 70, pattern B: record locality: 33, pattern B: taxon header: 7
- flags: none

### ZMSP11_63-72 — Dvě exotické liány na Těšínsku

- source: `pdf/11/ZMSPCBS_2022-11-63-72.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 5; occurrences: 8
- blocks by pattern: heading→None: 7, heading→records: 11, paragraph skipped (narrative/commentary/caption): 57, pattern B: record locality: 5
- flags: none

### ZMSP12_11-14 — Bryologická exkurze do okolí Štramberka

- source: `pdf/12/ZMSPCBS_2023-12-11-14.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 70
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 23, pattern A: locality entry: 4, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 12, TAXON_UNMATCHED 4

### ZMSP12_15-19 — Vycházka (nejen) za prstnatci bezovými na Osoblažsko

- source: `pdf/12/ZMSPCBS_2023-12-15-19.pdf`; section: EXKURZE; default record type: species_list
- localities: 16; occurrences: 192
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 15, pattern A: locality entry: 16, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 45, TAXON_UNMATCHED 5, MULTI_INTERPRETATION 3

### ZMSP12_20-24 — Krajinou sopek Nízkého Jeseníku – exkurze na Velký a Malý Roudný

- source: `pdf/12/ZMSPCBS_2023-12-20-24.pdf`; section: EXKURZE; default record type: species_list
- localities: 11; occurrences: 195
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 11, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 68, MULTI_INTERPRETATION 3, TAXON_UNMATCHED 2, ALT_IMPLAUSIBLE 1

### ZMSP12_25-30 — Exkurze Kytičky osady Hraničky

- source: `pdf/12/ZMSPCBS_2023-12-25-30.pdf`; section: EXKURZE; default record type: species_list
- localities: 10; occurrences: 217
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 10, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 81, LOC_NUMBER_NOT_FOUND 10, LOC_UNUSED 1, TAXON_UNMATCHED 1

### ZMSP12_31-36 — Exkurze za historickými lokalitami vstavače osmahlého (Neotinea ustulata)

- source: `pdf/12/ZMSPCBS_2023-12-31-36.pdf`; section: EXKURZE; default record type: species_list
- localities: 15; occurrences: 186
- blocks by pattern: heading→None: 1, heading→loc: 1, heading→records: 4, heading→species: 3, paragraph skipped (narrative/commentary/caption): 24, pattern A: locality entry: 15, pattern A: species-list paragraph: 27, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 41, TAXON_UNMATCHED 25, LIST_SPLIT 1

### ZMSP12_37-41 — Bryologická exkurze do údolí potoka Mazák v Ostravici

- source: `pdf/12/ZMSPCBS_2023-12-37-41.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 233
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 3, pattern A: species-list paragraph: 45, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 42, TAXON_UNMATCHED 6, GRID_COORD_MISMATCH 1

### ZMSP12_42-45 — Mykologická exkurze do okolí osady Jamník

- source: `pdf/12/ZMSPCBS_2023-12-42-45.pdf`; section: EXKURZE; default record type: species_list
- localities: 4; occurrences: 70
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 14, pattern A: locality entry: 4, pattern A: species-list paragraph: 9, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 24, TAXON_UNMATCHED 13, MULTI_INTERPRETATION 3

### ZMSP12_46-50 — Mykologická exkurze Palkovickými hůrkami

- source: `pdf/12/ZMSPCBS_2023-12-46-50.pdf`; section: EXKURZE; default record type: species_list
- localities: 7; occurrences: 102
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 17, pattern A: locality entry: 7, pattern A: species-list paragraph: 14, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 51, TAXON_UNMATCHED 14, MULTI_INTERPRETATION 2

### ZMSP12_51-62 — Stoletý příběh ostřice Otrubovy (Carex otrubae Podp.)

- source: `pdf/12/ZMSPCBS_2023-12-51-62.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 0; occurrences: 0
- blocks by pattern: heading→None: 16, heading→records: 1, paragraph skipped (narrative/commentary/caption): 71
- flags: none
- no records: narrative-only article (nothing excerpted, checkpoint 1 Q13)

### ZMSP13_11-16 — Exkurze do žulovských luhů a hájů

- source: `pdf/13/ZMSPCBS_2024-13_11-16.pdf`; section: EXKURZE; default record type: species_list
- localities: 9; occurrences: 220
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 21, pattern A: locality entry: 9, pattern A: species-list paragraph: 17, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 63, MULTI_INTERPRETATION 1

### ZMSP13_17-21 — Bryologická exkurze na rašelinné louky Beskyd

- source: `pdf/13/ZMSPCBS_2024-13_17-21.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 228
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 6, pattern A: species-list paragraph: 33, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 81, TAXON_UNMATCHED 12, MULTI_INTERPRETATION 1

### ZMSP13_22-25 — Exkurze za pozdně jarní květenou lesa Ochozy u Bystřice pod Hostýnem

- source: `pdf/13/ZMSPCBS_2024-13_22-25.pdf`; section: EXKURZE; default record type: species_list
- localities: 9; occurrences: 169
- blocks by pattern: heading→None: 3, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 15, pattern A: locality entry: 9, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 60, GRID_COORD_MISMATCH 3, TAXON_UNMATCHED 2

### ZMSP13_26-31 — Exkurze z Hané až na Makču Pikču

- source: `pdf/13/ZMSPCBS_2024-13_26-31.pdf`; section: EXKURZE; default record type: species_list
- localities: 11; occurrences: 197
- blocks by pattern: heading→None: 7, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 11, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 55, TAXON_UNMATCHED 1

### ZMSP13_32-39 — Strastiplné vlastivědné putování za květenou Beskyd moravských k připomenutí stého výročí úmrtí pátera Františka Gogely

- source: `pdf/13/ZMSPCBS_2024-13_32-39.pdf`; section: EXKURZE; default record type: species_list
- localities: 29; occurrences: 227
- blocks by pattern: heading→None: 8, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 29, pattern A: locality entry: 29, pattern A: species-list paragraph: 18, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 60, MULTI_INTERPRETATION 1, TAXON_UNMATCHED 1

### ZMSP13_40-45 — Mykologické exkurze do údolí Černé Ostravice a lesa Rovňa

- source: `pdf/13/ZMSPCBS_2024-13_40-45.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 199
- blocks by pattern: heading→None: 5, heading→loc: 2, heading→species: 4, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 5, pattern A: species-list paragraph: 26, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 98, TAXON_UNMATCHED 32, DUPLICATE 2

### ZMSP13_46-49 — Bryologická exkurze do přírodní rezervace Suchá Dora u Jakubčovic nad Odrou (Nízký Jeseník)

- source: `pdf/13/ZMSPCBS_2024-13_46-49.pdf`; section: EXKURZE; default record type: species_list
- localities: 1; occurrences: 52
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 1, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 18, TAXON_UNMATCHED 2

### ZMSP14_11-16 — Cestou necestou do Podbeskydí za pampeliškami nejen sekce Taraxacum

- source: `pdf/14/ZMSPCBS_2025-14_11-16.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 151
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 12, pattern A: species-list paragraph: 15, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 116, TAXON_UNMATCHED 2

### ZMSP14_17-22 — Exkurze do údolí Javorné u Zlatých Hor

- source: `pdf/14/ZMSPCBS_2025-14_17-22.pdf`; section: EXKURZE; default record type: species_list
- localities: 6; occurrences: 247
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 27, pattern A: locality entry: 6, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 74

### ZMSP14_23-27 — Copak roste v Hnojicích?

- source: `pdf/14/ZMSPCBS_2025-14_23-27.pdf`; section: EXKURZE; default record type: species_list
- localities: 12; occurrences: 161
- blocks by pattern: heading→None: 6, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 18, pattern A: locality entry: 12, pattern A: species-list paragraph: 19, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 54, TAXON_UNMATCHED 3

### ZMSP14_28-33 — Exkurze jižním okrajem CHKO Jeseníky na Přemyslovské sedlo

- source: `pdf/14/ZMSPCBS_2025-14_28-33.pdf`; section: EXKURZE; default record type: species_list
- localities: 5; occurrences: 217
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 21, pattern A: locality entry: 5, pattern A: species-list paragraph: 20, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 74

### ZMSP14_34-39 — Za teplomilnými plevely a jiným kvítím okolo Staříča

- source: `pdf/14/ZMSPCBS_2025-14_34-39.pdf`; section: EXKURZE; default record type: species_list
- localities: 13; occurrences: 301
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 2, paragraph skipped (narrative/commentary/caption): 20, pattern A: locality entry: 13, pattern A: species-list paragraph: 22, species-section paragraph skipped (commentary/signature): 1
- flags: ABBREV_GENUS 95, LIST_SPLIT 2, GRID_FORMAT 1, GRID_COORD_MISMATCH 1, TAXON_UNMATCHED 1

### ZMSP14_40-45 — Exkurze Za mechorosty na hrad Hukvaldy a jeho okolí

- source: `pdf/14/ZMSPCBS_2025-14_40-45.pdf`; section: EXKURZE; default record type: species_list
- localities: 9; occurrences: 98
- blocks by pattern: heading→None: 5, heading→loc: 1, heading→species: 3, paragraph skipped (narrative/commentary/caption): 35, pattern A: locality entry: 5, pattern A: species-list paragraph: 22, species-section paragraph skipped (commentary/signature): 2
- flags: ABBREV_GENUS 19, TAXON_UNMATCHED 2

### ZMSP14_46-49 — Bryologická exkurze za historií mechorostů v Beskydech

- source: `pdf/14/ZMSPCBS_2025-14_46-49.pdf`; section: EXKURZE; default record type: species_list
- localities: 3; occurrences: 139
- blocks by pattern: heading→None: 4, heading→loc: 1, heading→species: 4, paragraph skipped (narrative/commentary/caption): 22, pattern A: locality entry: 3, pattern A: species-list paragraph: 27, species-section paragraph skipped (commentary/signature): 3
- flags: ABBREV_GENUS 40, TAXON_UNMATCHED 9, MULTI_INTERPRETATION 6

### ZMSP14_50-58 — Poznámky k rozšíření některých vzácnějších druhů na Osoblažsku III

- source: `pdf/14/ZMSPCBS_2025-14_50-58.pdf`; section: FLORISTIKA; default record type: species_list
- localities: 24; occurrences: 27
- blocks by pattern: heading→None: 5, heading→records: 8, paragraph skipped (narrative/commentary/caption): 52, pattern B: record locality: 24, pattern B: taxon header: 9
- flags: TAXON_UNMATCHED 5, MULTI_INTERPRETATION 1

## Articles not excerpted (no records by type)

- ZMSP2_3 — Quo vadis, pobočkový časopise? (EDITORIAL)
- ZMSP2_61-63 — Publikace členů Moravskoslezské pobočky ČBS v roce 2012 (RŮZNÉ)
- ZMSP2_66 — RNDr. Lubomír Kincl, CSc. – vzpomínka (PERSONALIA)
- ZMSP3_5 — Do třetice všeho…? (EDITORIAL)
- ZMSP3_6-7 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2013 (VÝROČNÍ ZPRÁVA)
- ZMSP3_64-65 — Publikace členů Moravskoslezské pobočky ČBS v roce 2013 (RŮZNÉ)
- ZMSP3_66 — Nová kniha – Leo Bureš: Chráněné a ohrožené rostliny Chráněné krajinné oblasti Jeseníky (RŮZNÉ)
- ZMSP3_67 — Nová kniha – Kolektiv autorů: Příroda Pobečví (RŮZNÉ)
- ZMSP3_71 — RTDr. Ing. Ladislav David – vzpomínka (PERSONALIA)
- ZMSP3_72 — Vladimír „Jim“ Petr – vzpomínka (PERSONALIA)
- ZMSP4_4 — Čtvrtý ročník (EDITORIAL)
- ZMSP4_5-6 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2014 (VÝROČNÍ ZPRÁVA)
- ZMSP4_50-52 — Publikace členů Moravskoslezské pobočky ČBS v roce 2014 (RŮZNÉ)
- ZMSP4P1_3-29 — Floristický kurz České botanické společnosti, Litovel 2015 (12.–18. 7. 2015). Informační materiály pro účastníky (PŘÍLOHA)
- ZMSP5_4 — Půlkulatý, pátý ročník (EDITORIAL)
- ZMSP5_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2015 (VÝROČNÍ ZPRÁVA)
- ZMSP5_60-61 — Publikace členů Moravskoslezské pobočky ČBS v roce 2015 (RŮZNÉ)
- ZMSP5_62-64 — K 75. jubileu RNDr. Marie Sedláčkové (PERSONALIA)
- ZMSP6_4 — O šestém ročníku (EDITORIAL)
- ZMSP6_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2016 (VÝROČNÍ ZPRÁVA)
- ZMSP6_61-62 — Nová kniha – Rukopisy vsetínského botanika Jana Bubely (RŮZNÉ)
- ZMSP6_63-64 — Publikace členů Moravskoslezské pobočky ČBS v roce 2016 (RŮZNÉ)
- ZMSP7_4 — Sedmička (EDITORIAL)
- ZMSP7_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2017 (VÝROČNÍ ZPRÁVA)
- ZMSP7_76 — Nová kniha – Ohrožené rostliny střední Moravy (RŮZNÉ)
- ZMSP7_77-78 — Publikace členů Moravskoslezské pobočky ČBS v roce 2017 (RŮZNÉ)
- ZMSP7_79-80 — Doc. RNDr. Vratislav Bednář, CSc (PERSONALIA)
- ZMSP8_4 — Osmé číslo (EDITORIAL)
- ZMSP8_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2018 (VÝROČNÍ ZPRÁVA)
- ZMSP8_61-62 — Publikace členů Moravskoslezské pobočky ČBS v roce 2018 (RŮZNÉ)
- ZMSP9_4 — Deváté číslo (EDITORIAL)
- ZMSP9_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2019 (VÝROČNÍ ZPRÁVA)
- ZMSP9_77-82 — Nová kniha. Klíč ke květeně České republiky (RŮZNÉ)
- ZMSP9_83-84 — Publikace členů Moravskoslezské pobočky ČBS v roce 2019 (RŮZNÉ)
- ZMSP10_4 — Jubilejní desáté číslo (no section)
- ZMSP10_5-9 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2020 (no section)
- ZMSP10_10-23 — Moravskoslezská pobočka ČBS ve fotografii za uplynulých 10 let (2011–2020) (no section)
- ZMSP10_64-65 — Nová kniha. Klenoty květeny Zlínského kraje (no section)
- ZMSP10_66-69 — Publikace členů Moravskoslezské pobočky ČBS v roce 2020 (no section)
- ZMSP11_4 — Jedenácté číslo (EDITORIAL)
- ZMSP11_5-9 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2021 (VÝROČNÍ ZPRÁVA)
- ZMSP11_10-21 — Moravskoslezská pobočka ČBS ve fotografii za uplynulých 10 let (2011–2020) – taxony (HISTORIE)
- ZMSP11_73-76 — Publikace členů Moravskoslezské pobočky ČBS v roce 2021 (RŮZNÉ)
- ZMSP11_77-80 — Tomáš Svěrák (PERSONALIA)
- ZMSP12_4 — Dvanácté číslo (EDITORIAL)
- ZMSP12_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2022 (VÝROČNÍ ZPRÁVA)
- ZMSP12_63-64 — Nová kniha. Fenomén Velká kotlina 1: Flóra, vegetace, fauna (RŮZNÉ)
- ZMSP12_65-69 — Publikace členů Moravskoslezské pobočky ČBS v roce 2022 (RŮZNÉ)
- ZMSP12_70-72 — Odešel Zdeněk Vrubel, environmentalista a botanik z Pazderny (PERSONALIA)
- ZMSP13_4 — Třinácté číslo (EDITORIAL)
- ZMSP13_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2023 (VÝROČNÍ ZPRÁVA)
- ZMSP13_50 — Nová kniha. Spájajú nás Beskydy (RŮZNÉ)
- ZMSP13_51-53 — Publikace členů Moravskoslezské pobočky ČBS v roce 2023 (RŮZNÉ)
- ZMSP13_54-55 — K 60. narozeninám Boba Trávníčka (PERSONALIA)
- ZMSP14_4 — Čtrnácté číslo (EDITORIAL)
- ZMSP14_5-10 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2024 (VÝROČNÍ ZPRÁVA)
- ZMSP14_59-61 — Publikace členů Moravskoslezské pobočky ČBS v roce 2024 (RŮZNÉ)
- ZMSP14_62-64 — Ing. Milan Velička – 90 let (PERSONALIA)
- ZMSP14_65-74 — Petr Batoušek – 75 let (PERSONALIA)
- ZMSP14_75-77 — Ing. Ivan Jindra – 75 let (PERSONALIA)
- ZMSP14_78-80 — Prof. RNDr. Bronislav Hlůza, CSc. (8. 3. 1929 – 9. 12. 2024) (PERSONALIA)
- ZMSP15_4 — Patnácté číslo (no section)
- ZMSP15_78-82 — Publikace členů Moravskoslezské pobočky ČBS v roce 2025 (no section)
- ZMSP15_5-9 — Výroční zpráva Moravskoslezské pobočky ČBS za rok 2025 (no section)
