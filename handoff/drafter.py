"""③ Ask the LLM to list the assumptions. Owner: 鐘邦郡 bonginn."""

from __future__ import annotations

from typing import Optional

from .models import DraftResult, MockHit, SourceFile


def draft(files: list[SourceFile], hits: list[MockHit],
          spec: Optional[str] = None, fake: bool = False) -> DraftResult:
    """Return the checklist items and the coverage table.

    Input:  the full kept files (with line numbers added in the prompt), the hints
            from ②, and an optional spec text.
    Output: DraftResult(items, coverage). Every boundary x category cell is answered,
            "none_found" included. Items whose file or line does not exist are dropped.
    fake=True returns fixed data without calling the API
    (handoff.fakes.FAKE_RESULT is available for this).
    On a missing API key, a network error or a refusal, raise a clear error and let
    the caller write nothing (README, "what happens when it is wrong").
    """
    raise NotImplementedError("③ drafter.draft: to be implemented by bonginn")
