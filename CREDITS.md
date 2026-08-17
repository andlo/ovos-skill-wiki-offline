# Data credits and licensing

## Article list

Source: Wikipedia's own **[Level 4 Vital Articles](https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/Level/4)**
list - ~9,000 topics the Wikipedia community itself has curated as
the most essential encyclopedia entries, tracked via the 11 official
topic subcategories under `Category:Wikipedia level-4 vital articles
by topic` (Arts, Biology and health sciences, Everyday life,
Geography, History, Mathematics, People, Philosophy and religion,
Physical sciences, Society and social sciences, Technology).

Article titles are tagged on each article's own Talk page (a
standard WikiProject assessment convention, not a reader-facing
category) - `data/build_data.py` fetches this via the official
MediaWiki `list=categorymembers` API and strips the `Talk:` prefix.
9,033 unique titles resulted (some articles are cross-listed under
multiple topics; duplicates are kept once, tagged with whichever
topic was encountered first).

## Article summaries

Source: Wikipedia's own official **REST summary API**
(`en.wikipedia.org/api/rest_v1/page/summary/{title}`) - the lead
extract (first paragraph or so) of each article, plus a short
`description` field.

## License

Wikipedia article text, including these summaries, is licensed
**CC BY-SA 4.0** (and GFDL). This skill bundles the extracted
summaries verbatim (not paraphrased) as `data/summaries.json`,
consistent with how `ovos-skill-wikipedia` already reads Wikipedia
content aloud via its own live API lookups - this skill does the
same thing offline, from a locally bundled snapshot instead of a
live request. Per CC BY-SA's attribution requirement: content
sourced from Wikipedia, © Wikipedia contributors, CC BY-SA 4.0.

This does NOT extend to the skill's own code, which remains
GPL-3.0-or-later per `LICENSE`.

## Snapshot, not a live mirror

`data/summaries.json` is a one-time snapshot from when
`data/build_data.py` was run - not automatically kept in sync with
Wikipedia's ongoing edits. Article text may drift from the live
Wikipedia article over time. Re-running `build_data.py` refreshes it.

## Why the Level 4 list specifically, not Level 5 or full Wikipedia

See `DEVELOPMENT.md` "Why Level 4, not Level 5 or full Wikipedia" for
the size/tooling tradeoffs considered (Kiwix/ZIM, DBpedia short
abstracts, and Wikipedia's own nested vital-article levels).
