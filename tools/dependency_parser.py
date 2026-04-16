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

"""Multi-ecosystem dependency file parser.

Extracts package names and version constraints from dependency files
for Python, JavaScript, Java, C#, Go, Rust, and C/C++ ecosystems.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET


# ── Known dependency file basenames for auto-discovery ───────────────────────

_DEP_FILENAMES: set[str] = {
    "requirements.txt", "pyproject.toml", "setup.cfg", "Pipfile",
    "package.json", "package-lock.json", "yarn.lock",
    "pom.xml", "build.gradle",
    "CMakeLists.txt", "conanfile.txt", "vcpkg.json",
    "packages.config", "Directory.Packages.props",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}

_DEP_EXTENSIONS: set[str] = {".csproj"}


def detect_dep_files(directory: str) -> list[str]:
    """Find known dependency files in a directory (non-recursive)."""
    found = []
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if not os.path.isfile(full):
                continue
            if entry in _DEP_FILENAMES:
                found.append(full)
            elif os.path.splitext(entry)[1] in _DEP_EXTENSIONS:
                found.append(full)
    except OSError:
        pass
    return sorted(found)


# ── Dispatcher ───────────────────────────────────────────────────────────────

def parse_dependency_file(filename: str, content: str) -> dict:
    """Parse a dependency file and return structured package list."""
    basename = os.path.basename(filename)
    ext = os.path.splitext(basename)[1]

    if basename == "requirements.txt":
        return _parse_requirements_txt(content)
    if basename == "pyproject.toml":
        return _parse_pyproject_toml(content)
    if basename in ("setup.cfg", "Pipfile"):
        return _parse_generic_python(content)
    if basename == "package.json":
        return _parse_package_json(content)
    if basename == "pom.xml":
        return _parse_pom_xml(content)
    if basename == "build.gradle":
        return _parse_build_gradle(content)
    if ext == ".csproj" or basename == "packages.config" or basename == "Directory.Packages.props":
        return _parse_csproj(content)
    if basename == "go.mod":
        return _parse_go_mod(content)
    if basename == "Cargo.toml":
        return _parse_cargo_toml(content)
    if basename == "conanfile.txt":
        return _parse_conanfile_txt(content)
    if basename == "vcpkg.json":
        return _parse_vcpkg_json(content)

    return {"ecosystem": "unknown", "packages": []}


def _parse_requirements_txt(content: str) -> dict:
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*(?:[=!<>~]=*\s*(.+?))?$", line)
        if m:
            name = re.sub(r"\[.*\]", "", m.group(1))
            version = m.group(2) if m.group(2) else None
            packages.append({"name": name, "version": version})
    return {"ecosystem": "PyPI", "packages": packages}


def _parse_pyproject_toml(content: str) -> dict:
    packages = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies") and "=" in stripped:
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                in_deps = False
                continue
            m = re.match(r'["\']([A-Za-z0-9_.\-]+)\s*(?:[=!<>~]=*\s*(.+?))?["\']', stripped)
            if m:
                packages.append({"name": m.group(1), "version": m.group(2)})
    return {"ecosystem": "PyPI", "packages": packages}


def _parse_generic_python(content: str) -> dict:
    packages = []
    for line in content.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*[=<>!~]", line)
        if m:
            packages.append({"name": m.group(1), "version": None})
    return {"ecosystem": "PyPI", "packages": packages}


def _parse_package_json(content: str) -> dict:
    packages = []
    try:
        data = json.loads(content)
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in data.get(section, {}).items():
                clean = re.sub(r"^[\^~>=<]+", "", version) if version else None
                packages.append({"name": name, "version": clean})
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"ecosystem": "npm", "packages": packages}


def _parse_pom_xml(content: str) -> dict:
    packages = []
    try:
        clean = re.sub(r'\sxmlns="[^"]*"', "", content, count=1)
        root = ET.fromstring(clean)
        for dep in root.iter("dependency"):
            gid = dep.findtext("groupId", "")
            aid = dep.findtext("artifactId", "")
            ver = dep.findtext("version")
            if gid and aid:
                packages.append({"name": f"{gid}:{aid}", "version": ver})
    except ET.ParseError:
        pass
    return {"ecosystem": "Maven", "packages": packages}


def _parse_build_gradle(content: str) -> dict:
    packages = []
    for m in re.finditer(r"""(?:implementation|api|compile|testImplementation|runtimeOnly)\s+['"]([^:'"]+):([^:'"]+):([^'"]+)['"]""", content):
        packages.append({
            "name": f"{m.group(1)}:{m.group(2)}",
            "version": m.group(3),
        })
    return {"ecosystem": "Maven", "packages": packages}


def _parse_csproj(content: str) -> dict:
    packages = []
    try:
        root = ET.fromstring(content)
        for ref in root.iter("PackageReference"):
            name = ref.get("Include")
            version = ref.get("Version")
            if name:
                packages.append({"name": name, "version": version})
    except ET.ParseError:
        pass
    return {"ecosystem": "NuGet", "packages": packages}


def _parse_go_mod(content: str) -> dict:
    packages = []
    in_require = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require (") or stripped == "require (":
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if len(parts) >= 2:
                packages.append({"name": parts[0], "version": parts[1]})
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 3:
                packages.append({"name": parts[1], "version": parts[2]})
    return {"ecosystem": "Go", "packages": packages}


def _parse_cargo_toml(content: str) -> dict:
    packages = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
            continue
        if in_deps and "=" in stripped:
            m = re.match(r'^(\S+)\s*=\s*"([^"]+)"', stripped)
            if m:
                packages.append({"name": m.group(1), "version": m.group(2)})
            else:
                m = re.match(r'^(\S+)\s*=\s*\{.*version\s*=\s*"([^"]+)"', stripped)
                if m:
                    packages.append({"name": m.group(1), "version": m.group(2)})
    return {"ecosystem": "crates.io", "packages": packages}


def _parse_conanfile_txt(content: str) -> dict:
    packages = []
    in_requires = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[requires]":
            in_requires = True
            continue
        if stripped.startswith("[") and in_requires:
            in_requires = False
            continue
        if in_requires and "/" in stripped:
            parts = stripped.split("/", 1)
            packages.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else None})
    return {"ecosystem": "conan", "packages": packages}


def _parse_vcpkg_json(content: str) -> dict:
    packages = []
    try:
        data = json.loads(content)
        for dep in data.get("dependencies", []):
            if isinstance(dep, str):
                packages.append({"name": dep, "version": None})
            elif isinstance(dep, dict):
                packages.append({"name": dep.get("name", ""), "version": dep.get("version-string")})
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"ecosystem": "vcpkg", "packages": packages}
