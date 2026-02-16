import logging
from typing import Dict, Any


class PackagesInObsReport:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run(self) -> None:
        logging.info(f"Processing OBS project: {self.config.get('name')}")
        # Placeholder for future implementation
