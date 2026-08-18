# Development notes

## Architecture at a glance

Module-level data (`SUMMARIES`, `TITLE_INDEX`, `ALL_TITLES_LOWER`)
loaded once from `data/summaries.json` at import time. Two thin
entry points - `handle_common_query()` and `handle_fallback()` - both
call the same `lookup_answer()` pipeline: strip a question prefix,
resolve the remaining subject against the title index (exact, then
fuzzy), return the matching article's extract or `None`.

## Why Common Query + Fallback, not a fixed intent

Every other skill in this project family (geography, geometry,
convert, calculator) uses fixed Padatious intents as the primary
path, with a narrow `@common_query` safety net alongside. This skill
inverts that: no fixed intent at all, only Common Query + Fallback.

The reason is scale. Padatious intents work well for a BOUNDED slot
vocabulary (194 countries, 24 geometry terms, a handful of arithmetic
operators) where every valid entity is either enumerable in training
data or captured via a clean wildcard with a literal anchor word on
both sides. ~9,000 arbitrary, unrelated proper nouns ("Charlie
Chaplin", "Eiffel Tower", "Photosynthesis", "Napoleon") don't fit
that shape - there's no useful "training phrase" set to build, and a
bare `{topic}` wildcard intent would either be too promiscuous
(matching everything) or too narrow (missing most real phrasings)
depending on how it's anchored.

`ovos-skill-wolfie` already uses exactly this pattern in the same
OVOS ecosystem (Common Query for competing on general-knowledge
questions, Fallback as the last-resort catch), which is direct
precedent for treating "arbitrary open-domain lookup" as a Common
Query + Fallback problem rather than an intent-matching one - see
that skill's own README.

## `FallbackSkill`, not `@fallback_handler` alone

`@fallback_handler(priority=N)` only auto-registers if the skill
class extends `FallbackSkill` (confirmed by reading the installed
`ovos_workshop.skills.fallback` source directly, not assumed) -
`FallbackSkill._register_decorated()` scans for `fallback_priority`
after calling `super()._register_decorated()`, so plain `OVOSSkill`
subclasses never see it. `@common_query`, by contrast, works on any
plain `OVOSSkill` (confirmed the same way while building
`ovos-skill-geometry`'s Common Query safety net). This skill extends
`FallbackSkill` specifically to get both decorators working together.

`can_answer()` is a required abstract method on `FallbackSkill`, used
for the low-cost "ping" broadcast (a system-wide "who might handle
this utterance at all" check) - kept intentionally lightweight (just
the question-prefix check, no title resolution) since the REAL
decision happens in the `@fallback_handler`-decorated method, which
returns `True`/`False` per utterance.

Priority 85: after specific-domain skills (geography, geometry,
calculator, ...) and their own higher-priority intents have had a
fair shot at anything they can answer more authoritatively, but
before the generic `fallback-unknown` "I don't know" catch-all.

## Why Level 4, not Level 5 or full Wikipedia

Considered three options at very different scales:

- **Kiwix/ZIM** (a full or partial offline Wikipedia archive via
  `python-libzim`, GPLv3+): technically clean (license-compatible,
  mature tooling), but even a "mini" scope Simple Wikipedia ZIM is
  hundreds of MB to low GB - too large to bundle in a PyPI package,
  would need a separate download step and settings-driven file path,
  more like `ovos-skill-sound-like`'s optional freesound.org API key
  than anything else in this project family.
- **DBpedia short abstracts**: better per-entry shape (max 500 chars,
  built for exactly this "short spoken answer" use case) but the full
  English dataset is ~4.6 million entries - still hundreds of MB
  compressed, and DBpedia's traditional extraction pipeline's most
  recent well-documented snapshots are several years old.
- **Wikipedia's own "Vital Articles" levels** (1/10/100/1,000/10,000/
  50,000 articles, nested, actively maintained by a dedicated
  WikiProject): the only option in the same size range as this
  project's other datasets. Level 5 (50,000 articles) was estimated
  at ~25-40MB - still reasonable, but has no ready-made summary
  dataset and would need building the title list from 11 category
  pages split across further subpages. Level 4 (nominally 10,000
  articles, in practice 10,033 per Wikipedia's own bot-maintained
  count) is a strict subset of Level 5 (the levels are nested), and
  the final bundled data is ~6.3MB - well under what any other
  approach could offer at a comparable size. Starting here doesn't
  foreclose extending to the rest of Level 5 later - nothing built
  for Level 4 needs to be redone.

A candidate ready-made Level 4 summary dataset was found on GitHub
but explicitly NOT used: no LICENSE file, 0 stars, single
contributor, no description - an unmaintained personal project isn't
a stable or clearly-licensed enough source to depend on for a
published skill, even though the underlying Wikipedia content it's
built from is itself openly licensed. `data/build_data.py` fetches
directly from Wikipedia's own official APIs instead - see `CREDITS.md`.

## Why the master list, not category tags

The first working version of `data/build_data.py` built its title
list purely from the 11 topic subcategories (each tagged on an
article's own Talk page). It worked, tests passed, real questions
got real answers - but a manual spot-check with a few of the exact
questions this skill was designed for ("who was Charlie Chaplin",
"what is photosynthesis") turned up two silent gaps: both topics
were completely absent from the 9,033-title category-based list,
despite being unambiguously "vital" by any reasonable definition.

Checking Wikipedia's OWN separate master list page ("List of all
level 1-4 vital articles", bot-maintained, page title uses an en-dash
in "1-4") confirmed both ARE genuinely part of Level 4 - the category
tags and the master list are two parallel tracking mechanisms
Wikipedia itself doesn't keep perfectly in sync (the master list's
own header calls itself "a temporary solution" pending an internal
Wikipedia infrastructure fix). The master list's wikitext turned out
to be simple, clean `[[Article]]`-link text - switching to it as the
title source went from 9,033 to 10,033 titles, closing the gap
without needing to abandon the category data entirely (it's kept as
a secondary, best-effort topic-label enrichment - see `CREDITS.md`).

The lesson generalizing beyond this one skill: passing tests and a
few working example questions aren't the same as complete data -
worth spot-checking specifically the examples that MOTIVATED building
something in the first place, not just examples that are convenient
to construct after the fact.

## Single-entity lookup, not relational reasoning

This skill answers "what is a tomato" (single-entity lookup) but
cannot answer "are tomatoes and potatoes related" (a comparison
across two entities) - there's no structured "family"/"category"
field being compared, only free-text extracts. In practice, well-
written lead paragraphs sometimes mention a close relationship
directly in prose (Tomato's own extract happens to mention "potato"
by name, as part of describing the nightshade family) - so some
relational questions get incidentally, not reliably, answered if the
asked-about entity's OWN summary happens to reference the other. This
is not something the skill actively reasons about or guarantees.

If genuine relational/comparison answers become a real need later,
that requires a structured facts layer (entity -> typed
attributes like family/category, comparable programmatically) -
a different, larger project than this one, not an extension of it.

## Three languages in v1: en-us, es-es, fr-fr

Confirmed via Wikidata's own cross-language page-mapping (not
assumed) that Spanish and French BOTH have a native list at a
comparable ~10,000-topic scale to English's Level 4 - unlike German
(only a much smaller cross-wiki list) and Danish (no confirmed
equivalent at all). See "The Spanish gap" and "Why not German or
Danish yet" below, and
[issue #1](https://github.com/andlo/ovos-skill-wiki-offline/issues/1)
for the machine-translation approach planned for German/Danish.

`data/build_data.py` now takes a language argument
(`python3 build_data.py es-es`) and supports two title-source
STRATEGIES per language: `"master_list"` (en-us's single bot-
maintained page) and `"topic_subpages"` (es-es/fr-fr, which split
their list across ~11 topic subpages instead - no single master page
exists for these languages). Both extract the same way: raw
`[[Article]]` wikilinks from the page's wikitext.

## Interwiki links caused hangs, not clean errors

A genuinely nasty bug found while fetching Spanish data: the generic
`[[...]]` wikilink regex swept up **interwiki links** alongside real
article titles - e.g. `[[d:Q28989]]`, a cross-reference to a Wikidata
item, not a Spanish Wikipedia article. Requesting a REST summary for
a title shaped like `"d:Q28989"` didn't fail cleanly (no 404, no
exception) - it just **hung indefinitely**, with no visible cause:
the exact same URL fetched fine in isolation (outside the actual
fetch loop), which briefly looked like an environment-specific
problem before the "d:Q..." pattern was spotted in the logs.

Two fixes, both worth keeping even though the root cause is now
understood: (1) `INTERWIKI_PREFIX_RE` filters out any wikilink target
matching `^[a-z]{1,10}:` (interwiki prefixes are conventionally
lowercase and short - `d:`, `wikt:`, `commons:`, language codes like
`en:`/`fr:`, etc - a different convention from capitalized namespace
prefixes like `Wikipedia:`/`Categoría:`, which were already
filtered). (2) `with_hard_timeout()`, a `SIGALRM`-based hard backstop
around each summary fetch - `requests`' own `timeout=` parameter
doesn't always reliably bound DNS resolution time (a known
urllib3/requests limitation), so a single bad title can no longer
block the whole pipeline indefinitely regardless of the underlying
cause. 684 interwiki-link titles were found and purged from the
Spanish title list this way (7,315 -> 6,631 real titles) before this
fix; the hard timeout caught a handful of other malformed titles
(wikitext-parsing edge cases, e.g. a truncated `"G<Fuego griego"`)
during the actual fetch.

## The Spanish gap

Spanish's native list (`Lista de artículos que toda Wikipedia
debería tener/Expandida`) claims 100% completion across all 11 topic
categories in its own index table - but 3 of those 11 subpages
(**Biología y ciencias de la salud**, **Ciencias físicas**,
**Sociedad y ciencias sociales**) don't exist as actual pages at all,
confirmed via `action=query&list=allpages`, not just a broken link
guess. The index table is simply out of sync with reality - the same
class of issue as en-us's master-list-vs-category-tags gap, just a
bigger one (roughly a third of the intended scope, not a couple of
missing titles).

Decision (see conversation history / project owner's call): accept
the resulting 6,631-title, 6,239-summary Spanish dataset as-is for
v1, documented honestly, rather than patching the 3 missing
categories with machine-translated English content. Reasoning: mixing
genuine Spanish Wikipedia prose (8/11 categories) with machine-
translated English (3/11) would create an inconsistent tone
depending on which topic gets asked about - worse than a clean,
smaller, fully-native dataset. Concretely, this means Spanish cannot
answer biology/health, physics, or social-science questions ("what is
photosynthesis", "qué es la fotosíntesis") - confirmed and tested,
see `tests/test_real_data.py::test_es_tomate_and_fotosintesis_are_the_known_gap`.

Also noted in passing: part of Spanish's Tecnología category is
explicitly marked by the Spanish Wikipedia community itself as
untranslated content imported from Galician Wikipedia ("Traído desde
wiki Gallega, por favor ayudar a traducir!!") - visible in the
fetched titles as Galician spellings (e.g. "Horta froiteira",
"Enxeñaría", "Cicel" instead of Spanish "Cincel"). Not specifically
filtered out - these are still real, valid wikilinks that may or may
not resolve via the Spanish REST API depending on whether a Spanish-
language stub exists at that exact title. Left as-is rather than
attempting to detect and reroute Galician-looking titles to Galician
Wikipedia, which would be a disproportionate amount of complexity for
what's a relatively small slice of one topic category.

## Why not German or Danish yet

German only has a smaller, differently-scoped cross-wiki list (not a
full nested Level 1-5-equivalent structure at the ~10,000 scale);
Danish has no confirmed equivalent at all. Using either natively
would give a skill with much thinner, inconsistent coverage compared
to en-us/es-es/fr-fr. Machine-translating this same title/summary
dataset (recommended: `ovos-translate-plugin-nllb`, which runs
locally - NOT `ovos-translate-plugin-server`, which calls a remote
server by default and would make even this one-off data-build step
depend on a third party's uptime) is the planned path for both - see
[issue #1](https://github.com/andlo/ovos-skill-wiki-offline/issues/1)
for the full scoping, including whether to also backfill Spanish's 3
missing categories the same way as a smaller follow-on task.

## `resolve_title()`: exact match, then "the "-stripping, then fuzzy

Exact case-insensitive match covers the common case. A leading "the"
is stripped and retried before falling back to fuzzy matching (e.g.
"the Eiffel Tower" -> "Eiffel Tower") since it's a very common, low-
risk normalization that would otherwise force every "the X" phrasing
through the (slower, less precise) fuzzy path unnecessarily.
`match_one()` fuzzy matching (same tool `ovos-skill-convert` uses for
unit aliases) catches minor STT variation as a last resort, at a
deliberately high threshold (0.85) - a wrong match here means
confidently stating a WRONG fact as if it were the answer to the
question actually asked, which is worse than just not answering.

## Setup
```bash
git clone https://github.com/andlo/ovos-skill-wiki-offline.git
cd ovos-skill-wiki-offline
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-test.txt
```

## Running tests
```bash
python3 -m pytest tests/ -v
```

## Regenerating the data
```bash
pip install requests
python3 data/build_data.py en-us   # or es-es, fr-fr
```
Polite, rate-limited (0.5s between requests), checkpoints every 100
articles so an interruption doesn't lose progress - re-running resumes
from `data/summaries_<lang>.json` if it already exists. A hard
per-title timeout (see "Interwiki links caused hangs, not clean
errors") means a single bad title gets skipped and retried on the
next run rather than blocking the whole pipeline.

## Versioning
`0.0.X` (patch only) until told otherwise, matching the rest of this
project family.

## Style / conventions
Same conventions as the rest of this project family - see
`ovos-skill-geography`'s DEVELOPMENT.md for the general house style
(functions over methods where reusable, plain functions take `lang`
explicitly, no self.lang inside reusable helpers).
