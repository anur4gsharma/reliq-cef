import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from reliq.runtime import Runtime, discover, language_for_extension, plan


class RuntimeTests(unittest.TestCase):
    def test_discovers_python_and_available_optional_runtimes(self):
        found = discover()
        self.assertTrue(any(item.language == "Python" for item in found))
        self.assertTrue(all(item.version and item.executable for item in found))

    def test_invalid_probe_is_omitted(self):
        with patch("reliq.runtime.shutil.which", side_effect=lambda name: "/missing" if name == "python" else None), \
             patch("reliq.runtime._version", return_value=None):
            self.assertEqual(discover(), [])

    def test_environment_candidates_follow_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project_env = root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
            activated_env = root / "activated" / ("Scripts" if os.name == "nt" else "bin")
            project_env.mkdir(parents=True); activated_env.mkdir(parents=True)
            executable_name = "python.exe" if os.name == "nt" else "python"
            project_exe = project_env / executable_name
            activated_exe = activated_env / executable_name
            project_exe.touch(); activated_exe.touch()
            with patch.dict(os.environ, {"VIRTUAL_ENV": str(activated_exe.parent.parent)}), \
                 patch("reliq.runtime.shutil.which", side_effect=lambda _: None), \
                 patch("reliq.runtime._version", return_value="Python 3.test"):
                result = discover(root)
            self.assertEqual([item.source for item in result], ["activated environment", "project .venv"])

    def test_execution_plan_uses_argument_vector(self):
        runtime = Runtime("Python", "py", "/usr/bin/python3", "Python 3", "Python")
        result = plan(runtime, "/tmp/source;touch nope.py")
        self.assertEqual(result.argv, ("/usr/bin/python3", "-u", "/tmp/source;touch nope.py"))

    def test_extension_mapping(self):
        self.assertEqual(language_for_extension("demo.js"), "javascript")
        self.assertIsNone(language_for_extension("demo.txt"))


if __name__ == "__main__":
    unittest.main()
