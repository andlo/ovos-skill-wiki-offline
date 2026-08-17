"""Tests for question-prefix stripping and title resolution."""
from unittest.mock import MagicMock


def test_strip_question_prefix_who_was(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("who was Charlie Chaplin") == "Charlie Chaplin"


def test_strip_question_prefix_what_is(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("what is the Eiffel Tower") == "the Eiffel Tower"


def test_strip_question_prefix_tell_me_about(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("tell me about tomato") == "tomato"


def test_strip_question_prefix_strips_question_mark(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("who was Charlie Chaplin?") == "Charlie Chaplin"


def test_strip_question_prefix_no_match_returns_none(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("play some music") is None


def test_resolve_title_exact_match(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Charlie Chaplin") == "Charlie Chaplin"


def test_resolve_title_case_insensitive(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("charlie chaplin") == "Charlie Chaplin"


def test_resolve_title_strips_leading_the(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("the Eiffel Tower") == "Eiffel Tower"


def test_resolve_title_fuzzy_match_minor_typo(skill):
    from wiki_offline_skill import resolve_title
    # close enough to "Eiffel Tower" for the fuzzy threshold
    assert resolve_title("Eiffel Towr") == "Eiffel Tower"


def test_resolve_title_unknown_returns_none(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Some Completely Unknown Thing Xyz") is None


def test_resolve_title_empty_returns_none(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("") is None
    assert resolve_title(None) is None
