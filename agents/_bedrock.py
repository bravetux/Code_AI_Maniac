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

import json
import re

import boto3
from strands.models import BedrockModel
from config.settings import get_settings

_APPEND_PREFIX = "__append__\n"


def parse_json_response(text: str) -> dict:
    """Extract a JSON object from an LLM response that may contain reasoning text.

    Handles:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code fences
    - JSON embedded after reasoning / chain-of-thought text
    """
    text = text.strip()

    # 1. Try raw text directly (pure JSON response)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Try extracting from ```json ... ``` code fences (first match)
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Try to find the outermost { ... } JSON object
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, ValueError):
                        break

    # 4. Strip leading/trailing fences as last resort
    stripped = re.sub(r"^```(?:json)?\n?", "", text)
    stripped = re.sub(r"\n?```$", "", stripped)
    return json.loads(stripped)


def resolve_prompt(custom_prompt: str | None, base_prompt: str) -> str:
    """Return the effective system prompt based on mode encoded in custom_prompt.

    Encoding convention (set by feature_selector):
      - None / empty string  → use base_prompt unchanged (no override)
      - starts with __append__\\n → append user text to base_prompt
      - anything else        → overwrite: use custom_prompt as-is
    """
    if not custom_prompt:
        return base_prompt
    if custom_prompt.startswith(_APPEND_PREFIX):
        user_text = custom_prompt[len(_APPEND_PREFIX):]
        return f"{base_prompt}\n\n{user_text}"
    return custom_prompt


def make_bedrock_model() -> BedrockModel:
    """Create a BedrockModel with explicit credentials from settings."""
    s = get_settings()
    session_kwargs: dict = {"region_name": s.aws_region}
    if s.aws_access_key_id:
        session_kwargs["aws_access_key_id"] = s.aws_access_key_id
    if s.aws_secret_access_key:
        session_kwargs["aws_secret_access_key"] = s.aws_secret_access_key
    if s.aws_session_token:
        session_kwargs["aws_session_token"] = s.aws_session_token
    boto_session = boto3.Session(**session_kwargs)
    return BedrockModel(
        model_id=s.bedrock_model_id,
        temperature=s.bedrock_temperature,
        boto_session=boto_session,
    )
