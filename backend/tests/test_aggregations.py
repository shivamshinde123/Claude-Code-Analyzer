"""Unit tests for backend aggregation utilities."""

import pytest

from src.utils.aggregations import (
    calculate_quality_score,
    compute_rolling_average,
    detect_error_patterns,
    detect_trend,
)


# ── calculate_quality_score ────────────────────────────────────────────


class TestCalculateQualityScore:
    def test_perfect_score(self):
        score = calculate_quality_score(
            cyclomatic_complexity=1.0,
            lines_of_code=10,
            has_type_hints=True,
            max_nesting_depth=1,
        )
        assert score == pytest.approx(0.96, abs=0.01)

    def test_worst_complexity(self):
        score = calculate_quality_score(
            cyclomatic_complexity=10.0,
            lines_of_code=100,
            has_type_hints=False,
            max_nesting_depth=5,
        )
        # complexity=0, hints=0.1, nesting=0.1 → 0.2
        assert score == pytest.approx(0.2, abs=0.01)

    def test_all_none_gives_neutral(self):
        score = calculate_quality_score(
            cyclomatic_complexity=None,
            lines_of_code=None,
            has_type_hints=False,
        )
        # neutral complexity=0.2, no hints=0.1, no nesting=0.15 → 0.45
        assert score == pytest.approx(0.45, abs=0.01)

    def test_clamped_to_0_1(self):
        score = calculate_quality_score(
            cyclomatic_complexity=50.0,
            lines_of_code=1000,
            has_type_hints=False,
            max_nesting_depth=20,
        )
        assert 0.0 <= score <= 1.0

    def test_type_hints_boost(self):
        without = calculate_quality_score(1.0, 10, has_type_hints=False, max_nesting_depth=1)
        with_hints = calculate_quality_score(1.0, 10, has_type_hints=True, max_nesting_depth=1)
        assert with_hints > without


# ── detect_error_patterns ──────────────────────────────────────────────


class TestDetectErrorPatterns:
    def test_empty_list(self):
        result = detect_error_patterns([])
        assert result["distribution"] == {}
        assert result["most_common"] is None
        assert result["avg_recovery"] == 0.0
        assert result["recovery_rate"] == 0.0

    def test_single_error(self):
        result = detect_error_patterns([
            {
                "error_type": "syntax",
                "recovery_interactions_count": 2,
                "was_resolved_in_next_interaction": True,
            }
        ])
        assert result["distribution"] == {"syntax": 1}
        assert result["most_common"] == "syntax"
        assert result["avg_recovery"] == 2.0
        assert result["recovery_rate"] == 1.0

    def test_multiple_types(self):
        errors = [
            {"error_type": "syntax", "recovery_interactions_count": 1, "was_resolved_in_next_interaction": True},
            {"error_type": "syntax", "recovery_interactions_count": 3, "was_resolved_in_next_interaction": False},
            {"error_type": "runtime", "recovery_interactions_count": 2, "was_resolved_in_next_interaction": True},
        ]
        result = detect_error_patterns(errors)
        assert result["distribution"] == {"syntax": 2, "runtime": 1}
        assert result["most_common"] == "syntax"
        assert result["avg_recovery"] == 2.0
        assert result["recovery_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_no_recovery_counts(self):
        errors = [
            {"error_type": "logic", "recovery_interactions_count": None, "was_resolved_in_next_interaction": False},
        ]
        result = detect_error_patterns(errors)
        assert result["avg_recovery"] == 0.0


# ── compute_rolling_average ────────────────────────────────────────────


class TestComputeRollingAverage:
    def test_short_data_returns_as_is(self):
        data = [("2025-01-01", 1.0), ("2025-01-02", 2.0)]
        result = compute_rolling_average(data, window=5)
        assert result == data

    def test_correct_window(self):
        data = [
            ("2025-01-01", 1.0),
            ("2025-01-02", 2.0),
            ("2025-01-03", 3.0),
            ("2025-01-04", 4.0),
            ("2025-01-05", 5.0),
        ]
        result = compute_rolling_average(data, window=3)
        # Window 1: (1+2+3)/3=2.0, Window 2: (2+3+4)/3=3.0, Window 3: (3+4+5)/3=4.0
        assert len(result) == 3
        assert result[0] == ("2025-01-03", 2.0)
        assert result[1] == ("2025-01-04", 3.0)
        assert result[2] == ("2025-01-05", 4.0)

    def test_empty_data(self):
        result = compute_rolling_average([], window=3)
        assert result == []


# ── detect_trend ───────────────────────────────────────────────────────


class TestDetectTrend:
    def test_too_few_values_is_stable(self):
        assert detect_trend([1.0, 2.0]) == "stable"

    def test_improving(self):
        values = [0.3, 0.3, 0.3, 0.3, 0.8, 0.8, 0.8, 0.8]
        assert detect_trend(values) == "improving"

    def test_declining(self):
        values = [0.8, 0.8, 0.8, 0.8, 0.3, 0.3, 0.3, 0.3]
        assert detect_trend(values) == "declining"

    def test_stable(self):
        values = [0.5, 0.5, 0.5, 0.5, 0.52, 0.52, 0.52, 0.52]
        assert detect_trend(values) == "stable"
