"""Install Reliq from an archive URL in a fresh venv and smoke-test it."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", help="GitHub ZIP URL or local source ZIP URL")
    source.add_argument("--checkout", action="store_true", help="archive the current working tree without Git")
    parser.add_argument("smoke_script", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="reliq-archive-install-") as tmp:
        archive = args.archive
        if args.checkout:
            project = Path(__file__).resolve().parent.parent
            archive_path = Path(tmp) / "reliq-source.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                sources = [project / "pyproject.toml", project / "README.md", project / "LICENSE"]
                for package in (project / "reliq", project / "executor" / "ui"):
                    sources.extend(path for path in package.rglob("*.py") if "__pycache__" not in path.parts)
                for path in sources:
                    bundle.write(path, Path("reliq-cef-main") / path.relative_to(project))
            archive = archive_path.as_uri()
        environment = Path(tmp) / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", archive], check=True, timeout=300)
        command_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        child_env = os.environ.copy()
        child_env["PATH"] = str(command_dir) + os.pathsep + child_env.get("PATH", "")
        child_env.pop("PYTHONPATH", None)
        subprocess.run(["reliq", "--help"], check=True, timeout=15, env=child_env,
                       cwd=tmp, stdout=subprocess.DEVNULL)
        subprocess.run([str(python), str(args.smoke_script.resolve())], check=True,
                       timeout=30, env=child_env, cwd=tmp)
    print("Archive installation and installed-launch smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
