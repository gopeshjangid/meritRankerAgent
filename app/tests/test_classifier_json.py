"""Tests for strict classifier JSON parsing."""

from __future__ import annotations

import pytest

from services.doubt_solver.classifier_json import ClassifierJsonError, parse_classifier_json_strict

_VALID = (
    '{"intent":"solve_question","subject":"math","topic":null,'
    '"topic_confidence":0.9,"pattern_topic_candidate":null,'
    '"pattern_family_candidate":null,"retrieval_tags":[],"difficulty":"default",'
    '"response_style":"step_by_step","confidence":0.9,"retrieval_need":"similar_question",'
    '"reasoning_summary":null,"need_web_search":false,"web_search_reason":null,'
    '"web_search_query":null}'
)


class TestClassifierJsonStrict:
    def test_valid_single_json_passes(self) -> None:
        parsed, recovered = parse_classifier_json_strict(_VALID)
        assert parsed["subject"] == "math"
        assert recovered is False

    def test_json_plus_trailing_text_fails(self) -> None:
        with pytest.raises(ClassifierJsonError) as exc_info:
            parse_classifier_json_strict(_VALID + "\nextra")
        assert exc_info.value.error_type == "extra_trailing_text"

    def test_two_json_objects_fail(self) -> None:
        with pytest.raises(ClassifierJsonError):
            parse_classifier_json_strict(_VALID + _VALID)

    def test_markdown_fenced_json_recovers_with_flag(self) -> None:
        fenced = f"```json\n{_VALID}\n```"
        parsed, recovered = parse_classifier_json_strict(fenced)
        assert parsed["subject"] == "math"
        assert recovered is True

    def test_empty_output_fails(self) -> None:
        with pytest.raises(ClassifierJsonError) as exc_info:
            parse_classifier_json_strict("   ")
        assert exc_info.value.error_type == "empty_output"
