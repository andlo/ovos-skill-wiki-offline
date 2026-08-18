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

## English only in v1

The title list and summaries are both sourced from English
Wikipedia's own vital-articles project and REST API. Danish Wikipedia
has its own, much smaller and differently-curated vital-articles
list, and machine-translating ~9,000 English summaries was out of
scope for a first version. Non-English support is a real gap, not an
oversight - worth revisiting if there's a clean path to a comparable
non-English data source.

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
python3 data/build_data.py
```
Polite, rate-limited (0.5s between requests), checkpoints every 100
articles so an interruption doesn't lose progress - re-running resumes
from `data/summaries.json` if it already exists.

## Versioning
`0.0.X` (patch only) until told otherwise, matching the rest of this
project family.

## Style / conventions
Same conventions as the rest of this project family - see
`ovos-skill-geography`'s DEVELOPMENT.md for the general house style
(functions over methods where reusable, plain functions take `lang`
explicitly, no self.lang inside reusable helpers).
