"""Runtime discovery, validation, and deterministic execution-plan construction."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class Runtime:
    language: str
    alias: str
    executable: str
    version: str
    label: str
    source: str = "PATH"
    environment_type: str = ""
    environment_name: str = ""
    project: str = ""
    identity: str = ""

    def __post_init__(self):
        if not self.identity:
            normalized = os.path.normcase(os.path.realpath(os.path.abspath(self.executable)))
            object.__setattr__(self, "identity", f"{self.language.lower()}:{normalized}")


@dataclass(frozen=True)
class ExecutionPlan:
    runtime: Runtime
    argv: tuple[str, ...]
    suffix: str


_COMMANDS = {
    "python": ("python", "python3"), "javascript": ("node",),
    "powershell": ("pwsh", "powershell"), "bash": ("bash", "sh"),
    "cpp": ("g++", "c++", "clang++"),
}
_ALIASES = {"python": "py", "javascript": "js", "powershell": "ps", "bash": "sh", "cpp": "cpp"}
_ENV_TIMEOUT = 2


def _run(argv: list[str], timeout: float = _ENV_TIMEOUT, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Manager and probe commands always use argv, bounded timeouts, and no shell."""
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, check=False, cwd=cwd)


def _version(exe: str, language: str) -> str | None:
    language = language.lower()
    args = {"python": ["--version"], "javascript": ["--version"],
            "powershell": ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            "bash": ["--version"], "cpp": ["--version"]}.get(language)
    if not args:
        return None
    try:
        result = _run([exe, *args])
        output = (result.stdout or result.stderr).strip().splitlines()
        if result.returncode or not output:
            return None
        checks = {"python": [exe, "-c", "pass"], "javascript": [exe, "-e", "process.exit(0)"],
                  "powershell": [exe, "-NoLogo", "-NoProfile", "-Command", "exit 0"], "bash": [exe, "-c", ":"]}
        if language == "cpp":
            with tempfile.TemporaryDirectory(prefix="reliq-probe-") as directory:
                source = Path(directory) / "probe.cpp"
                output_path = Path(directory) / ("probe.exe" if os.name == "nt" else "probe")
                source.write_text("int main(){return 0;}\n", encoding="utf-8")
                check = _run([exe, "-std=c++17", str(source), "-o", str(output_path)], timeout=4)
        else:
            check = _run(checks[language])
        return output[0][:120] if check.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, PermissionError):
        return None


def validate(runtime: Runtime) -> bool:
    """Recheck a pinned executable immediately before execution."""
    try:
        return Path(runtime.executable).is_file() and _version(runtime.executable, runtime.language.lower()) is not None
    except (OSError, PermissionError, ValueError):
        return False


def _python_executable(base: Path, conda: bool = False) -> Path:
    if os.name == "nt":
        return base / ("python.exe" if conda else "Scripts/python.exe")
    return base / "bin/python"


def _normalize(path: str | Path) -> str:
    try:
        return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))
    except (OSError, ValueError):
        return os.path.normcase(os.path.abspath(os.fspath(path)))


def _project_root(project: str | Path | None) -> Path | None:
    if not project:
        return None
    try:
        path = Path(project).expanduser().resolve()
        return path.parent if path.is_file() else path
    except (OSError, RuntimeError):
        return None


def _manager_output(argv: list[str], *, timeout: float = 3, cwd: str | None = None) -> str | None:
    try:
        result = _run(argv, timeout, cwd)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, PermissionError):
        return None


def _json_executable_paths(output: str) -> list[str]:
    """Extract executable path fields from manager JSON without relying on order."""
    try:
        payload = json.loads(output)
    except (ValueError, TypeError):
        return []
    paths: list[str] = []
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"path", "executable"} and isinstance(item, str):
                    paths.append(item)
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(payload)
    return paths


def _python_candidates(project: str | Path | None) -> list[tuple[str, str, str, str, str]]:
    """Return (path, origin, env type, env name, associated project) candidates."""
    found: list[tuple[str, str, str, str, str]] = []
    project_root = _project_root(project)
    project_text = str(project_root) if project_root else ""

    def add(path: str | Path, origin: str, kind: str = "", name: str = "", association: str = ""):
        found.append((os.fspath(path), origin, kind, name, association))

    active = os.environ.get("VIRTUAL_ENV")
    conda_prefix = os.environ.get("CONDA_PREFIX")

    project_markers = set()
    if project_root:
        for marker in ("Pipfile", "poetry.lock", "uv.lock", "pyproject.toml"):
            if (project_root / marker).is_file():
                project_markers.add(marker)
        for dirname in (".venv", "venv", "env"):
            add(_python_executable(project_root / dirname), "project environment", "", dirname, project_text)

        # Supported CLI lookups are scoped to their project and never create an env.
    uv = shutil.which("uv")
    if uv:
        # This reports only already-installed uv-managed interpreters; it cannot
        # trigger a Python download and does not inspect uv's cache format.
        output = _manager_output([uv, "python", "list", "--managed-python", "--only-installed", "--output-format", "json"], timeout=4)
        if output:
            for executable in _json_executable_paths(output):
                add(executable, "uv", "uv", Path(executable).parent.name, "")
        if project_root and ("uv.lock" in project_markers or (project_root / ".venv").is_dir()):
            # uv python find reports the interpreter selected for this project; the
            # local .venv above remains the primary, manager-neutral project entry.
            output = _manager_output([uv, "python", "find", "--project", str(project_root)])
            if output:
                add(output.strip().splitlines()[0], "uv", "uv", "project interpreter", project_text)
    if project_root:
        poetry = shutil.which("poetry")
        if poetry and ("poetry.lock" in project_markers or _has_poetry_marker(project_root)):
            output = _manager_output([poetry, "env", "info", "--path"], timeout=4, cwd=project_text)
            if output:
                add(_python_executable(Path(output.strip())), "Poetry", "poetry", Path(output.strip()).name, project_text)
        pipenv = shutil.which("pipenv")
        if pipenv and ("Pipfile" in project_markers):
            output = _manager_output([pipenv, "--venv"], timeout=4, cwd=project_text)
            if output:
                add(_python_executable(Path(output.strip())), "Pipenv", "pipenv", Path(output.strip()).name, project_text)

    # Project-local explicit choices take precedence in the initial list. Refresh
    # still preserves the currently pinned identity in the presentation layer.
    active_prefix = active or conda_prefix
    if active_prefix:
        kind = "venv" if active else "conda"
        add(_python_executable(Path(active_prefix), conda=not bool(active)), "active environment", kind,
            Path(active_prefix).name, project_text)
    # sys.executable ensures Reliq can discover the interpreter that launched it.
    add(sys.executable, "active interpreter", "", "", project_text)

    conda = shutil.which("conda")
    if conda:
        output = _manager_output([conda, "env", "list", "--json"], timeout=4)
        if output:
            try:
                environments = json.loads(output).get("envs", [])
                for env in environments if isinstance(environments, list) else []:
                    prefix = Path(env)
                    add(_python_executable(prefix, conda=True), "Conda", "conda", prefix.name,
                        project_text if conda_prefix and _normalize(prefix) == _normalize(conda_prefix) else "")
            except (ValueError, TypeError, OSError):
                pass

    for command in _COMMANDS["python"]:
        executable = shutil.which(command)
        if executable:
            add(executable, "PATH", "", "", "")
    return found


def _has_poetry_marker(root: Path) -> bool:
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
        return "[tool.poetry" in text
    except (OSError, UnicodeError):
        return False


def discover(project: str | Path | None = None) -> list[Runtime]:
    """Find and verify local interpreters without recursive filesystem scans.

    Manager enumeration is best-effort: Conda uses ``conda env list --json``;
    Poetry and Pipenv are queried only for associated project markers; uv is
    asked for the project interpreter when a uv project environment is present.
    This is intentionally not an exhaustive inventory of every manager cache.
    """
    candidates: list[Runtime] = []
    seen: dict[str, int] = {}
    for executable, source, kind, name, association in _python_candidates(project):
        key = _normalize(executable)
        if key in seen:
            index = seen[key]
            old = candidates[index]
            # Keep the highest-value origin and fill gaps with useful metadata.
            priorities = {"project environment": 0, "Poetry": 1, "Pipenv": 1, "Conda": 1,
                          "uv": 1, "active environment": 2, "active interpreter": 2, "PATH": 3}
            if priorities.get(source, 4) < priorities.get(old.source, 4):
                candidates[index] = replace(old, source=source, environment_type=kind or old.environment_type,
                                            environment_name=name or old.environment_name,
                                            project=association or old.project,
                                            label=f"{old.version} · {name or source}")
            elif not old.environment_name and name:
                candidates[index] = replace(old, environment_type=kind or old.environment_type,
                                            environment_name=name, project=association or old.project)
            continue
        try:
            if not Path(executable).is_file():
                continue
            version = _version(executable, "python")
        except (OSError, PermissionError, ValueError):
            version = None
        if not version:
            continue
        display_env = name or (Path(executable).parent.parent.name if source in {"active environment", "project environment"} else source)
        label = f"{version} · {display_env}"
        resolved_executable = os.path.realpath(os.path.abspath(executable))
        runtime = Runtime("Python", "py", resolved_executable, version, label, source,
                          kind, name, association)
        seen[key] = len(candidates)
        candidates.append(runtime)

    for language, commands in _COMMANDS.items():
        if language == "python":
            continue
        seen_language: set[str] = set()
        for command in commands:
            executable = shutil.which(command)
            if not executable:
                continue
            key = _normalize(executable)
            if key in seen_language:
                continue
            seen_language.add(key)
            version = _version(executable, language)
            if version:
                candidates.append(Runtime(language, _ALIASES[language], os.path.realpath(os.path.abspath(executable)), version,
                                          f"{version} · {executable}", "PATH"))
                break
    return candidates


def plan(runtime: Runtime, source_path: str, output_path: str | None = None) -> ExecutionPlan:
    """Construct argument vectors; source is always a file inside Reliq's workspace."""
    lang = runtime.language.lower()
    if lang == "python": argv, suffix = (runtime.executable, "-u", source_path), ".py"
    elif lang == "javascript": argv, suffix = (runtime.executable, source_path), ".js"
    elif lang == "bash": argv, suffix = (runtime.executable, source_path), ".sh"
    elif lang == "powershell": argv, suffix = (runtime.executable, "-NoLogo", "-NoProfile", "-File", source_path), ".ps1"
    elif lang == "cpp":
        if not output_path: raise ValueError("C++ execution requires an output path")
        argv, suffix = (runtime.executable, "-std=c++17", source_path, "-o", output_path), ".cpp"
    else: raise ValueError(f"Unsupported language: {runtime.language}")
    return ExecutionPlan(runtime, argv, suffix)


def language_for_extension(path: str) -> str | None:
    return {".py": "python", ".js": "javascript", ".mjs": "javascript", ".sh": "bash",
            ".ps1": "powershell", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp"}.get(Path(path).suffix.lower())
