"""Smoke-test the installed console command without requiring a display."""
from __future__ import annotations

import subprocess
from shutil import which


def main() -> None:
    command = which("reliq")
    if not command:
        raise RuntimeError("the installed reliq console command is not on PATH")
    subprocess.run([command, "--help"], check=True, timeout=10)
    result = subprocess.run([command, "-"], input="print('archive-ok')\n",
                            text=True, capture_output=True, timeout=15)
    if result.returncode or "archive-ok" not in result.stdout:
        raise RuntimeError(f"stdin CLI smoke failed: {result.returncode}: {result.stderr}")
    print("Installed CLI and stdin execution smoke checks passed")


if __name__ == "__main__":
    main()
