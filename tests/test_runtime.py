import unittest
import os
import json
import tempfile
from pathlib import Path, PureWindowsPath
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

    def test_probe_timeouts_permissions_and_failed_manager_commands_are_ignored(self):
        from reliq.runtime import _manager_output, _version
        import subprocess
        for error in (subprocess.TimeoutExpired(["python"], 2), PermissionError("denied"), FileNotFoundError("missing")):
            with self.subTest(error=type(error).__name__), patch("reliq.runtime._run", side_effect=error):
                self.assertIsNone(_version("/candidate/python", "python"))
                self.assertIsNone(_manager_output(["manager", "--version"]))

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
                 patch("reliq.runtime.sys.executable", "/not-here/python"), \
                 patch("reliq.runtime.shutil.which", side_effect=lambda _: None), \
                 patch("reliq.runtime._version", return_value="Python 3.test"):
                result = discover(root)
            self.assertEqual([item.source for item in result], ["project environment", "active environment"])
            self.assertEqual(result[0].project, str(root.resolve()))

    def test_project_environment_directories_are_scoped_and_named(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for dirname in (".venv", "venv", "env"):
                binary = root / dirname / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
                binary.parent.mkdir(parents=True); binary.touch()
            with patch.dict(os.environ, {}, clear=True), \
                 patch("reliq.runtime.sys.executable", "/unrelated/python"), \
                 patch("reliq.runtime.shutil.which", return_value=None), \
                 patch("reliq.runtime._version", return_value="Python 3.test"):
                found = discover(root)
            self.assertEqual([item.environment_name for item in found], [".venv", "venv", "env"])

    def test_conda_json_listing_and_duplicate_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = root / "conda env space"
            python = env / ("python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True); python.touch()
            with patch.dict(os.environ, {"CONDA_PREFIX": str(env)}), \
                 patch("reliq.runtime.sys.executable", "/not-here/python"), \
                 patch("reliq.runtime.shutil.which", side_effect=lambda name: "/tools/conda" if name == "conda" else None), \
                 patch("reliq.runtime._manager_output", return_value=json.dumps({"envs": [str(env)]})), \
                 patch("reliq.runtime._version", return_value="Python 3.12"):
                from reliq.runtime import _python_candidates
                candidates = _python_candidates(None)
            matches = [candidate for candidate in candidates if Path(candidate[0]) == python]
            self.assertEqual(len(matches), 2)  # active prefix + supported Conda listing
            with patch("reliq.runtime._python_candidates", return_value=candidates), \
                 patch("reliq.runtime.shutil.which", return_value=None), \
                 patch("reliq.runtime._version", return_value="Python 3.12"):
                found = discover()
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].environment_type, "conda")
            self.assertEqual(found[0].environment_name, env.name)

    def test_poetry_and_pipenv_queries_are_project_scoped(self):
        from reliq.runtime import _python_candidates
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pyproject.toml").write_text("[tool.poetry]\nname='demo'", encoding="utf-8")
            (root / "Pipfile").touch()
            poetry_env, pipenv_env = root / "poetry-env", root / "pipenv-env"
            calls = []
            def manager(argv, **kwargs):
                calls.append((argv, kwargs.get("cwd")))
                if argv[0] == "/tools/poetry": return str(poetry_env)
                if argv[0] == "/tools/pipenv": return str(pipenv_env)
                return None
            with patch("reliq.runtime.shutil.which", side_effect=lambda name: f"/tools/{name}" if name in {"poetry", "pipenv"} else None), \
                 patch("reliq.runtime._manager_output", side_effect=manager):
                candidates = _python_candidates(root)
            origins = {entry[1] for entry in candidates}
            self.assertTrue({"Poetry", "Pipenv"}.issubset(origins))
            self.assertTrue(all(cwd == str(root) for _argv, cwd in calls))

    def test_uv_project_lookup_is_best_effort_and_project_scoped(self):
        from reliq.runtime import _python_candidates
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "uv.lock").touch()
            with patch("reliq.runtime.shutil.which", side_effect=lambda name: "/tools/uv" if name == "uv" else None), \
                 patch("reliq.runtime._manager_output", return_value="/uv/python path/python"):
                candidates = _python_candidates(root)
            self.assertTrue(any(item[1] == "uv" and item[4] == str(root) for item in candidates))

    def test_uv_managed_interpreter_list_uses_installed_json_only(self):
        from reliq.runtime import _python_candidates
        with patch("reliq.runtime.shutil.which", side_effect=lambda name: "/tools/uv" if name == "uv" else None), \
             patch("reliq.runtime._manager_output", return_value=json.dumps({"installations": [{"path": "/uv/python 3.12/bin/python"}]})) as manager:
            candidates = _python_candidates(None)
        self.assertTrue(any(item[0] == "/uv/python 3.12/bin/python" and item[1] == "uv" for item in candidates))
        self.assertIn("--only-installed", manager.call_args.args[0])

    def test_missing_managers_and_bad_json_are_nonfatal(self):
        from reliq.runtime import _python_candidates
        with tempfile.TemporaryDirectory() as temp:
            with patch("reliq.runtime.shutil.which", return_value=None), \
                 patch("reliq.runtime.sys.executable", "/not-here/python"):
                self.assertTrue(_python_candidates(temp))
            with patch("reliq.runtime.shutil.which", side_effect=lambda name: "/tools/conda" if name == "conda" else None), \
                 patch("reliq.runtime.sys.executable", "/not-here/python"), \
                 patch("reliq.runtime._manager_output", return_value="not-json"):
                self.assertFalse(any(candidate[1] == "Conda" for candidate in _python_candidates(None)))

    def test_windows_venv_and_conda_paths(self):
        from reliq.runtime import _python_executable
        with patch("reliq.runtime.os.name", "nt"):
            self.assertEqual(str(_python_executable(PureWindowsPath("C:/project/.venv"))), "C:\\project\\.venv\\Scripts\\python.exe")
            self.assertEqual(str(_python_executable(PureWindowsPath("C:/conda/env"), conda=True)), "C:\\conda\\env\\python.exe")

    def test_duplicate_path_merging_and_distinct_same_version_interpreters(self):
        from reliq.runtime import _python_candidates
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "python A", Path(temp) / "python B"
            a.touch(); b.touch()
            candidates = [(str(a), "PATH", "", "", ""), (str(a), "project environment", "venv", ".venv", temp),
                          (str(b), "PATH", "", "", "")]
            with patch("reliq.runtime._python_candidates", return_value=candidates), \
                 patch("reliq.runtime.shutil.which", return_value=None), \
                 patch("reliq.runtime._version", return_value="Python 3.12"):
                found = discover()
            self.assertEqual(len(found), 2)
            self.assertEqual(found[0].source, "project environment")
            self.assertNotEqual(found[0].identity, found[1].identity)

    def test_execution_plan_uses_argument_vector(self):
        runtime = Runtime("Python", "py", "/usr/bin/python3", "Python 3", "Python")
        result = plan(runtime, "/tmp/source;touch nope.py")
        self.assertEqual(result.argv, ("/usr/bin/python3", "-u", "/tmp/source;touch nope.py"))

    def test_extension_mapping(self):
        self.assertEqual(language_for_extension("demo.js"), "javascript")
        self.assertIsNone(language_for_extension("demo.txt"))


if __name__ == "__main__":
    unittest.main()
