import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from .config import load_config
from .iso import check_command
from .models import MirrorcacheConfig, AppConfig, Package, ObsRequest
from .reporting import (
    print_iso_results,
    print_obs_results,
    print_git_report,
    print_obs_requests_results,
    extract_git_hashes,
)
from .reports import RpmsOnIsoReport, PackagesInObsReport
from .reports.obs_requests import ObsSubmitRequestsReport
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
    parser.add_argument(
        "--no-command-cache",
        action="store_true",
        help="Force refresh of cached command results (e.g. osc commands).",
    )
    parser.add_argument(
        "--recent-rq",
        action="store_true",
        help="Show requests of all states modified within the past two weeks.",
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
    obs_requests_results: List[Tuple[Dict[str, Any], List[ObsRequest]]] = []
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
            obs_report = PackagesInObsReport(
                stage, rpm_map, config.specs, no_cache=args.no_command_cache
            )
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

            if stage.get("submit_requests"):
                requests_report = ObsSubmitRequestsReport(
                    stage,
                    rpm_map,
                    no_cache=args.no_command_cache,
                    recent_requests=args.recent_rq,
                )
                _, requests = requests_report.run()
                if requests:
                    obs_requests_results.append(
                        (
                            {
                                "name": stage.get("name", "Unknown OBS Project"),
                                "url": stage.get("url"),
                            },
                            requests,
                        )
                    )

        elif stage_type == "git":
            pass

    if iso_results:
        print_iso_results(iso_results, rpm_map)
    if obs_results:
        print_obs_results(obs_results, list(rpm_map.keys()), config.specs)
    if obs_requests_results:
        print_obs_requests_results(obs_requests_results)

    print_git_report(all_git_hashes, config.git_config)


if __name__ == "__main__":
    main()
