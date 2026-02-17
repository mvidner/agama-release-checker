import subprocess
from pathlib import Path

# https://docs.python.org/3/library/unittest.mock.html
from unittest.mock import MagicMock, patch

import pytest  # type: ignore

from agama_release_checker.reports.obs_report import PackagesInObsReport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    with open(FIXTURES_DIR / filename, "r") as f:
        return f.read()


@patch("agama_release_checker.reports.obs_report.subprocess.run")
def test_packages_in_obs_report(mock_run):
    # Setup mock responses
    def side_effect(cmd, **kwargs):
        mock_proc = MagicMock()
        mock_proc.returncode = 0

        args = cmd
        if args == ["osc", "version"]:
            mock_proc.stdout = "osc 0.180.0"
        elif args == ["osc", "ls", "systemsmanagement:Agama:Devel"]:
            mock_proc.stdout = load_fixture("osc_ls_project.txt")
        elif args == ["osc", "ls", "systemsmanagement:Agama:Devel", "agama"]:
            mock_proc.stdout = load_fixture("osc_ls_package_agama.txt")
        elif args == [
            "osc",
            "cat",
            "systemsmanagement:Agama:Devel",
            "agama",
            "agama.obsinfo",
        ]:
            mock_proc.stdout = load_fixture("osc_cat_agama_obsinfo.txt")
        elif args == [
            "osc",
            "cat",
            "systemsmanagement:Agama:Devel",
            "agama",
            "agama.spec",
        ]:
            mock_proc.stdout = load_fixture("osc_cat_agama_spec.txt")
        elif args == [
            "osc",
            "ls",
            "systemsmanagement:Agama:Devel",
            "rubygem-agama-yast",
        ]:
            mock_proc.stdout = load_fixture("osc_ls_package_rubygem_agama_yast.txt")
        elif args == [
            "osc",
            "cat",
            "systemsmanagement:Agama:Devel",
            "rubygem-agama-yast",
            "rubygem-agama-yast.spec",
        ]:
            mock_proc.stdout = load_fixture("osc_cat_rubygem_agama_yast_spec.txt")
        elif args == [
            "osc",
            "cat",
            "systemsmanagement:Agama:Devel",
            "rubygem-agama-yast",
            "agama-yast.spec",
        ]:
            mock_proc.stdout = load_fixture("osc_cat_agama_yast_spec.txt")
        else:
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            # Raise CalledProcessError for unknown commands if check=True is used
            if kwargs.get("check"):
                raise subprocess.CalledProcessError(1, cmd)

        return mock_proc

    mock_run.side_effect = side_effect

    config = {
        "url": "https://build.opensuse.org/project/show/systemsmanagement:Agama:Devel",
        "name": "obs-sm-A-Devel",
    }

    rpm_map = {
        "agama": ["agama"],
        "rubygem-agama-yast": ["rubygem-agama-yast", "agama-yast"],
    }

    specs_map = {"rubygem-agama-yast": ["rubygem-agama-yast", "agama-yast"]}

    report = PackagesInObsReport(config, rpm_map, specs_map)
    latest_url, packages = report.run()

    assert latest_url is None
    assert packages is not None
    assert len(packages) == 3  # agama, rubygem-agama-yast, agama-yast

    pkg_map = {p.name: p for p in packages}

    # Check agama (dynamic version from .obsinfo)
    assert "agama" in pkg_map
    assert pkg_map["agama"].version == "19.pre+1558.7e90c6ef1"

    # Check rubygem-agama-yast (from spec)
    assert "rubygem-agama-yast" in pkg_map
    assert pkg_map["rubygem-agama-yast"].version == "19.pre.devel1558.7e90c6ef1"

    # Check agama-yast (from spec)
    assert "agama-yast" in pkg_map
    assert pkg_map["agama-yast"].version == "19.pre.devel1558.7e90c6ef1"


@patch("agama_release_checker.reports.obs_report.subprocess.run")
def test_osc_missing(mock_run):
    mock_run.side_effect = FileNotFoundError("No such file or directory")

    config = {"url": "https://build.opensuse.org/project/show/foo"}
    report = PackagesInObsReport(config, {}, {})
    latest_url, packages = report.run()

    assert packages is None
