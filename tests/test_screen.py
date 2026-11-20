"""The answer on a screen (issue #4): the article's title and the answer as text."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def wiki(skill):
    import sys
    return sys.modules[type(skill).__module__]


def test_fallback_shows_title_and_answer(skill, wiki):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["who was charlie chaplin"], "lang": "en-us"}
    assert skill.handle_fallback(message) is True
    skill.gui.show_text.assert_called_once()
    args, kwargs = skill.gui.show_text.call_args
    assert args[0].startswith("Charlie Chaplin was")
    assert kwargs == {"title": "Charlie Chaplin", "override_idle": wiki.SCREEN_SECONDS}


def test_no_answer_shows_nothing(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["who was Some Random Nobody Xyz"], "lang": "en-us"}
    assert skill.handle_fallback(message) is False
    skill.gui.show_text.assert_not_called()


def test_common_query_callback_shows_the_answer(skill):
    skill._cq_selected("what is the eiffel tower", "The Eiffel Tower is ...", "en-US")
    args, kwargs = skill.gui.show_text.call_args
    assert args[0] == "The Eiffel Tower is ..."
    assert kwargs["title"] == "Eiffel Tower"


def test_common_query_registers_the_callback(skill, wiki):
    assert skill.handle_common_query.cq_callback is wiki.WikiOffline._cq_selected


def test_translated_answer_shows_without_title(skill):
    skill._cq_selected("hvem var charlie chaplin", "Charlie Chaplin var ...", "de-de")
    args, kwargs = skill.gui.show_text.call_args
    assert kwargs["title"] is None
