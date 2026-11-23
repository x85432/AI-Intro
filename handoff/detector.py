"""② Find where outside data enters the code, and where mocks live. No AI here.
Owner: 鄧皓澤 Daniel."""

from __future__ import annotations

from .models import MockHit, SourceFile


def detect(files: list[SourceFile]) -> list[MockHit]:
    """Return hints for ③: one MockHit per data boundary or mock found.

    Input:  the kept files from ①.
    Output: MockHit(file, line, snippet, kind) with kind one of models.KINDS.
    Rule-based (Python `ast`; fall back to text matching on syntax errors).
    Prefer finding too much over missing something: ③ also reads the full files.
    Test against handoff.fakes.FAKE_FILES (expected hits: handoff.fakes.FAKE_HITS).
    """
    raise NotImplementedError("② detector.detect: to be implemented by Daniel")
