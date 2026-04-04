"""Infer programming language from a file extension."""

import os

_EXT_MAP: dict[str, str] = {
    # Systems / embedded
    "c": "C", "h": "C", "cpp": "C++", "cc": "C++", "cxx": "C++",
    "hpp": "C++", "hh": "C++",
    # JVM
    "java": "Java", "kt": "Kotlin", "kts": "Kotlin", "scala": "Scala", "groovy": "Groovy",
    # .NET
    "cs": "C#", "vb": "Visual Basic", "fs": "F#",
    # Scripting
    "py": "Python", "pyw": "Python",
    "js": "JavaScript", "mjs": "JavaScript", "cjs": "JavaScript",
    "ts": "TypeScript", "tsx": "TypeScript",
    "jsx": "JavaScript",
    "rb": "Ruby", "rake": "Ruby",
    "php": "PHP",
    "go": "Go",
    "rs": "Rust",
    "swift": "Swift",
    "m": "Objective-C", "mm": "Objective-C",
    "pl": "Perl", "pm": "Perl",
    "sh": "Shell", "bash": "Shell", "zsh": "Shell", "fish": "Shell",
    "ps1": "PowerShell", "psm1": "PowerShell",
    "bat": "Batch", "cmd": "Batch",
    # Data / config
    "sql": "SQL",
    "r": "R", "rmd": "R",
    "lua": "Lua",
    "ex": "Elixir", "exs": "Elixir",
    "erl": "Erlang", "hrl": "Erlang",
    "hs": "Haskell", "lhs": "Haskell",
    "clj": "Clojure", "cljs": "Clojure",
    "dart": "Dart",
    "tf": "Terraform", "tfvars": "Terraform",
    "yaml": "YAML", "yml": "YAML",
    "json": "JSON",
    "xml": "XML",
    "html": "HTML", "htm": "HTML",
    "css": "CSS", "scss": "SCSS", "sass": "SASS", "less": "LESS",
    "md": "Markdown",
    "toml": "TOML",
    "ini": "INI",
    "makefile": "Makefile",
}


def detect_language(file_path: str) -> str | None:
    """
    Return a human-readable language name for the given file path,
    or None if the extension is not recognised.
    """
    name = os.path.basename(file_path).lower()
    # Special filenames with no extension
    if name in ("makefile", "dockerfile", "rakefile", "gemfile", "podfile"):
        return name.capitalize()

    ext = os.path.splitext(name)[1].lstrip(".")
    return _EXT_MAP.get(ext)
