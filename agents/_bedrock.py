import boto3
from strands.models import BedrockModel
from config.settings import get_settings

_APPEND_PREFIX = "__append__\n"


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
