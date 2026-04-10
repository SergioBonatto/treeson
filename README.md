# Treeson

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Treeson is a command-line tool that converts directory structures and GitHub repositories into JSON format. Perfect for documentation, analysis, and tooling purposes.

## Features

- **Directory to JSON**: Convert local directory structures to structured JSON
- **GitHub Repository Support**: Fetch and convert GitHub repository structures
- **Smart Filtering**: Built-in ignore patterns for common files/folders
- **Highly Configurable**: Custom ignore patterns, depth limits, and hidden file handling
- **Multiple Output Options**: stdout, file output, compact or pretty-printed JSON
- **Fast and Lightweight**: Minimal dependencies, efficient processing

## Installation

### Using uv (Recommended)

To install as a global tool:

```bash
uv tool install git+https://github.com/SergioBonatto/treeson.git
```

To add as a dependency in another project:

```bash
uv add git+https://github.com/SergioBonatto/treeson.git
```

### From source

```bash
git clone https://github.com/SergioBonatto/treeson.git
cd treeson
uv sync
```

## Quick Start

### Convert current directory to JSON

```bash
treeson
```

### Convert specific directory

```bash
treeson /path/to/directory
```

### Convert GitHub repository

```bash
treeson https://github.com/user/repository
```

### Save output to file

```bash
treeson . --output structure.json
```

## Usage

```
treeson [TARGET] [OPTIONS]
```

### Arguments

- `TARGET`: Directory path or GitHub URL (default: current directory)

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--ignore PATTERN` | `-i` | Additional files/folders to ignore (can be used multiple times) |
| `--branch NAME` | `-b` | GitHub branch name (default: main) |
| `--include-hidden` | | Include hidden files and directories |
| `--max-depth N` | | Maximum directory depth to traverse |
| `--output FILE` | `-o` | Write output to file instead of stdout |
| `--compact` | | Output compact JSON (no indentation) |
| `--version` | | Show version and exit |

## Output Format

The tool generates a JSON structure where:
- Directories are represented as objects with nested structure
- Files are listed in a `"files"` array within each directory
- The structure preserves the hierarchical organization

### Example output

```json
{
  "files": ["main.py", "README.md"],
  "src": {
    "files": ["__init__.py", "utils.py"],
    "models": {
      "files": ["user.py", "base.py"]
    }
  },
  "tests": {
    "files": ["test_main.py"]
  }
}
```

## Configuration

### Programmatic Usage

```python
from treeson import dir_to_json, TreesonConfig
from pathlib import Path

# Custom configuration
config = TreesonConfig(
    ignores={"temp", "logs", "*.tmp"},
    include_hidden=True,
    max_depth=5
)

# Convert directory
result = dir_to_json(Path("/path/to/dir"), config)
print(result)
```

### GitHub API Usage

```python
from treeson import github_repo_to_json, TreesonConfig

# Convert GitHub repository
config = TreesonConfig(ignores={"docs", "examples"})
result = github_repo_to_json(
    "https://github.com/user/repo",
    config,
    branch="main"
)
print(result)
```

## Requirements

- Python 3.8+
- `requests` library (included as dependency)

## Development

### Setup development environment

We recommend using [uv](https://github.com/astral-sh/uv) for development:

```bash
git clone https://github.com/SergioBonatto/treeson.git
cd treeson
uv sync
```

### Running tests

```bash
uv run pytest
```

### Code formatting

```bash
uv run black treeson/
uv run isort treeson/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v0.1.2
- **Architectural Refactor**: Separated core logic from CLI interface.
- **Improved Package Structure**: Better programmatic API access via `__init__.py`.
- **Enhanced Hygiene**: Improved `.gitignore` and removed redundant `main.py`.
- **Modern Tooling**: Full support for `uv` and dynamic versioning.

### v0.1.1
- Initial release
- Basic directory to JSON conversion
- GitHub repository support
- CLI interface with comprehensive options
- Smart ignore patterns

---

Made with care by [Sergio Bonatto](https://github.com/SergioBonatto)
