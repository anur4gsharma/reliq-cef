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
        self.toolbar = Toolbar(self.root, runtime_options)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.panes = tk.PanedWindow(
            self.root, orient="vertical", bg=theme.BORDER,
            sashwidth=5, sashrelief="flat", bd=0, opaqueresize=True,
        )
        self.panes.grid(row=1, column=0, sticky="nsew")
        self.editor = CodeEditor(self.panes)
        self.output = OutputPanel(self.panes)
        self.panes.add(self.editor, minsize=180, stretch="always")
        self.panes.add(self.output, minsize=120, stretch="always")
        self.panes.paneconfigure(self.editor, height=470)
        self.panes.paneconfigure(self.output, height=180)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

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

    def set_running(self, running):
        self.toolbar.run_button.configure(
            relief=tk.SUNKEN if running else tk.RAISED,
        )


def current_runtime_option(version):
    """Build placeholder display data without probing for installed runtimes."""
    return RuntimeOption(language="Python", runtime=f"Python {version}", environment="Current")
