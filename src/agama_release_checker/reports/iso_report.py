import logging
from pathlib import Path
from typing import List, Optional, Tuple

from agama_release_checker.iso import (
    mount_iso,
    unmount_iso,
    get_packages_from_metadata,
)
from agama_release_checker.models import MirrorcacheConfig, Package
from agama_release_checker.network import find_iso_urls, download_file

CACHE_DIR = Path.home() / ".cache" / "agama-release-checker"


class RpmsOnIsoReport:
    def __init__(self, config: MirrorcacheConfig):
        self.config = config

    def run(self) -> Tuple[Optional[str], Optional[List[Package]]]:
        """Processes a single mirrorcache configuration."""
        logging.info(f"Processing mirrorcache: {self.config.name}")
        base_url = self.config.url
        patterns = self.config.files
        iso_urls = find_iso_urls(base_url, patterns)

        if not iso_urls:
            logging.warning(f"No ISOs found matching patterns {patterns} at {base_url}")
            return None, None

        iso_urls.sort()
        latest_iso_url = iso_urls[-1]
        logging.debug(f"Determined latest ISO: {latest_iso_url}")

        iso_filename = latest_iso_url.split("/")[-1]
        iso_filepath = CACHE_DIR / iso_filename

        if not iso_filepath.exists():
            if not download_file(latest_iso_url, iso_filepath):
                return latest_iso_url, None  # Skip if download fails
        else:
            logging.info(f"In cache: {iso_filename}")

        mount_point = CACHE_DIR / f"iso_mount_{self.config.name}"

        # Ensure mount point exists
        mount_point.mkdir(parents=True, exist_ok=True)

        if mount_iso(iso_filepath, mount_point):
            try:
                iso_packages = get_packages_from_metadata(mount_point)
                return latest_iso_url, iso_packages
            finally:
                unmount_iso(mount_point)
        return latest_iso_url, None
