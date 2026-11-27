"""① Read the files the user chose. Owner: 方騏為 Cactex."""

from __future__ import annotations

from pathlib import Path
import sys

from .models import SourceFile


MAX_FILE_SIZE = 1024 * 1024
_SKIP_DIRECTORIES = {".git", ".venv", "venv", "env", "__pycache__"}


def _display_path(path: Path, project_root: Path) -> str:
    """Use project-relative POSIX paths, or absolute paths for external files."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _report_skip(path: Path, reason: str) -> None:
    print(f"Skipped {path.as_posix()}: {reason}", file=sys.stderr)


def _excluded_directory(path: Path) -> bool:
    return path.name in _SKIP_DIRECTORIES or (path / "pyvenv.cfg").is_file()


def collect(paths: list[str]) -> list[SourceFile]:
    """Walk the given files and folders and return the text files to scan.

    Input:  paths given on the command line, e.g. ["examples/stream_demo"].
    Output: one SourceFile per text file, sorted by path, without duplicates.
    Skip .git, virtualenvs, __pycache__, binary files and very large files,
    and tell the user what was skipped on stderr. Symbolic links are skipped.

    The current working directory is the scan's project root. Paths inside it
    are relative POSIX paths; external paths are absolute POSIX paths. Text is
    UTF-8 (an optional BOM is accepted). Files larger than MAX_FILE_SIZE bytes
    are skipped. Missing explicitly requested paths raise FileNotFoundError;
    individual read/traversal failures are reported and skipped. Empty input
    returns an empty list. Sensitive-content filtering belongs to filters.py.
    """
    project_root = Path.cwd().resolve()
    roots = []
    for raw_path in paths:
        if not raw_path:
            raise ValueError("Input paths must not be empty strings")
        path = Path(raw_path).absolute()
        if not path.exists() and not path.is_symlink():
            raise FileNotFoundError(f"Input path does not exist: {raw_path}")
        roots.append(path)

    files: list[SourceFile] = []
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        try:
            if path.is_symlink():
                _report_skip(path, "symbolic link")
                return
            # Worktrees use a .git marker file instead of a directory.
            if path.name == ".git" or (path.is_dir() and _excluded_directory(path)):
                _report_skip(path, "excluded directory or virtual environment")
                return

            resolved = path.resolve()
            if resolved in visited:
                return
            visited.add(resolved)

            if path.is_dir():
                for child in sorted(path.iterdir()):
                    visit(child)
                return
            if not path.is_file():
                _report_skip(path, "not a regular file or directory")
                return
            if path.stat().st_size > MAX_FILE_SIZE:
                _report_skip(path, f"larger than {MAX_FILE_SIZE} bytes")
                return

            # Bound the read too, in case the file grows after stat().
            with path.open("rb") as source:
                data = source.read(MAX_FILE_SIZE + 1)
            if len(data) > MAX_FILE_SIZE:
                _report_skip(path, f"larger than {MAX_FILE_SIZE} bytes")
                return
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                _report_skip(path, "binary or non-UTF-8 file")
                return
            if any(ord(char) < 32 and char not in "\t\n\r\f" for char in text):
                _report_skip(path, "binary control characters")
                return
            files.append(SourceFile(path=_display_path(path, project_root), text=text))
        except OSError as error:
            _report_skip(path, f"cannot read: {error}")

    for root in roots:
        # Apply exclusions even when a file inside an excluded directory was
        # explicitly selected rather than reached through directory traversal.
        try:
            if any(_excluded_directory(parent) for parent in root.parents):
                _report_skip(root, "inside an excluded directory or virtual environment")
                continue
            if any(parent.is_symlink() for parent in root.parents):
                _report_skip(root, "inside a symbolic link directory")
                continue
        except OSError as error:
            _report_skip(root, f"cannot inspect parent directories: {error}")
            continue
        visit(root)

    return sorted(files, key=lambda source: source.path)
