"""① Keep secrets away from the LLM. Owner: 方騏為 Cactex (PR 2)."""

from __future__ import annotations

from .models import SourceFile


def split_sensitive(files: list[SourceFile]) -> tuple[list[SourceFile], list[str]]:
    """Return (kept, skipped_paths).

    A file is skipped whole if its name looks like a secret (.env, *.pem, *.key,
    credentials*.json) or its content does (API_KEY=, private key headers, AKIA...).
    Only `kept` goes on to ② and ③. The rules are recorded in DECISIONS.md.
    """
    raise NotImplementedError("① filters.split_sensitive: to be implemented by Cactex")
