"""Tests for question-prefix stripping and title resolution, across
all supported languages."""


def test_strip_question_prefix_who_was_en(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("who was Charlie Chaplin", "en-us") == "Charlie Chaplin"


def test_strip_question_prefix_what_is_en(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("what is the Eiffel Tower", "en-us") == "the Eiffel Tower"


def test_strip_question_prefix_tell_me_about_en(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("tell me about tomato", "en-us") == "tomato"


def test_strip_question_prefix_strips_question_mark(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("who was Charlie Chaplin?", "en-us") == "Charlie Chaplin"


def test_strip_question_prefix_no_match_returns_none(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("play some music", "en-us") is None


def test_strip_question_prefix_es(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("quién fue Charlie Chaplin", "es-es") == "Charlie Chaplin"
    assert _strip_question_prefix("cuéntame sobre el Tomate", "es-es") == "el Tomate"


def test_strip_question_prefix_fr(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("qui était Charlie Chaplin", "fr-fr") == "Charlie Chaplin"
    assert _strip_question_prefix("parle-moi de la Tomate", "fr-fr") == "la Tomate"


def test_strip_question_prefix_unsupported_lang_returns_none(skill):
    from wiki_offline_skill import _strip_question_prefix
    assert _strip_question_prefix("who was Charlie Chaplin", "de-de") is None


def test_resolve_title_exact_match(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Charlie Chaplin", "en-us") == "Charlie Chaplin"


def test_resolve_title_case_insensitive(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("charlie chaplin", "en-us") == "Charlie Chaplin"


def test_resolve_title_strips_leading_article_en(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("the Eiffel Tower", "en-us") == "Eiffel Tower"


def test_resolve_title_strips_leading_article_es(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("la Torre Eiffel", "es-es") == "Torre Eiffel"


def test_resolve_title_strips_leading_article_fr(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("la Tour Eiffel", "fr-fr") == "Tour Eiffel"


def test_resolve_title_fuzzy_match_minor_typo(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Eiffel Towr", "en-us") == "Eiffel Tower"


def test_resolve_title_unknown_returns_none(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Some Completely Unknown Thing Xyz", "en-us") is None


def test_resolve_title_empty_returns_none(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("", "en-us") is None
    assert resolve_title(None, "en-us") is None


def test_resolve_title_unsupported_lang_returns_none(skill):
    from wiki_offline_skill import resolve_title
    assert resolve_title("Charlie Chaplin", "de-de") is None
