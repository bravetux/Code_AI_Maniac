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

from unittest.mock import patch, MagicMock
from tools.fetch_gitea import fetch_gitea_file


def test_fetch_gitea_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "ZGVmIGhlbGxvKCk6CiAgICBwYXNzCg==",  # base64 of "def hello():\n    pass\n"
        "name": "hello.py",
        "size": 22,
    }
    with patch("tools.fetch_gitea.httpx.get", return_value=mock_response):
        result = fetch_gitea_file(
            gitea_url="http://localhost:3000",
            repo="owner/repo",
            file_path="src/hello.py",
            branch="main",
            token="fake-token"
        )
    assert "def hello" in result["content"]
    assert result["file_path"] == "src/hello.py"


def test_fetch_gitea_file_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("tools.fetch_gitea.httpx.get", return_value=mock_response):
        result = fetch_gitea_file(
            gitea_url="http://localhost:3000",
            repo="owner/repo",
            file_path="missing.py",
            branch="main",
            token="fake-token"
        )
    assert "error" in result
