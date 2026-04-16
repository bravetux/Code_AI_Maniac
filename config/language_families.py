# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

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
