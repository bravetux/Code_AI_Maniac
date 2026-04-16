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

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


@tool
def chunk_by_lines(content: str, max_tokens: int = 3000,
                   overlap_lines: int = 0) -> list[dict]:
    """Split file content into token-bounded chunks with optional line overlap."""
    lines = content.splitlines(keepends=True)
    chunks = []
    i = 0
    while i < len(lines):
        chunk_lines = []
        token_count = 0
        start = i
        while i < len(lines):
            line_tokens = estimate_tokens(lines[i])
            if token_count + line_tokens > max_tokens and chunk_lines:
                break
            chunk_lines.append(lines[i])
            token_count += line_tokens
            i += 1
        chunk_content = "".join(chunk_lines)
        chunks.append({
            "content": chunk_content,
            "start_line": start + 1,
            "end_line": start + len(chunk_lines),
            "token_count": token_count,
        })
        if overlap_lines > 0 and i < len(lines):
            i = max(start + len(chunk_lines) - overlap_lines, start + 1)
    return chunks
