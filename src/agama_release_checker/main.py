import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import load_config
from .iso import (
    check_command,
    mount_iso,
    unmount_iso,
    get_packages_from_metadata,
)
from .models import MirrorcacheConfig, AppConfig, Package
from .network import find_iso_urls, download_file
from .reporting import print_results

CACHE_DIR = Path.home() / ".cache" / "agama-release-checker"


def create_cache_dir(cache_dir_path: Path) -> None:
    """Creates the cache directory if it doesn't already exist."""
    cache_dir_path.mkdir(parents=True, exist_ok=True)


def process_mirrorcache(
    mirrorcache_config: MirrorcacheConfig,
) -> Tuple[Optional[str], Optional[List[Package]]]:
    """Processes a single mirrorcache configuration."""
    logging.info(f"Processing mirrorcache: {mirrorcache_config.name}")
    base_url = mirrorcache_config.url
    patterns = mirrorcache_config.files
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

    mount_point = CACHE_DIR / f"iso_mount_{mirrorcache_config.name}"
    if mount_iso(iso_filepath, mount_point):
        try:
            iso_packages = get_packages_from_metadata(mount_point)
            return latest_iso_url, iso_packages
        finally:
            unmount_iso(mount_point)
    return latest_iso_url, None


def main() -> None:
    # Configure logging
    log = logging.getLogger()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(
        description="Checks for the latest Agama release, downloads it, and verifies package versions."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    parser.add_argument(
        "--name",
        action="append",
        help="Specify the name of the mirrorcache to process. Can be used multiple times.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled.")

    print("# Agama Release Status")

    if not all(map(check_command, ["curl", "fuseiso", "fusermount"])):
        logging.error(
            "Required command(s) not found. Please ensure 'curl', 'fuseiso', and 'fusermount' are installed and in your PATH."
        )
        if not check_command("fuseiso"):
            logging.info("On openSUSE/SLES, try: sudo zypper install fuseiso")
            logging.info("On Debian/Ubuntu, try: sudo apt-get install fuseiso")
        sys.exit(1)

    create_cache_dir(CACHE_DIR)
    config: AppConfig = load_config(Path("config.yml"))
    mirrorcache_configs: List[MirrorcacheConfig] = config.mirrorcache_configs

    if not mirrorcache_configs:
        logging.error("No mirrorcache configuration found in config.yml.")
        sys.exit(1)

    if args.name:
        mirrorcache_configs = [
            cfg for cfg in mirrorcache_configs if cfg.name in args.name
        ]

    results: List[Tuple[Dict[str, Any], Optional[str], Optional[List[Package]]]] = []
    rpm_map: Dict[str, List[str]] = config.rpms
    for mirrorcache_config in mirrorcache_configs:
        # The reporting function still expects a dict, so we convert it back for now
        # This can be refactored later
        config_dict = {
            "name": mirrorcache_config.name,
            "url": mirrorcache_config.url,
            "files": mirrorcache_config.files,
        }
        latest_iso_url, iso_packages = process_mirrorcache(mirrorcache_config)
        results.append((config_dict, latest_iso_url, iso_packages))

    print_results(results, config.git_config, rpm_map)


if __name__ == "__main__":
    main()
