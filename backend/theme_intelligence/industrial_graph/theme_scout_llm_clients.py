from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Callable

import requests

from .theme_scout_manifest import ThemeScoutEvidenceManifest


LLMTransport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class LLMThemeScoutClient(ABC):
    provider_name: str
    provider_model: str

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> dict[str, Any]:
        raise NotImplementedError


class StaticLLMThemeScoutClient(LLMThemeScoutClient):
    provider_name = "static"
    provider_model = "static"

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        provider = response.get("provider") if isinstance(response, dict) else None
        if isinstance(provider, dict):
            self.provider_name = str(provider.get("name") or self.provider_name)
            self.provider_model = str(provider.get("model") or self.provider_model)

    def generate_json(
        self,
        prompt: str,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> dict[str, Any]:
        del prompt, evidence_manifest
        return self.response


class _HTTPThemeScoutClient(LLMThemeScoutClient):
    env_key_name: str
    endpoint: str

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: LLMTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not str(api_key or "").strip():
            raise ValueError(f"{self.env_key_name} is required for {self.provider_name}")
        if not str(model or "").strip():
            raise ValueError("LLM model is required")
        self.api_key = api_key
        self.provider_model = model
        self.transport = transport or self._requests_transport
        self.timeout = float(timeout)

    @staticmethod
    def _requests_transport(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("LLM provider returned non-object JSON")
        return data

    @staticmethod
    def _parse_json_text(text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM provider returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("LLM provider JSON must be an object")
        return payload

    @staticmethod
    def _evidence_payload(
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> list[dict[str, Any]]:
        return [row.to_dict() for row in evidence_manifest.evidence]


class OpenAIThemeScoutClient(_HTTPThemeScoutClient):
    provider_name = "openai"
    env_key_name = "OPENAI_API_KEY"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4.1",
        transport: LLMTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(api_key=api_key, model=model, transport=transport, timeout=timeout)

    def generate_json(
        self,
        prompt: str,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> dict[str, Any]:
        payload = {
            "model": self.provider_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"evidence": self._evidence_payload(evidence_manifest)}, ensure_ascii=False, sort_keys=True)},
            ],
            "response_format": {"type": "json_object"},
            "evidence": self._evidence_payload(evidence_manifest),
        }
        response = self.transport(
            self.endpoint,
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            payload,
            self.timeout,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI response did not contain JSON content") from exc
        return self._parse_json_text(str(content))


class AnthropicThemeScoutClient(_HTTPThemeScoutClient):
    provider_name = "anthropic"
    env_key_name = "ANTHROPIC_API_KEY"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        transport: LLMTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(api_key=api_key, model=model, transport=transport, timeout=timeout)

    def generate_json(
        self,
        prompt: str,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> dict[str, Any]:
        payload = {
            "model": self.provider_model,
            "max_tokens": 4096,
            "temperature": 0,
            "system": prompt,
            "messages": [{
                "role": "user",
                "content": json.dumps({"evidence": self._evidence_payload(evidence_manifest)}, ensure_ascii=False, sort_keys=True),
            }],
            "evidence": self._evidence_payload(evidence_manifest),
        }
        response = self.transport(
            self.endpoint,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            payload,
            self.timeout,
        )
        try:
            content = next(
                item["text"]
                for item in response["content"]
                if item.get("type") == "text"
            )
        except (KeyError, StopIteration, TypeError) as exc:
            raise ValueError("Anthropic response did not contain JSON text") from exc
        return self._parse_json_text(str(content))


class GeminiThemeScoutClient(_HTTPThemeScoutClient):
    provider_name = "gemini"
    env_key_name = "GEMINI_API_KEY"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-1.5-pro",
        transport: LLMTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        super().__init__(api_key=api_key, model=model, transport=transport, timeout=timeout)

    def generate_json(
        self,
        prompt: str,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> dict[str, Any]:
        payload = {
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": prompt + "\n\n" + json.dumps({"evidence": self._evidence_payload(evidence_manifest)}, ensure_ascii=False, sort_keys=True),
                }],
            }],
            "evidence": self._evidence_payload(evidence_manifest),
        }
        response = self.transport(
            self.endpoint,
            {"Content-Type": "application/json"},
            payload,
            self.timeout,
        )
        try:
            content = response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Gemini response did not contain JSON text") from exc
        return self._parse_json_text(str(content))
