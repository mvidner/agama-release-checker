from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import pytest  # type: ignore
import subprocess

from agama_release_checker.reports.gitea_report import PackagesInGiteaReport
from agama_release_checker.models import Package


@patch(
    "agama_release_checker.reports.gitea_report.PackagesInGiteaReport._run_git_command"
)
@patch("agama_release_checker.reports.gitea_report.Path.exists")
@patch("agama_release_checker.reports.gitea_report.Path.read_text")
@patch("agama_release_checker.reports.gitea_report.ensure_dir")
def test_packages_in_gitea_report(
    mock_ensure_dir, mock_read_text, mock_exists, mock_run_git
):
    # Setup mocks
    # For exists, we want it to return True for the repo and the files
    mock_exists.return_value = True

    # We'll use side_effect for read_text to provide different content for different files
    # The first call is for agama.obsinfo, second for agama.spec
    mock_read_text.side_effect = [
        "version: 1.2.3\n",  # agama.obsinfo
        "Version: 1.2.3\nRelease: 1\n",  # agama.spec
    ]

    # Mock return values for _run_git_command
    # Assumes repo exists (mock_exists=True), so clone/init (first block) are skipped.
    # But now we added fetch/reset/init logic to the else block.
    # 1. fetch (success)
    # 2. reset --hard (success)
    # 3. sparse-checkout init (success)
    # 4. ls-tree (success, returns file list)
    # 5. sparse-checkout set (success)
    mock_run_git.side_effect = [
        (True, ""),  # fetch
        (True, ""),  # reset
        (True, ""),  # init --no-cone
        (True, "agama.obsinfo\nagama.spec\nother.file"),  # ls-tree
        (True, ""),  # sparse-checkout set
    ]

    config = {
        "url": "https://src.suse.de/pool/",
        "name": "ibs-pool",
    }
    # Only one package in rpm_map for this test
    rpm_map = {
        "agama": ["agama"],
    }
    specs_map = {}

    report = PackagesInGiteaReport(config, rpm_map, specs_map)
    _, packages = report.run()

    assert packages is not None
    assert len(packages) == 1
    assert packages[0].name == "agama"
    assert packages[0].version == "1.2.3"
    assert packages[0].release == "1"

    # Verify git sparse-checkout was called with --no-cone and correct files
    # The last call to _run_git_command should be the sparse-checkout set
    mock_run_git.assert_called_with(
        ["git", "sparse-checkout", "set", "--no-cone", "agama.obsinfo", "agama.spec"],
        cwd=ANY,
    )


def test_get_remote_url():
    config = {
        "url": "https://src.suse.de/pool/",
        "name": "ibs-pool",
    }
    report = PackagesInGiteaReport(config, {}, {})
    remote_url = report._get_remote_url("agama")
    assert remote_url == "gitea@src.suse.de:pool/agama.git"
