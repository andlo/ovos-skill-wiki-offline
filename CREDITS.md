# Data credits and licensing

## Article list

Source: Wikipedia's own bot-maintained master list page,
**[List of all level 1–4 vital articles](https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/List_of_all_level_1%E2%80%934_vital_articles)**
- the authoritative, complete list of the ~10,000 topics the
Wikipedia community itself has curated as the most essential
encyclopedia entries (nested levels 1 through 4; a "Level 4 Vital
Article" is by definition also every Level 1-3 vital article).
`data/build_data.py` fetches the page's own wikitext via the official
MediaWiki `action=parse` API and extracts every `[[Article]]` link -
10,033 unique titles resulted.

Topic labels (Arts, Geography, People, etc - informational only, not
required for the skill to work) come from a SEPARATE, secondary
source: the 11 topic subcategories under `Category:Wikipedia
level-4 vital articles by topic`, tagged on each article's own Talk
page (a standard WikiProject assessment convention). This category-
based tracking turned out to be INCOMPLETE as a title source in its
own right (missing ~1,000 titles the master list has, including
"Photosynthesis" - confirmed missing during development, see
DEVELOPMENT.md), so it's used only to enrich the master list's
titles with a topic label where available; titles without a category
match are labeled `"Uncategorized"` rather than dropped.

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
