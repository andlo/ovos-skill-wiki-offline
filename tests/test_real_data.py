"""Regression tests against the REAL bundled data/summaries_<lang>.json
files (not the small fixture) - one per supported language, each
skipped individually if its data file isn't present (e.g. a fresh
clone before running data/build_data.py <lang>).

en-us: Charlie Chaplin/Photosynthesis are the two topics whose
absence from an earlier version of data/build_data.py motivated
switching from category-tag-based extraction to Wikipedia's own
master list - see DEVELOPMENT.md "Why the master list, not category
tags".

es-es: Tomate/Fotosíntesis are EXPECTED absent (the real, documented
"Spanish gap" - see DEVELOPMENT.md), tested as an explicit assertion
of the known gap rather than treated as a bug.
"""
import json
from pathlib import Path

import pytest

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load(lang):
    path = _DATA_DIR / f"summaries_{lang}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def en_summaries():
    data = _load("en-us")
    if data is None:
        pytest.skip("data/summaries_en-us.json not present")
    return data


@pytest.fixture(scope="module")
def es_summaries():
    data = _load("es-es")
    if data is None:
        pytest.skip("data/summaries_es-es.json not present")
    return data


@pytest.fixture(scope="module")
def fr_summaries():
    data = _load("fr-fr")
    if data is None:
        pytest.skip("data/summaries_fr-fr.json not present")
    return data


def test_en_has_roughly_ten_thousand_titles(en_summaries):
    assert len(en_summaries) > 9900


def test_en_charlie_chaplin_present(en_summaries):
    assert "Charlie Chaplin" in en_summaries
    assert "comic actor" in en_summaries["Charlie Chaplin"]["extract"]


def test_en_photosynthesis_present(en_summaries):
    assert "Photosynthesis" in en_summaries
    assert "light" in en_summaries["Photosynthesis"]["extract"].lower()


def test_en_eiffel_tower_present(en_summaries):
    assert "Eiffel Tower" in en_summaries
    assert "Paris" in en_summaries["Eiffel Tower"]["extract"]


def test_es_has_at_least_six_thousand_titles(es_summaries):
    """Smaller than en-us/fr-fr by design - see DEVELOPMENT.md "The
    Spanish gap" (3 of 11 native topic categories don't exist)."""
    assert len(es_summaries) > 6000


def test_es_charlie_chaplin_present(es_summaries):
    assert "Charlie Chaplin" in es_summaries
    assert "actor" in es_summaries["Charlie Chaplin"]["extract"].lower()


def test_es_eiffel_tower_present(es_summaries):
    assert "Torre Eiffel" in es_summaries
    assert "París" in es_summaries["Torre Eiffel"]["extract"]


def test_es_tomate_and_fotosintesis_are_the_known_gap(es_summaries):
    """Explicit assertion of the documented gap, not an oversight -
    if either of these starts appearing (e.g. Spanish Wikipedia
    eventually writes the missing Biología category), this test
    should be updated, not treated as newly broken."""
    assert "Tomate" not in es_summaries
    assert "Fotosíntesis" not in es_summaries


def test_fr_has_roughly_ten_thousand_titles(fr_summaries):
    assert len(fr_summaries) > 9900


def test_fr_charlie_chaplin_present(fr_summaries):
    assert "Charlie Chaplin" in fr_summaries
    assert "acteur" in fr_summaries["Charlie Chaplin"]["extract"]


def test_fr_photosynthese_present(fr_summaries):
    assert "Photosynthèse" in fr_summaries


def test_fr_tomate_present(fr_summaries):
    """Confirms fr-fr does NOT have the es-es gap - full native
    coverage, all 11 topic categories exist."""
    assert "Tomate" in fr_summaries


def test_fr_tour_eiffel_present(fr_summaries):
    assert "Tour Eiffel" in fr_summaries
    assert "Paris" in fr_summaries["Tour Eiffel"]["extract"]
