import gzip
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any


def check_command(command: str) -> bool:
    """Checks if a command is available in PATH."""
    return shutil.which(command) is not None


def mount_iso(iso_path: Path, mount_point: Path) -> bool:
    """Mounts an ISO file using fuseiso."""
    logging.debug(f"Mounting ISO {iso_path} to {mount_point}")
    try:
        mount_point.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["fuseiso", str(iso_path), str(mount_point)],
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        logging.debug(f"ISO successfully mounted to {mount_point}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Error mounting ISO {iso_path}: {e}")
        return False


def unmount_iso(mount_point: Path) -> bool:
    """Unmounts a fuseiso mounted directory."""
    logging.debug(f"Unmounting {mount_point}")
    try:
        subprocess.run(
            ["fusermount", "-u", str(mount_point)],
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        logging.debug(f"Successfully unmounted {mount_point}")
        os.rmdir(mount_point)
        logging.debug(f"Removed mount point directory {mount_point}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Error unmounting {mount_point}: {e}")
        return False


def get_packages_from_metadata(mount_point: Path) -> List[Dict[str, Any]]:
    """
    Parses LiveOS/.packages.json.gz to get a list of all packages.
    """
    metadata_path = mount_point / "LiveOS" / ".packages.json.gz"
    logging.debug(f"Reading packages from {metadata_path}...")

    if not metadata_path.exists():
        logging.error(f"Metadata file not found: {metadata_path}")
        return []

    try:
        with gzip.open(metadata_path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (gzip.BadGzipFile, json.JSONDecodeError, KeyError) as e:
        logging.error(f"Failed to parse metadata file {metadata_path}: {e}")
        return []
