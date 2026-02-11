#!/usr/bin/env python3
import yaml
import pprint
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import fnmatch
from urllib.parse import urljoin
import logging
import subprocess
import sys
import shutil
import gzip
import json
import argparse
import re




CACHE_DIR = Path.home() / ".cache" / "agama-release-checker"


def load_config(config_path):
    """Loads and returns the YAML configuration from the given path."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_config(config, entry_type):
    """Extracts and returns the entry of a specific type from the configuration."""
    for entry in config.get("stages", []):
        if entry.get("type") == entry_type:
            return entry
    return None


def create_cache_dir(cache_dir_path):
    """Creates the cache directory if it doesn't already exist."""
    cache_dir_path.mkdir(parents=True, exist_ok=True)


def find_iso_urls(base_url, patterns):
    """Scrapes the given URL and returns a list of matching ISO URLs."""
    logging.info(f"Fetching ISO directory from: {base_url}")
    logging.debug(f"Scraping with patterns: {patterns}")
    try:
        response = requests.get(base_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {base_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    iso_urls = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        filename = href.split("/")[-1]
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                iso_urls.append(urljoin(base_url, href))
                break
    logging.debug(f"Found {len(iso_urls)} ISO URLs.")
    return iso_urls


def download_file(url, destination_path):
    """Downloads a file from a URL using curl."""
    logging.info(f"Dowloading to {destination_path} from {url} with curl.")
    try:
        command = ["curl", "-L", url, "-o", str(destination_path), "--progress-bar"]
        subprocess.run(command, check=True, stdout=sys.stdout, stderr=sys.stderr)
        logging.info(f"Success: {destination_path.name}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Download failed: {e}")
        return False


def check_command(command):
    """Checks if a command is available in PATH."""
    return shutil.which(command) is not None


def mount_iso(iso_path, mount_point):
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


def unmount_iso(mount_point):
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


def get_packages_from_metadata(mount_point):
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


def print_unified_packages_table(rpm_map, iso_packages):
    """Prints a formatted table of packages in a single table."""

    iso_pkg_map = {pkg["name"]: pkg for pkg in iso_packages}
    git_hashes = set()
    all_found_packages_by_source = {}

    for source_rpm, binary_patterns in rpm_map.items():
        found_packages = []
        for pattern in binary_patterns:
            for pkg_name, pkg_details in iso_pkg_map.items():
                if fnmatch.fnmatch(pkg_name, pattern):
                    found_packages.append(pkg_details)
                    # Extract git hash from version
                    version = pkg_details.get("version", "N/A")
                    match = re.search(r"([0-9a-fA-F]{7,})$", version)
                    if match:
                        git_hashes.add(match.group(1))

        all_found_packages_by_source[source_rpm] = sorted(
            found_packages, key=lambda p: p.get("name")
        )

    all_packages_flat = [
        pkg for pkgs in all_found_packages_by_source.values() for pkg in pkgs
    ]
    if not all_packages_flat:
        print("  (No matching packages found in ISO)")
        return git_hashes

    # Calculate column widths
    source_name_width = max((len(source_rpm) for source_rpm in rpm_map.keys()), default=0)
    name_width = (
        max((len(pkg.get("name", "N/A")) for pkg in all_packages_flat), default=0)
        if all_packages_flat
        else 0
    )
    version_width = (
        max((len(pkg.get("version", "N/A")) for pkg in all_packages_flat), default=0)
        if all_packages_flat
        else 0
    )
    release_width = (
        max((len(pkg.get("release", "N/A")) for pkg in all_packages_flat), default=0)
        if all_packages_flat
        else 0
    )

    # Ensure minimum width for headers
    source_name_width = max(source_name_width, len("Source Name"))
    name_width = max(name_width, len("Name"))
    version_width = max(version_width, len("Version"))
    release_width = max(release_width, len("Release"))

    # Print header
    header = f"| {'Source Name':<{source_name_width}} | {'Name':<{name_width}} | {'Version':<{version_width}} | {'Release':<{release_width}} |"
    print(header)
    print(
        f"|{'-' * (source_name_width + 2)}|{'-' * (name_width + 2)}|{'-' * (version_width + 2)}|{'-' * (release_width + 2)}|"
    )

    # Print rows
    for source_rpm, found_packages in sorted(all_found_packages_by_source.items()):
        # Print an empty row for the source rpm heading
        print(
            f"| {source_rpm:<{source_name_width}} | {'':<{name_width}} | {'':<{version_width}} | {'':<{release_width}} |"
        )
        if not found_packages:
            continue

        for pkg in found_packages:
            name = pkg.get("name", "N/A")
            version = pkg.get("version", "N/A")
            release = pkg.get("release", "N/A")
            print(
                f"| {'':<{source_name_width}} | {name:<{name_width}} | {version:<{version_width}} | {release:<{release_width}} |"
            )

    return git_hashes


def main():
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
    config = load_config("config.yml")
    mirrorcache_config = get_config(config, "mirrorcache")
    git_config = get_config(config, "git")

    if not mirrorcache_config:
        logging.error("No mirrorcache configuration found in config.yml.")
        sys.exit(1)

    base_url = mirrorcache_config["url"]
    patterns = mirrorcache_config["files"]
    iso_urls = find_iso_urls(base_url, patterns)

    if not iso_urls:
        logging.warning(f"No ISOs found matching patterns {patterns} at {base_url}")
        sys.exit(0)

    iso_urls.sort()
    latest_iso_url = iso_urls[-1]
    logging.debug(f"Determined latest ISO: {latest_iso_url}")

    iso_filename = latest_iso_url.split("/")[-1]
    iso_filepath = CACHE_DIR / iso_filename

    if not iso_filepath.exists():
        if not download_file(latest_iso_url, iso_filepath):
            sys.exit(1)  # Exit if download fails
    else:
        logging.info(f"In cache: {iso_filename}")

    mount_point = CACHE_DIR / "iso_mount"
    if mount_iso(iso_filepath, mount_point):
        try:
            iso_packages = get_packages_from_metadata(mount_point)
            rpm_map = config.get("rpms", {})
            if iso_packages and rpm_map:
                git_hashes = print_unified_packages_table(rpm_map, iso_packages)
                if git_hashes and git_config:
                    git_base_url = git_config["url"]
                    print("\n## Git Commits\n")
                    for githash in sorted(list(git_hashes)):
                        print(f"- {urljoin(git_base_url, f'commit/{githash}')}")
                elif not git_config:
                    logging.warning(
                        "No 'git' configuration found in config.yml. Cannot print commit URLs."
                    )
            else:
                logging.warning("Could not find packages in ISO or RPM map in config.")
        finally:
            unmount_iso(mount_point)


if __name__ == "__main__":
    main()
