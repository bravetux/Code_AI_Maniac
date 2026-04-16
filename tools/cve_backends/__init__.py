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

"""CVE backend system — pluggable vulnerability lookup backends."""
from __future__ import annotations
from typing import Callable
from tools.cve_backends.osv import lookup_osv
from tools.cve_backends.nvd import lookup_nvd
from tools.cve_backends.github_advisory import lookup_github
from tools.cve_backends.llm_only import lookup_llm
from tools.cve_backends.hybrid import lookup_hybrid

_BACKENDS: dict[str, Callable] = {
    "osv": lookup_osv, "nvd": lookup_nvd, "github": lookup_github,
    "llm": lookup_llm, "osv_llm": lookup_hybrid,
}

def get_backend(name: str) -> Callable:
    if name not in _BACKENDS:
        raise ValueError(f"Unknown CVE backend: {name!r}. Valid: {list(_BACKENDS)}")
    return _BACKENDS[name]

def lookup_vulnerabilities(packages: list[dict], backend: str = "osv_llm") -> list[dict]:
    return get_backend(backend)(packages)
