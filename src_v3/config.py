"""Configuration helpers for v2."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data_v2"
RESULTS_DIR = ROOT_DIR / "results_v2"


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None
    temperature: float
    max_tokens: int


def load_neo4j_config() -> Neo4jConfig:
    load_dotenv(ROOT_DIR / ".env")
    return Neo4jConfig(
        uri=os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", ""),
        database=os.getenv("NEO4J_DATABASE", "nutrition"),
    )


def load_llm_config(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LLMConfig:
    load_dotenv(ROOT_DIR / ".env")
    selected_provider = provider or os.getenv("LLM_PROVIDER", "kimi")
    selected_model = model or os.getenv("LLM_MODEL") or _default_model_for(selected_provider)
    return LLMConfig(
        provider=selected_provider,
        model=selected_model,
        api_key=_api_key_for(selected_provider),
        base_url=_base_url_for(selected_provider),
        temperature=(
            temperature
            if temperature is not None
            else float(os.getenv("LLM_TEMPERATURE", "0.2"))
        ),
        max_tokens=(
            max_tokens
            if max_tokens is not None
            else int(os.getenv("LLM_MAX_TOKENS", "700"))
        ),
    )


def _api_key_for(provider: str) -> str:
    normalized = provider.lower()
    if normalized == "kimi":
        return os.getenv("MOONSHOT_API_KEY", "")
    if normalized == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY", "")
    if normalized == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY", "")
    return os.getenv("OPENAI_API_KEY", "")


def _base_url_for(provider: str) -> str | None:
    normalized = provider.lower()
    if normalized == "kimi":
        return os.getenv("KIMI_API_BASE_URL", "https://api.moonshot.cn/v1")
    if normalized == "deepseek":
        return os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")
    return os.getenv("OPENAI_API_BASE_URL")


def _default_model_for(provider: str) -> str:
    normalized = provider.lower()
    if normalized == "kimi":
        return "moonshot-v1-8k"
    if normalized == "deepseek":
        return "deepseek-chat"
    if normalized == "anthropic":
        return "claude-3-haiku-20240307"
    return "gpt-4o-mini"
