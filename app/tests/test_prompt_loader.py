"""
app/tests/test_prompt_loader.py
---------------------------------
Unit tests for services/prompt_loader.py.

Tests cover:
- loads known prompt files from disk
- caches result (lru_cache hit on repeated call)
- rejects path traversal attempts
- rejects unknown prompt names
- raises PromptLoadError when file is missing (allowlist entry with no file)

No AWS credentials, network, or LLM calls required.
"""

from __future__ import annotations

import pytest

import services.prompt_loader as loader_module
from services.prompt_loader import PromptLoadError, load_prompt


def _clear_cache() -> None:
    """Clear the lru_cache so each test starts from a clean state."""
    load_prompt.cache_clear()


class TestLoadPromptKnownFiles:
    def test_loads_query_classifier_prompt(self):
        _clear_cache()
        text = load_prompt("query_classifier")
        assert len(text) > 50  # non-trivial content

    def test_loads_answer_generator_prompt(self):
        _clear_cache()
        text = load_prompt("answer_generator")
        assert len(text) > 50

    def test_classifier_prompt_is_string(self):
        _clear_cache()
        text = load_prompt("query_classifier")
        assert isinstance(text, str)

    def test_answer_generator_prompt_is_string(self):
        _clear_cache()
        text = load_prompt("answer_generator")
        assert isinstance(text, str)


class TestPromptCaching:
    def test_caches_repeated_load(self):
        _clear_cache()
        text1 = load_prompt("query_classifier")
        text2 = load_prompt("query_classifier")
        # Same object returned from cache
        assert text1 == text2
        info = load_prompt.cache_info()
        assert info.hits >= 1

    def test_cache_miss_on_first_call(self):
        _clear_cache()
        load_prompt("query_classifier")
        info = load_prompt.cache_info()
        assert info.misses >= 1

    def test_two_different_prompts_cached_independently(self):
        _clear_cache()
        t1 = load_prompt("query_classifier")
        t2 = load_prompt("answer_generator")
        # Both cached; contents differ
        assert t1 != t2
        info = load_prompt.cache_info()
        assert info.currsize == 2


class TestPathTraversalRejection:
    def test_path_traversal_dot_dot(self):
        _clear_cache()
        with pytest.raises(PromptLoadError):
            load_prompt("../config")

    def test_path_traversal_slash_prefix(self):
        _clear_cache()
        with pytest.raises(PromptLoadError):
            load_prompt("/etc/passwd")

    def test_empty_string_rejected(self):
        _clear_cache()
        with pytest.raises(PromptLoadError):
            load_prompt("")

    def test_unknown_name_rejected(self):
        _clear_cache()
        with pytest.raises(PromptLoadError):
            load_prompt("nonexistent_prompt")

    def test_extension_suffix_rejected(self):
        """Name with .md extension is not in allowlist — only bare names are."""
        _clear_cache()
        with pytest.raises(PromptLoadError):
            load_prompt("query_classifier.md")


class TestMissingFile:
    def test_missing_file_raises_prompt_load_error(self, monkeypatch):
        """Allowlist entry that has no corresponding file raises PromptLoadError."""
        _clear_cache()
        # Temporarily extend the allowlist to include a name with no file.
        monkeypatch.setattr(
            loader_module,
            "_ALLOWED_PROMPTS",
            frozenset({"missing_prompt"}),
        )
        with pytest.raises(PromptLoadError, match="not found"):
            load_prompt("missing_prompt")
        _clear_cache()
