#!/usr/bin/env python3
"""Probe the configured OpenAI-compatible endpoint for the capabilities the course needs.

Usage:  python scripts/check_endpoint.py
Reads LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, the optional LLM_EXTRA_BODY (a JSON
object sent as extra_body on every request) and the optional VISION_* variables
from the repository .env. Exit code 0 when chat and tool calling both work.
"""
from __future__ import annotations

import json
import os
import sys

from dotenv import find_dotenv, load_dotenv

CAPABILITIES = {
    "chat": "all lessons",
    "tools": "01, 03-05, 07-13, 16-18 (create_agent needs tool calling)",
    "structured": "03, 07, 08 (structured output forces a tool call; DeepSeek thinking models need LLM_EXTRA_BODY to disable thinking)",
    "vision": "10 (expense demo), 15 (browser-use) — optional, set VISION_* to enable",
}

# 1x1 PNG, used to test image input without shipping an asset.
TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

STRUCTURED_HINT = (
    "Hint: structured output needs forced tool calls. "
    "On DeepSeek set LLM_EXTRA_BODY='{\"thinking\": {\"type\": \"disabled\"}}' in .env."
)


def extra_body_from_env(var: str = "LLM_EXTRA_BODY") -> dict | None:
    """Parse a JSON object from an environment variable; empty or unset means no extra body."""
    raw = os.environ.get(var, "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        print(f"Ignoring {var}: not valid JSON ({exc}).", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"Ignoring {var}: must be a JSON object, got {type(data).__name__}.", file=sys.stderr)
        return None
    return data


def probe_chat(client, model, extra_body=None) -> bool:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with the single word OK."}],
        extra_body=extra_body,
    )
    return bool((r.choices[0].message.content or "").strip())


def probe_tools(client, model, extra_body=None) -> bool:
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    }]
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "What is the weather in Paris right now? You must call the tool."}],
        tools=tools,
        tool_choice="auto",
        extra_body=extra_body,
    )
    calls = r.choices[0].message.tool_calls or []
    return any(c.function.name == "get_weather" for c in calls)


def probe_structured(client, model, extra_body=None) -> bool:
    """Force one tool call, which is how LangChain's create_agent(response_format=...) gets structured output."""
    tools = [{
        "type": "function",
        "function": {
            "name": "Recommendation",
            "description": "A travel recommendation.",
            "parameters": {
                "type": "object",
                "properties": {"destination": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["destination", "reason"],
            },
        },
    }]
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Recommend one European city for a weekend of museums."}],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "Recommendation"}},
        extra_body=extra_body,
    )
    for call in r.choices[0].message.tool_calls or []:
        if call.function.name != "Recommendation":
            continue
        try:
            data = json.loads(call.function.arguments or "")
        except ValueError:
            return False
        return isinstance(data, dict) and "destination" in data
    return False


def probe_vision(client, model, extra_body=None) -> bool:
    r = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in five words or fewer."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{TINY_PNG_B64}"}},
            ],
        }],
        extra_body=extra_body,
    )
    return bool(r.choices[0].message.content)


MIN_SECRET_LENGTH = 8


def _redact(text: str) -> str:
    """Replace any configured API key with a placeholder so diagnostics never leak secrets."""
    for var in ("LLM_API_KEY", "VISION_API_KEY"):
        secret = os.environ.get(var, "")
        if len(secret) >= MIN_SECRET_LENGTH:  # placeholders like "ollama" are not secrets
            text = text.replace(secret, "<redacted>")
    return text


def _describe(exc: BaseException) -> str:
    parts = [f"{type(exc).__name__}: {exc}"]
    if exc.__cause__ is not None:  # e.g. APIConnectionError only says "Connection error."
        parts.append(f"caused by {type(exc.__cause__).__name__}: {exc.__cause__}")
    return _redact(" | ".join(parts))[:300]


def _safe(fn, *args) -> bool:
    try:
        return bool(fn(*args))
    except Exception as exc:  # any provider error means "capability not available"
        print(f"    ({fn.__name__}: {_describe(exc)})", file=sys.stderr)
        return False


def run_probes(
    client, model, vision_client=None, vision_model=None, extra_body=None, vision_extra_body=None
) -> dict[str, bool | None]:
    results: dict[str, bool | None] = {"chat": _safe(probe_chat, client, model, extra_body)}
    if results["chat"]:
        results["tools"] = _safe(probe_tools, client, model, extra_body)
        results["structured"] = _safe(probe_structured, client, model, extra_body)
    else:  # nothing else can work without a reply; do not bury the one real error under two more
        results["tools"] = results["structured"] = None  # reported as SKIPPED; exit code still fails
    results["vision"] = None
    if vision_client is not None and vision_model:
        results["vision"] = _safe(probe_vision, vision_client, vision_model, vision_extra_body)
    return results


def exit_code(results: dict[str, bool | None]) -> int:
    return 0 if results.get("chat") and results.get("tools") else 1


def print_report(results: dict[str, bool | None], model: str, base_url: str) -> None:
    print(f"Endpoint: {base_url}\nModel:    {model}\n")
    print(f"{'capability':<12}{'result':<10}used by lessons")
    for name, lessons in CAPABILITIES.items():
        value = results.get(name)
        label = "SKIPPED" if value is None else ("PASS" if value else "FAIL")
        print(f"{name:<12}{label:<10}{lessons}")
    print()
    if exit_code(results) == 0:
        print("Ready: this endpoint supports everything the course requires.")
        if results.get("structured") is False:
            print(STRUCTURED_HINT)
    elif not results.get("chat"):
        print("Not ready: no reply from the endpoint. Check LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env (see the error above).")
    else:
        print("Not ready: the course needs a Chat Completions endpoint with tool calling. Pick another model or provider.")


def main() -> int:
    from openai import OpenAI

    load_dotenv(find_dotenv())
    base_url = os.environ.get("LLM_BASE_URL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    if not (base_url and api_key and model):
        print("Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env first (copy .env.example).")
        return 1
    client = OpenAI(base_url=base_url, api_key=api_key)
    extra_body = extra_body_from_env("LLM_EXTRA_BODY")

    vision_client = vision_model = vision_extra_body = None
    if os.environ.get("VISION_MODEL"):
        vision_model = os.environ["VISION_MODEL"]
        vision_client = OpenAI(
            base_url=os.environ.get("VISION_BASE_URL") or base_url,
            api_key=os.environ.get("VISION_API_KEY") or api_key,
        )
        vision_extra_body = extra_body_from_env("VISION_EXTRA_BODY")

    results = run_probes(client, model, vision_client, vision_model, extra_body, vision_extra_body)
    print_report(results, model, base_url)
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
