import tkinter as tk
import subprocess
import sys
import threading

root = tk.Tk()
root.title("Reliq")
root.geometry("900x600")

toolbar = tk.Frame(root)
editor_frame = tk.Frame(root)
output_frame = tk.Frame(root)

toolbar.grid(row=0, column=0, sticky="ew")
editor_frame.grid(row=1, column=0, sticky="nsew")
output_frame.grid(row=2, column=0, sticky="nsew")

root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=3)
root.grid_columnconfigure(0, weight=1)

code = tk.Text(editor_frame)
code.grid(row=0, column=0, sticky="nsew")

editor_frame.grid_rowconfigure(0, weight=1)
editor_frame.grid_columnconfigure(0, weight=1)

output = tk.Text(output_frame)
output.grid(row=0, column=0, sticky="nsew")

output_frame.grid_rowconfigure(0, weight=1)
output_frame.grid_columnconfigure(0, weight=1)

output.tag_config("stderr", foreground="red")

def output_insert_stdout(line):
    output.insert(tk.END, line)

def output_insert_stderr(line):
    output.insert(tk.END, line, "stderr")

def stderr_thread_run(process):
    for line in process:
        root.after(0, output_insert_stderr, line)

def stdout_thread_run(process):
    for line in process:
        root.after(0, output_insert_stdout, line)

def execute_code(source):
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", source],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout_thread = threading.Thread(
        target=stdout_thread_run,
        args=(process.stdout,)
    )

    stderr_thread = threading.Thread(
        target=stderr_thread_run,
        args=(process.stderr,)
    )
    stdout_thread.start()
    stderr_thread.start()

    process.wait()

    print(process.returncode)


def run_code():
    source = code.get("1.0", tk.END)
    output.delete("1.0", tk.END)

    thread = threading.Thread(
        target=execute_code,
        args=(source,)
    )
    thread.start()

run_btn = tk.Button(toolbar, text="RUN", command=run_code)
run_btn.pack(side="bottom")

root.mainloop()
