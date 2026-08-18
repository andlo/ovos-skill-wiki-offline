"""
skill OVOS Wiki Offline
Copyright (C) 2026  Andreas Lorensen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

---

Fully offline, general-knowledge fallback for questions like "who was
Charlie Chaplin", "what is the Eiffel Tower", "tell me about tomato" -
an offline alternative to ovos-skill-wikipedia/ovos-skill-ddg/
ovos-skill-wolfie for the subset of questions covered by Wikipedia's
own "Level 4 Vital Articles" list (~9,000 topics the Wikipedia
community itself has curated as the most essential encyclopedia
entries - see data/build_data.py and CREDITS.md for the exact
sourcing).

NOT a fixed-intent skill, deliberately - see DEVELOPMENT.md "Why
Common Query + Fallback, not a fixed intent" for the reasoning.

This is an ENCYCLOPEDIA LOOKUP, not a reasoning engine: it can answer
"what is a tomato" (single-entity lookup) but not "are tomatoes and
potatoes related" (a comparison across two entities) - see
DEVELOPMENT.md "Single-entity lookup, not relational reasoning".

English, Spanish, and French in v1 - the underlying data is sourced
from each language's own Wikipedia vital-articles list/REST summary
API. Spanish is a real, partial exception - 3 of the native list's 11
topic categories (Biology and health sciences, Physical sciences,
Society and social sciences) don't exist as actual pages despite the
index table claiming 100% completion - see DEVELOPMENT.md "The
Spanish gap" and CREDITS.md. German and Danish are NOT covered - see
DEVELOPMENT.md "Why not German or Danish yet" and
github.com/andlo/ovos-skill-wiki-offline/issues/1 for the machine-
translation approach planned for those two instead.
"""
import json
import re
from pathlib import Path

from ovos_workshop.skills.fallback import FallbackSkill
from ovos_workshop.decorators import common_query, fallback_handler
from ovos_utils.parse import match_one

SKILL_ROOT = Path(__file__).resolve().parent
DATA_DIR = SKILL_ROOT / "data"

FUZZY_MATCH_THRESHOLD = 0.85

SUPPORTED_LANGS = ("en-us", "es-es", "fr-fr")


def _load_summaries(lang):
    path = DATA_DIR / f"summaries_{lang}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# lang -> {title -> {title, extract, description, topic}}
SUMMARIES_BY_LANG = {lang: _load_summaries(lang) for lang in SUPPORTED_LANGS}
# lang -> {lowercased title -> canonical title}
TITLE_INDEX_BY_LANG = {
    lang: {title.lower(): title for title in summaries}
    for lang, summaries in SUMMARIES_BY_LANG.items()
}
ALL_TITLES_LOWER_BY_LANG = {
    lang: list(index.keys()) for lang, index in TITLE_INDEX_BY_LANG.items()
}

# Deliberately simple substring prefixes, not full NLU - a safety
# net / fallback catch, not a second implementation of intent
# parsing. See DEVELOPMENT.md.
QUESTION_PREFIXES = {
    "en-us": [
        "who is ", "who was ", "who's ",
        "what is ", "what's ", "what are ",
        "where is ", "where's ", "where are ",
        "tell me about ", "what do you know about ",
    ],
    "es-es": [
        "quién es ", "quién fue ", "quiénes son ",
        "qué es ", "qué son ",
        "dónde está ", "dónde están ", "dónde queda ",
        "cuéntame sobre ", "háblame de ", "háblame sobre ",
        "qué sabes sobre ", "qué sabes de ",
    ],
    "fr-fr": [
        "qui est ", "qui était ", "qui sont ",
        "qu'est-ce que ", "qu'est-ce qu'", "qu'est-ce qui est ",
        "où est ", "où se trouve ", "où sont ",
        "parle-moi de ", "parle-moi du ", "parle-moi des ",
        "que sais-tu sur ", "que sais-tu de ",
    ],
}

# Leading articles stripped before an exact-match retry, per language
# (see resolve_title()'s "the "-stripping - same idea, but Spanish/
# French have gendered/plural articles English doesn't).
LEADING_ARTICLES = {
    "en-us": ["the "],
    "es-es": ["el ", "la ", "los ", "las "],
    "fr-fr": ["le ", "la ", "les ", "l'"],
}


def _strip_question_prefix(phrase, lang):
    """Returns the subject after a recognized question prefix, or
    None if the phrase doesn't start with one of ours for this
    language."""
    stripped = phrase.strip().rstrip("?").strip()
    lower = stripped.lower()
    for prefix in QUESTION_PREFIXES.get(lang, []):
        if lower.startswith(prefix):
            return stripped[len(prefix):].strip()
    return None


def resolve_title(subject, lang):
    """Exact match first (case-insensitive, with/without a leading
    article), then a fuzzy match against this language's titles as a
    fallback for minor STT variation. Returns a canonical title key
    into SUMMARIES_BY_LANG[lang], or None."""
    if not subject or lang not in SUMMARIES_BY_LANG:
        return None
    title_index = TITLE_INDEX_BY_LANG[lang]
    key = subject.strip().lower()
    if key in title_index:
        return title_index[key]
    for article in LEADING_ARTICLES.get(lang, []):
        if key.startswith(article):
            stripped_key = key[len(article):]
            if stripped_key in title_index:
                return title_index[stripped_key]
    all_titles = ALL_TITLES_LOWER_BY_LANG.get(lang, [])
    if not all_titles:
        return None
    match, score = match_one(key, all_titles)
    if score >= FUZZY_MATCH_THRESHOLD:
        return title_index[match]
    return None


def lookup_answer(phrase, lang):
    """Full pipeline: strip a question prefix, resolve the remaining
    subject against this language's title index, return the short
    spoken answer (str) or None. Shared by both the Common Query and
    fallback entry points below - one implementation, two triggers."""
    subject = _strip_question_prefix(phrase, lang)
    if subject is None:
        return None
    title = resolve_title(subject, lang)
    if title is None:
        return None
    return SUMMARIES_BY_LANG[lang][title]["extract"]


class WikiOffline(FallbackSkill):
    """Deliberately extends FallbackSkill (not plain OVOSSkill) - the
    @fallback_handler decorator only auto-registers on this base
    class, see DEVELOPMENT.md. Combines both entry points because
    they serve different purposes: Common Query competes fairly
    against other knowledge skills (Wikipedia, DDG, Wolfram) when the
    platform routes there; the fallback handler catches whatever the
    rest of the pipeline - including Common Query itself, when it
    isn't reached at all - didn't answer."""

    def can_answer(self, message):
        """Lightweight pre-check for the fallback 'ping' broadcast -
        the real decision happens in handle_fallback() below, this
        just avoids answering 'yes' to utterances that obviously
        aren't questions at all."""
        utterances = message.data.get("utterances") or []
        if not utterances:
            return False
        lang = message.data.get("lang", self.lang).lower()
        return _strip_question_prefix(utterances[0], lang) is not None

    @common_query()
    def handle_common_query(self, phrase, lang):
        """See DEVELOPMENT.md 'Why Common Query + Fallback' - this
        lets the skill compete on equal footing with Wikipedia/DDG/
        Wolfram when the platform's own routing (including the m2v
        misrouting documented in ovos-skill-geometry's DEVELOPMENT.md)
        sends a question to Common Query."""
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return None
        answer = lookup_answer(phrase, lang)
        if answer is None:
            return None
        return answer, 0.8

    @fallback_handler(priority=85)
    def handle_fallback(self, message):
        """Priority 85: after specific-domain skills (geography,
        geometry, calculator, ...) and their own higher-priority
        intents have had a chance, but before the generic
        fallback-unknown 'I don't know' catch-all. See
        FallbackSkill's own priority-tier documentation."""
        utterances = message.data.get("utterances") or []
        if not utterances:
            return False
        lang = message.data.get("lang", self.lang).lower()
        answer = lookup_answer(utterances[0], lang)
        if answer is None:
            return False
        self.speak(answer)
        return True
