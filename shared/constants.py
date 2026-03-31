"""Shared constants for Claude Code Analyzer."""

# All programming languages recognised by the analyser.
SUPPORTED_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "csharp",
    "cpp",
    "ruby",
    "php",
    "swift",
    "kotlin",
]

# Maps file extensions to their canonical language name used across services.
LANGUAGE_EXTENSIONS = {
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

# Possible interaction classification values produced by classify_interaction().
INTERACTION_TYPES = ["new_code", "refactor", "bugfix", "explanation"]

# High-level error categories used for grouping in analytics.
ERROR_TYPES = ["syntax", "runtime", "type", "logic"]

# Severity levels assigned to detected errors (low → medium → high).
ERROR_SEVERITIES = ["low", "medium", "high"]

# Lifecycle states a session can be in.
SESSION_STATUSES = ["completed", "abandoned", "in_progress"]

# Service defaults (can be overridden via environment variables).
DEFAULT_DATABASE_PATH = "../data/sessions.db"
DEFAULT_SESSION_TIMEOUT_SECONDS = 300
DEFAULT_API_PORT = 8000
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_FRONTEND_ORIGIN = "http://localhost:5173"
