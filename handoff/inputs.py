"""① Read the files the user chose. Owner: 方騏為 Cactex."""

from __future__ import annotations

from .models import SourceFile


def collect(paths: list[str]) -> list[SourceFile]:
    """Walk the given files and folders and return the text files to scan.

    Input:  paths given on the command line, e.g. ["examples/stream_demo"].
    Output: one SourceFile per text file, sorted by path.
    Skip .git, virtualenvs, __pycache__, binary files and very large files,
    and tell the user what was skipped.
    """
    raise NotImplementedError("① inputs.collect: to be implemented by Cactex")
