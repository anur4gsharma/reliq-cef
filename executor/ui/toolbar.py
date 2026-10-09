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
        super().__init__(master, bg=theme.SURFACE, height=52)
        self.grid_propagate(False)
        self.options = tuple(runtime_options)
        self.language_value = tk.StringVar()
        self.runtime_value = tk.StringVar(value=self._display(self.options[0]) if self.options else "")
        self.language_selector = ttk.Combobox(
            self, textvariable=self.language_value, values=[], state="readonly", width=14,
            font=(theme.FONT, 10),
        )
        self.language_selector.pack(side="left", padx=(14, 4), pady=10)
        self.selector = ttk.Combobox(
            self, textvariable=self.runtime_value, values=[self._display(item) for item in self.options],
            state="readonly", width=24, font=(theme.FONT, 10),
        )
        self.selector.pack(side="left", padx=(4, 8), pady=10)
        self.language_selector.bind("<<ComboboxSelected>>", self._language_changed)
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
    def selected_option(self):
        index = self.selector.current()
        values = self._language_options()
        return values[index] if 0 <= index < len(values) else None

    def set_options(self, runtime_options, selected_language=None):
        previous = self.selected_option()
        previous_language = self.language_value.get()
        self.options = tuple(runtime_options)
        languages = list(dict.fromkeys(getattr(item, "language", "") for item in self.options))
        display = {"python": "Python", "javascript": "JavaScript", "bash": "Bash", "powershell": "PowerShell", "cpp": "C++"}
        self._languages = {display.get(language.lower(), language): language for language in languages}
        labels = list(self._languages)
        self.language_selector.configure(values=labels)
        self.selector.set("")
        if selected_language:
            self.select_language(selected_language)
        elif previous:
            match = next((item for item in self.options
                          if getattr(item, "executable", None) == getattr(previous, "executable", None)
                          and getattr(item, "language", None) == getattr(previous, "language", None)), None)
            if match:
                display_name = next((name for name, value in self._languages.items() if value == match.language), None)
                if display_name:
                    self.language_value.set(display_name)
                    self._language_changed()
                    subset = self._language_options()
                    self.selector.current(subset.index(match))
            else:
                self.language_value.set(previous_language)
                self.selector.set("")
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
        options = self._language_options()
        self.selector.configure(values=[self._display(item) for item in options])
        if options:
            self.selector.current(0)
        else:
            self.selector.set("")
        if len(options) > 1:
            self.selector.pack(side="left", padx=(4, 8), pady=10)
        else:
            self.selector.pack_forget()

    @staticmethod
    def _display(item):
        return getattr(item, "label", None) or str(item)
