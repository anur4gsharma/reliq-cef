import subprocess
import sys
import tkinter as tk
import threading
import time

root = tk.Tk()
root.title("Reliq")

code = tk.Text(root)
code.grid(row=1, column=1)

output = tk.Text(root)
output.grid(row=2, column=1)

def execute_code(source):
    
    result = subprocess.run(
        [sys.executable, '-c', source],
        capture_output=True,
        check=False,
        text=True
    )

    output.insert(tk.END, result.stdout)
    if result.stderr:
        output.insert(tk.END, result.stderr)

def run_code():
    source = code.get("1.0", tk.END)
    output.delete("1.0", tk.END)

    thread = threading.Thread(target=execute_code, args=(source,))
    thread.start()

run_btn = tk.Button(root, text='RUN', command=run_code)
run_btn.grid(row=2, column=2)

root.mainloop()