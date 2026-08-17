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

English only in v1 - the underlying data is sourced from English
Wikipedia's own vital-articles list and REST summary API; there is
no equivalent bundled data for other languages yet (Danish Wikipedia
has a different, much smaller vital-articles set, and machine-
translating ~9,000 English summaries was out of scope for v1 - see
DEVELOPMENT.md "English only in v1").
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


def _load_summaries():
    path = DATA_DIR / "summaries.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# title -> {title, extract, description, topic}
SUMMARIES = _load_summaries()
# lowercased title -> canonical title, for exact lookup
TITLE_INDEX = {title.lower(): title for title in SUMMARIES}
ALL_TITLES_LOWER = list(TITLE_INDEX.keys())

# Deliberately simple substring prefixes, not full NLU - a safety
# net / fallback catch, not a second implementation of intent
# parsing. See DEVELOPMENT.md.
QUESTION_PREFIXES = [
    "who is ", "who was ", "who's ",
    "what is ", "what's ", "what are ",
    "where is ", "where's ", "where are ",
    "tell me about ", "what do you know about ",
]


def _strip_question_prefix(phrase):
    """Returns the subject after a recognized question prefix, or
    None if the phrase doesn't start with one of ours."""
    stripped = phrase.strip().rstrip("?").strip()
    lower = stripped.lower()
    for prefix in QUESTION_PREFIXES:
        if lower.startswith(prefix):
            return stripped[len(prefix):].strip()
    return None


def resolve_title(subject):
    """Exact match first (case-insensitive, with/without a leading
    'the'), then a fuzzy match against all ~9,000 titles as a
    fallback for minor STT variation. Returns a canonical title key
    into SUMMARIES, or None."""
    if not subject:
        return None
    key = subject.strip().lower()
    if key in TITLE_INDEX:
        return TITLE_INDEX[key]
    if key.startswith("the "):
        stripped_key = key[4:]
        if stripped_key in TITLE_INDEX:
            return TITLE_INDEX[stripped_key]
    match, score = match_one(key, ALL_TITLES_LOWER)
    if score >= FUZZY_MATCH_THRESHOLD:
        return TITLE_INDEX[match]
    return None


def lookup_answer(phrase):
    """Full pipeline: strip a question prefix, resolve the remaining
    subject against the title index, return the short spoken answer
    (str) or None. Shared by both the Common Query and fallback
    entry points below - one implementation, two triggers."""
    subject = _strip_question_prefix(phrase)
    if subject is None:
        return None
    title = resolve_title(subject)
    if title is None:
        return None
    return SUMMARIES[title]["extract"]


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
        return _strip_question_prefix(utterances[0]) is not None

    @common_query()
    def handle_common_query(self, phrase, lang):
        """See DEVELOPMENT.md 'Why Common Query + Fallback' - this
        lets the skill compete on equal footing with Wikipedia/DDG/
        Wolfram when the platform's own routing (including the m2v
        misrouting documented in ovos-skill-geometry's DEVELOPMENT.md)
        sends a question to Common Query."""
        if lang.lower() != "en-us":
            return None
        answer = lookup_answer(phrase)
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
        answer = lookup_answer(utterances[0])
        if answer is None:
            return False
        self.speak(answer)
        return True
