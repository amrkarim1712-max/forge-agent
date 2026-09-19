"""OpenAI chat-completions compatible provider implementation."""

from __future__ import annotations

import json
import time
from typing import Any, Iterable

import httpx

from forge_agent.core.errors import ConfigurationError, ProviderError
from .base import ModelResponse, ToolCall


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model_name: str,
        timeout: int = 120,
        retry_attempts: int = 3,
        retry_backoff: float = 1.0,
        api_key_env: str = "FORGE_API_KEY",
    ) -> None:
        if not api_key:
            raise ConfigurationError(f"No API key found. Set {api_key_env} for the configured provider.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.retry_attempts = max(1, retry_attempts)
        self.retry_backoff = max(0.0, retry_backoff)

    def _request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        last_error: Exception | None = None
        for attempt in range(self.retry_attempts):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                break
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt + 1 == self.retry_attempts:
                    raise ProviderError("The model request timed out after retries.") from exc
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 401:
                    raise ProviderError("The provider rejected the API key.") from exc
                if status not in {408, 409, 425, 429} and status < 500:
                    raise ProviderError(f"The provider returned HTTP {status}.") from exc
                last_error = exc
                if attempt + 1 == self.retry_attempts:
                    raise ProviderError(f"The provider returned transient HTTP {status} after retries.") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt + 1 == self.retry_attempts:
                    raise ProviderError("Could not reach the model provider after retries.") from exc
            except ValueError as exc:
                raise ProviderError("The provider returned invalid JSON.") from exc
            time.sleep(self.retry_backoff * (2**attempt))
        else:
            raise ProviderError("The model request failed after retries.") from last_error
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("The provider returned a malformed model response.") from exc
        calls: list[ToolCall] = []
        for call in message.get("tool_calls") or []:
            try:
                raw_args = call["function"].get("arguments", "{}")
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                calls.append(ToolCall(id=call.get("id", "call"), name=call["function"]["name"], arguments=arguments))
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise ProviderError("The model returned an invalid tool call.") from exc
        return ModelResponse(
            content=message.get("content") or "",
            tool_calls=calls,
            finish_reason=(data.get("choices") or [{}])[0].get("finish_reason"),
        )

    def generate(self, messages, tools=None, *, temperature=0.2, max_tokens=4096) -> ModelResponse:
        return self._request(messages, tools, temperature, max_tokens)

    def stream(self, messages, tools=None, *, temperature=0.2, max_tokens=4096) -> Iterable[str]:
        yield self.generate(messages, tools, temperature=temperature, max_tokens=max_tokens).content

    def supports_tools(self) -> bool:
        return True