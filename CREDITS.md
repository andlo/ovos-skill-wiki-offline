# Data credits and licensing

## Article lists

**English (en-us):** Wikipedia's own bot-maintained master list page,
**[List of all level 1–4 vital articles](https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/List_of_all_level_1%E2%80%934_vital_articles)**
- the authoritative, complete list of the ~10,000 topics the English
Wikipedia community itself has curated as the most essential
encyclopedia entries (nested levels 1 through 4). `data/build_data.py`
fetches the page's own wikitext via the official MediaWiki
`action=parse` API and extracts every `[[Article]]` link - 10,033
unique titles.

**Spanish (es-es):** Spanish Wikipedia's own equivalent,
**[Lista de artículos que toda Wikipedia debería tener/Expandida](https://es.wikipedia.org/wiki/Wikipedia:Lista_de_art%C3%ADculos_que_toda_Wikipedia_deber%C3%ADa_tener/Expandida)**,
split across 11 topic subpages rather than one master page. **3 of
those 11 subpages don't actually exist** despite the index table
claiming 100% completion - see `DEVELOPMENT.md` "The Spanish gap".
6,631 unique titles resulted (of an intended ~10,000).

**French (fr-fr):** French Wikipedia's own equivalent,
**[Articles vitaux/Niveau 4](https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Articles_vitaux/Niveau_4)**,
also split across 11 topic subpages, all of which exist. 9,988
unique titles resulted.

Topic labels (Arts, Geography, People, etc - informational only, not
required for the skill to work) for en-us come from a SEPARATE,
secondary source: the 11 topic subcategories under `Category:Wikipedia
level-4 vital articles by topic`, tagged on each article's own Talk
page (a standard WikiProject assessment convention). This category-
based tracking turned out to be INCOMPLETE as a title source in its
own right (missing ~1,000 titles the master list has, including
"Photosynthesis" - confirmed missing during development, see
DEVELOPMENT.md), so it's used only to enrich the master list's
titles with a topic label where available; titles without a category
match are labeled `"Uncategorized"` rather than dropped. es-es/fr-fr
already get topic labels directly from their own subpage structure.

## Article summaries

Source: each language's own official Wikipedia **REST summary API**
(`{lang}.wikipedia.org/api/rest_v1/page/summary/{title}`) - the lead
extract (first paragraph or so) of each article, plus a short
`description` field.

## License

Wikipedia article text, including these summaries, is licensed
**CC BY-SA 4.0** (and GFDL). This skill bundles the extracted
summaries verbatim (not paraphrased) as
`data/summaries_en-us.json`/`summaries_es-es.json`/`summaries_fr-fr.json`,
consistent with how `ovos-skill-wikipedia` already reads Wikipedia
content aloud via its own live API lookups - this skill does the
same thing offline, from a locally bundled snapshot instead of a
live request. Per CC BY-SA's attribution requirement: content
sourced from Wikipedia, © Wikipedia contributors, CC BY-SA 4.0.

This does NOT extend to the skill's own code, which remains
GPL-3.0-or-later per `LICENSE`.

## A partial-translation note on the Spanish data

Part of Spanish's "Tecnología" category is explicitly marked by the
Spanish Wikipedia community itself as content imported from Galician
Wikipedia, not yet translated ("Traído desde wiki Gallega, por favor
ayudar a traducir!!"). Visible as Galician spellings among the
fetched titles. Not specifically filtered - see DEVELOPMENT.md "The
Spanish gap" for why this was left as-is.

## Snapshot, not a live mirror

Each `data/summaries_<lang>.json` is a one-time snapshot from when
`data/build_data.py <lang>` was run - not automatically kept in sync
with Wikipedia's ongoing edits. Article text may drift from the live
Wikipedia article over time. Re-running `build_data.py` refreshes it.

## Why the Level 4 list specifically, not Level 5 or full Wikipedia

See `DEVELOPMENT.md` "Why Level 4, not Level 5 or full Wikipedia" for
the size/tooling tradeoffs considered (Kiwix/ZIM, DBpedia short
abstracts, and Wikipedia's own nested vital-article levels).

