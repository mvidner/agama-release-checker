import logging
import subprocess
import sys
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import fnmatch


def find_iso_urls(base_url: str, patterns: List[str]) -> List[str]:
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


def download_file(url: str, destination_path: Path) -> bool:
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
