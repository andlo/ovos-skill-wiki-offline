# <img src='icon.png' card_color='#8E44AD' width='50' height='50' style='vertical-align:bottom'/> Wiki Offline

A fully offline general-knowledge fallback for OVOS - "who was
Charlie Chaplin", "what is the Eiffel Tower", "tell me about tomato".
An offline alternative to `ovos-skill-wikipedia`/`ovos-skill-ddg`/
`ovos-skill-wolfie` for the topics covered by each language's own
Wikipedia "Level 4 Vital Articles" equivalent - the subjects that
language's Wikipedia community itself has curated as the most
essential encyclopedia entries. No internet connection needed at
runtime. Available in English, Spanish, and French.

[![Tests](https://github.com/andlo/ovos-skill-wiki-offline/actions/workflows/test.yml/badge.svg)](https://github.com/andlo/ovos-skill-wiki-offline/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/ovos-skill-wiki-offline.svg)](https://pypi.org/project/ovos-skill-wiki-offline/)

- [Usage](#usage)
- [What this is (and isn't)](#what-this-is-and-isnt)
- [A Common Query + Fallback skill, not a fixed intent](#a-common-query--fallback-skill-not-a-fixed-intent)
- [Data sourcing and licensing](#data-sourcing-and-licensing)
- [Known limitations](#known-limitations)
- [Install](#install)
- [Development](#development)

## Usage
```
"who was Charlie Chaplin"
"what is the Eiffel Tower"
"tell me about tomato"
"what do you know about photosynthesis"
"where is Mount Everest"
"quién fue Charlie Chaplin"       (Spanish)
"cuéntame sobre el Tomate"        (Spanish)
"qui était Charlie Chaplin"       (French)
"parle-moi de la Tomate"          (French)
```

## What this is (and isn't)

An **encyclopedia lookup**, not a reasoning engine. It resolves a
single named entity from the question and speaks that entity's own
short summary. It can answer "what is a tomato" but not "are tomatoes
and potatoes related" - the second is a comparison across two
entities, and there's no structured data being compared here, only
free-text extracts (some relational questions get answered by luck,
when one entity's own summary happens to mention the other - not by
design). See DEVELOPMENT.md for the reasoning.

## A Common Query + Fallback skill, not a fixed intent

Every sibling skill in this project family (geography, geometry,
convert, calculator) uses fixed Padatious intents as the primary
path. This one doesn't - ~10,000 arbitrary proper nouns don't fit a
bounded intent-slot vocabulary the way 194 countries or 24 geometry
terms do. Instead this skill competes via Common Query (alongside
Wikipedia/DDG/Wolfram, when the platform routes a question there) and
catches whatever's left via a Fallback handler - the same dual
pattern `ovos-skill-wolfie` already uses. See DEVELOPMENT.md for the
full reasoning, including why this needed extending `FallbackSkill`
specifically (not just adding the `@fallback_handler` decorator to a
plain skill).

## Data sourcing and licensing

Article titles and summaries both come directly from Wikipedia's own
official APIs - the Level 4 Vital Articles category structure for the
title list, and the REST summary API for the short spoken extracts.
Wikipedia content is CC BY-SA 4.0; this skill bundles it offline the
same way `ovos-skill-wikipedia` reads it aloud live. **Full
attribution and licensing details, plus why Level 4 was chosen over
Kiwix/ZIM, DBpedia, or Wikipedia's own larger vital-article levels:
[CREDITS.md](CREDITS.md)** and **[DEVELOPMENT.md](DEVELOPMENT.md)**.

## Known limitations

- **Native, bundled data for English, Spanish, and French only** -
  German, Danish, and any other language fall back to **ad-hoc
  runtime translation** instead (translates the question and answer
  on demand via whatever OVOS translation plugin the user has
  configured, e.g. the fully-local `ovos-translate-plugin-nllb`) -
  slower (a few extra seconds per answer) and needs a translator
  configured, but works for any language with zero bundled data. See
  DEVELOPMENT.md "Ad-hoc translation for unsupported languages".
- **The Spanish dataset is smaller** (~6,200 topics vs ~10,000 for
  English/French) - 3 of Spanish Wikipedia's own 11 topic categories
  (biology/health, physics, social sciences) don't actually exist as
  pages despite the source list claiming full completion. See
  DEVELOPMENT.md "The Spanish gap" for the full story - this means
  Spanish can't currently answer biology, physics, or social-science
  questions.
- **Single-entity lookup, not relational reasoning** - see above and
  DEVELOPMENT.md.
- **A snapshot, not a live mirror** - each `data/summaries_<lang>.json`
  reflects Wikipedia as of whenever `data/build_data.py` was last run
  for that language, not the current live article.
- **Scope is Level 4** (~10,000 topics for en-us/fr-fr) - Level 5
  (50,000 articles) exists as a natural future extension (Level 4 is
  a strict subset), not built in v1.

## Install
```bash
pip install ovos-skill-wiki-offline
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md).

## Category
**Information**

## Tags
#wikipedia #offline #encyclopedia #reference #commonquery #fallback
