"""Small LLM client for v2 experiment runners."""

from __future__ import annotations

from dataclasses import asdict

from .config import LLMConfig


class LLMClientError(RuntimeError):
    """Raised when the configured LLM cannot be called."""


class ExperimentLLMClient:
    """Thin wrapper around OpenAI-compatible and Anthropic chat APIs."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider.lower()
        if not config.api_key:
            raise LLMClientError(
                f"Missing API key for provider '{config.provider}'. "
                "Set MOONSHOT_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, "
                "or ANTHROPIC_API_KEY."
            )
        self._client = self._build_client()

    def generate(self, prompt: str) -> str:
        if self.provider in {"openai", "kimi", "deepseek"}:
            return self._generate_openai_compatible(prompt)
        if self.provider == "anthropic":
            return self._generate_anthropic(prompt)
        raise LLMClientError(f"Unsupported LLM provider: {self.config.provider}")

    def metadata(self) -> dict:
        data = asdict(self.config)
        data["api_key"] = "***" if self.config.api_key else ""
        return data

    def _build_client(self):
        if self.provider in {"openai", "kimi", "deepseek"}:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMClientError("The openai package is required for this provider.") from exc
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            return OpenAI(**kwargs)

        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise LLMClientError("The anthropic package is required for this provider.") from exc
            return Anthropic(api_key=self.config.api_key)

        raise LLMClientError(f"Unsupported LLM provider: {self.config.provider}")

    def _generate_openai_compatible(self, prompt: str) -> str:
        temperature = self.config.temperature
        if self.provider == "kimi":
            temperature = 1
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a clinical nutrition recommendation baseline. "
                        "Return only machine-readable JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=self.config.max_tokens,
        )
        message = response.choices[0].message
        return getattr(message, "reasoning_content", None) or message.content or ""

    def _generate_anthropic(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=(
                "You are a clinical nutrition recommendation baseline. "
                "Return only machine-readable JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        parts = []
        for block in response.content:
            text = getattr(block, "text", "")
            if text:
                parts.append(text)
        return "\n".join(parts)
