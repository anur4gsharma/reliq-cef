"""PyInstaller entry point that imports Reliq as a package."""
from reliq.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
