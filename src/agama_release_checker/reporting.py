import logging
import re
from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urljoin
import fnmatch

from .models import GitConfig, Package


def extract_git_hashes(
    packages: List[Package], rpm_map: Dict[str, List[str]]
) -> Set[str]:
    """Extracts git hashes from the version strings of packages."""
    git_hashes = set()
    pkg_map = {pkg.name: pkg for pkg in packages}
    for source_rpm, binary_patterns in rpm_map.items():
        for pattern in binary_patterns:
            for pkg_name, pkg_details in pkg_map.items():
                if fnmatch.fnmatch(pkg_name, pattern):
                    version = pkg_details.version
                    match = re.search(r"([0-9a-fA-F]{7,})$", version)
                    if match:
                        git_hashes.add(match.group(1))
    return git_hashes


def print_packages_table(
    rpm_map: Dict[str, List[str]], packages: List[Package], label: str = "ISO"
) -> None:
    """Prints a formatted table of packages."""

    pkg_map = {pkg.name: pkg for pkg in packages}
    all_found_packages_by_source = {}

    for source_rpm, binary_patterns in rpm_map.items():
        found_packages = []
        for pattern in binary_patterns:
            for pkg_name, pkg_details in pkg_map.items():
                if fnmatch.fnmatch(pkg_name, pattern):
                    found_packages.append(pkg_details)

        all_found_packages_by_source[source_rpm] = sorted(
            found_packages, key=lambda p: p.name
        )

    all_packages_flat = [
        pkg for pkgs in all_found_packages_by_source.values() for pkg in pkgs
    ]
    if not all_packages_flat:
        print(f"  (No matching packages found in {label})")
        return

    _print_table(rpm_map.keys(), all_packages_flat, all_found_packages_by_source)


def print_obs_packages_table(
    rpm_map_keys: List[str],
    specs_map: Dict[str, List[str]],
    packages: List[Package],
) -> None:
    """Prints a formatted table of OBS source packages."""
    pkg_map = {pkg.name: pkg for pkg in packages}
    all_found_packages_by_source = {}

    for obs_package in rpm_map_keys:
        found_packages = []
        # Get expected source names (specs) for this OBS package
        source_names = specs_map.get(obs_package, [obs_package])

        for source_name in source_names:
            if source_name in pkg_map:
                found_packages.append(pkg_map[source_name])

        all_found_packages_by_source[obs_package] = sorted(
            found_packages, key=lambda p: p.name
        )

    all_packages_flat = [
        pkg for pkgs in all_found_packages_by_source.values() for pkg in pkgs
    ]
    if not all_packages_flat:
        print(f"  (No matching packages found in OBS)")
        return

    _print_table(rpm_map_keys, all_packages_flat, all_found_packages_by_source)


def _print_table(
    source_names: Any,  # Iterable
    all_packages_flat: List[Package],
    grouped_packages: Dict[str, List[Package]],
) -> None:
    # Calculate column widths
    source_name_width = max((len(s) for s in source_names), default=0)
    name_width = (
        max((len(pkg.name) for pkg in all_packages_flat), default=0)
        if all_packages_flat
        else 0
    )
    version_width = (
        max((len(pkg.version) for pkg in all_packages_flat), default=0)
        if all_packages_flat
        else 0
    )
    release_width = (
        max((len(pkg.release) for pkg in all_packages_flat), default=0)
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
    for source_rpm, found_packages in sorted(grouped_packages.items()):
        # Print an empty row for the source rpm heading
        print(
            f"| {source_rpm:<{source_name_width}} | {'':<{name_width}} | {'':<{version_width}} | {'':<{release_width}} |"
        )
        if not found_packages:
            continue

        for pkg in found_packages:
            name = pkg.name
            version = pkg.version
            release = pkg.release
            print(
                f"| {'':<{source_name_width}} | {name:<{name_width}} | {version:<{version_width}} | {release:<{release_width}} |"
            )


def print_iso_results(
    results: List[Tuple[Dict[str, Any], Optional[str], Optional[List[Package]]]],
    rpm_map: Dict[str, List[str]],
) -> None:
    """Prints results for ISO images."""
    for mirrorcache_config, latest_iso_url, iso_packages in results:
        print(f"\n## ISO: {mirrorcache_config['name']}\n")
        if latest_iso_url:
            print(f"URL: {latest_iso_url}\n")
        if iso_packages:
            print_packages_table(rpm_map, iso_packages, label="ISO")
        else:
            print("  (No packages found)")


def print_obs_results(
    results: List[Tuple[Dict[str, Any], Optional[List[Package]]]],
    rpm_map_keys: List[str],
    specs_map: Dict[str, List[str]],
) -> None:
    """Prints results for OBS projects."""
    for obs_config, packages in results:
        print(f"\n## OBS: {obs_config['name']}\n")
        print(f"Project: {obs_config['url']}\n")
        if packages:
            print_obs_packages_table(rpm_map_keys, specs_map, packages)
        else:
            print("  (No packages found)")


def print_git_report(
    git_hashes: Set[str],
    git_config: Optional[GitConfig],
) -> None:
    """Prints the git commit report."""
    if not git_hashes:
        return

    if git_config:
        git_base_url = git_config.url
        print("\n## Git Commits\n")
        for githash in sorted(list(git_hashes)):
            print(f"- {urljoin(git_base_url, f'commit/{githash}')}")
    else:
        logging.warning(
            "No 'git' configuration found in config.yml. Cannot print commit URLs."
        )
