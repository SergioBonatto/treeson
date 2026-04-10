"""
Core logic for Treeson - Directory and GitHub repository structure conversion.
"""

import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass, field

try:
    import requests
except ImportError:
    requests = None  # type: ignore


DEFAULT_IGNORES = frozenset({
    ".git",
    "__pycache__",
    ".DS_Store",
    "node_modules",
    "venv",
    ".venv",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    "*.egg-info",
})


@dataclass
class TreesonConfig:
    """Configuration for treeson operations."""
    ignores: Set[str] = field(default_factory=lambda: set(DEFAULT_IGNORES))
    include_hidden: bool = False
    max_depth: Optional[int] = None

    def should_ignore(self, name: str) -> bool:
        """Check if a file or directory should be ignored."""
        if not self.include_hidden and name.startswith('.'):
            return True
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.ignores)


class TreesonError(Exception):
    """Base exception for treeson operations."""
    pass


class DirectoryNotFoundError(TreesonError):
    """Raised when target directory doesn't exist."""
    pass


class GitHubAPIError(TreesonError):
    """Raised when GitHub API request fails."""
    pass


def dir_to_json(
    path: Path,
    config: Optional[TreesonConfig] = None,
    current_depth: int = 0
) -> Dict[str, Any]:
    """
    Convert a directory structure to JSON format.
    """
    if config is None:
        config = TreesonConfig()

    if not path.exists():
        raise DirectoryNotFoundError(f"Directory not found: {path}")

    if not path.is_dir():
        raise TreesonError(f"Path is not a directory: {path}")

    result: Dict[str, Any] = {"files": []}

    if config.max_depth is not None and current_depth >= config.max_depth:
        return result

    try:
        with os.scandir(path) as it:
            entries = sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))
            
            for entry in entries:
                if config.should_ignore(entry.name):
                    continue

                try:
                    if entry.is_file():
                        result["files"].append(entry.name)
                    elif entry.is_dir():
                        result[entry.name] = dir_to_json(
                            Path(entry.path), config, current_depth + 1
                        )
                except PermissionError:
                    import sys
                    print(f"Warning: Permission denied accessing {entry.path}", file=sys.stderr)
                    continue
    except PermissionError:
        import sys
        print(f"Warning: Permission denied accessing {path}", file=sys.stderr)
        return result

    return result


def github_repo_to_json(
    url: str,
    config: Optional[TreesonConfig] = None,
    branch: str = "main"
) -> Dict[str, Any]:
    """
    Convert a GitHub repository structure to JSON format.
    """
    if requests is None:
        raise ImportError(
            "requests library is required for GitHub functionality. "
            "Install with: pip install requests"
        )

    if config is None:
        config = TreesonConfig()

    url_clean = url.rstrip('/').replace('.git', '')
    parts = url_clean.split('/')

    if len(parts) < 2:
        raise GitHubAPIError(f"Invalid GitHub URL format: {url}")

    owner, repo = parts[-2], parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        if isinstance(e, requests.exceptions.HTTPError) and resp.status_code == 404:
            raise GitHubAPIError(f"Repository or branch not found: {owner}/{repo}@{branch}")
        raise GitHubAPIError(f"GitHub API error: {e}")

    tree = resp.json().get("tree", [])
    root: Dict[str, Any] = {}

    for node in tree:
        path_parts = node["path"].split("/")

        if config.max_depth is not None and len(path_parts) > config.max_depth:
            continue

        if any(config.should_ignore(part) for part in path_parts):
            continue

        current = root
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {"files": []}
            current = current[part]

        final_part = path_parts[-1]
        if node["type"] == "blob":
            if "files" not in current:
                current["files"] = []
            current["files"].append(final_part)
        elif node["type"] == "tree":
            if final_part not in current:
                current[final_part] = {"files": []}

    return root
