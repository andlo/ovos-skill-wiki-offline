"""Tests for the ad-hoc runtime translation fallback
(lookup_answer_via_translation, _get_translator, _translate_text) -
see DEVELOPMENT.md 'Ad-hoc translation for unsupported languages'.

Uses a small fake translator (not the real NLLB model, which is too
heavy for unit tests) that does deterministic word-substitution, so
these tests verify the PIPELINE logic (pivot through en-us, sentence-
splitting, error handling) without needing real translation quality
or model weights."""
from unittest.mock import MagicMock


class FakeTranslator:
    """Deterministic stand-in for a real OVOS LanguageTranslator.
    Recognizes a few fixed phrases in each direction; anything else
    is returned unchanged (good enough to prove the pipeline wires
    calls together correctly)."""

    PHRASES = {
        ("de-de", "en-us", "wer war Charlie Chaplin"): "who was Charlie Chaplin",
        ("en-us", "de-de", "Charlie Chaplin was an English comic actor, filmmaker, and composer who rose to fame in the era of silent film."):
            "Charlie Chaplin war ein englischer Comic-Schauspieler.",
    }

    def translate(self, text, target, source):
        key = (source, target, text)
        if key in self.PHRASES:
            return self.PHRASES[key]
        return text  # unrecognized input - pass through unchanged


def test_lookup_answer_via_translation_full_pipeline(skill):
    from wiki_offline_skill import lookup_answer_via_translation
    fake = FakeTranslator()
    answer = lookup_answer_via_translation("wer war Charlie Chaplin", "de-de", translator=fake)
    assert answer == "Charlie Chaplin war ein englischer Comic-Schauspieler."


def test_lookup_answer_via_translation_supported_lang_returns_none(skill):
    """SUPPORTED_LANGS should never go through the translation path -
    lookup_answer() (the direct, native-data path) handles those."""
    from wiki_offline_skill import lookup_answer_via_translation
    fake = FakeTranslator()
    assert lookup_answer_via_translation("who was Charlie Chaplin", "en-us", translator=fake) is None


def test_lookup_answer_via_translation_no_translator_configured_returns_none(skill, monkeypatch):
    from wiki_offline_skill import lookup_answer_via_translation
    import wiki_offline_skill
    monkeypatch.setattr(wiki_offline_skill, "_get_translator", lambda: None)
    assert lookup_answer_via_translation("wer war Charlie Chaplin", "de-de") is None


def test_lookup_answer_via_translation_unknown_entity_returns_none(skill):
    from wiki_offline_skill import lookup_answer_via_translation
    fake = FakeTranslator()
    # Not in FakeTranslator.PHRASES, passes through unchanged, then
    # fails to resolve against the en-us title index - same "clean
    # None" contract as lookup_answer() itself.
    answer = lookup_answer_via_translation("wer war Irgendjemand Unbekannt", "de-de", translator=fake)
    assert answer is None


def test_lookup_answer_via_translation_translator_exception_returns_none(skill):
    from wiki_offline_skill import lookup_answer_via_translation
    broken = MagicMock()
    broken.translate.side_effect = RuntimeError("model not loaded")
    assert lookup_answer_via_translation("wer war Charlie Chaplin", "de-de", translator=broken) is None


def test_translate_text_splits_sentences_and_rejoins(skill):
    """The real NLLB plugin was confirmed (by hand, during
    development) to silently TRUNCATE a multi-sentence string to
    just its first sentence rather than translating the whole thing
    - see DEVELOPMENT.md. This verifies _translate_text() calls the
    translator once PER SENTENCE rather than once for the whole
    string, and rejoins the results."""
    from wiki_offline_skill import _translate_text
    calls = []

    class RecordingTranslator:
        def translate(self, text, target, source):
            calls.append(text)
            return text.upper()

    result = _translate_text(RecordingTranslator(), "First sentence. Second sentence!", "de-de", "en-us")
    assert calls == ["First sentence.", "Second sentence!"]
    assert result == "FIRST SENTENCE. SECOND SENTENCE!"


def test_get_translator_returns_none_when_unconfigured(skill, monkeypatch):
    """No translation_module configured at all - OVOSLangTranslationFactory
    raises ValueError, which _get_translator() catches and turns into
    a clean None rather than crashing the skill."""
    from wiki_offline_skill import _get_translator
    import ovos_plugin_manager.language as lang_module
    monkeypatch.setattr(
        lang_module.OVOSLangTranslationFactory, "create",
        MagicMock(side_effect=ValueError("`language.translation_module` not configured")))
    assert _get_translator() is None
