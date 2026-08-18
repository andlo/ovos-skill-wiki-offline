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
# data/summaries_<lang>.json has (or hasn't) fetched on disk. Mirrors
# the real REST API shape and the exact examples verified against the
# live API during development (see DEVELOPMENT.md). "Tomate"/
# "Fotosíntesis" are deliberately ABSENT from es-es here too, mirroring
# the real, documented Spanish gap (see DEVELOPMENT.md "The Spanish
# gap") - tests rely on this absence to verify the gap is handled
# gracefully (returns None, doesn't crash), not just to have data.
FIXTURE_SUMMARIES = {
    "en-us": {
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
    },
    "es-es": {
        "Charlie Chaplin": {
            "title": "Charlie Chaplin",
            "extract": "Charles Spencer Chaplin fue un actor cómico, cineasta y compositor inglés que alcanzó la fama en la era del cine mudo.",
            "description": "Actor cómico y cineasta inglés",
            "topic": "Personas",
        },
        "Torre Eiffel": {
            "title": "Torre Eiffel",
            "extract": "La torre Eiffel es una estructura de hierro situada en el Campo de Marte, en París, Francia.",
            "description": "Estructura emblemática en París",
            "topic": "Geografía",
        },
        # Tomate/Fotosíntesis deliberately absent - see docstring above
    },
    "fr-fr": {
        "Charlie Chaplin": {
            "title": "Charlie Chaplin",
            "extract": "Charlie Chaplin est un acteur, réalisateur et compositeur britannique, né en 1889 à Londres.",
            "description": "Acteur et réalisateur britannique",
            "topic": "Personnalités",
        },
        "Tour Eiffel": {
            "title": "Tour Eiffel",
            "extract": "La tour Eiffel est une tour de fer puddlé située à Paris, à l'extrémité du parc du Champ-de-Mars.",
            "description": "Tour emblématique à Paris",
            "topic": "Géographie",
        },
        "Tomate": {
            "title": "Tomate",
            "extract": "La tomate est une espèce de plantes herbacées de la famille des Solanacées, originaire du Mexique.",
            "description": "Légume-fruit",
            "topic": "Science",
        },
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
    # whatever data/summaries_<lang>.json actually contains on disk.
    monkeypatch.setattr(_module, "SUMMARIES_BY_LANG", FIXTURE_SUMMARIES)
    title_index = {
        lang: {t.lower(): t for t in summaries}
        for lang, summaries in FIXTURE_SUMMARIES.items()
    }
    monkeypatch.setattr(_module, "TITLE_INDEX_BY_LANG", title_index)
    monkeypatch.setattr(_module, "ALL_TITLES_LOWER_BY_LANG",
                        {lang: list(idx.keys()) for lang, idx in title_index.items()})

    # _get_translator() caches its result across calls (see its own
    # docstring for why) - reset that cache per test so one test's
    # translator (real or mocked) can't leak into another.
    monkeypatch.setattr(_module, "_translator_cache", {})

    return s
