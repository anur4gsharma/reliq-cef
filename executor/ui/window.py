import tkinter as tk
from tkinter import ttk

from . import theme
from .editor import CodeEditor
from .output import OutputPanel
from .toolbar import RuntimeOption, Toolbar


class ReliqWindow:
    def __init__(self, runtime_options):
        self.root = tk.Tk()
        self.root.title("Reliq")
        self.root.geometry("1000x700")
        self.root.minsize(700, 440)
        self.root.configure(bg=theme.BG)
        self._configure_styles()

        self._build_menu()
        self.titlebar = tk.Frame(self.root, bg=theme.BG, height=42)
        self.titlebar.grid(row=0, column=0, sticky="ew")
        self.titlebar.grid_propagate(False)
        tk.Label(
            self.titlebar, text="R", bg=theme.ACCENT_DARK, fg=theme.ACCENT,
            font=(theme.FONT, 10, "bold"), width=2, height=1,
        ).pack(side="left", padx=(14, 9), pady=8)
        tk.Label(
            self.titlebar, text="Reliq", bg=theme.BG, fg=theme.TEXT,
            font=(theme.FONT, 11, "bold"),
        ).pack(side="left", pady=8)
        self.toolbar = Toolbar(self.root, runtime_options)
        self.toolbar.grid(row=1, column=0, sticky="ew")

        self.panes = tk.PanedWindow(
            self.root, orient="vertical", bg=theme.BORDER,
            sashwidth=5, sashrelief="flat", bd=0, opaqueresize=True,
        )
        self.panes.grid(row=2, column=0, sticky="nsew")
        self.editor = CodeEditor(self.panes)
        self.output = OutputPanel(self.panes)
        self.panes.add(self.editor, minsize=180, stretch="always")
        self.panes.add(self.output, minsize=120, stretch="always")
        self.panes.paneconfigure(self.editor, height=470)
        self.panes.paneconfigure(self.output, height=180)

        self.output_meta = tk.Frame(self.root, bg=theme.SURFACE, height=30)
        self.output_meta.grid(row=3, column=0, sticky="ew")
        self.output_meta.grid_propagate(False)
        self.exit_label = tk.Label(
            self.output_meta, text="Exit code: —", bg=theme.SURFACE,
            fg=theme.MUTED, font=(theme.MONO, 9),
        )
        self.exit_label.pack(side="left", padx=14)
        self.time_label = tk.Label(
            self.output_meta, text="Runtime: —", bg=theme.SURFACE,
            fg=theme.MUTED, font=(theme.MONO, 9),
        )
        self.time_label.pack(side="left", padx=14)

        self.statusbar = tk.Frame(self.root, bg=theme.BG, height=28)
        self.statusbar.grid(row=4, column=0, sticky="ew")
        self.statusbar.grid_propagate(False)
        self.cursor_label = tk.Label(
            self.statusbar, text="Ln 1, Col 1", bg=theme.BG,
            fg=theme.MUTED, font=(theme.MONO, 9),
        )
        self.cursor_label.pack(side="left", padx=14)
        self.language_label = tk.Label(
            self.statusbar, text="Python  ·  UTF-8", bg=theme.BG,
            fg=theme.MUTED, font=(theme.FONT, 9),
        )
        self.language_label.pack(side="right", padx=14)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.editor.text.bind("<KeyRelease>", self._update_cursor, add="+")
        self.editor.text.bind("<ButtonRelease-1>", self._update_cursor, add="+")
        self.editor.text.bind("<FocusIn>", self._update_cursor, add="+")
        self.toolbar.selector.bind("<<ComboboxSelected>>", self._update_runtime_label)
        self._update_cursor()
        self._update_runtime_label()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "TCombobox", fieldbackground=theme.SURFACE_RAISED,
            background=theme.SURFACE_RAISED, foreground=theme.TEXT,
            arrowcolor=theme.MUTED, bordercolor=theme.BORDER,
            lightcolor=theme.BORDER, darkcolor=theme.BORDER,
            padding=(8, 5),
        )
        style.map(
            "TCombobox", fieldbackground=[("readonly", theme.SURFACE_RAISED)],
            foreground=[("readonly", theme.TEXT)],
        )

    def _build_menu(self):
        menu = tk.Menu(
            self.root, bg=theme.SURFACE, fg=theme.TEXT,
            activebackground=theme.ACCENT_DARK, activeforeground=theme.TEXT,
            tearoff=False, borderwidth=0,
        )
        file_menu = tk.Menu(menu, tearoff=False, bg=theme.SURFACE, fg=theme.TEXT)
        file_menu.add_command(label="Quit", command=self.root.destroy, accelerator="Alt+F4")
        menu.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(menu, tearoff=False, bg=theme.SURFACE, fg=theme.TEXT)
        edit_menu.add_command(
            label="Undo", command=lambda: self.editor.text.event_generate("<<Undo>>"),
            accelerator="Ctrl+Z",
        )
        edit_menu.add_command(
            label="Redo", command=lambda: self.editor.text.event_generate("<<Redo>>"),
            accelerator="Ctrl+Y",
        )
        menu.add_cascade(label="Edit", menu=edit_menu)
        self.root.configure(menu=menu)

    def _update_cursor(self, _event=None):
        line, column = self.editor.line_column()
        self.cursor_label.configure(text=f"Ln {line}, Col {column}")

    def _update_runtime_label(self, _event=None):
        option = self.toolbar.selected_option()
        if option:
            self.language_label.configure(text=f"{option.language}  ·  UTF-8")

    def set_state(self, state, exit_code=None, elapsed=None):
        colors = {
            "Ready": theme.GREEN,
            "Running": theme.ACCENT,
            "Stopped": theme.AMBER,
            "Error": theme.RED,
            "Timeout": theme.RED,
        }
        self.toolbar.state_label.configure(
            text=f"● {state}", fg=colors.get(state, theme.MUTED),
        )
        if state == "Running":
            self.exit_label.configure(text="Exit code: —")
            self.time_label.configure(text="Runtime: —")
        if exit_code is not None:
            self.exit_label.configure(text=f"Exit code: {exit_code}")
        if elapsed is not None:
            self.time_label.configure(text=f"Runtime: {elapsed:.2f}s")


def current_runtime_option(version):
    """Build placeholder display data without probing for installed runtimes."""
    return RuntimeOption(language="Python", runtime=f"Python {version}", environment="Current")
