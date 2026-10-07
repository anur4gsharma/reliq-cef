import os
import pathlib
import subprocess
import sys
import tempfile
import time


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
import os
print(os.listdir("C:/Users/a"))
'''

result = execute(code)
print(result)
