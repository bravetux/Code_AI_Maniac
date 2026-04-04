import boto3
from strands.models import BedrockModel
from config.settings import get_settings


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
