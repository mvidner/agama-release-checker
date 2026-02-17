import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from agama_release_checker.reports.obs_requests import ObsSubmitRequestsReport
from agama_release_checker.models import ObsRequest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    with open(FIXTURES_DIR / filename, "r") as f:
        return f.read()


@patch("agama_release_checker.reports.obs_requests.run_cached_command")
def test_obs_submit_requests_report(mock_run_cached):
    # Setup mock responses
    def side_effect(cmd, **kwargs):
        if cmd == ["osc", "version"]:
            return True, "osc 0.180.0"
        elif cmd[0:2] == ["osc", "api"]:
            # Extract package from query
            query = cmd[2]
            if "target/@package='agama'" in query:
                return True, load_fixture("osc_api_search_request_agama.xml")
            else:
                return True, '<collection matches="0"></collection>'
        return False, ""

    mock_run_cached.side_effect = side_effect

    config = {
        "url": "https://build.opensuse.org/project/show/openSUSE:Factory",
        "name": "obs-factory",
        "submit_requests": True,
    }

    rpm_map = {
        "agama": ["agama"],
        "agama-web-ui": ["agama-web-ui"],
    }

    report = ObsSubmitRequestsReport(config, rpm_map)
    _, requests = report.run()

    assert requests is not None
    assert len(requests) == 1
    req = requests[0]
    assert req.id == "1302942"
    assert req.state == "declined"
    assert req.source_project == "systemsmanagement:Agama:Devel"
    assert req.source_package == "agama"
    assert req.target_project == "openSUSE:Factory"
    assert req.target_package == "agama"
    assert "Current development branch of agama" in req.description
    assert req.created_at == "2025-09-05T14:53:29"
    # updated_at corresponds to 'when' attribute in the state element
    assert req.updated_at == "2025-09-05T14:55:46"
