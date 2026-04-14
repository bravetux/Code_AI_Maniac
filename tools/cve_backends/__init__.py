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
