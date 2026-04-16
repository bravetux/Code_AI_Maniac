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

"""Web scraper — extracts clean text content from a URL.

Usage:
    python tools/web_scraper.py https://example.com
    python tools/web_scraper.py https://example.com -o output.txt

Import:
    from tools.web_scraper import scrape_url
    result = scrape_url("https://example.com")
    print(result["text"])
"""

import argparse
import re
import sys

import httpx

# Tags whose content is not visible text
_STRIP_TAGS = re.compile(
    r"<(script|style|noscript|iframe|svg|head)[\s>].*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
# Any remaining HTML tags
_HTML_TAG = re.compile(r"<[^>]+>")
# Collapse whitespace
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
# HTML entities
_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&apos;": "'", "&nbsp;": " ", "&#39;": "'",
}


def _decode_entities(text: str) -> str:
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    # Numeric entities &#123;
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    # Hex entities &#x1F;
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
    return text


def _html_to_text(html: str) -> str:
    """Convert raw HTML to clean readable text."""
    text = _STRIP_TAGS.sub("", html)
    # Convert block elements to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr|blockquote|section|article|header|footer)>",
                  "\n", text, flags=re.IGNORECASE)
    text = _HTML_TAG.sub("", text)
    text = _decode_entities(text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def scrape_url(url: str, timeout: int = 30) -> dict:
    """Scrape a URL and return clean text content.

    Parameters
    ----------
    url : str
        The URL to scrape.
    timeout : int
        Request timeout in seconds (default 30).

    Returns
    -------
    dict with keys:
        url        : str — the requested URL
        status     : int — HTTP status code
        title      : str — page <title> if found
        text       : str — cleaned visible text content
        length     : int — character count of text
        error      : str — error message if request failed (empty on success)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AICodeManiac/1.0; +https://github.com)",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        html = resp.text

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        title = _decode_entities(title_match.group(1).strip()) if title_match else ""

        text = _html_to_text(html)

        return {
            "url": str(resp.url),
            "status": resp.status_code,
            "title": title,
            "text": text,
            "length": len(text),
            "error": "",
        }
    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "status": e.response.status_code,
            "title": "",
            "text": "",
            "length": 0,
            "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
        }
    except Exception as e:
        return {
            "url": url,
            "status": 0,
            "title": "",
            "text": "",
            "length": 0,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Scrape clean text from a URL")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("-o", "--output", help="Save text to file instead of stdout")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="Request timeout (default 30s)")
    args = parser.parse_args()

    result = scrape_url(args.url, timeout=args.timeout)

    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    header = f"# {result['title']}\nSource: {result['url']}\nLength: {result['length']} chars\n\n"
    content = header + result["text"]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved {result['length']} chars to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()
