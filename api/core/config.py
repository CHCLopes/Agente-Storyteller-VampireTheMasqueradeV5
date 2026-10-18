"""Central, secret-safe configuration for the Storyteller modular monolith."""

from __future__ import annotations

import os
import re
from typing import List, Literal, Optional

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


CapabilityMode = Literal["native", "emulated", "unsupported", "unknown"]
ReasoningEffort = Literal["none", "low", "medium", "high"]
LLMAdapterKind = Literal["openai-compatible", "openrouter", "gemini", "nvidia", "groq"]
DOTENV_DISABLE_ENV_VAR = "STORYTELLER_DISABLE_DOTENV"
_GEMINI_STABLE_MODEL = re.compile(
    r"\Agemini-\d+(?:\.\d+)+-[a-z0-9]+(?:-[a-z0-9]+)*\Z"
)
_NVIDIA_NIM_OFFICIAL_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NVIDIA_NIM_PROVIDER_LABEL = "nvidia nim"
_NVIDIA_NIM_MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b"
_GROQ_OFFICIAL_BASE_URL = "https://api.groq.com/openai/v1"
_GROQ_PROVIDER_LABEL = "groq"
_GROQ_FIXED_REASONING_EFFORT = {
    "qwen/qwen3.8-27b": "none",
    "openai/gpt-oss-120b": "low",
}


def _configured_dotenv_file() -> str | None:
    """Return the normal dotenv path unless the process explicitly disables it."""

    disabled = os.environ.get(DOTENV_DISABLE_ENV_VAR, "").strip().casefold()
    return None if disabled in {"1", "true", "yes", "on"} else ".env"


class Settings(BaseSettings):
    """Load product configuration without selecting an LLM provider in code."""

    environment: str = Field(default="development")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=True)

    # The SQLite event store is local-first and intentionally independent from
    # the deprecated SQLAlchemy URL retained below for startup compatibility.
    storyteller_db_path: str = Field(
        default="data/saves/storyteller.sqlite3",
        validation_alias=AliasChoices("STORYTELLER_DB_PATH"),
    )
    database_url: str = Field(default="sqlite:///./campaign.db")
    database_pool_size: int = Field(default=5)

    # Provider-neutral LLM composition. No target identity, endpoint or model
    # has a production default: every component must be explicitly supplied.
    # Legacy Gemini/LM Studio names remain aliases only for non-secret endpoint
    # fields; target identity, provider label and any credential stay explicit.
    llm_target_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_TARGET_ID"),
    )
    llm_provider_label: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_PROVIDER_LABEL", "LLM_PROVIDER"),
    )
    llm_model: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MODEL", "GEMINI_MODEL", "LMSTUDIO_MODEL"),
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "LLM_BASE_URL",
            "GEMINI_BASE_URL",
            "LM_STUDIO_BASE_URL",
            "LMSTUDIO_BASE_URL",
        ),
    )
    llm_api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY"),
    )
    llm_adapter_kind: LLMAdapterKind = Field(
        default="openai-compatible",
        validation_alias=AliasChoices("LLM_ADAPTER_KIND"),
    )
    llm_openrouter_provider: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_OPENROUTER_PROVIDER"),
    )
    llm_timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=600,
        validation_alias=AliasChoices(
            "LLM_TIMEOUT_SECONDS", "GEMINI_TIMEOUT", "LMSTUDIO_TIMEOUT"
        ),
    )
    llm_h0_timeout_seconds: float = Field(
        default=15.0,
        gt=0.0,
        le=600.0,
        validation_alias=AliasChoices("LLM_H0_TIMEOUT_SECONDS"),
    )
    llm_h1_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=600.0,
        validation_alias=AliasChoices("LLM_H1_TIMEOUT_SECONDS"),
    )
    llm_h4_timeout_seconds: float = Field(
        default=20.0,
        gt=0.0,
        le=600.0,
        validation_alias=AliasChoices("LLM_H4_TIMEOUT_SECONDS"),
    )
    llm_h0_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LLM_H0_ENABLED"),
    )
    llm_h1_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LLM_H1_ENABLED"),
    )
    llm_h4_action_enrichment_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LLM_H4_ACTION_ENRICHMENT_ENABLED"),
    )
    llm_h6_max_output_tokens: int = Field(
        default=96,
        ge=32,
        le=2048,
        validation_alias=AliasChoices("LLM_H6_MAX_OUTPUT_TOKENS"),
    )
    llm_scene_director_max_output_tokens: int = Field(
        default=256,
        ge=128,
        le=4096,
        validation_alias=AliasChoices("LLM_SCENE_DIRECTOR_MAX_OUTPUT_TOKENS"),
    )
    llm_scene_director_temperature: float = Field(
        default=0.65,
        ge=0.0,
        le=1.5,
        validation_alias=AliasChoices("LLM_SCENE_DIRECTOR_TEMPERATURE"),
    )
    llm_reasoning_effort: Optional[ReasoningEffort] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_REASONING_EFFORT"),
    )
    llm_campaign_data_allowed: bool = Field(
        default=False,
        validation_alias=AliasChoices("LLM_CAMPAIGN_DATA_ALLOWED"),
    )
    llm_structured_generation: CapabilityMode = Field(
        default="unknown",
        validation_alias=AliasChoices("LLM_STRUCTURED_GENERATION"),
    )
    llm_streaming: CapabilityMode = Field(
        default="unknown",
        validation_alias=AliasChoices("LLM_STREAMING"),
    )

    context_token_budget: int = Field(default=2400, ge=256, le=32768)
    context_chars_per_token: float = Field(default=4.0, gt=0.0, le=16.0)
    narrator_context_token_budget: int = Field(
        default=192,
        ge=64,
        le=4096,
        validation_alias=AliasChoices("NARRATOR_CONTEXT_TOKEN_BUDGET"),
    )

    frontend_url: str = Field(default="http://localhost:3000")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"])
    jwt_secret: SecretStr = Field(
        default=SecretStr("super_secret_default_key_change_in_production")
    )
    queue_max_size: int = Field(default=10, ge=1)

    model_config = SettingsConfigDict(
        env_file=_configured_dotenv_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def llm_is_configured(self) -> bool:
        identity = (
            self.llm_target_id,
            self.llm_provider_label,
            self.llm_model,
            self.llm_base_url,
        )
        if not all(value is not None and bool(value.strip()) for value in identity):
            return False
        if self.llm_adapter_kind == "openai-compatible":
            return True
        key_is_present = (
            self.llm_api_key is not None
            and bool(self.llm_api_key.get_secret_value().strip())
        )
        if self.llm_adapter_kind == "openrouter":
            return (
                self.llm_provider_label is not None
                and self.llm_provider_label.strip().casefold() == "openrouter"
                and self.llm_openrouter_provider is not None
                and bool(self.llm_openrouter_provider.strip())
                and key_is_present
            )
        if self.llm_adapter_kind == "groq":
            return (
                self.llm_provider_label is not None
                and self.llm_provider_label.strip().casefold() == _GROQ_PROVIDER_LABEL
                and self.llm_base_url is not None
                and self.llm_base_url.strip().rstrip("/") == _GROQ_OFFICIAL_BASE_URL
                and self.llm_model is not None
                and self.llm_model.strip() in _GROQ_FIXED_REASONING_EFFORT
                and self.llm_reasoning_effort
                == _GROQ_FIXED_REASONING_EFFORT[self.llm_model.strip()]
                and key_is_present
            )
        if self.llm_adapter_kind == "nvidia":
            return (
                self.llm_provider_label is not None
                and self.llm_provider_label.strip().casefold()
                == _NVIDIA_NIM_PROVIDER_LABEL
                and self.llm_model is not None
                and self.llm_model.strip() == _NVIDIA_NIM_MODEL_ID
                and self.llm_base_url is not None
                and self.llm_base_url.strip().rstrip("/")
                == _NVIDIA_NIM_OFFICIAL_BASE_URL
                and key_is_present
                and self.llm_campaign_data_allowed
            )
        return (
            self.llm_provider_label is not None
            and self.llm_provider_label.strip().casefold() == "google gemini"
            and self.llm_model is not None
            and _GEMINI_STABLE_MODEL.fullmatch(self.llm_model.strip().casefold())
            is not None
            and not any(
                marker in self.llm_model.strip().casefold()
                for marker in ("latest", "preview", "experimental", "-exp")
            )
            and self.llm_base_url is not None
            and self.llm_base_url.strip().rstrip("/")
            == "https://generativelanguage.googleapis.com/v1beta"
            and key_is_present
            and self.llm_campaign_data_allowed
        )

    def db_connection_string(self) -> str:
        return self.database_url

    def cors_origins(self) -> list[str]:
        return [self.frontend_url] + self.allowed_hosts


settings = Settings()
