from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "agama-release-checker"


def ensure_dir(path: Path) -> None:
    """Creates the directory if it doesn't already exist."""
    path.mkdir(parents=True, exist_ok=True)
