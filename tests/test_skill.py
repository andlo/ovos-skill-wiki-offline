"""Tests for lookup_answer(), handle_common_query(), can_answer(),
and handle_fallback() - the two entry points sharing one resolution
pipeline, across all supported languages. See DEVELOPMENT.md 'Why
Common Query + Fallback'."""
from unittest.mock import MagicMock


def test_lookup_answer_known_entity_en(skill):
    from wiki_offline_skill import lookup_answer
    answer = lookup_answer("who was Charlie Chaplin", "en-us")
    assert "comic actor" in answer


def test_lookup_answer_known_entity_es(skill):
    from wiki_offline_skill import lookup_answer
    answer = lookup_answer("quién fue Charlie Chaplin", "es-es")
    assert "actor cómico" in answer


def test_lookup_answer_known_entity_fr(skill):
    from wiki_offline_skill import lookup_answer
    answer = lookup_answer("qui était Charlie Chaplin", "fr-fr")
    assert "acteur" in answer


def test_lookup_answer_unknown_entity_returns_none(skill):
    from wiki_offline_skill import lookup_answer
    assert lookup_answer("who was Some Random Nobody Xyz", "en-us") is None


def test_lookup_answer_non_question_returns_none(skill):
    from wiki_offline_skill import lookup_answer
    assert lookup_answer("play some music", "en-us") is None


def test_lookup_answer_spanish_gap_returns_none_gracefully(skill):
    """The real, documented Spanish data gap (Tomate/Fotosíntesis
    missing - see DEVELOPMENT.md 'The Spanish gap') should degrade
    to a clean None, not an error, so other Common Query
    participants (Wikipedia, DDG) get a fair shot instead."""
    from wiki_offline_skill import lookup_answer
    assert lookup_answer("cuéntame sobre el Tomate", "es-es") is None


def test_handle_common_query_returns_answer_and_confidence_en(skill):
    answer, confidence = skill.handle_common_query("tell me about tomato", "en-us")
    assert "nightshade" in answer
    assert confidence == 0.8


def test_handle_common_query_es(skill):
    answer, confidence = skill.handle_common_query("quién fue Charlie Chaplin", "es-es")
    assert "actor cómico" in answer
    assert confidence == 0.8


def test_handle_common_query_fr(skill):
    answer, confidence = skill.handle_common_query("qui était Charlie Chaplin", "fr-fr")
    assert "acteur" in answer
    assert confidence == 0.8


def test_handle_common_query_unsupported_lang_without_translator_returns_none(skill):
    # de-de isn't a SUPPORTED_LANGS dataset - falls through to ad-hoc
    # translation (see test_translation.py), which returns None here
    # since no translator plugin is configured in this test
    # environment. See DEVELOPMENT.md "Ad-hoc translation for
    # unsupported languages".
    assert skill.handle_common_query("wer war Charlie Chaplin", "de-de") is None


def test_handle_common_query_unknown_returns_none(skill):
    assert skill.handle_common_query("who was Some Random Nobody Xyz", "en-us") is None


def test_can_answer_true_for_question_shaped_utterance(skill):
    message = MagicMock()
    message.data = {"utterances": ["who was Charlie Chaplin"], "lang": "en-us"}
    assert skill.can_answer(message) is True


def test_can_answer_true_for_spanish_question(skill):
    message = MagicMock()
    message.data = {"utterances": ["quién fue Charlie Chaplin"], "lang": "es-es"}
    assert skill.can_answer(message) is True


def test_can_answer_false_for_non_question(skill):
    message = MagicMock()
    message.data = {"utterances": ["play some music"], "lang": "en-us"}
    assert skill.can_answer(message) is False


def test_can_answer_false_for_empty_utterances(skill):
    message = MagicMock()
    message.data = {"utterances": [], "lang": "en-us"}
    assert skill.can_answer(message) is False


def test_can_answer_falls_back_to_skill_lang_when_missing(skill):
    message = MagicMock()
    message.data = {"utterances": ["who was Charlie Chaplin"]}  # no "lang" key
    assert skill.can_answer(message) is True


def test_can_answer_unsupported_lang_true_when_translator_configured(skill, monkeypatch):
    """See DEVELOPMENT.md 'Ad-hoc translation for unsupported
    languages': can_answer() checks _translator_configured() (a fast
    config lookup) rather than _get_translator() (which can block for
    ~40s on a first-time model load - caught live, see DEVELOPMENT.md)."""
    import wiki_offline_skill
    monkeypatch.setattr(wiki_offline_skill, "_translator_configured", lambda: True)
    message = MagicMock()
    message.data = {"utterances": ["wer war Charlie Chaplin"], "lang": "de-de"}
    assert skill.can_answer(message) is True


def test_can_answer_unsupported_lang_false_without_translator(skill, monkeypatch):
    import wiki_offline_skill
    monkeypatch.setattr(wiki_offline_skill, "_translator_configured", lambda: False)
    message = MagicMock()
    message.data = {"utterances": ["wer war Charlie Chaplin"], "lang": "de-de"}
    assert skill.can_answer(message) is False


def test_handle_fallback_speaks_and_returns_true_on_match_en(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["tell me about tomato"], "lang": "en-us"}
    result = skill.handle_fallback(message)
    assert result is True
    skill.speak.assert_called_once()
    spoken = skill.speak.call_args[0][0]
    assert "nightshade" in spoken


def test_handle_fallback_speaks_french(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["parle-moi de la Tomate"], "lang": "fr-fr"}
    result = skill.handle_fallback(message)
    assert result is True
    spoken = skill.speak.call_args[0][0]
    assert "Solanacées" in spoken


def test_handle_fallback_returns_false_without_speaking_on_no_match(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["who was Some Random Nobody Xyz"], "lang": "en-us"}
    result = skill.handle_fallback(message)
    assert result is False
    skill.speak.assert_not_called()


def test_handle_fallback_spanish_gap_returns_false_gracefully(skill):
    skill.speak = MagicMock()
    message = MagicMock()
    message.data = {"utterances": ["cuéntame sobre el Tomate"], "lang": "es-es"}
    result = skill.handle_fallback(message)
    assert result is False
    skill.speak.assert_not_called()
