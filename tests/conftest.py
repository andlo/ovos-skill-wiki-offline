"""Shared pytest fixtures for the wiki-offline skill test suite."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_INIT_PATH = Path(__file__).resolve().parents[1] / "__init__.py"
_spec = importlib.util.spec_from_file_location("wiki_offline_skill", _INIT_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["wiki_offline_skill"] = _module
_spec.loader.exec_module(_module)

WikiOffline = _module.WikiOffline

# Small, deterministic fixture dataset - independent of whatever
# data/build_data.py has (or hasn't) fetched on disk at test time.
# Mirrors the real REST API shape and the exact examples verified
# against the live API during development (see DEVELOPMENT.md).
FIXTURE_SUMMARIES = {
    "Charlie Chaplin": {
        "title": "Charlie Chaplin",
        "extract": "Charlie Chaplin was an English comic actor, filmmaker, and composer who rose to fame in the era of silent film.",
        "description": "English comic actor and filmmaker",
        "topic": "People",
    },
    "Eiffel Tower": {
        "title": "Eiffel Tower",
        "extract": "The Eiffel Tower is a lattice tower on the Champ de Mars in Paris, France.",
        "description": "Landmark tower in Paris, France",
        "topic": "Geography",
    },
    "Tomato": {
        "title": "Tomato",
        "extract": "The tomato is a plant whose fruit is an edible berry. It is a member of the nightshade family that includes tobacco and potato.",
        "description": "Edible berry, culinary vegetable",
        "topic": "Biology and health sciences",
    },
}


@pytest.fixture
def skill(monkeypatch):
    s = WikiOffline.__new__(WikiOffline)
    s.log = MagicMock()
    s.skill_id = "ovos-skill-wiki-offline.test"
    s.status = MagicMock()
    s._bus = MagicMock()
    monkeypatch.setattr(WikiOffline, "lang", "en-us", raising=False)
    s.res_dir = str(Path(__file__).resolve().parents[1])
    s._lang_resources = {}

    # Point the module-level data at our small fixture set, not
    # whatever data/summaries.json actually contains on disk.
    monkeypatch.setattr(_module, "SUMMARIES", FIXTURE_SUMMARIES)
    title_index = {t.lower(): t for t in FIXTURE_SUMMARIES}
    monkeypatch.setattr(_module, "TITLE_INDEX", title_index)
    monkeypatch.setattr(_module, "ALL_TITLES_LOWER", list(title_index.keys()))

    return s
