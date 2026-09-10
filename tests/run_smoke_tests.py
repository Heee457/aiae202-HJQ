#!/usr/bin/env python3
"""Run a smoke-test catalog against a locally served agent.

Usage:
  python tests/run_smoke_tests.py tests/lesson-16-smoke-tests.json --url http://localhost:8000

Service contract (implemented by the FastAPI services in lessons 01, 04, 05 and 16):
  GET  /health -> 200 {"status": "ok", "version": "..."}
  POST /chat   {"message": str, "conversation_id": str | null}
               -> 200 {"reply": str, "conversation_id": str}

Catalog entries POST one prompt each and assert on the reply. Assertions are
case-insensitive substring checks. `save_response_id_as` stores the returned
conversation_id under a name; `use_previous_response_id` sends it again so the
turn continues that conversation. A step that saves an id fails if the service
did not return a conversation_id; a step that uses an id which was never saved
fails without sending a request. Transport errors (connection refused, non-JSON
body, timeout) fail the step with status 0 and the run continues.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Result:
    test_id: str
    passed: bool
    detail: str


def _post_json(url: str, payload: dict, timeout: float) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, raw = response.status, response.read()
        body = json.loads(raw or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {"reply": exc.read().decode(errors="replace")}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return 0, {"reply": f"<transport error: {exc}>"}
    if not isinstance(body, dict):
        return 0, {"reply": raw.decode(errors="replace")}
    return status, body


def check_health(base_url: str, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def evaluate(assertions: dict, status: int, reply: str) -> tuple[bool, str]:
    expected_status = assertions.get("status", 200)
    if status != expected_status:
        return False, f"expected status {expected_status}, got {status}"
    text = reply.lower()
    problems = []
    if "contains_any" in assertions and not any(s.lower() in text for s in assertions["contains_any"]):
        problems.append(f"none of {assertions['contains_any']} found")
    if "contains_all" in assertions:
        missing = [s for s in assertions["contains_all"] if s.lower() not in text]
        if missing:
            problems.append(f"missing {missing}")
    if "contains_none" in assertions:
        present = [s for s in assertions["contains_none"] if s.lower() in text]
        if present:
            problems.append(f"forbidden {present} present")
    return (False, "; ".join(problems)) if problems else (True, "")


def run_step(test: dict, chat_url: str, saved_ids: dict[str, str], timeout: float) -> Result:
    payload = {"message": test["prompt"], "conversation_id": None}
    previous = test.get("use_previous_response_id")
    if previous:
        if previous not in saved_ids:
            return Result(test["id"], False, f"no saved conversation_id named {previous!r} (did the earlier step fail?)")
        payload["conversation_id"] = saved_ids[previous]
    status, body = _post_json(chat_url, payload, timeout)
    reply = str(body.get("reply", ""))
    passed, detail = evaluate(test.get("assertions", {}), status, reply)
    save_as = test.get("save_response_id_as")
    if save_as:
        if body.get("conversation_id"):
            saved_ids[save_as] = str(body["conversation_id"])
        else:
            passed = False
            detail = "; ".join(filter(None, [detail, "service did not return conversation_id"]))
    if not passed:
        detail = f"{detail} | reply: {reply[:200]!r}"
    return Result(test["id"], passed, detail)


def run_catalog(
    catalog: dict,
    base_url: str,
    timeout: float = 120.0,
    on_result: Callable[[Result], None] | None = None,
) -> list[Result]:
    chat_url = f"{base_url.rstrip('/')}/chat"
    saved_ids: dict[str, str] = {}
    results: list[Result] = []
    for test in catalog.get("tests", []):
        result = run_step(test, chat_url, saved_ids, timeout)
        results.append(result)
        if on_result:
            on_result(result)
    return results


def print_result(r: Result) -> None:
    print(f"{'PASS' if r.passed else 'FAIL'}  {r.test_id}" + (f"  {r.detail}" if r.detail else ""), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--url", default="http://localhost:8000", help="base URL of the running agent service")
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per request")
    args = parser.parse_args(argv)

    catalog = json.loads(args.catalog.read_text())
    if not catalog.get("tests"):
        print(f"FAIL: catalog has no tests ({args.catalog})")
        return 1
    if not check_health(args.url):
        print(f"FAIL: {args.url}/health is not reachable. Start the agent service first.")
        return 1
    results = run_catalog(catalog, args.url, args.timeout, on_result=print_result)
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
