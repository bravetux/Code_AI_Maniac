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
