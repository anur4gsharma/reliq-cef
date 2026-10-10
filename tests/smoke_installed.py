"""Smoke-test the installed command and installed Tk application."""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from shutil import which
from unittest.mock import patch

import reliq
import reliq.app as app
from executor.ui.window import ReliqWindow


def stop_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
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


def main() -> None:
    print(f"Installed Reliq module: {reliq.__file__}")
    command = which("reliq")
    if not command:
        raise RuntimeError("the installed reliq console command is not on PATH")
    subprocess.run([command, "--help"], check=True, timeout=10,
                   stdout=subprocess.DEVNULL)

    with tempfile.TemporaryDirectory(prefix="reliq-launch-cwd-") as other_directory:
        subprocess.run([command, "--help"], cwd=other_directory, check=True,
                       timeout=10, stdout=subprocess.DEVNULL)
        process = subprocess.Popen(
            [command], cwd=other_directory,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=(os.name != "nt"),
        )
        try:
            time.sleep(1.5)
            if process.poll() is not None:
                raise RuntimeError(f"installed reliq exited during GUI startup: {process.returncode}")
        finally:
            stop_tree(process)

    view = ReliqWindow([])
    calls = []
    callbacks = [lambda name=name: calls.append(name)
                 for name in ("new", "open", "save", "save_as", "run", "stop")]
    try:
        view.root.withdraw()
        view.set_commands(
            new_file=callbacks[0], open_file=callbacks[1], save=callbacks[2],
            save_as=callbacks[3], run=callbacks[4], stop=callbacks[5],
        )
        for index in range(4):
            view.file_menu.invoke(index)
        for index in range(2):
            view.run_menu.invoke(index)
        view.editor.text.insert("1.0", "print('smoke')")
        if view.editor.text.get("1.0", "end-1c") != "print('smoke')":
            raise RuntimeError("editor did not retain inserted text")
        view.set_running(True, True)
        if view.toolbar.run_button["state"] != "disabled" or view.toolbar.stop_button["state"] != "normal":
            raise RuntimeError("Run/Stop state did not update")
        if calls != ["new", "open", "save", "save_as", "run", "stop"]:
            raise RuntimeError(f"menu callbacks routed incorrectly: {calls}")
    finally:
        view.root.destroy()

    original_window = app.ReliqWindow

    class AutoCloseWindow(original_window):
        def __init__(self, options):
            super().__init__(options)
            self.root.after(250, self.root.destroy)

    with patch.object(app, "ReliqWindow", AutoCloseWindow):
        if app.launch() != 0:
            raise RuntimeError("installed application launch returned a failure status")
    print("Installed command and Tk interaction smoke checks passed")


if __name__ == "__main__":
    main()
