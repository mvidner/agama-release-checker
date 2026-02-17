from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Package:
    name: str
    version: str
    release: str
    arch: str


@dataclass
class StageConfig:
    type: str
    name: str
    url: str


@dataclass
class MirrorcacheConfig(StageConfig):
    files: List[str] = field(default_factory=list)


@dataclass
class GitConfig(StageConfig):
    pass


@dataclass
class AppConfig:
    stages: List[Dict[str, Any]]
    rpms: Dict[str, List[str]]
    specs: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def mirrorcache_configs(self) -> List[MirrorcacheConfig]:
        return [
            MirrorcacheConfig(**s)
            for s in self.stages
            if s.get("type") == "mirrorcache"
        ]

    @property
    def git_config(self) -> Optional[GitConfig]:
        for stage in self.stages:
            if stage.get("type") == "git":
                return GitConfig(**stage)
        return None
