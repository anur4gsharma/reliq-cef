import subprocess
import sys
import time
import tempfile
import os
import pathlib

print("CWD:", os.getcwd())
print("USER:", os.getlogin() if hasattr(os, "getlogin") else "N/A")
print("PYTHON:", sys.executable)
print("ENVIRONMENT:")
for key in os.environ:
    print(key)
print(os.listdir("."))
print(pathlib.Path.cwd())
print(list(pathlib.Path(".").iterdir()))

paths = [
    ".",
    "..",
    os.path.expanduser("~"),
    os.environ.get("TEMP"),
    os.environ.get("USERPROFILE"),
]

for path in paths:
    print(path, "=>", os.path.exists(path))

def execute(code : str):

    with tempfile.NamedTemporaryFile(
    mode="w+", prefix="temp", suffix=".py", dir=".", delete=False
    ) as temp:
        temp.write(code)
        temp.seek(0)

    try :

        st = time.perf_counter()
        result = subprocess.run(
        [sys.executable, temp.name],
        capture_output=True,
        text=True,
        timeout=3
        )
        end = time.perf_counter()

        status = "COMPLETED" if result.returncode == 0 else "ERROR"

        fn_result = {
                "status" : status,
                "stdout" : result.stdout,
                "stderr" : result.stderr,
                "exit_code" : result.returncode,
                "execution_time" : end - st
            }
               

    except subprocess.TimeoutExpired:

        fn_result = {
            "status" : "TIMEOUT",
            "stdout" : "",
            "stderr" : "",
            "exit_code" : 124,
            "execution_time" : time.perf_counter() - st
            }
    
    finally :
        if os.path.exists(temp.name):
            os.remove(temp.name)

    return fn_result

code = '''
print("Hello")
'''

result = execute(code)
print(result)
