import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import load_config
from .iso import check_command
from .models import MirrorcacheConfig, AppConfig, Package
from .reporting import print_results
from .reports import RpmsOnIsoReport, PackagesInObsReport

CACHE_DIR = Path.home() / ".cache" / "agama-release-checker"


def create_cache_dir(cache_dir_path: Path) -> None:
    """Creates the cache directory if it doesn't already exist."""
    cache_dir_path.mkdir(parents=True, exist_ok=True)


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
        help="Specify the name of the stage to process. Can be used multiple times.",
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

    results: List[Tuple[Dict[str, Any], Optional[str], Optional[List[Package]]]] = []
    rpm_map: Dict[str, List[str]] = config.rpms

    stages_to_process = config.stages
    if args.name:
        stages_to_process = [s for s in config.stages if s.get("name") in args.name]

    if not stages_to_process:
        logging.warning("No stages to process found.")
        # We don't exit here because we might just want to print git info if available?
        # But usually we want to process something.
        # Original code exited if no mirrorcache configs found.

    for stage in stages_to_process:
        stage_type = stage.get("type")
        if stage_type == "mirrorcache":
            # Filter known keys for MirrorcacheConfig
            mc_args = {
                k: stage[k] for k in ["type", "name", "url", "files"] if k in stage
            }
            mirrorcache_config = MirrorcacheConfig(**mc_args)

            iso_report = RpmsOnIsoReport(mirrorcache_config)
            latest_iso_url, iso_packages = iso_report.run()

            config_dict = {
                "name": mirrorcache_config.name,
                "url": mirrorcache_config.url,
                "files": mirrorcache_config.files,
            }
            results.append((config_dict, latest_iso_url, iso_packages))

        elif stage_type == "obsproject":
            obs_report = PackagesInObsReport(stage)
            obs_report.run()

        elif stage_type == "git":
            pass

    print_results(results, config.git_config, rpm_map)


if __name__ == "__main__":
    main()
