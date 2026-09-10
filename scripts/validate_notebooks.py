#!/usr/bin/env python3
"""Execute course notebooks and fail on any cell error.

Usage:
  python scripts/validate_notebooks.py                     # every notebook in every lesson
  python scripts/validate_notebooks.py --lesson 01 --lesson 04
  python scripts/validate_notebooks.py --path 05-agentic-rag/code_samples/05-python-langchain-agent.ipynb

Each notebook runs in its own directory with a fresh python3 kernel. There is no
skip option: a notebook that cannot run is a failure and must be fixed or
recorded as "not verified" in docs/superpowers/specs/acceptance-record.md.

A cell timeout, a kernel crash, or a missing notebook file is reported as FAIL
for that notebook and the run continues with the next one. The kernel may print
"[IPKernelApp] WARNING ... TCP without encryption" on stderr; that is harmless.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError

ROOT = Path(__file__).resolve().parent.parent
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def find_notebooks(root: Path, lessons: list[str]) -> list[Path]:
    found: list[Path] = []
    for lesson_dir in sorted(root.iterdir()):
        if not lesson_dir.is_dir() or not lesson_dir.name[:2].isdigit():
            continue
        if lessons and lesson_dir.name[:2] not in lessons:
            continue
        found.extend(
            p for p in sorted(lesson_dir.rglob("*.ipynb")) if ".ipynb_checkpoints" not in p.parts
        )
    return found


def execute(path: Path, timeout: int) -> tuple[bool, str]:
    try:
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(path.parent)}},
        )
        client.execute()
        return True, ""
    except CellTimeoutError as exc:
        return False, f"Timeout: a cell timed out after {timeout}s\n{exc}"
    except DeadKernelError as exc:
        return False, f"Kernel died: {exc}"
    except CellExecutionError as exc:
        return False, str(exc)
    except (OSError, ValueError) as exc:  # ValueError covers nbformat's NotJSONError on a corrupt file
        return False, f"Cannot read notebook: {exc}"


def excerpt(text: str, limit: int = 2000) -> str:
    """Strip ANSI colour codes; keep the head (cell source) and tail (exception) of long errors."""
    text = ANSI_ESCAPE.sub("", text).strip()
    if len(text) <= limit:
        return text
    return text[:400] + "\n...\n" + text[-1600:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lesson", action="append", default=[], help="two-digit lesson prefix, repeatable")
    parser.add_argument("--path", action="append", default=[], type=Path, help="explicit notebook path, repeatable")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to scan")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per cell")
    args = parser.parse_args()
    lessons = [lesson.zfill(2) for lesson in args.lesson]

    notebooks = [p.resolve() for p in args.path] if args.path else find_notebooks(args.root.resolve(), lessons)
    if not notebooks:
        print("No notebooks selected.")
        return 1

    failures = 0
    for nb_path in notebooks:
        start = time.monotonic()
        ok, error = execute(nb_path, args.timeout)
        elapsed = time.monotonic() - start
        label = "PASS" if ok else "FAIL"
        try:
            shown = nb_path.relative_to(args.root.resolve())
        except ValueError:
            shown = nb_path
        print(f"{label}  {shown}  ({elapsed:.0f}s)", flush=True)
        if not ok:
            failures += 1
            print(excerpt(error), flush=True)
    print(f"\n{len(notebooks) - failures}/{len(notebooks)} notebooks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
