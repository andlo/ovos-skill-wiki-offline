"""Tests for lookup_answer(), handle_common_query(), can_answer(),
and handle_fallback() - the two entry points sharing one resolution
pipeline. See DEVELOPMENT.md 'Why Common Query + Fallback'."""
from unittest.mock import MagicMock


def test_lookup_answer_known_entity(skill):
    from wiki_offline_skill import lookup_answer
    answer = lookup_answer("who was Charlie Chaplin")
    assert "comic actor" in answer


def test_lookup_answer_unknown_entity_returns_none(skill):
    from wiki_offline_skill import lookup_answer
    assert lookup_answer("who was Some Random Nobody Xyz") is None


def test_lookup_answer_non_question_returns_none(skill):
    from wiki_offline_skill import lookup_answer
    assert lookup_answer("play some music") is None


def test_handle_common_query_returns_answer_and_confidence(skill):
    answer, confidence = skill.handle_common_query("what is the Eiffel Tower", "en-us")
    assert "Paris" in answer
    assert confidence == 0.8


def test_handle_common_query_non_english_returns_none(skill):
    # English only in v1 - see DEVELOPMENT.md
    assert skill.handle_common_query("qui était Charlie Chaplin", "fr-fr") is None


def test_handle_common_query_unknown_returns_none(skill):
    assert skill.handle_common_query("who was Some Random Nobody Xyz", "en-us") is None


def test_can_answer_true_for_question_shaped_utterance(skill):
    message = MagicMock()
    message.data = {"utterances": ["who was Charlie Chaplin"]}
    assert skill.can_answer(message) is True


def test_can_answer_false_for_non_question(skill):
    message = MagicMock()
    message.data = {"utterances": ["play some music"]}
    assert skill.can_answer(message) is False


def test_can_answer_false_for_empty_utterances(skill):
    message = MagicMock()
    message.data = {"utterances": []}
    assert skill.can_answer(message) is False


def test_handle_fallback_speaks_and_returns_true_on_match(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["tell me about tomato"]}
    result = skill.handle_fallback(message)
    assert result is True
    skill.speak.assert_called_once()
    spoken = skill.speak.call_args[0][0]
    assert "nightshade" in spoken


def test_handle_fallback_returns_false_without_speaking_on_no_match(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["who was Some Random Nobody Xyz"]}
    result = skill.handle_fallback(message)
    assert result is False
    skill.speak.assert_not_called()
