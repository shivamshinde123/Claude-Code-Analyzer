"""Helper functions for the monitor service."""

import ast
import os
import re
from typing import Dict, Optional, Tuple

# Extension → language mapping
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
}


def extract_language(file_path: str) -> str:
    """Determine programming language from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return LANGUAGE_EXTENSIONS.get(ext, "unknown")


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token)."""
    return max(1, len(text) // 4)


def calculate_nesting_depth(code: str, language: str) -> int:
    """Calculate maximum nesting depth of code.

    Uses AST for Python, indentation heuristic for other languages.
    """
    if language == "python":
        return _python_nesting_depth(code)
    return _indent_nesting_depth(code)


def _python_nesting_depth(code: str) -> int:
    """Walk the Python AST to find max nesting depth."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _indent_nesting_depth(code)

    max_depth = 0

    def _walk(node: ast.AST, depth: int) -> None:
        nonlocal max_depth
        nesting_nodes = (
            ast.If, ast.For, ast.While, ast.With,
            ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
        )
        if isinstance(node, nesting_nodes):
            depth += 1
            max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(node):
            _walk(child, depth)

    _walk(tree, 0)
    return max_depth


def _indent_nesting_depth(code: str) -> int:
    """Estimate nesting depth from indentation levels."""
    max_depth = 0
    for line in code.splitlines():
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        # Assume 4-space or 2-space indent
        depth = indent // 2
        max_depth = max(max_depth, depth)
    return max_depth


def compute_code_metrics(code: str, language: str) -> Dict:
    """Compute static analysis metrics from a code snippet.

    Returns dict with: cyclomatic_complexity, lines_of_code, function_count,
    class_count, max_nesting_depth, has_type_hints, code_quality_score.
    """
    metrics: Dict = {
        "cyclomatic_complexity": None,
        "lines_of_code": None,
        "function_count": None,
        "class_count": None,
        "max_nesting_depth": None,
        "has_type_hints": None,
        "code_quality_score": None,
    }

    # Lines of code (non-blank, non-comment)
    lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
    metrics["lines_of_code"] = len(lines)

    if language == "python":
        metrics.update(_python_metrics(code))
    elif language in ("javascript", "typescript"):
        metrics.update(_js_metrics(code))

    metrics["max_nesting_depth"] = calculate_nesting_depth(code, language)
    metrics["code_quality_score"] = _calculate_quality_score(metrics)
    return metrics


def _python_metrics(code: str) -> Dict:
    """Extract metrics from Python code using AST."""
    result: Dict = {
        "cyclomatic_complexity": None,
        "function_count": None,
        "class_count": None,
        "has_type_hints": None,
    }
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return result

    nodes = list(ast.walk(tree))
    result["function_count"] = sum(
        1 for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    result["class_count"] = sum(
        1 for n in nodes if isinstance(n, ast.ClassDef)
    )

    # Cyclomatic complexity: count decision points + 1
    decision_nodes = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)
    decisions = sum(1 for n in nodes if isinstance(n, decision_nodes))
    # Count boolean operators (and/or)
    bool_ops = sum(1 for n in nodes if isinstance(n, ast.BoolOp))
    result["cyclomatic_complexity"] = float(1 + decisions + bool_ops)

    # Type hints: check if any function has annotations
    has_hints = False
    for n in nodes:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.returns is not None or any(arg.annotation for arg in n.args.args):
                has_hints = True
                break
    result["has_type_hints"] = has_hints
    return result


def _js_metrics(code: str) -> Dict:
    """Extract metrics from JavaScript/TypeScript using regex."""
    result: Dict = {
        "cyclomatic_complexity": None,
        "function_count": None,
        "class_count": None,
        "has_type_hints": None,
    }

    # Function count
    fn_patterns = [
        r"\bfunction\s+\w+",      # function declarations
        r"\bconst\s+\w+\s*=\s*\(", # arrow functions
        r"\blet\s+\w+\s*=\s*\(",
    ]
    fn_count = sum(len(re.findall(p, code)) for p in fn_patterns)
    result["function_count"] = fn_count

    # Class count
    result["class_count"] = len(re.findall(r"\bclass\s+\w+", code))

    # Cyclomatic complexity
    decision_keywords = [r"\bif\b", r"\belse\s+if\b", r"\bfor\b", r"\bwhile\b",
                         r"\bcatch\b", r"\bcase\b", r"\b\?\b"]
    decisions = sum(len(re.findall(p, code)) for p in decision_keywords)
    result["cyclomatic_complexity"] = float(1 + decisions)

    # TypeScript type annotations
    result["has_type_hints"] = bool(re.search(r":\s*(string|number|boolean|void|any)\b", code))
    return result


def _calculate_quality_score(metrics: Dict) -> float:
    """Calculate 0-1 code quality score from metrics."""
    score = 0.0

    # Lower complexity is better (40% weight)
    complexity = metrics.get("cyclomatic_complexity")
    if complexity is not None:
        score += (1 - min(complexity, 10) / 10) * 0.4
    else:
        score += 0.2  # neutral if unknown

    # Type hints present (30% weight)
    if metrics.get("has_type_hints"):
        score += 0.3
    else:
        score += 0.1

    # Shallow nesting (30% weight)
    nesting = metrics.get("max_nesting_depth")
    if nesting is not None and nesting <= 3:
        score += 0.3
    elif nesting is not None:
        score += 0.1
    else:
        score += 0.15  # neutral

    return max(0.0, min(1.0, score))


def classify_interaction(code_response: str) -> str:
    """Classify an interaction type based on the code response content.

    Returns one of: new_code, refactor, bugfix, explanation.
    """
    # Mostly comments / prose → explanation
    lines = code_response.strip().splitlines()
    if lines:
        comment_lines = sum(
            1 for l in lines
            if l.strip().startswith(("#", "//", "/*", "*", "```"))
        )
        if comment_lines / len(lines) > 0.6:
            return "explanation"

    # Short response → likely a bugfix
    if len(code_response) < 100:
        return "bugfix"

    # Many new definitions → new code
    defs = (
        code_response.count("def ")
        + code_response.count("class ")
        + code_response.count("function ")
    )
    if defs >= 2:
        return "new_code"

    return "refactor"


def parse_error_message(error_text: str) -> Tuple[str, str]:
    """Classify error type and severity from error text.

    Returns (error_type, severity).
    """
    text_lower = error_text.lower()

    # Determine error type
    if any(kw in text_lower for kw in ["syntaxerror", "syntax error", "unexpected token"]):
        error_type = "syntax"
    elif any(kw in text_lower for kw in ["typeerror", "type error", "mypy", "tsc"]):
        error_type = "type"
    elif any(kw in text_lower for kw in [
        "nameerror", "attributeerror", "indexerror", "keyerror",
        "valueerror", "runtime", "traceback", "exception",
    ]):
        error_type = "runtime"
    else:
        error_type = "logic"

    # Determine severity
    if any(kw in text_lower for kw in ["critical", "fatal", "security", "injection"]):
        severity = "high"
    elif any(kw in text_lower for kw in ["warning", "deprecated"]):
        severity = "low"
    else:
        severity = "medium"

    return error_type, severity
