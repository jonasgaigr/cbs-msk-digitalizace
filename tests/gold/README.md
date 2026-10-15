# Gold standard

Ten articles (`gold_articles.csv`) are checked by hand so that `scripts/eval.py` can measure recall and precision of
the excerption. Three of them are a held-out set (drawn with seed 20261015 from the seven articles that are not Phase 1/2
targets); they are never looked at while rules are developed.

| set | article | pattern | candidates |
|---|---|---|---:|
| dev | 2: 43–47 | A + M | 119 |
| dev | 4/P2 pp. 23–29 (block drawn with seed 20261015) | A | 233 |
| dev | 10: 53–63 | A2 + B | 29 |
| dev | 5: 55–59 | H | 61 |
| dev | 7: 66–69 | A3 (group sub-labels, date markers) | 156 + 5 parser-only |
| dev | 2: 48–49 | numbered micro-habitats | 48 |
| dev | 4: 7–10 | narrative | 24 |
| held-out | 13: 46–49 | A1 | 75 |
| held-out | 3: 34–38 | A4 + B | 150 + 1 parser-only |
| held-out | 7: 61–65 | A3 + B | 34 + 1 parser-only |

## Files

- `review/<article>.pdf` — the original PDF; every candidate is highlighted and labelled with its `cand_id`.
  **Green**: the parser produced an occurrence for it. **Red**: it did not. **Grey**: front matter, caption or literature
  (out of scope). Hovering a highlight shows the name.
- `review/<article>_cp1250.csv` — one row per candidate, sorted by page (Windows-1250, `;`, opens in Czech Excel).
- `checked/` — put the checked CSVs here, under the same file names.

Regenerate with `python -X utf8 scripts/gold_candidates.py` (deterministic; built from the frozen `tests/baseline/`).

## How to check a row

| column | meaning |
|---|---|
| `cand_id` | `c…` harvested name; `P…` parser row that no harvested name explains (e.g. an empty taxon); `ARTICLE`; `M…` rows for records the harvester missed |
| `taxon_as_printed`, `source_line` | the name and its list item / sentence / table row, as printed |
| `parser_occurrence_id`, `parser_locality`, `parser_date` | what the parser made of it (several localities: their numbers) |
| `record_type_suggested` | the parser's record type, otherwise the harvester's guess — edit it if wrong |
| `is_record` | **1** = a record of this taxon at a locality of the article, **0** = not (mention in comments, distribution, literature, title, caption…) |
| `locality_ok` | **1** = the parser's localities are exactly the printed ones |
| `date_ok` | **1** = the parser's date is right (an empty date is right when no date applies) |
| `correction` | only when something is wrong or missing, as `key=value` separated by `;` (below) |
| `note` | free text; pre-filled with the parser's flags and genus expansion |
| `colour`, `harvest_locality` | help only: highlight colour; locality numbers printed after the name (`refs: …`) or the locality line a list belongs to |

Green rows are pre-filled (`is_record`, `locality_ok`, `date_ok` = 1 where the parser has a value); grey rows have
`is_record = 0`. Red rows are blank: type 1 or 0.

`correction` keys:

- `loc=3, 5, 11` (locality numbers) or `loc=PR Doubek` (text that occurs in the locality line or description).
  Needed when `locality_ok = 0`, and for a red record that has neither `refs:` nor a list locality in `harvest_locality`
  (otherwise that printed locality is taken).
- `date=2017-04-22` (or `2017-04-22/2017-04-23`). Needed when `date_ok = 0` and you know the date.
- `taxon=Brachythecium rutabulum` when the parser read the name wrong (e.g. a wrong genus expansion).

`ARTICLE` row: `date=YYYY-MM-DD` there is the date of every record of the article whose date is neither confirmed nor
corrected — saves typing for single-day excursions.

`M01`–`M25`: records the harvester missed (Czech-only names, names not in italics): fill `page`, `taxon_as_printed`,
`source_line`, `record_type_suggested` and `correction` (`loc=`, `date=`).
