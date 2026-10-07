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
        self.runtime_value = tk.StringVar(value=str(self.options[0]) if self.options else "")
        self.selector = ttk.Combobox(
            self, textvariable=self.runtime_value, values=[str(item) for item in self.options],
            state="readonly", width=24, font=(theme.FONT, 10),
        )
        self.selector.pack(side="left", padx=(14, 8), pady=10)
        self.run_button = tk.Button(
            self, text="Run", bg=theme.ACCENT_DARK, fg="#dce9ff",
            activebackground="#314d75", activeforeground="white", relief="flat",
            borderwidth=0, font=(theme.FONT, 10, "bold"), padx=16,
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
        self.state_label = tk.Label(
            self, text="● Ready", bg=theme.SURFACE, fg=theme.GREEN,
            font=(theme.FONT, 9, "bold"),
        )
        self.state_label.pack(side="right", padx=16)

    def selected_option(self):
        index = self.selector.current()
        return self.options[index] if 0 <= index < len(self.options) else None
