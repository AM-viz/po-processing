"""
Bedrock inference client -- drop-in compatibility shim for the Vertex AI
``GenerativeModel`` API used throughout this package.

The rest of the codebase was written against Google Vertex AI's
``vertexai.generative_models`` API:

    model = GenerativeModel(model_name, generation_config=GenerationConfig(...))
    response = model.generate_content(prompt | [pdf_part, prompt])
    text = response.text
    usage = response.usage_metadata  # .prompt_token_count / .candidates_token_count

This module provides the same surface (``GenerativeModel``, ``GenerationConfig``,
``Part`` and a response object) but routes calls to **AWS Bedrock** via the
``bedrock-runtime`` Converse API (Anthropic Claude). Call-sites only need to
swap their import; the call expressions stay identical.

Model role mapping (Sonnet/Haiku split):
  * a model name containing "flash"  -> fast role   -> BEDROCK_HAIKU_MODEL_ID
  * a model name containing "pro"    -> heavy role   -> BEDROCK_SONNET_MODEL_ID
  * anything else                    -> DEFAULT_LLM_ROLE (default: heavy)

Configuration (environment variables):
  AWS_REGION                AWS GovCloud region, e.g. "us-gov-west-1"
  BEDROCK_ENDPOINT_URL      optional explicit endpoint override
  BEDROCK_SONNET_MODEL_ID   Claude Sonnet model / inference-profile id (heavy)
  BEDROCK_HAIKU_MODEL_ID    Claude Haiku model / inference-profile id (fast)
  BEDROCK_MAX_TOKENS        max output tokens (default 8192)
  BEDROCK_MAX_RETRIES       boto3 adaptive retry attempts (default 5)
  BEDROCK_CALL_DELAY_SECONDS  optional throttle between calls (default 0)
"""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def get_aws_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-gov-west-1")


def get_bedrock_endpoint_url() -> str | None:
    return os.getenv("BEDROCK_ENDPOINT_URL") or None


def get_sonnet_model_id() -> str:
    return os.getenv(
        "BEDROCK_SONNET_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )


def get_haiku_model_id() -> str:
    return os.getenv("BEDROCK_HAIKU_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")


def get_max_tokens() -> int:
    return int(os.getenv("BEDROCK_MAX_TOKENS", "8192"))


def get_max_retries() -> int:
    return int(os.getenv("BEDROCK_MAX_RETRIES", "5"))


def get_call_delay() -> float:
    return float(os.getenv("BEDROCK_CALL_DELAY_SECONDS", "0"))


def model_id_for_role(role: str) -> str:
    """Resolve a logical role ("fast" / "heavy") to a Bedrock model id."""
    return get_haiku_model_id() if role == "fast" else get_sonnet_model_id()


def _role_from_model_name(model_name: str | None) -> str:
    """Map a (legacy Gemini) model-name string to a logical role."""
    name = (model_name or "").lower()
    if "flash" in name or "haiku" in name:
        return "fast"
    if "pro" in name or "sonnet" in name or "opus" in name:
        return "heavy"
    return os.getenv("DEFAULT_LLM_ROLE", "heavy")


# ---------------------------------------------------------------------------
# Bedrock client (cached)
# ---------------------------------------------------------------------------

_bedrock_client = None


def get_bedrock_client():
    """Return a cached bedrock-runtime client configured for adaptive retries."""
    global _bedrock_client  # noqa: PLW0603 (module-level singleton cache)
    if _bedrock_client is None:
        import boto3  # noqa: PLC0415
        from botocore.config import Config  # noqa: PLC0415

        cfg = Config(
            retries={"max_attempts": get_max_retries(), "mode": "adaptive"},
            read_timeout=300,
            connect_timeout=30,
        )
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=get_aws_region(),
            endpoint_url=get_bedrock_endpoint_url(),
            config=cfg,
        )
    return _bedrock_client


# ---------------------------------------------------------------------------
# Compatibility shim: GenerationConfig / Part / response objects
# ---------------------------------------------------------------------------

# Bedrock Converse document blocks reject names with spaces / special chars.
_DOCUMENT_NAME = "document"
# Throttle / transient Bedrock errors worth an explicit backoff retry.
_RETRYABLE_ERRORS = (
    "ThrottlingException",
    "ModelTimeoutException",
    "ServiceUnavailableException",
    "InternalServerException",
)


@dataclass
class GenerationConfig:
    """Mirrors vertexai GenerationConfig (only the fields this code uses)."""

    temperature: float = 0.0
    response_mime_type: str | None = None
    max_output_tokens: int | None = None


class Part:
    """Mirrors vertexai Part. Only ``from_data`` (inline bytes) is used here."""

    def __init__(self, *, mime_type: str, data: bytes):
        self.mime_type = mime_type
        self.data = data

    @classmethod
    def from_data(cls, *, mime_type: str, data: bytes) -> Part:
        return cls(mime_type=mime_type, data=data)


@dataclass
class _Usage:
    """Mirrors response.usage_metadata."""

    prompt_token_count: int = 0
    candidates_token_count: int = 0


@dataclass
class _Response:
    """Mirrors a vertexai generate_content response."""

    text: str
    usage_metadata: _Usage


def _mime_to_doc_format(mime_type: str) -> str:
    mapping = {
        "application/pdf": "pdf",
        "text/csv": "csv",
        "text/html": "html",
        "text/plain": "txt",
        "text/markdown": "md",
    }
    return mapping.get(mime_type, "pdf")


def _build_content_blocks(contents: Any) -> list[dict]:
    """Convert vertexai-style ``contents`` into Converse content blocks."""
    if isinstance(contents, (str, Part)):
        contents = [contents]

    blocks: list[dict] = []
    doc_index = 0
    for item in contents:
        if isinstance(item, Part):
            doc_index += 1
            blocks.append(
                {
                    "document": {
                        "format": _mime_to_doc_format(item.mime_type),
                        "name": f"{_DOCUMENT_NAME}{doc_index}",
                        "source": {"bytes": item.data},
                    }
                }
            )
        else:
            blocks.append({"text": str(item)})
    return blocks


class GenerativeModel:
    """Drop-in replacement for vertexai ``GenerativeModel`` backed by Bedrock."""

    def __init__(
        self,
        model_name: str | None = None,
        generation_config: GenerationConfig | None = None,
        *,
        role: str | None = None,
    ):
        self._role = role or _role_from_model_name(model_name)
        self._model_id = model_id_for_role(self._role)
        self._config = generation_config or GenerationConfig()

    @property
    def model_id(self) -> str:
        return self._model_id

    def generate_content(self, contents: Any) -> _Response:
        client = get_bedrock_client()
        messages = [{"role": "user", "content": _build_content_blocks(contents)}]

        inference_config: dict[str, Any] = {
            "temperature": float(getattr(self._config, "temperature", 0.0) or 0.0),
            "maxTokens": self._config.max_output_tokens or get_max_tokens(),
        }

        kwargs: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": messages,
            "inferenceConfig": inference_config,
        }

        # Anthropic on Bedrock has no native response_mime_type; nudge via system.
        if self._config.response_mime_type == "application/json":
            kwargs["system"] = [
                {
                    "text": (
                        "Respond with only a single valid JSON object. "
                        "Do not include markdown fences or any prose."
                    )
                }
            ]

        resp = self._converse_with_retry(client, kwargs)

        text = self._extract_text(resp)
        usage = resp.get("usage", {}) or {}
        meta = _Usage(
            prompt_token_count=int(usage.get("inputTokens", 0)),
            candidates_token_count=int(usage.get("outputTokens", 0)),
        )

        delay = get_call_delay()
        if delay > 0:
            time.sleep(delay)

        return _Response(text=text, usage_metadata=meta)

    @staticmethod
    def _extract_text(resp: dict) -> str:
        try:
            blocks = resp["output"]["message"]["content"]
        except (KeyError, TypeError):
            return ""
        return "".join(b.get("text", "") for b in blocks if isinstance(b, dict))

    def _converse_with_retry(self, client, kwargs: dict) -> dict:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        attempts = get_max_retries()
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return client.converse(**kwargs)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code not in _RETRYABLE_ERRORS or attempt == attempts - 1:
                    raise
                last_exc = exc
                backoff = min(2**attempt + random.uniform(0, 1), 30)
                logger.warning(
                    "[Bedrock] %s on %s (attempt %d/%d); retrying in %.1fs",
                    code,
                    self._model_id,
                    attempt + 1,
                    attempts,
                    backoff,
                )
                time.sleep(backoff)
        if last_exc:
            raise last_exc
        raise RuntimeError("Bedrock converse failed without an exception")
