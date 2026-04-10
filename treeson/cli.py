import argparse
import json
import sys
from pathlib import Path

from treeson import (
    DEFAULT_IGNORES,
    TreesonConfig,
    TreesonError,
    dir_to_json,
    github_repo_to_json,
    __version__,
)

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
        "--include-hidden", "-H",
        action="store_true",
        help="Include hidden files and directories"
    )

    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        metavar="N",
        help="Maximum directory depth to traverse"
    )

    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write output to file instead of stdout"
    )

    output_format = parser.add_mutually_exclusive_group()
    output_format.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Output compact JSON (no indentation)"
    )

    output_format.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Output pretty-printed JSON (indent=2)"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    config = TreesonConfig(
        ignores=set(DEFAULT_IGNORES.union(args.ignore)),
        include_hidden=args.include_hidden,
        max_depth=args.max_depth
    )

    try:
        if args.target.startswith(("http://", "https://")):
            data = github_repo_to_json(args.target, config, args.branch)
        else:
            target_path = Path(args.target).resolve()
            data = dir_to_json(target_path, config)

        indent = None if args.compact else 2
        output = json.dumps(data, indent=indent, ensure_ascii=False)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"Output written to: {output_path}", file=sys.stderr)
        elif args.pretty:
            from pygments import highlight
            from pygments.lexers import JsonLexer
            from pygments.formatters import TerminalFormatter
            sys.stdout.write(highlight(output, JsonLexer(), TerminalFormatter()))
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
        return 1

if __name__ == "__main__":
    sys.exit(main())
