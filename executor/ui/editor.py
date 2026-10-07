import keyword
import re
import tkinter as tk

from . import theme


class CodeEditor(tk.Frame):
    """Compact text editor with a synchronized line number gutter."""

    def __init__(self, master):
        super().__init__(master, bg=theme.EDITOR_BG)
        self.gutter = tk.Canvas(
            self, width=48, bg=theme.EDITOR_BG, highlightthickness=0,
            borderwidth=0,
        )
        self.text = tk.Text(
            self, bg=theme.EDITOR_BG, fg=theme.TEXT, insertbackground=theme.ACCENT,
            selectbackground="#304461", selectforeground=theme.TEXT,
            font=(theme.MONO, 11), padx=12, pady=14, wrap="none",
            undo=True, maxundo=-1, relief="flat", borderwidth=0,
            highlightthickness=0, tabs=("4c",),
        )
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self._scroll_text,
            troughcolor=theme.EDITOR_BG, bg=theme.SURFACE_RAISED,
            activebackground=theme.MUTED, relief="flat", borderwidth=0,
        )
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.scrollbar.grid(row=0, column=2, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.text.configure(yscrollcommand=self._sync_scrollbar)
        self.text.bind("<KeyRelease>", self._on_edit)
        self.text.bind("<ButtonRelease-1>", self._on_edit)
        self.text.bind("<MouseWheel>", self._on_scroll)
        self.text.bind("<Button-4>", self._on_scroll)
        self.text.bind("<Button-5>", self._on_scroll)
        self.text.bind("<Configure>", self._on_scroll)
        self.text.bind("<<Change>>", self._on_scroll)
        self.text.tag_configure("keyword", foreground="#c5a0ff")
        self.text.tag_configure("string", foreground="#a6d69a")
        self.text.tag_configure("comment", foreground="#707b8c")
        self.text.tag_configure("number", foreground="#e5b879")
        self.text.tag_configure("current_line", background="#191e27")
        self._draw_gutter()
        self._highlight()

    def _scroll_text(self, *args):
        self.text.yview(*args)
        self._draw_gutter()

    def _sync_scrollbar(self, first, last):
        self.scrollbar.set(first, last)
        self._draw_gutter()

    def _on_scroll(self, _event=None):
        self.after_idle(self._draw_gutter)

    def _on_edit(self, _event=None):
        self._draw_gutter()
        self._highlight()

    def _draw_gutter(self):
        self.gutter.delete("all")
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            y = info[1] + info[3] / 2
            number = index.split(".")[0]
            color = theme.ACCENT if number == self.text.index("insert").split(".")[0] else theme.MUTED
            self.gutter.create_text(
                39, y, anchor="e", text=number, fill=color,
                font=(theme.MONO, 10),
            )
            index = self.text.index(f"{index}+1line")

    def _highlight(self):
        for tag in ("keyword", "string", "comment", "number", "current_line"):
            self.text.tag_remove(tag, "1.0", "end")
        source = self.text.get("1.0", "end-1c")
        for word in keyword.kwlist:
            for match in re.finditer(rf"\b{re.escape(word)}\b", source):
                self._tag_offsets("keyword", match.start(), match.end())
        patterns = (
            ("string", r"(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"),
            ("comment", r"#.*"),
            ("number", r"\b\d+(?:\.\d+)?\b"),
        )
        for tag, pattern in patterns:
            for match in re.finditer(pattern, source):
                self._tag_offsets(tag, match.start(), match.end())
        line = self.text.index("insert").split(".")[0]
        self.text.tag_add("current_line", f"{line}.0", f"{line}.end+1c")
        self.text.tag_lower("current_line")
        self._draw_gutter()

    def _tag_offsets(self, tag, start, end):
        self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

    def line_column(self):
        line, column = self.text.index("insert").split(".")
        return int(line), int(column) + 1
