# Reliq

Reliq is a small, keyboard-first local code scratchpad built with Python and Tkinter. It targets Windows and Linux and has no third-party runtime dependencies.

## Requirements and installation

Install Python 3.10 or newer with Tk support. Install Reliq from a checkout:

```sh
python -m pip install .
reliq
```

On some Linux distributions, Tk is a separate OS package (often `python3-tk`). For development, use `python -m unittest discover -v` from the repository root.

## Use

- `reliq` opens a blank scratchpad.
- `reliq py`, `reliq js`, or `reliq sh` opens a blank editor with that language selected when its runtime is installed.
- `reliq path/to/file.py` opens a supported source file in the editor.
- `reliq -` executes piped stdin as Python; use `reliq - --language javascript` to choose another language.
- `Ctrl+Enter` runs; `Ctrl+.` stops; `Ctrl+O`, `Ctrl+S`, and `Ctrl+N` open, save, and create a file.

Supported languages are Python, Node.js JavaScript, Bash, PowerShell, and C++ using g++, c++, or clang++. Only runtimes that can return a version within the discovery timeout are shown. Runtime discovery checks PATH and relevant Python environments (`VIRTUAL_ENV`, `CONDA_PREFIX`, and `.venv`, `venv`, or `env` beside an opened file). Python choices display their interpreter path/version and source. The first detected candidate follows activated environment, project environment, then PATH precedence. Other choices can be selected from the runtime list.

Reliq saves edited files as UTF-8. Scratchpad execution uses a fresh Reliq-owned temporary directory as its working directory. For a saved source file, execution uses the file's parent directory, so relative reads and writes follow that project context. The source file itself is never used as the temporary execution file.

Execution defaults to a 30 second timeout. Stop and timeout terminate a POSIX process group on Linux, escalating from TERM to KILL. On Windows Reliq starts a new process group and uses `taskkill /T` for process-tree termination. Output is streamed over separate stdout and stderr readers and capped at 1 MB per stream. Since the streams are read independently, cross-stream ordering is approximate. Stale workspaces older than 24 hours are swept from Reliq's dedicated temp root at startup.

Reliq executes local programs with the current user's permissions and environment. A subprocess is not a security sandbox. Run only code you trust.

## Runtime installation

Install the desired runtime using its normal platform installation process and ensure its executable is on `PATH`. C++ additionally requires a working compiler toolchain. Reliq does not install or manage language runtimes.

## Limitations

The editor provides lightweight Python-oriented syntax coloring, line numbers, and basic file operations; it is not a full IDE. Runtime discovery validates availability through a bounded version command, then execution revalidates the selected executable. Python launcher `py.exe` enumeration, automatic Conda environment enumeration, and settings persistence are not implemented. Linux and Windows are the supported targets; macOS is not claimed.

## License

Reliq is available under the MIT License; see [LICENSE](LICENSE).
