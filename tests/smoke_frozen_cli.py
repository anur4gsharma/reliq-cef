"""Smoke-test a frozen console executable and its stdin execution mode."""
from __future__ import annotations

import subprocess
import sys


def main(executable: str) -> None:
    subprocess.run([executable, "--help"], check=True, timeout=10,
                   stdout=subprocess.DEVNULL)
    result = subprocess.run([executable, "-"], input="print('frozen-cli-ok')\n",
                            text=True, capture_output=True, timeout=15)
    if result.returncode or "frozen-cli-ok" not in result.stdout:
        raise RuntimeError(f"frozen CLI stdin failed: {result.returncode}: {result.stderr}")
    print("Frozen CLI help and stdin smoke checks passed")


if __name__ == "__main__":
    main(sys.argv[1])
