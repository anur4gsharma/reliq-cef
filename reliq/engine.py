"""Subprocess supervision with bounded capture and Reliq-owned workspaces."""
from __future__ import annotations

import os
import codecs
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .runtime import Runtime, plan

OUTPUT_LIMIT = 1_000_000
DEFAULT_TIMEOUT = 30


@dataclass
class ExecutionResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration: float
    error: str = ""


def _root() -> Path:
    path = Path(tempfile.gettempdir()) / "reliq" / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _safe_remove(path: Path, root: Path) -> None:
    resolved = path.resolve(strict=False)
    if resolved.parent != root or not resolved.name.startswith("run-"):
        raise ValueError("Refusing to remove a path outside Reliq's run root")
    if path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def sweep_stale() -> None:
    root = _root()
    for child in root.iterdir():
        if child.name.startswith("run-") and child.parent.resolve() == root:
            try:
                # A process from another live Reliq window may still own a run.
                # Crash leftovers are recovered after a conservative age limit.
                if time.time() - child.stat().st_mtime > 24 * 60 * 60:
                    _safe_remove(child, root)
            except (OSError, ValueError):
                pass


class Runner:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, output_limit: int = OUTPUT_LIMIT):
        self.timeout = timeout
        self.output_limit = output_limit
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    def prepare(self) -> None:
        """Reset cancellation before dispatching a worker for a new run."""
        with self._lock:
            self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            process = self._process
        if process and process.poll() is None:
            self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen) -> None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=2, check=False)
                if process.poll() is None: process.kill()
            else:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=0.75)
        except (OSError, subprocess.TimeoutExpired):
            try:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass

    def execute(self, runtime: Runtime, source: str, working_directory: str | None = None,
                on_output: Callable[[str, str], None] | None = None) -> ExecutionResult:
        started = time.monotonic()
        workspace = _root() / f"run-{uuid.uuid4().hex}"
        workspace.mkdir()
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        totals = {"stdout": 0, "stderr": 0}
        status, exit_code, error = "launch_error", None, ""
        process = None
        result = None
        try:
            source_path = str(workspace / ("program" + _suffix(runtime.language)))
            Path(source_path).write_text(source, encoding="utf-8", newline="")
            binary = str(workspace / ("program.exe" if os.name == "nt" else "program")) if runtime.language.lower() == "cpp" else None
            execution = plan(runtime, source_path, binary)
            compile_process = None
            argv = execution.argv
            if runtime.language.lower() == "cpp":
                compile_process = subprocess.run(argv, cwd=working_directory or workspace, capture_output=True, text=True, timeout=self.timeout, check=False)
                if compile_process.returncode:
                    result = ExecutionResult("nonzero_exit", "", compile_process.stderr, compile_process.returncode, time.monotonic()-started)
                    return result
                argv = (binary,)
            kwargs = {"cwd": working_directory or workspace, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True
            with self._lock:
                process = subprocess.Popen(argv, **kwargs)
                self._process = process
            def read(stream, name, store):
                decoder = codecs.getincrementaldecoder("utf-8")("replace")
                while True:
                    data = stream.read1(4096)
                    if not data:
                        chunk = decoder.decode(b"", final=True)
                        if not chunk: break
                    else:
                        chunk = decoder.decode(data)
                    remaining = max(0, self.output_limit - totals[name])
                    if remaining:
                        kept = chunk[:remaining]
                        store.append(kept)
                        totals[name] += len(kept)
                        if kept and on_output:
                            on_output(name, kept)
                    if len(chunk) > remaining and not totals.get("truncated"):
                        marker = "\n[output truncated at 1 MB]\n"
                        store.append(marker)
                        totals["truncated"] = 1
                        if on_output:
                            on_output(name, marker)
            readers = [threading.Thread(target=read, args=(process.stdout, "stdout", stdout_parts), daemon=True),
                       threading.Thread(target=read, args=(process.stderr, "stderr", stderr_parts), daemon=True)]
            for reader in readers: reader.start()
            try:
                process.wait(timeout=self.timeout)
                status = "success" if process.returncode == 0 else "nonzero_exit"
            except subprocess.TimeoutExpired:
                status = "timeout"
                self._terminate(process)
                try: process.wait(timeout=1)
                except subprocess.TimeoutExpired: pass
            if os.name != "nt" and any(reader.is_alive() for reader in readers):
                try: os.killpg(process.pid, signal.SIGTERM)
                except OSError: pass
                time.sleep(.1)
                try: os.killpg(process.pid, signal.SIGKILL)
                except OSError: pass
            for reader in readers: reader.join(timeout=2)
            for stream in (process.stdout, process.stderr):
                if stream: stream.close()
            exit_code = process.poll()
            with self._lock:
                if self._cancelled and status != "timeout": status = "cancelled"
            result = ExecutionResult(status, "".join(stdout_parts), "".join(stderr_parts), exit_code,
                                    time.monotonic()-started, error)
            return result
        except subprocess.TimeoutExpired as exc:
            result = ExecutionResult("timeout", "".join(stdout_parts), "".join(stderr_parts), exit_code,
                                     time.monotonic()-started, str(exc))
            return result
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result = ExecutionResult(status, "".join(stdout_parts), "".join(stderr_parts), exit_code,
                                     time.monotonic()-started, str(exc))
            return result
        finally:
            if process is not None and process.poll() is None:
                self._terminate(process)
                try: process.wait(timeout=1)
                except subprocess.TimeoutExpired: pass
            if process is not None:
                for stream in (process.stdout, process.stderr):
                    if stream and not stream.closed: stream.close()
            with self._lock: self._process = None
            try: _safe_remove(workspace, _root())
            except (OSError, ValueError) as exc:
                if result is not None:
                    result.error = f"workspace cleanup failed: {exc}"


def _suffix(language: str) -> str:
    return {"python": ".py", "javascript": ".js", "bash": ".sh", "powershell": ".ps1", "cpp": ".cpp"}[language.lower()]
