# Reliq

Reliq is a small, keyboard-first local code scratchpad for Windows and Linux. It opens quickly, discovers usable local runtimes, and runs short programs without freezing the editor.

## Install Reliq

Choose a ready-to-run release artifact or install the Python package directly from a GitHub source archive. No clone or Git installation is needed for either route.

### Option 1: Download a ready-to-run application

Open [Reliq Releases](https://github.com/anur4gsharma/reliq-cef/releases) and download the asset for your platform. Release assets are generated for a version tag only after the Windows and Linux builds, tests, and smoke checks pass. If no release is listed yet, use the source archive option below.

**Windows:** Download `reliq-windows-x86_64.zip`, extract it, and double-click `reliq.exe` to open the GUI. The archive also contains `reliq-cli.exe` for command-line use, including piped stdin.

**Linux:** Download `reliq-linux-x86_64.tar.gz`, extract it, open a terminal in the extracted `reliq-linux-x86_64` directory, then run:

```sh
./reliq
```

The Linux artifact is built on Ubuntu 22.04 and requires a compatible glibc system. These applications bundle Reliq's Python and Tk runtime. They do **not** bundle the language runtimes used for your code: install Python, Node.js, Bash, PowerShell, or a C++ compiler separately for the languages you want to run. Linux builds and Windows artifacts are native to their respective operating systems; use the release that matches your platform and architecture.

### Option 2: Install from a GitHub source archive

This installs Reliq into your selected Python environment. It requires Python 3.10 or newer **with Tkinter/Tcl-Tk available**. The archive does not bundle Python or Tkinter.

**Windows prerequisites:** Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) and include the Tcl/Tk and IDLE feature in the installer. In PowerShell, install and start Reliq:

```powershell
py -3 -m pip install "https://github.com/anur4gsharma/reliq-cef/archive/refs/heads/main.zip"
reliq
```

**Linux prerequisites:** Install Python, pip, virtual environments, and your distribution's Tk package. For Debian/Ubuntu:

```sh
sudo apt install python3 python3-pip python3-venv python3-tk
python3 -m venv --system-site-packages "$HOME/.venvs/reliq"
source "$HOME/.venvs/reliq/bin/activate"
python -m pip install "https://github.com/anur4gsharma/reliq-cef/archive/refs/heads/main.zip"
reliq
```

The source archive follows the repository's `main` branch. To install a specific published source version instead, use the ZIP linked under that release's source assets or substitute its actual tag in the GitHub archive URL.

**Download the source ZIP in a browser:** Open [the Reliq repository](https://github.com/anur4gsharma/reliq-cef), select **Code**, choose **Download ZIP**, then extract it. With Python/Tkinter installed, install from the extracted directory using `py -3 -m pip install .` on Windows or `python -m pip install .` on Linux (activate a virtual environment first if desired), then run `reliq`.

### Launch and runtime prerequisites

- `reliq` opens a blank scratchpad.
- `reliq py`, `reliq js`, or `reliq sh` opens a blank editor with that language selected when its runtime is available.
- `reliq path/to/file.py` opens a supported source file.
- `reliq -` executes piped stdin as Python; select another language with `reliq - --language javascript`.

Reliq does not install language runtimes. Install the runtimes you need and make them available on `PATH`: Python; Node.js for JavaScript; Bash; PowerShell (`pwsh` or the platform's PowerShell executable); and a C++ compiler such as g++, c++, or clang++. Only detected, usable runtimes are shown in the editor.

### Troubleshooting

- **“Tkinter is not available” / `No module named '_tkinter'`:** Install the operating system's Tk development/runtime package for the same Python installation. On Debian/Ubuntu, install `python3-tk`; on Windows, rerun the Python installer and enable Tcl/Tk and IDLE. Then reinstall Reliq into that same Python environment.
- **A language is missing:** Install its runtime/compiler and ensure its executable is on `PATH`, then restart Reliq. An absent optional runtime does not prevent Reliq from launching.
- **Linux release executable does not start:** Extract the archive and run `./reliq` from a terminal to see diagnostics. The ready-to-run Linux build targets Ubuntu 22.04-compatible glibc; older or non-glibc distributions may not be compatible. Use source-archive installation if necessary.

### Uninstall

For a Python installation, use the same Python environment where Reliq was installed: `python -m pip uninstall reliq` (on Windows, `py -3 -m pip uninstall reliq` when installed into that interpreter). For the Linux virtual environment above, activate it first. For a downloaded application, close Reliq and delete the extracted folder.

## Using Reliq

- `Ctrl+Enter` runs the code; `Ctrl+.` stops it.
- `Ctrl+O`, `Ctrl+S`, and `Ctrl+N` open, save, and create a file.
- Reliq saves edited files as UTF-8. Scratchpad execution uses a fresh Reliq-owned temporary directory as its working directory. For a saved source file, execution uses the file's parent directory, so relative file access follows that project context. The original source file is not overwritten for execution.
- Execution has a 30-second default timeout. On Linux, Reliq terminates the execution process group, escalating from TERM to KILL. On Windows, it starts a new process group and uses `taskkill /T` for process-tree termination.
- stdout and stderr are streamed independently and each is capped at 1 MB. Their relative ordering is approximate. Stale workspaces older than 24 hours are swept from Reliq's dedicated temporary root at startup.

Reliq runs local code with your user's permissions and environment. A subprocess is **not a security sandbox**. Run only code you trust.

## Runtime discovery and editor behavior

Reliq supports Python, Node.js JavaScript, Bash, PowerShell, and C++ when a usable runtime/compiler is installed. Python choices include the interpreter running Reliq, the active `venv`/`virtualenv` or Conda environment, project `.venv`, `venv`, and `env` directories, and Python executables on `PATH`. Project-associated Poetry and Pipenv environments are queried through their CLIs. When `uv` is installed, Reliq queries its supported installed-managed-interpreter JSON listing and asks it for the interpreter selected by a uv project; ordinary `.venv` directories remain ordinary project environments in the list. Conda environments are enumerated with `conda env list --json`. Every candidate is probed before it appears.

Discovery is best-effort and deliberately bounded. Reliq does not crawl disks or undocumented manager caches, does not enumerate every `nvm` installation, and cannot guarantee a complete list of every interpreter managed by every tool. For JavaScript it uses the Node executable selected by the current `PATH` (including a currently selected nvm Node). Missing or failing optional managers do not prevent launch. Discovery and refresh run in the background. Choose the language and the specific interpreter in the toolbar; its details line shows the discovery source and executable path. Refresh keeps the current executable selected when it remains available. If it disappears, Reliq reports that it is unavailable and leaves the choice blank until you explicitly select another runtime. Opening a source file selects its language and prefers its project-local environment when one is found. Reliq never changes environments or silently swaps the selected executable before running; it revalidates the selected executable for each run.

The `tk.Text` editor pairs `()`, `[]`, `{}`, quotes, and backticks, skips an existing closer, removes a newly paired empty pair with Backspace, indents with four spaces, and carries indentation across Enter. Python gets a conservative colon and block-statement indentation heuristic. Other languages only carry the existing line indentation. Tab and Shift+Tab indent and dedent lines. Syntax coloring recognizes language-specific keywords, strings, comments, and numbers for Python, JavaScript, Bash, PowerShell, and C++; it is a lightweight lexer, not a parser, and does not understand every language grammar or interpolation rule. macOS is not a supported target.

## Development

The project requires Python 3.10+ and Tkinter. To work from a checkout, create a virtual environment and install the project:

```sh
python -m venv .venv
# Linux: use --system-site-packages when Tkinter comes from the OS package manager.
.venv/bin/python -m pip install -e .
.venv/bin/reliq
.venv/bin/python -m unittest discover -v
```

On Windows, use `.venv\Scripts\python -m pip install -e .`, `.venv\Scripts\reliq`, and `.venv\Scripts\python -m unittest discover -v`. See `.github/workflows/ci.yml` for the Windows/Linux CI matrix. Release binaries are built and smoke-tested by `.github/workflows/release.yml` when a `v*` tag is pushed; this repository does not claim an artifact exists until that workflow succeeds.

## License

Reliq is available under the MIT License; see [LICENSE](LICENSE).
