"""Map detected language names to paradigm families.

Language names match those returned by ``tools.language_detect.detect_language``.
"""

from __future__ import annotations

LANGUAGE_FAMILIES: dict[str, str] = {
    # Dynamic Scripting
    "Python": "dynamic_scripting",
    "Ruby": "dynamic_scripting",
    "PHP": "dynamic_scripting",
    "Perl": "dynamic_scripting",
    "Lua": "dynamic_scripting",
    "R": "dynamic_scripting",

    # Systems / Memory Safety
    "C": "systems",
    "C++": "systems",
    "Rust": "systems",
    "Objective-C": "systems",

    # JVM
    "Java": "jvm",
    "Kotlin": "jvm",
    "Scala": "jvm",
    "Groovy": "jvm",
    "Clojure": "jvm",

    # .NET
    "C#": "dotnet",
    "F#": "dotnet",
    "Visual Basic": "dotnet",

    # Go (own family — unique idioms)
    "Go": "go",

    # Frontend / Web
    "JavaScript": "frontend",
    "TypeScript": "frontend",
    "HTML": "frontend",
    "CSS": "frontend",
    "SCSS": "frontend",
    "SASS": "frontend",
    "LESS": "frontend",
    "Dart": "frontend",

    # Functional
    "Haskell": "functional",
    "Elixir": "functional",
    "Erlang": "functional",
    "F#": "functional",       # F# fits both; functional takes precedence
    "Clojure": "functional",  # Clojure also fits; functional takes precedence
    "Scala": "functional",    # Scala straddles JVM and functional

    # Infrastructure / Config
    "Shell": "infrastructure",
    "PowerShell": "infrastructure",
    "Batch": "infrastructure",
    "Terraform": "infrastructure",
    "YAML": "infrastructure",
    "JSON": "infrastructure",
    "TOML": "infrastructure",
    "XML": "infrastructure",
    "INI": "infrastructure",
    "Makefile": "infrastructure",
    "SQL": "infrastructure",
    "Markdown": "infrastructure",
}

# Families in display order
FAMILY_NAMES: list[str] = [
    "dynamic_scripting",
    "systems",
    "jvm",
    "dotnet",
    "go",
    "frontend",
    "functional",
    "infrastructure",
    "generic",
]

FAMILY_LABELS: dict[str, str] = {
    "dynamic_scripting": "Dynamic Scripting (Python, Ruby, PHP, Perl, Lua, R)",
    "systems": "Systems / Memory Safety (C, C++, Rust)",
    "jvm": "JVM (Java, Kotlin, Scala, Groovy)",
    "dotnet": ".NET (C#, F#, VB)",
    "go": "Go",
    "frontend": "Frontend / Web (JS, TS, Dart)",
    "functional": "Functional (Haskell, Elixir, Erlang)",
    "infrastructure": "Infrastructure (Shell, SQL, Terraform, YAML)",
    "generic": "Generic (language-agnostic)",
}


def get_language_family(language: str | None) -> str:
    """Return the paradigm family for a language, or ``'generic'`` if unknown."""
    if not language:
        return "generic"
    return LANGUAGE_FAMILIES.get(language, "generic")
