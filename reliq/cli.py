"""Command-line parsing and execution entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import Runner, sweep_stale
from .runtime import discover, language_for_extension

LANGUAGE_ALIASES = {
    "py": "python",
    "python": "python",
    "js": "javascript",
    "javascript": "javascript",
    "sh": "bash",
    "bash": "bash",
    "ps": "powershell",
    "powershell": "powershell",
    "cpp": "cpp",
    "c++": "cpp",
}


def normalize_language(value: str) -> str:
    normalized = value.lower()
    return LANGUAGE_ALIASES.get(normalized, normalized)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reliq", description="A small local code scratchpad")
    parser.add_argument("target", nargs="?", help="language alias, source file, or - for stdin")
    parser.add_argument("--language", "-l", help="language used for stdin input")
    args = parser.parse_args(argv)
    target = args.target
    if target != "-":
        path = Path(target).expanduser() if target and Path(target).exists() else None
        if path:
            language = language_for_extension(str(path))
            if not language:
                parser.error(f"unsupported source extension: {path.suffix or '(none)'}")
            from .app import launch
            return launch(str(path))
        elif target:
            language = LANGUAGE_ALIASES.get(target.lower())
            if not language:
                parser.error(f"unknown language or file: {target}")
            from .app import launch
            return launch(selected_language=language)
        else:
            from .app import launch
            return launch()
    else:
        if sys.stdin.isatty(): parser.error("stdin mode requires piped input")
        source = sys.stdin.read()
        language = normalize_language(args.language or "python")
        if language not in {"python", "javascript", "bash", "powershell", "cpp"}:
            parser.error(f"unsupported language: {language}")
        project = None
    runtimes = discover(project)
    runtime = next((item for item in runtimes if item.language.lower() == language), None)
    if not runtime: parser.error(f"no usable {language} runtime found; install it and ensure it is on PATH")
    sweep_stale()
    result = Runner().execute(runtime, source, project, lambda stream, value: (sys.stderr if stream == "stderr" else sys.stdout).write(value))
    if result.error: print(result.error, file=sys.stderr)
    if result.status == "timeout": print("execution timed out", file=sys.stderr)
    if result.status == "timeout": return 124
    return result.exit_code if result.exit_code is not None else 1
