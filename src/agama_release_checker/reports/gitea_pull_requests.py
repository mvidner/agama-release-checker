import json
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from agama_release_checker.models import GiteaPullRequest


class GiteaPullRequestsReport:
    def __init__(
        self,
        config: Dict[str, Any],
        rpm_map: Dict[str, List[str]],
        no_cache: bool = False,
    ):
        self.config = config
        self.rpm_map = rpm_map
        self.no_cache = no_cache

    def _get_repo_path(self, package_name: str) -> str:
        base_url = self.config.get("url", "").rstrip("/")
        # https://src.suse.de/pool/ -> pool/package_name
        parsed = urlparse(base_url)
        path = parsed.path.strip("/")
        return f"{path}/{package_name}"

    def _get_login(self) -> str:
        url = self.config.get("url", "")
        parsed = urlparse(url)
        return parsed.netloc

    def _fetch_prs(self, package_name: str) -> List[GiteaPullRequest]:
        repo = self._get_repo_path(package_name)
        login = self._get_login()
        branch = self.config.get("branch")

        cmd = [
            "tea",
            "pr",
            "--login",
            login,
            "--repo",
            repo,
            "--output",
            "json",
            "-f",
            "index,state,author,url,title,mergeable,base,created,updated,comments",
        ]

        logging.debug(f"Executing tea command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            data = json.loads(result.stdout)
            prs = []
            for item in data:
                # Filter by branch if specified
                if branch and item.get("base") != branch:
                    continue

                prs.append(
                    GiteaPullRequest(
                        index=item.get("index", ""),
                        state=item.get("state", ""),
                        author=item.get("author", ""),
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        mergeable=item.get("mergeable") == "true",
                        base=item.get("base", ""),
                        created_at=item.get("created", ""),
                        updated_at=item.get("updated", ""),
                        comments=item.get("comments", "0"),
                    )
                )
            return prs
        except subprocess.CalledProcessError as e:
            # If repo doesn't exist or other error, just log and return empty
            logging.debug(f"Tea command failed for {repo}: {e.stderr.strip()}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode tea output for {repo}: {e}")
            return []

    def run(self) -> Tuple[None, List[GiteaPullRequest]]:
        logging.info(f"Processing Gitea pull requests for: {self.config.get('name')}")
        all_prs: List[GiteaPullRequest] = []
        for package_name in self.rpm_map.keys():
            prs = self._fetch_prs(package_name)
            all_prs.extend(prs)
        return None, all_prs
