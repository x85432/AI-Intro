"""④ Write HANDOFF.md, read it back, and record a human's verification.
Owner: 吳弘叡 x85432."""

from __future__ import annotations

from typing import Optional

from .models import Assumption, DraftResult


def write(result: DraftResult, out_path: str, scope: list[str]) -> None:
    """Write HANDOFF.md.

    Layout: an "AI-drafted, may be incomplete" notice, the scanned scope, status
    counts and the coverage table; then one section per item; then the open
    question for the receiving engineer.
    Test against handoff.fakes.FAKE_RESULT.
    """
    raise NotImplementedError("④ writer.write: to be implemented by x85432")


def parse(path: str) -> list[Assumption]:
    """Read HANDOFF.md back into Assumption objects (write then parse must round-trip)."""
    raise NotImplementedError("④ writer.parse: to be implemented by x85432")


def mark(path: str, item_id: str, status: str, evidence: str,
         evidence_type: Optional[str] = None) -> None:
    """Update one item's status and evidence, noting who changed it and when.

    For humans only: the AI never marks an item verified (CP1 human-AI boundary).
    Reject unknown ids and statuses outside models.STATUSES.
    """
    raise NotImplementedError("④ writer.mark: to be implemented by x85432")
