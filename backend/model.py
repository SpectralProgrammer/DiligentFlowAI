import json
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from base import ModelStructure


class GeminiModel(ModelStructure):
    def __init__(self, model: str = None, system_prompt: str = None, api_key: str = None):
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt

    def chat(
        self,
        prompt: str | None = None,
        messages: Sequence[dict[str, str]] | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY must be configured before the backend can generate text.")

        payload = {
            "contents": self._build_contents(prompt=prompt, messages=messages)
        }
        if self.system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": self.system_prompt}],
            }

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(self.model or 'gemini-2.5-flash', safe='')}:generateContent"
        )
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API request failed with {exc.code}: {detail}") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            reason_text = str(reason or exc)
            raise RuntimeError(
                "The backend could not reach the Gemini API. "
                f"Check internet access, firewall/proxy settings, and GEMINI_API_KEY. Details: {reason_text}"
            ) from exc

        candidates = response_payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {response_payload}")

        text_parts: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content", {})
            if not isinstance(content, dict):
                continue
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])

        if not text_parts:
            raise RuntimeError(f"Gemini returned an unexpected response payload: {response_payload}")

        return "\n".join(text_parts)

    def _build_contents(
        self,
        prompt: str | None,
        messages: Sequence[dict[str, str]] | None,
    ) -> list[dict[str, object]]:
        contents: list[dict[str, object]] = []

        if messages:
            for message in messages:
                role = message.get("role")
                content = message.get("content", "").strip()
                if role not in {"assistant", "user"} or not content:
                    continue

                contents.append(
                    {
                        "role": "model" if role == "assistant" else "user",
                        "parts": [{"text": content}],
                    }
                )

        if not contents and prompt:
            stripped_prompt = prompt.strip()
            if stripped_prompt:
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"text": stripped_prompt}],
                    }
                )

        if not contents:
            raise RuntimeError("A prompt or at least one chat message is required.")

        return contents


OpenAIModel = GeminiModel
Llama3 = GeminiModel
