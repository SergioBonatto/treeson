"""
Treeson - Convert directory structures and GitHub repositories to JSON format.
"""

__version__ = "0.1.2"

from treeson.core import (
    TreesonConfig,
    TreesonError,
    DirectoryNotFoundError,
    GitHubAPIError,
    dir_to_json,
    github_repo_to_json,
    DEFAULT_IGNORES,
)

__all__ = [
    "TreesonConfig",
    "TreesonError",
    "DirectoryNotFoundError",
    "GitHubAPIError",
    "dir_to_json",
    "github_repo_to_json",
    "DEFAULT_IGNORES",
]
