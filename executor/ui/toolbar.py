from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from . import theme


@dataclass(frozen=True)
class RuntimeOption:
    """Display data for one selectable language/runtime candidate."""

    language: str
    runtime: str
    environment: str = ""
    path: str = ""

    def __str__(self):
        return f"{self.language}  ·  {self.runtime}"


class Toolbar(tk.Frame):
    def __init__(self, master, runtime_options):
        super().__init__(master, bg=theme.SURFACE, height=74)
        self.grid_propagate(False)
        self.options = tuple(runtime_options)
        self._pinned_runtime = None
        self._languages = {"Python": "python", "JavaScript": "javascript", "Bash": "bash",
                           "PowerShell": "powershell", "C++": "cpp"}
        self.language_value = tk.StringVar()
        self.runtime_value = tk.StringVar(value=self._display(self.options[0]) if self.options else "")
        self.language_selector = ttk.Combobox(
            self, textvariable=self.language_value, values=[], state="readonly", width=14,
            font=(theme.FONT, 10),
        )
        self.language_selector.pack(side="left", padx=(14, 4), pady=10)
        self.selector = ttk.Combobox(
            self, textvariable=self.runtime_value, values=[self._display(item) for item in self.options],
            state="readonly", width=28, font=(theme.FONT, 10),
        )
        self.selector.pack(side="left", padx=(4, 8), pady=10)
        self.language_selector.bind("<<ComboboxSelected>>", self._language_changed)
        self.selector.bind("<<ComboboxSelected>>", self._selection_changed)
        self.on_language_change = None
        self.run_button = tk.Button(
            self, text="Run", font=(theme.FONT, 10), padx=16,
            cursor="hand2", takefocus=True,
        )
        self.run_button.pack(side="left", padx=(2, 6), pady=8, ipady=4)
        tk.Label(
            self, text="Ctrl+Enter", bg=theme.SURFACE, fg=theme.MUTED,
            font=(theme.FONT, 9),
        ).pack(side="left", padx=(0, 12))
        self.stop_button = tk.Button(
            self, text="Stop", bg=theme.SURFACE_RAISED, fg=theme.TEXT,
            activebackground="#39313a", activeforeground=theme.RED,
            relief="flat", borderwidth=0, font=(theme.FONT, 10), padx=14,
            cursor="hand2", takefocus=True,
        )
        self.stop_button.pack(side="left", pady=8, ipady=4)
        self.refresh_button = tk.Button(
            self, text="Refresh", bg=theme.SURFACE_RAISED, fg=theme.TEXT,
            activebackground=theme.BORDER, relief="flat", borderwidth=0,
            font=(theme.FONT, 9), padx=9, cursor="hand2", takefocus=True,
        )
        self.refresh_button.pack(side="right", padx=12, pady=8, ipady=3)
        self.details = tk.StringVar(value="No runtimes found")
        self.details_label = tk.Label(self, textvariable=self.details, anchor="w",
                                      bg=theme.SURFACE, fg=theme.MUTED, font=(theme.FONT, 8))
        self.details_label.pack(side="bottom", fill="x", padx=16, pady=(0, 4))
        self._selection_changed()
    def selected_option(self):
        index = self.selector.current()
        values = self._language_options()
        selected = values[index] if 0 <= index < len(values) else None
        if selected is not None:
            self._pinned_runtime = selected
        return selected

    def _selection_changed(self, _event=None):
        item = self.selected_option()
        if item is None:
            self.details.set("No usable runtime for this language; refresh or choose another language")
            self.selector.configure(state="disabled")
            return
        self.selector.configure(state="readonly")
        source = getattr(item, "source", "")
        path = getattr(item, "executable", "")
        self.details.set(f"{source} · {path}")
        self.selector.configure(state="readonly")

    def set_options(self, runtime_options, selected_language=None):
        previous = self.selected_option() or self._pinned_runtime
        previous_language = self.language_value.get()
        self.options = tuple(runtime_options)
        display = {"python": "Python", "javascript": "JavaScript", "bash": "Bash", "powershell": "PowerShell", "cpp": "C++"}
        self._languages = {name: language for language, name in display.items()}
        labels = list(self._languages)
        self.language_selector.configure(values=labels)
        if not self.language_value.get():
            self.language_value.set("Python")
        self.selector.set("")
        if selected_language:
            self.select_language(selected_language)
        elif previous:
            match = next((item for item in self.options
                          if getattr(item, "identity", None) == getattr(previous, "identity", None)
                          or (getattr(item, "executable", None) == getattr(previous, "executable", None)
                              and getattr(item, "language", None) == getattr(previous, "language", None))), None)
            if match:
                display_name = next((name for name, value in self._languages.items() if value == match.language), None)
                if display_name:
                    self.language_value.set(display_name)
                    self._language_changed()
                    subset = self._language_options()
                    self.selector.current(subset.index(match))
                    self._selection_changed()
            else:
                self.language_value.set(previous_language)
                alternatives = self._language_options()
                self.selector.configure(values=[self._display(item) for item in alternatives])
                self.selector.set("")
                self.selector.configure(state="readonly" if alternatives else "disabled")
                self._selection_changed()
        elif self.language_value.get():
            self._language_changed()
        elif labels:
            self.language_selector.current(0)
            self._language_changed()
        return bool(previous and self.selected_option() is None)

    def select_language(self, language):
        names = {"py": "python", "js": "javascript", "sh": "bash", "ps": "powershell", "c++": "cpp"}
        wanted = names.get(language.lower(), language.lower())
        display = next((name for name, value in getattr(self, "_languages", {}).items() if value.lower() == wanted), None)
        if display:
            self.language_value.set(display)
            self._language_changed()
            return True
        for item in self.options:
            if getattr(item, "alias", "") == language:
                return self.select_language(item.language)
        return False

    def _language_options(self):
        language = getattr(self, "_languages", {}).get(self.language_value.get())
        return [item for item in self.options if getattr(item, "language", "") == language]

    def _language_changed(self, _event=None):
        pinned_language = getattr(self._pinned_runtime, "language", None)
        new_language = self._languages.get(self.language_value.get())
        if _event is not None and pinned_language and new_language != pinned_language:
            self._pinned_runtime = None
        options = self._language_options()
        self.selector.configure(values=[self._display(item) for item in options])
        if options:
            self.selector.current(0)
        else:
            self.selector.set("")
        self.selector.configure(state="readonly" if options else "disabled")
        self._selection_changed()
        if self.on_language_change:
            self.on_language_change(self._languages.get(self.language_value.get()))

    @staticmethod
    def _display(item):
        return getattr(item, "label", None) or str(item)
