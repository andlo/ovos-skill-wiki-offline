"""Regression tests against the REAL bundled data/summaries.json (not
the small fixture) - specifically the two topics whose absence from
an earlier version of data/build_data.py motivated switching from
category-tag-based extraction to Wikipedia's own master list. See
DEVELOPMENT.md 'Why the master list, not category tags'.

Skipped automatically if data/summaries.json isn't present (e.g. a
fresh clone before running data/build_data.py)."""
import json
from pathlib import Path

import pytest

_SUMMARIES_PATH = Path(__file__).resolve().parents[1] / "data" / "summaries.json"

pytestmark = pytest.mark.skipif(
    not _SUMMARIES_PATH.exists(),
    reason="data/summaries.json not present - run data/build_data.py first",
)


@pytest.fixture(scope="module")
def real_summaries():
    with open(_SUMMARIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_has_roughly_ten_thousand_titles(real_summaries):
    assert len(real_summaries) > 9900


def test_charlie_chaplin_present(real_summaries):
    """Was silently missing from the category-tag-only extraction -
    see DEVELOPMENT.md."""
    assert "Charlie Chaplin" in real_summaries
    assert "comic actor" in real_summaries["Charlie Chaplin"]["extract"]


def test_photosynthesis_present(real_summaries):
    """Same gap as Charlie Chaplin above - the concrete example that
    motivated switching to the master-list source."""
    assert "Photosynthesis" in real_summaries
    assert "light" in real_summaries["Photosynthesis"]["extract"].lower()


def test_eiffel_tower_present(real_summaries):
    assert "Eiffel Tower" in real_summaries
    assert "Paris" in real_summaries["Eiffel Tower"]["extract"]
