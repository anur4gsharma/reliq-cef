import os
import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def test_help_and_stdin_execution(self):
        help_result = subprocess.run([sys.executable, "-m", "reliq", "--help"], capture_output=True, text=True, timeout=5)
        self.assertEqual(help_result.returncode, 0)
        result = subprocess.run([sys.executable, "-m", "reliq", "-", "--language", "python"], input="print('cli-ok')\n", capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cli-ok", result.stdout)

    def test_unknown_target_errors(self):
        result = subprocess.run([sys.executable, "-m", "reliq", "unknown-language"], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown language or file", result.stderr)


if __name__ == "__main__":
    unittest.main()
