"""Tk application controller. All Tk calls stay on the main thread."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from .engine import Runner, sweep_stale
from .runtime import discover, language_for_extension, validate
from executor.ui.window import ReliqWindow


def launch(target: str | None = None, selected_language: str | None = None) -> int:
    sweep_stale()
    view = ReliqWindow([])
    root, editor = view.root, view.editor
    events: queue.Queue = queue.Queue()
    runner = Runner()
    state = {"busy": False, "path": None, "dirty": False, "runtimes": [], "last_runtime": None,
             "initial_selection_applied": False, "pending_language": None, "discovery_revision": 0}
    view.toolbar.on_language_change = editor.set_language
    def discover_async(project):
        state["discovery_revision"] += 1
        revision = state["discovery_revision"]
        def worker(): events.put(("runtimes", revision, discover(project)))
        threading.Thread(target=worker, daemon=True).start()
    def show_error(title, exc): messagebox.showerror(title, str(exc), parent=root)
    def confirm_discard():
        if not state["dirty"]: return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save changes before continuing?", parent=root)
        if answer is None: return False
        return save() if answer else True
    def load(path, startup=False):
        if not startup and not confirm_discard(): return
        try: content = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc: show_error("Open failed", exc); return
        editor.text.delete("1.0", "end"); editor.text.insert("1.0", content)
        editor.text.edit_modified(False)
        editor.refresh()
        state.update(path=str(Path(path).resolve()), dirty=False)
        state["pending_language"] = language_for_extension(str(path))
        if state["pending_language"]:
            editor.set_language(state["pending_language"])
            view.toolbar.select_language(state["pending_language"])
        root.title(f"Reliq — {Path(path).name}")
        discover_async(str(Path(path).parent))
    def save(save_as=False):
        path = state["path"]
        if save_as or not path: path = filedialog.asksaveasfilename(parent=root, defaultextension=".py", filetypes=[("Source files", "*.py *.js *.mjs *.sh *.ps1 *.cpp *.cc *.cxx"), ("All files", "*")])
        if not path: return False
        try: Path(path).write_text(editor.text.get("1.0", "end-1c"), encoding="utf-8", newline="")
        except OSError as exc: show_error("Save failed", exc); return False
        state.update(path=str(Path(path).resolve()), dirty=False); root.title(f"Reliq — {Path(path).name}"); return True
    def new_file():
        if not confirm_discard(): return
        editor.text.delete("1.0", "end"); editor.text.edit_modified(False)
        editor.refresh()
        state.update(path=None, dirty=False, pending_language=None); root.title("Reliq")
    def run_code(_event=None):
        if state["busy"]: return "break"
        runtime = view.toolbar.selected_option()
        if runtime is None: messagebox.showerror("No runtime", "No supported language runtime was found.", parent=root); return "break"
        # Revalidate the pinned executable before each launch; never swap silently.
        source = editor.text.get("1.0", "end-1c")
        state["last_runtime"] = runtime
        view.output.clear(); state["busy"] = True; view.set_running(True, True)
        runner.prepare()
        cwd = str(Path(state["path"]).parent) if state["path"] else None
        def worker():
            try:
                if not validate(runtime):
                    events.put(("runtime_missing", runtime.identity, cwd))
                    events.put(("done", None, "Selected runtime is no longer available. Choose another runtime.")); return
                result = runner.execute(runtime, source, cwd, lambda stream, value: events.put(("output", stream, value)))
                events.put(("done", result, ""))
            except Exception as exc: events.put(("done", None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        return "break"
    def stop(): runner.cancel()
    def delete_previous_word(event):
        widget = event.widget
        cursor = widget.index(tk.INSERT)
        line_start = widget.index(f"{cursor} linestart")
        before = widget.get(line_start, cursor)
        index = len(before) - 1
        if index < 0: return "break"
        whitespace = before[index].isspace()
        while index >= 0 and before[index].isspace() == whitespace: index -= 1
        widget.delete(f"{cursor} - {len(before) - index - 1} chars", cursor)
        return "break"
    def on_modified(_event=None):
        if not editor.text.edit_modified(): return
        editor.text.edit_modified(False)
        state["dirty"] = True
        update_cursor_status()
    def update_cursor_status():
        line, column = editor.line_column()
        if not state["busy"]: view.set_status(f"Ln {line}, Col {column}")
    view.toolbar.run_button.configure(command=run_code)
    view.toolbar.stop_button.configure(command=stop, state="disabled")
    def refresh_runtimes():
        project = str(Path(state["path"]).parent) if state["path"] else None
        view.set_status("Refreshing runtimes…")
        discover_async(project)
    view.toolbar.refresh_button.configure(command=refresh_runtimes)
    editor.text.bind("<<Modified>>", on_modified, add="+")
    editor.text.bind("<KeyRelease>", lambda _event: update_cursor_status(), add="+")
    editor.text.bind("<Control-BackSpace>", delete_previous_word)
    editor.text.bind("<Control-Return>", run_code)
    root.bind("<Control-period>", lambda _event: (stop(), "break")[1])
    root.bind("<Control-s>", lambda _e: save())
    def open_dialog():
        path = filedialog.askopenfilename(parent=root)
        if path: load(path)
    root.bind("<Control-o>", lambda _e: open_dialog())
    root.bind("<Control-n>", lambda _e: new_file())
    def close_window():
        if confirm_discard(): runner.cancel(); root.destroy()
    root.protocol("WM_DELETE_WINDOW", close_window)
    view.set_commands(
        new_file=new_file,
        open_file=open_dialog,
        save=lambda: save(),
        save_as=lambda: save(True),
        run=run_code,
        stop=stop,
    )
    if target: load(target, startup=True)
    if selected_language: view.toolbar.select_language(selected_language)
    # runtime discovery starts only after the window has been mapped
    def initial_probe():
        project = str(Path(state["path"]).parent) if state["path"] else None
        discover_async(project)
    def poll():
        try:
            while True:
                event = events.get_nowait()
                if event[0] == "runtimes":
                    _, revision, candidates = event
                    if revision != state["discovery_revision"]:
                        continue
                    state["runtimes"] = candidates
                    requested = state["pending_language"] or (selected_language if not state["initial_selection_applied"] else None)
                    lost = view.set_runtimes(candidates, requested)
                    state["pending_language"] = None
                    state["initial_selection_applied"] = True
                    if lost: view.set_status("Selected runtime is unavailable; choose another runtime.")
                elif event[0] == "runtime_missing":
                    _, identity, project = event
                    selected = view.toolbar.selected_option()
                    current_project = str(Path(state["path"]).parent) if state["path"] else None
                    if selected and selected.identity == identity and current_project == project:
                        discover_async(project)
                elif event[0] == "output": view.output.insert(tk.END, event[2], "stderr" if event[1] == "stderr" else None)
                else:
                    _, result, error = event; state["busy"] = False; view.set_running(False, False)
                    if error: show_error("Execution failed", error)
                    if result:
                        runtime = state["last_runtime"]
                        label = getattr(runtime, "label", "")
                        view.set_status(f"{result.status} · {label} · exit {result.exit_code} · {result.duration:.2f}s")
                        if result.error: show_error("Execution cleanup", result.error)
        except queue.Empty: pass
        if root.winfo_exists(): root.after(40, poll)
    if not target: root.after(0, initial_probe)
    root.after(40, poll)
    root.mainloop()
    return 0
