"""Verify a frozen GUI executable stays alive after successful startup."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def main(executable: str) -> None:
    process = subprocess.Popen(
        [executable], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=(os.name != "nt"),
    )
    try:
        time.sleep(3)
        if process.poll() is not None:
            raise RuntimeError(f"frozen GUI exited during startup with status {process.returncode}")
    finally:
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=5, check=False)
            else:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
    print("Frozen GUI smoke check passed")


if __name__ == "__main__":
    main(sys.argv[1])
