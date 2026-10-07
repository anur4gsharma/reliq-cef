import subprocess
import sys
import threading
import tkinter as tk

if __package__:
    from .ui.window import ReliqWindow, current_runtime_option
else:
    from ui.window import ReliqWindow, current_runtime_option

view = ReliqWindow([current_runtime_option(".".join(map(str, sys.version_info[:3])))])
root = view.root
code = view.editor.text
output = view.output
current_process = None

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

    global current_process
    current_process = process

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

    stdout_thread.join()
    stderr_thread.join()

    if getattr(process, "reliq_interrupted", False):
        print("Process interrupted")
    else:
        print(f"Process exited with code {process.returncode}")
    root.after(0, view.set_running, False)

def run_code():

    source = code.get("1.0", tk.END)
    output.delete("1.0", tk.END)
    view.set_running(True)
    previous_process = current_process

    thread = threading.Thread(
        target=execute_code,
        args=(source,)
    )
    thread.start()

    if previous_process is not None and previous_process.poll() is None:
        previous_process.terminate()

def stop_code():
    if current_process is not None and current_process.poll() is None:
        current_process.reliq_interrupted = True
        current_process.terminate()

view.toolbar.run_button.configure(command=run_code)
view.toolbar.stop_button.configure(command=stop_code)
code.bind("<Control-Return>", lambda _event: (run_code(), "break")[1])
root.bind("<Control-period>", lambda _event: (stop_code(), "break")[1])

if __name__ == "__main__":
    root.mainloop()
