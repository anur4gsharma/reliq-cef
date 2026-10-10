"""Tk text editor with conservative editing helpers and a synchronized gutter."""
from __future__ import annotations

import tkinter as tk

from . import theme
from .editor_logic import INDENT, PAIRS, QUOTES, indentation_for_enter, lexical_spans


class CodeEditor(tk.Frame):
    """Compact editor; lexical highlighting is intentionally not a parser."""

    def __init__(self, master):
        super().__init__(master, bg=theme.EDITOR_BG)
        self.gutter = tk.Canvas(self, width=48, bg=theme.EDITOR_BG, highlightthickness=0, borderwidth=0)
        self.text = tk.Text(self, bg=theme.EDITOR_BG, fg=theme.TEXT, insertbackground=theme.ACCENT,
                            selectbackground="#304461", selectforeground=theme.TEXT,
                            font=(theme.MONO, 11), padx=12, pady=14, wrap="none",
                            undo=True, autoseparators=True, maxundo=-1, relief="flat", borderwidth=0,
                            highlightthickness=0, tabs=("4c",))
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self._scroll_text,
                                      troughcolor=theme.EDITOR_BG, bg=theme.SURFACE_RAISED,
                                      activebackground=theme.MUTED, relief="flat", borderwidth=0)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.scrollbar.grid(row=0, column=2, sticky="ns")
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1)
        self.text.configure(yscrollcommand=self._sync_scrollbar)
        self.text.bind("<KeyPress>", self._key_press, add="+")
        self.text.bind("<KeyRelease>", self._on_edit, add="+")
        self.text.bind("<ButtonRelease-1>", self._on_edit, add="+")
        self.text.bind("<MouseWheel>", self._on_scroll, add="+")
        self.text.bind("<Button-4>", self._on_scroll, add="+")
        self.text.bind("<Button-5>", self._on_scroll, add="+")
        self.text.bind("<Configure>", self._on_scroll, add="+")
        self.text.bind("<<Change>>", self._on_scroll, add="+")
        self.language = "python"
        self._highlight_job = None
        for tag, color in (("keyword", "#c5a0ff"), ("string", "#a6d69a"),
                           ("comment", "#707b8c"), ("number", "#e5b879")):
            self.text.tag_configure(tag, foreground=color)
        self.text.tag_configure("current_line", background="#191e27")
        self._draw_gutter(); self._schedule_highlight()

    def set_language(self, language: str | None):
        self.language = (language or "python").lower()
        self.refresh()

    def refresh(self):
        self._draw_gutter()
        self._schedule_highlight()

    def _key_press(self, event):
        key = event.keysym
        if key == "Return":
            if event.state & 0x0004:  # Ctrl+Enter belongs to the app's run binding.
                return None
            self._newline(); return "break"
        if key == "Tab":
            if event.state & 0x0001: self._dedent_lines()
            else: self._indent_lines()
            return "break"
        if key == "BackSpace" and event.state & 0x0004:
            return None  # Preserve the app's Ctrl+Backspace word deletion.
        if key == "BackSpace" and self._backspace_special():
            return "break"
        char = event.char
        if char in PAIRS or char in QUOTES:
            if self._insert_pair(char): return "break"
        if char in ")]}\'\"`" and self._skip_closer(char): return "break"
        return None

    def _has_selection(self):
        return bool(self.text.tag_ranges("sel"))

    def _insert_pair(self, opener):
        cursor = self.text.index("insert")
        if opener in QUOTES:
            before = self.text.get(f"{cursor} - 1c", cursor) if cursor != "1.0" else ""
            # Avoid quote pairs in obvious escaped and word-internal contexts.
            prefix = self.text.get(f"{cursor} linestart", cursor)
            active_quote = None
            escaped = False
            for char in prefix:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif active_quote == char:
                    active_quote = None
                elif active_quote is None and char in QUOTES:
                    active_quote = char
            if before == "\\" or before.isalnum() or before == "_" or active_quote:
                return False
        closer = PAIRS.get(opener, QUOTES.get(opener))
        self.text.edit_separator()
        if self._has_selection():
            selected = self.text.get("sel.first", "sel.last")
            start = self.text.index("sel.first")
            self.text.delete("sel.first", "sel.last")
            self.text.insert(start, opener + selected + closer)
            self.text.mark_set("insert", f"{start}+{len(selected) + 1}c")
        else:
            start = cursor
            self.text.insert("insert", opener + closer)
            self.text.mark_set("insert", f"{start}+1c")
        # Tags move with text edits and let Backspace distinguish our pairs from
        # ordinary adjacent source characters.
        self.text.tag_add("auto_pair_open", start, f"{start}+1c")
        close = f"{start}+{len(selected) + 1}c" if 'selected' in locals() else f"{start}+1c"
        self.text.tag_add("auto_pair_close", close, f"{close}+1c")
        self.text.edit_separator()
        return True

    def _skip_closer(self, closer):
        cursor = self.text.index("insert")
        if cursor == "end-1c": return False
        if self.text.get(cursor, f"{cursor}+1c") != closer: return False
        self.text.mark_set("insert", f"{cursor}+1c")
        return True

    def _backspace_special(self):
        cursor = self.text.index("insert")
        if self._has_selection(): return False
        if cursor != "1.0":
            previous = self.text.index(f"{cursor} - 1c")
            if self.text.tag_ranges("auto_pair_open") and self.text.tag_nextrange("auto_pair_open", previous, cursor):
                if self.text.get(previous, cursor) in set(PAIRS) | set(QUOTES):
                    if self.text.tag_nextrange("auto_pair_close", cursor, f"{cursor}+1c"):
                        self.text.edit_separator(); self.text.delete(previous, f"{cursor}+1c"); self.text.edit_separator()
                        return True
            line_start = self.text.index(f"{cursor} linestart")
            prefix = self.text.get(line_start, cursor)
            if prefix and not prefix.strip() and prefix.endswith(" "):
                count = (len(prefix) % len(INDENT)) or len(INDENT)
                self.text.edit_separator(); self.text.delete(f"{cursor} - {count}c", cursor); self.text.edit_separator()
                return True
        return False

    def _newline(self):
        text = self.text
        if self._has_selection():
            start = text.index("sel.first")
            text.delete("sel.first", "sel.last")
            text.mark_set("insert", start)
        cursor = text.index("insert")
        line_start = text.index(f"{cursor} linestart")
        line_end = text.index(f"{cursor} lineend")
        left = text.get(line_start, cursor)
        right = text.get(cursor, line_end)
        # Expand between matching delimiters only when the characters are adjacent.
        if left and right and left[-1] in PAIRS and PAIRS[left[-1]] == right[0]:
            outer = indentation_for_enter(left[:len(left)-1], self.language)
            text.edit_separator(); text.insert(cursor, "\n" + outer + INDENT + "\n" + outer)
            text.mark_set("insert", f"{cursor}+{len(outer) + len(INDENT) + 1}c"); text.edit_separator()
            return
        indent = indentation_for_enter(left, self.language)
        text.edit_separator(); text.insert(cursor, "\n" + indent); text.edit_separator()

    def _selected_line_range(self):
        if self._has_selection():
            start = self.text.index("sel.first linestart")
            end = self.text.index("sel.last linestart")
            if self.text.compare("sel.last", "!=", end) or end == start:
                end = self.text.index(f"{end}+1line")
            return start, end
        return self.text.index("insert linestart"), self.text.index("insert + 1line linestart")

    def _indent_lines(self):
        start, end = self._selected_line_range()
        lines = []
        line = start
        while self.text.compare(line, "<", end):
            lines.append(line)
            line = self.text.index(f"{line}+1line")
        if self._has_selection() and len(lines) > 1 and self.text.compare("sel.last", "==", lines[-1]):
            lines.pop()
        self.text.edit_separator()
        for line in reversed(lines): self.text.insert(line, INDENT)
        self.text.edit_separator()

    def _dedent_lines(self):
        start, end = self._selected_line_range()
        has_selection = self._has_selection()
        lines = []
        line = start
        while self.text.compare(line, "<", end):
            prefix = self.text.get(line, f"{line}+4c")
            count = len(prefix) - len(prefix.lstrip(" "))
            lines.append((line, min(count, len(INDENT))))
            next_line = self.text.index(f"{line}+1line")
            if next_line == line: break
            line = next_line
        if has_selection and len(lines) > 1 and self.text.compare("sel.last", "==", lines[-1][0]):
            lines.pop()
        self.text.edit_separator()
        for line, count in reversed(lines):
            if count: self.text.delete(line, f"{line}+{count}c")
        self.text.edit_separator()

    def _scroll_text(self, *args):
        self.text.yview(*args); self._draw_gutter()

    def _sync_scrollbar(self, first, last):
        self.scrollbar.set(first, last); self._draw_gutter()

    def _on_scroll(self, _event=None): self.after_idle(self._draw_gutter)

    def _on_edit(self, _event=None):
        self._draw_gutter(); self._schedule_highlight()

    def _schedule_highlight(self):
        if self._highlight_job is not None:
            try: self.after_cancel(self._highlight_job)
            except tk.TclError: pass
        self._highlight_job = self.after(90, self._run_highlight)

    def _run_highlight(self):
        self._highlight_job = None; self._highlight()

    def _draw_gutter(self):
        self.gutter.delete("all")
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None: break
            y = info[1] + info[3] / 2
            number = index.split(".")[0]
            color = theme.ACCENT if number == self.text.index("insert").split(".")[0] else theme.MUTED
            self.gutter.create_text(39, y, anchor="e", text=number, fill=color, font=(theme.MONO, 10))
            next_index = self.text.index(f"{index}+1line")
            if next_index == index: break
            index = next_index

    def _highlight(self):
        for tag in ("keyword", "string", "comment", "number", "current_line"):
            self.text.tag_remove(tag, "1.0", "end")
        source = self.text.get("1.0", "end-1c")
        for tag, start, end in lexical_spans(source, self.language):
            self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
        line = self.text.index("insert").split(".")[0]
        self.text.tag_add("current_line", f"{line}.0", f"{line}.end+1c")
        self.text.tag_lower("current_line"); self._draw_gutter()

    def line_column(self):
        line, column = self.text.index("insert").split(".")
        return int(line), int(column) + 1
