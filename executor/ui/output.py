import tkinter as tk

from . import theme


class OutputPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=theme.OUTPUT_BG)
        heading = tk.Frame(self, bg=theme.SURFACE, height=36)
        heading.grid(row=0, column=0, sticky="ew")
        heading.grid_propagate(False)
        tk.Label(
            heading, text="OUTPUT", bg=theme.SURFACE, fg=theme.MUTED,
            font=(theme.FONT, 9, "bold"),
        ).pack(side="left", padx=(14, 8))
        self.clear_button = tk.Button(
            heading, text="Clear", command=self.clear, bg=theme.SURFACE,
            fg=theme.MUTED, activebackground=theme.SURFACE_RAISED,
            activeforeground=theme.TEXT, relief="flat", borderwidth=0,
            font=(theme.FONT, 9), padx=10, cursor="hand2",
        )
        self.clear_button.pack(side="right", padx=6)

        body = tk.Frame(self, bg=theme.OUTPUT_BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.text = tk.Text(
            body, bg=theme.OUTPUT_BG, fg=theme.TEXT, font=(theme.MONO, 10),
            padx=14, pady=10, wrap="word", state="disabled", relief="flat",
            borderwidth=0, highlightthickness=0,
        )
        self.scrollbar = tk.Scrollbar(
            body, orient="vertical", command=self.text.yview,
            troughcolor=theme.OUTPUT_BG, bg=theme.SURFACE_RAISED,
            activebackground=theme.MUTED, relief="flat", borderwidth=0,
        )
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.tag_configure("stderr", foreground=theme.RED)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def insert(self, index, value, tag=None):
        self.text.configure(state="normal")
        self.text.insert(index, value, tag or ())
        self.text.see("end")
        self.text.configure(state="disabled")

    def delete(self, start, end):
        self.text.configure(state="normal")
        self.text.delete(start, end)
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
