# Agent Smoke Tests

This folder holds **smoke-test catalogs** for the agents you build in the course
and a small runner, `run_smoke_tests.py`, that executes a catalog against an
agent you are serving locally. A smoke test is a cheap, fast check that a served
agent is reachable, responding, and following its most basic prompt
expectations. It is a first gate, not a replacement for the evaluation pipeline
you build in [Lesson 10](../10-ai-agents-production/README.md) and
[Lesson 16](../16-deploying-scalable-agents/README.md).

## Service contract

The runner talks to any HTTP service that implements two routes. Each lesson's
`NN-serve-*.py` script (Lessons 01, 04, 05 and 16) implements them; you can wrap
any agent the same way.

| Route | Request | Response |
|---|---|---|
| `GET /health` | – | `200 {"status": "ok", "version": "<active version>"}` |
| `POST /chat` | `{"message": "<text>", "conversation_id": "<id or null>"}` | `200 {"reply": "<text>", "conversation_id": "<id>"}` |

A null `conversation_id` starts a new conversation. Reusing the returned id
continues it, which is how multi-turn catalog steps work.

## How to run

1. Serve the lesson's agent (each lesson with a catalog shows how in its README).
2. Run the catalog:

   ```bash
   ```

3. The runner prints one `PASS`/`FAIL` line per step and exits non-zero on any failure.

## Catalog → lesson

| Catalog | Lesson |
|---|---|
| [`lesson-01-smoke-tests.json`](./lesson-01-smoke-tests.json) | [01 – Intro to AI Agents](../01-intro-to-ai-agents/README.md) |

Lessons that are conceptual, run only locally (17), or produce open-ended
creative output do not ship a catalog.

## Catalog schema

Each catalog is a JSON document with a top-level `tests` array:

| Field | Meaning |
|-------|---------|
| `id` | Unique step identifier printed in the log. |
| `description` | Human-readable purpose. |
| `prompt` | The message sent to the agent. |
| `assertions.status` | Expected HTTP status (default 200). |
| `assertions.contains_any` | Pass if the reply contains any of these substrings. |
| `assertions.contains_all` | Pass if the reply contains every substring. |
| `assertions.contains_none` | Pass if the reply contains none of these substrings. |
| `save_response_id_as` | Store the returned `conversation_id` under this name. |
| `use_previous_response_id` | Send the stored `conversation_id` so this turn continues that conversation. |

Assertions are case-insensitive substring checks.

Three rules keep multi-turn steps honest: a step with `save_response_id_as`
fails if the service does not return a `conversation_id`; a step with
`use_previous_response_id` naming an id that was never saved fails without
sending a request; and a transport error (connection refused, timeout,
non-JSON body) is reported as HTTP status `0`, so the `status` assertion fails
and the run continues with the next step.

## Unit tests for the tooling

`tests/scripts/` contains pytest tests for the runner and for the scripts in
`scripts/`. Run them with `python -m pytest tests/scripts -q`.
