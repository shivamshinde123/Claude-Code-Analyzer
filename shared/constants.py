"""Shared constants for Claude Code Analyzer."""

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

INTERACTION_TYPES = ["new_code", "refactor", "bugfix", "explanation"]

ERROR_TYPES = ["syntax", "runtime", "type", "logic"]

ERROR_SEVERITIES = ["low", "medium", "high"]

SESSION_STATUSES = ["completed", "abandoned", "in_progress"]

# Defaults
DEFAULT_DATABASE_PATH = "../data/sessions.db"
DEFAULT_SESSION_TIMEOUT_SECONDS = 300
DEFAULT_API_PORT = 8000
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_FRONTEND_ORIGIN = "http://localhost:5173"
