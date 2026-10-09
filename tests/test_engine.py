import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from reliq.engine import Runner, _root, _safe_remove
from reliq.runtime import Runtime, discover


def python_runtime():
    return Runtime("Python", "py", sys.executable, sys.version, "test Python")


class EngineTests(unittest.TestCase):
    def test_success_and_stream_identity(self):
        seen = []
        result = Runner().execute(python_runtime(), "import sys; print('out', flush=True); print('err', file=sys.stderr, flush=True)", on_output=lambda *x: seen.append(x))
        self.assertEqual(result.status, "success")
        self.assertIn("out", result.stdout)
        self.assertIn("err", result.stderr)
        self.assertEqual({item[0] for item in seen}, {"stdout", "stderr"})

    def test_unterminated_output_is_live_and_capture_is_bounded(self):
        ready = threading.Event()
        result_box = []
        def execute():
            result_box.append(Runner(output_limit=128).execute(
                python_runtime(), "import sys,time; sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(.2); print('x'*1000)",
                on_output=lambda stream, value: ready.set()))
        thread = threading.Thread(target=execute)
        thread.start()
        self.assertTrue(ready.wait(1), "flushed partial output should reach the callback before process exit")
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertLessEqual(len(result_box[0].stdout), 160)
        self.assertIn("output truncated", result_box[0].stdout)

    def test_nonzero_and_syntax_failure(self):
        result = Runner().execute(python_runtime(), "raise SystemExit(7)")
        self.assertEqual((result.status, result.exit_code), ("nonzero_exit", 7))
        result = Runner().execute(python_runtime(), "if:")
        self.assertEqual(result.status, "nonzero_exit")
        self.assertIn("SyntaxError", result.stderr)

    def test_timeout_and_cancellation(self):
        result = Runner(timeout=.15).execute(python_runtime(), "import time; time.sleep(10)")
        self.assertEqual(result.status, "timeout")
        runner = Runner(timeout=8)
        thread = threading.Thread(target=lambda: setattr(self, "cancel_result", runner.execute(python_runtime(), "import time; time.sleep(10)")))
        thread.start(); time.sleep(.25); runner.cancel(); thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.cancel_result.status, "cancelled")

    def test_workspace_cleanup_and_containment(self):
        before = set(_root().iterdir())
        Runner().execute(python_runtime(), "print('done')")
        self.assertEqual(set(_root().iterdir()), before)
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / "run-owned"
            outside.mkdir()
            with self.assertRaises(ValueError): _safe_remove(outside, _root())
            self.assertTrue(outside.exists())

    def test_cleanup_failure_is_reported(self):
        with patch("reliq.engine._safe_remove", side_effect=OSError("simulated cleanup failure")):
            result = Runner().execute(python_runtime(), "print('done')")
        self.assertEqual(result.status, "success")
        self.assertIn("workspace cleanup failed", result.error)

    def _check_adapter(self, language, source):
        runtime = next((item for item in discover() if item.language.lower() == language), None)
        if runtime is None: self.skipTest(f"optional runtime unavailable: {language}")
        result = Runner(timeout=15).execute(runtime, source)
        self.assertEqual(result.status, "success", result.stderr or result.error)
        self.assertIn("adapter-ok", result.stdout)

    def test_javascript_adapter(self): self._check_adapter("javascript", "console.log('adapter-ok')")

    def test_bash_adapter(self): self._check_adapter("bash", "printf 'adapter-ok\\n'")

    def test_cpp_adapter(self):
        self._check_adapter("cpp", "#include <iostream>\nint main(){std::cout << \"adapter-ok\\n\";}\n")

    def test_powershell_adapter(self): self._check_adapter("powershell", "Write-Output 'adapter-ok'")

    def test_child_process_is_terminated(self):
        result = Runner(timeout=.2).execute(python_runtime(), "import subprocess,time,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(15)']); time.sleep(15)")
        self.assertEqual(result.status, "timeout")


if __name__ == "__main__":
    unittest.main()
