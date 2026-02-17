import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from .config import load_config
from .iso import check_command
from .models import MirrorcacheConfig, AppConfig, Package
from .reporting import (
    print_iso_results,
    print_obs_results,
    print_git_report,
    extract_git_hashes,
)
from .reports import RpmsOnIsoReport, PackagesInObsReport
from .utils import CACHE_DIR, ensure_dir


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

    ensure_dir(CACHE_DIR)
    config: AppConfig = load_config(Path("config.yml"))

    iso_results: List[Tuple[Dict[str, Any], Optional[str], Optional[List[Package]]]] = (
        []
    )
    obs_results: List[Tuple[Dict[str, Any], Optional[List[Package]]]] = []
    all_git_hashes: Set[str] = set()
    rpm_map: Dict[str, List[str]] = config.rpms

    stages_to_process = config.stages
    if args.name:
        stages_to_process = [s for s in config.stages if s.get("name") in args.name]

    if not stages_to_process:
        logging.warning("No stages to process found.")

    for stage in stages_to_process:
        stage_type = stage.get("type")
        if stage_type == "mirrorcache":
            mc_args = {
                k: stage[k] for k in ["type", "name", "url", "files"] if k in stage
            }
            mirrorcache_config = MirrorcacheConfig(**mc_args)

            iso_report = RpmsOnIsoReport(mirrorcache_config)
            latest_iso_url, iso_packages = iso_report.run()

            iso_results.append(
                (
                    {
                        "name": mirrorcache_config.name,
                        "url": mirrorcache_config.url,
                        "files": mirrorcache_config.files,
                    },
                    latest_iso_url,
                    iso_packages,
                )
            )
            if iso_packages:
                all_git_hashes.update(extract_git_hashes(iso_packages, rpm_map))

        elif stage_type == "obsproject":
            obs_report = PackagesInObsReport(stage, rpm_map, config.specs)
            latest_url, obs_packages = obs_report.run()

            obs_results.append(
                (
                    {
                        "name": stage.get("name", "Unknown OBS Project"),
                        "url": stage.get("url"),
                    },
                    obs_packages,
                )
            )
            if obs_packages:
                all_git_hashes.update(extract_git_hashes(obs_packages, rpm_map))

        elif stage_type == "git":
            pass

    if iso_results:
        print_iso_results(iso_results, rpm_map)
    if obs_results:
        print_obs_results(obs_results, list(rpm_map.keys()), config.specs)

    print_git_report(all_git_hashes, config.git_config)


if __name__ == "__main__":
    main()
