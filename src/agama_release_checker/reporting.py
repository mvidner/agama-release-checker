import logging
import re
from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urljoin
import fnmatch

from .models import GitConfig


def extract_git_hashes(
    iso_packages: List[Dict[str, Any]], rpm_map: Dict[str, List[str]]
) -> Set[str]:
    """Extracts git hashes from the version strings of packages."""
    git_hashes = set()
    iso_pkg_map = {pkg["name"]: pkg for pkg in iso_packages}
    for source_rpm, binary_patterns in rpm_map.items():
        for pattern in binary_patterns:
            for pkg_name, pkg_details in iso_pkg_map.items():
                if fnmatch.fnmatch(pkg_name, pattern):
                    version = pkg_details.get("version", "N/A")
                    match = re.search(r"([0-9a-fA-F]{7,})$", version)
                    if match:
                        git_hashes.add(match.group(1))
    return git_hashes


def print_unified_packages_table(
    rpm_map: Dict[str, List[str]], iso_packages: List[Dict[str, Any]]
) -> None:
    """Prints a formatted table of packages in a single table."""

    iso_pkg_map = {pkg["name"]: pkg for pkg in iso_packages}
    all_found_packages_by_source = {}

    for source_rpm, binary_patterns in rpm_map.items():
        found_packages = []
        for pattern in binary_patterns:
            for pkg_name, pkg_details in iso_pkg_map.items():
                if fnmatch.fnmatch(pkg_name, pattern):
                    found_packages.append(pkg_details)

        all_found_packages_by_source[source_rpm] = sorted(
            found_packages, key=lambda p: p.get("name", "")
        )

    all_packages_flat = [
        pkg for pkgs in all_found_packages_by_source.values() for pkg in pkgs
    ]
    if not all_packages_flat:
        print("  (No matching packages found in ISO)")
        return

    # Calculate column widths
    source_name_width = max(
        (len(source_rpm) for source_rpm in rpm_map.keys()), default=0
    )
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


def print_results(
    results: List[Tuple[Dict[str, Any], Optional[str], Optional[List[Dict[str, Any]]]]],
    git_config: Optional[GitConfig],
    rpm_map: Dict[str, List[str]],
) -> None:
    """Prints the collected results in a consolidated format."""
    all_git_hashes = set()
    for mirrorcache_config, latest_iso_url, iso_packages in results:
        print(f"\n## {mirrorcache_config['name']}\n")
        if latest_iso_url:
            print(f"ISO: {latest_iso_url}\n")
        if iso_packages:
            print_unified_packages_table(rpm_map, iso_packages)
            all_git_hashes.update(extract_git_hashes(iso_packages, rpm_map))
        else:
            print("  (No packages found)")

    if all_git_hashes and git_config:
        git_base_url = git_config.url
        print("\n## Git Commits\n")
        for githash in sorted(list(all_git_hashes)):
            print(f"- {urljoin(git_base_url, f'commit/{githash}')}")
    elif not git_config:
        logging.warning(
            "No 'git' configuration found in config.yml. Cannot print commit URLs."
        )
