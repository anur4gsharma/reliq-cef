"""Runtime discovery and deterministic execution-plan construction."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Runtime:
    language: str
    alias: str
    executable: str
    version: str
    label: str
    source: str = "global"


@dataclass(frozen=True)
class ExecutionPlan:
    runtime: Runtime
    argv: tuple[str, ...]
    suffix: str


_COMMANDS = {
    "python": ("python", "py"), "javascript": ("node", "js"),
    "powershell": ("pwsh", "powershell"), "bash": ("bash", "sh"),
    "cpp": ("g++", "c++", "clang++"),
}
_ALIASES = {"python": "python", "py": "python", "javascript": "javascript", "js": "javascript",
            "powershell": "powershell", "ps": "powershell", "bash": "bash", "sh": "bash",
            "cpp": "cpp", "c++": "cpp"}


def _version(exe: str, language: str) -> str | None:
    args = {"python": ["--version"], "javascript": ["--version"], "powershell": ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            "bash": ["--version"], "cpp": ["--version"]}[language]
    try:
        result = subprocess.run([exe, *args], capture_output=True, text=True, timeout=2, check=False)
        output = (result.stdout or result.stderr).strip().splitlines()
        if result.returncode != 0 or not output: return None
        checks = {
            "python": [exe, "-c", "pass"], "javascript": [exe, "-e", "process.exit(0)"],
            "powershell": [exe, "-NoLogo", "-NoProfile", "-Command", "exit 0"],
            "bash": [exe, "-c", ":"],
        }
        if language == "cpp":
            with tempfile.TemporaryDirectory(prefix="reliq-probe-") as directory:
                source = Path(directory) / "probe.cpp"
                output_path = Path(directory) / ("probe.exe" if os.name == "nt" else "probe")
                source.write_text("int main(){return 0;}\n", encoding="utf-8")
                check = subprocess.run([exe, "-std=c++17", str(source), "-o", str(output_path)],
                                       capture_output=True, timeout=3, check=False)
        else:
            check = subprocess.run(checks[language], capture_output=True, timeout=2, check=False)
        return output[0][:120] if check.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def discover(project: str | Path | None = None) -> list[Runtime]:
    """Find and validate likely runtimes; project Python env checks are scoped."""
    candidates: list[Runtime] = []
    python_paths: list[tuple[str, str]] = []
    if os.environ.get("VIRTUAL_ENV"):
        base = Path(os.environ["VIRTUAL_ENV"])
        python_paths.append((str(base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")), "activated environment"))
    if os.environ.get("CONDA_PREFIX"):
        base = Path(os.environ["CONDA_PREFIX"])
        python_paths.append((str(base / ("python.exe" if os.name == "nt" else "bin/python")), "Conda environment"))
    if project:
        base = Path(project).expanduser().resolve()
        if base.is_file():
            base = base.parent
        for dirname in (".venv", "venv", "env"):
            env = base / dirname
            python_paths.append((str(env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")), f"project {dirname}"))
    for command in ("python", "python3"):
        found = shutil.which(command)
        if found:
            python_paths.append((found, "PATH"))
    seen: set[str] = set()
    for exe, source in python_paths:
        if not Path(exe).is_file():
            continue
        key = os.path.normcase(os.path.abspath(exe))
        if key in seen:
            continue
        seen.add(key)
        version = _version(exe, "python")
        if version:
            candidates.append(Runtime("Python", "py", exe, version, f"{version} · {source}", source))
    for lang, commands in _COMMANDS.items():
        if lang == "python":
            continue
        for command in commands:
            exe = shutil.which(command)
            if exe and os.path.normcase(exe) not in seen:
                version = _version(exe, lang)
                if version:
                    candidates.append(Runtime(lang, _language_alias(lang), exe, version, f"{version} · {exe}"))
                    seen.add(os.path.normcase(exe))
                    break
    return candidates


def validate(runtime: Runtime) -> bool:
    """Recheck a pinned runtime immediately before execution."""
    return Path(runtime.executable).is_file() and _version(runtime.executable, runtime.language.lower()) is not None


def _language_alias(language: str) -> str:
    return {"javascript": "js", "powershell": "ps", "bash": "sh", "cpp": "cpp"}.get(language, "py")


def plan(runtime: Runtime, source_path: str, output_path: str | None = None) -> ExecutionPlan:
    """Construct argument vectors; source is always a file inside Reliq's workspace."""
    lang = runtime.language.lower()
    if lang == "python":
        argv, suffix = (runtime.executable, "-u", source_path), ".py"
    elif lang == "javascript":
        argv, suffix = (runtime.executable, source_path), ".js"
    elif lang == "bash":
        argv, suffix = (runtime.executable, source_path), ".sh"
    elif lang == "powershell":
        argv, suffix = (runtime.executable, "-NoLogo", "-NoProfile", "-File", source_path), ".ps1"
    elif lang == "cpp":
        if not output_path:
            raise ValueError("C++ execution requires an output path")
        argv, suffix = (runtime.executable, "-std=c++17", source_path, "-o", output_path), ".cpp"
    else:
        raise ValueError(f"Unsupported language: {runtime.language}")
    return ExecutionPlan(runtime, argv, suffix)


def language_for_extension(path: str) -> str | None:
    return {".py": "python", ".js": "javascript", ".mjs": "javascript", ".sh": "bash", ".ps1": "powershell", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp"}.get(Path(path).suffix.lower())
