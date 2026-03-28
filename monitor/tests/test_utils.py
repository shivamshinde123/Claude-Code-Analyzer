"""Unit tests for monitor utility functions."""

import pytest

from src.utils import (
    extract_language,
    estimate_tokens,
    calculate_nesting_depth,
    compute_code_metrics,
    classify_interaction,
    parse_error_message,
)


# ── extract_language ───────────────────────────────────────────────────


class TestExtractLanguage:
    def test_python(self):
        assert extract_language("main.py") == "python"

    def test_javascript(self):
        assert extract_language("app.js") == "javascript"
        assert extract_language("Component.jsx") == "javascript"

    def test_typescript(self):
        assert extract_language("index.ts") == "typescript"
        assert extract_language("App.tsx") == "typescript"

    def test_go(self):
        assert extract_language("server.go") == "go"

    def test_unknown_extension(self):
        assert extract_language("Makefile") == "unknown"
        assert extract_language("data.csv") == "unknown"

    def test_path_with_directories(self):
        assert extract_language("/home/user/project/src/main.py") == "python"


# ── estimate_tokens ────────────────────────────────────────────────────


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_text(self):
        assert estimate_tokens("hi") == 1  # max(1, 2//4)

    def test_normal_text(self):
        text = "def hello_world(): print('hello')"
        result = estimate_tokens(text)
        assert result == len(text) // 4


# ── calculate_nesting_depth ────────────────────────────────────────────


class TestCalculateNestingDepth:
    def test_flat_python(self):
        code = "x = 1\ny = 2\nprint(x + y)"
        assert calculate_nesting_depth(code, "python") == 0

    def test_nested_python(self):
        code = "def f():\n    if True:\n        for i in range(10):\n            print(i)"
        depth = calculate_nesting_depth(code, "python")
        assert depth == 3  # function > if > for

    def test_invalid_python_falls_back(self):
        code = "def f(\n    pass"
        depth = calculate_nesting_depth(code, "python")
        assert isinstance(depth, int)

    def test_javascript_indentation(self):
        code = "function f() {\n    if (true) {\n        console.log('hi')\n    }\n}"
        depth = calculate_nesting_depth(code, "javascript")
        assert depth >= 2


# ── compute_code_metrics ───────────────────────────────────────────────


class TestComputeCodeMetrics:
    def test_python_simple_function(self):
        code = "def hello():\n    print('hello')"
        metrics = compute_code_metrics(code, "python")
        assert metrics["lines_of_code"] == 2
        assert metrics["function_count"] == 1
        assert metrics["class_count"] == 0
        assert metrics["cyclomatic_complexity"] == 1.0
        assert metrics["has_type_hints"] is False
        assert 0 <= metrics["code_quality_score"] <= 1

    def test_python_with_type_hints(self):
        code = "def greet(name: str) -> str:\n    return f'Hello {name}'"
        metrics = compute_code_metrics(code, "python")
        assert metrics["has_type_hints"] is True
        # Quality score should be higher with type hints
        no_hints = compute_code_metrics("def greet(name):\n    return f'Hello {name}'", "python")
        assert metrics["code_quality_score"] > no_hints["code_quality_score"]

    def test_python_with_branches(self):
        code = "def f(x):\n    if x > 0:\n        return x\n    else:\n        return -x"
        metrics = compute_code_metrics(code, "python")
        assert metrics["cyclomatic_complexity"] >= 2.0

    def test_javascript_function(self):
        code = "function hello() { console.log('hello') }"
        metrics = compute_code_metrics(code, "javascript")
        assert metrics["function_count"] == 1
        assert metrics["cyclomatic_complexity"] >= 1.0

    def test_empty_code(self):
        metrics = compute_code_metrics("", "python")
        assert metrics["lines_of_code"] == 0


# ── classify_interaction ───────────────────────────────────────────────


class TestClassifyInteraction:
    def test_short_is_bugfix(self):
        assert classify_interaction("x = 1") == "bugfix"

    def test_many_defs_is_new_code(self):
        # Must be > 100 chars to avoid the bugfix short-circuit
        code = "def validate_email(email):\n    import re\n    return bool(re.match(r'^[a-z]+@[a-z]+\\.[a-z]+$', email))\n\ndef validate_phone(phone):\n    return len(phone) == 10"
        assert classify_interaction(code) == "new_code"

    def test_medium_code_is_refactor(self):
        code = "x = 1\n" * 30  # 30 lines, no defs
        assert classify_interaction(code) == "refactor"

    def test_mostly_comments_is_explanation(self):
        code = "# This is a comment\n# explaining something\n# in detail\n# more explanation\n# end\nx = 1"
        assert classify_interaction(code) == "explanation"


# ── parse_error_message ────────────────────────────────────────────────


class TestParseErrorMessage:
    def test_syntax_error(self):
        error_type, severity = parse_error_message("SyntaxError: invalid syntax at line 5")
        assert error_type == "syntax"
        assert severity == "medium"

    def test_type_error(self):
        error_type, severity = parse_error_message("TypeError: cannot add str and int")
        assert error_type == "type"

    def test_runtime_error(self):
        error_type, severity = parse_error_message("NameError: name 'x' is not defined")
        assert error_type == "runtime"

    def test_logic_error(self):
        error_type, severity = parse_error_message("Wrong output: expected 5, got 3")
        assert error_type == "logic"

    def test_high_severity(self):
        _, severity = parse_error_message("CRITICAL: SQL injection vulnerability detected")
        assert severity == "high"

    def test_low_severity(self):
        _, severity = parse_error_message("DeprecationWarning: this function is deprecated")
        assert severity == "low"
