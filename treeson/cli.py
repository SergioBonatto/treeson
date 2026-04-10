"""
Treeson - Directory and GitHub repository structure to JSON converter.

This module provides functionality to convert directory structures and GitHub
repositories into a JSON representation, useful for documentation, analysis,
and tooling purposes.
"""

import argparse
import fnmatch
import json
import os
import sys
from importlib import metadata
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
) -> Dict:
    """
    Convert a directory structure to JSON format.

    Args:
        path: Path to the directory to convert
        config: Configuration object for filtering and options
        current_depth: Current recursion depth (internal use)

    Returns:
        Dictionary representing the directory structure

    Raises:
        DirectoryNotFoundError: If the path doesn't exist
        PermissionError: If the path is not accessible
    """
    if config is None:
        config = TreesonConfig()

    if not path.exists():
        raise DirectoryNotFoundError(f"Directory not found: {path}")

    if not path.is_dir():
        raise TreesonError(f"Path is not a directory: {path}")

    result: Dict[str, Any] = {"files": []}

    # Check max depth
    if config.max_depth is not None and current_depth >= config.max_depth:
        return result

    try:
        # Use os.scandir for better performance
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
                    print(f"Warning: Permission denied accessing {entry.path}", file=sys.stderr)
                    continue
    except PermissionError:
        print(f"Warning: Permission denied accessing {path}", file=sys.stderr)
        return result

    return result


def github_repo_to_json(
    url: str,
    config: Optional[TreesonConfig] = None,
    branch: str = "main"
) -> Dict:
    """
    Convert a GitHub repository structure to JSON format.

    Args:
        url: GitHub repository URL
        config: Configuration object for filtering
        branch: Branch name to fetch (default: main)

    Returns:
        Dictionary representing the repository structure

    Raises:
        GitHubAPIError: If API request fails
        ImportError: If requests library is not installed
    """
    if requests is None:
        raise ImportError(
            "requests library is required for GitHub functionality. "
            "Install with: pip install requests"
        )

    if config is None:
        config = TreesonConfig()

    # Parse GitHub URL
    url_clean = url.rstrip('/').replace('.git', '')
    parts = url_clean.split('/')

    if len(parts) < 2:
        raise GitHubAPIError(f"Invalid GitHub URL format: {url}")

    owner, repo = parts[-2], parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise GitHubAPIError(f"Request timeout for repository: {owner}/{repo}")
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            raise GitHubAPIError(
                f"Repository or branch not found: {owner}/{repo}@{branch}"
            )
        raise GitHubAPIError(f"GitHub API error: {e}")
    except requests.exceptions.RequestException as e:
        raise GitHubAPIError(f"Network error: {e}")

    tree = resp.json().get("tree", [])
    root: Dict = {}

    for node in tree:
        path_parts = node["path"].split("/")

        # Check max depth
        if config.max_depth is not None and len(path_parts) > config.max_depth:
            continue

        # Check if any part should be ignored
        if any(config.should_ignore(part) for part in path_parts):
            continue

        current = root

        # Navigate/create directory structure
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {"files": []}
            current = current[part]

        # Add file or directory
        final_part = path_parts[-1]
        if node["type"] == "blob":
            if "files" not in current:
                current["files"] = []
            current["files"].append(final_part)
        elif node["type"] == "tree":
            if final_part not in current:
                current[final_part] = {"files": []}

    return root


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="treeson",
        description="Convert directory or GitHub repository structure to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Current directory
  %(prog)s /path/to/dir             # Specific directory
  %(prog)s https://github.com/user/repo  # GitHub repository
  %(prog)s -i "*.log" -i temp .     # Ignore additional patterns
  %(prog)s --branch dev github_url  # Specify branch
        """
    )

    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory path or GitHub URL (default: current directory)"
    )

    parser.add_argument(
        "--ignore", "-i",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Additional files/folders to ignore (can be used multiple times)"
    )

    parser.add_argument(
        "--branch", "-b",
        default="main",
        metavar="NAME",
        help="GitHub branch name (default: main)"
    )

    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories"
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        metavar="N",
        help="Maximum directory depth to traverse"
    )

    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write output to file instead of stdout"
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)"
    )

    try:
        version = metadata.version("treeson")
    except metadata.PackageNotFoundError:
        version = "unknown"

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version}"
    )

    return parser


def main() -> int:
    """
    Main entry point for the CLI.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Build configuration
    config = TreesonConfig(
        ignores=set(DEFAULT_IGNORES.union(args.ignore)),
        include_hidden=args.include_hidden,
        max_depth=args.max_depth
    )

    try:
        # Determine if target is URL or path
        if args.target.startswith(("http://", "https://")):
            data = github_repo_to_json(args.target, config, args.branch)
        else:
            target_path = Path(args.target).resolve()
            data = dir_to_json(target_path, config)

        # Format JSON output
        indent = None if args.compact else 2
        output = json.dumps(data, indent=indent, ensure_ascii=False)

        # Write output
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"Output written to: {output_path}", file=sys.stderr)
        else:
            print(output)

        return 0

    except TreesonError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if "--debug" in sys.argv:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
