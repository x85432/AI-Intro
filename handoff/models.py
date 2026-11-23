"""Shared data formats passed between the four pieces of the pipeline.

    ① inputs.collect  -> list[SourceFile]  -> ② detector.detect -> list[MockHit]
    ③ drafter.draft(files, hits, spec)    -> DraftResult      -> ④ writer.write -> HANDOFF.md

Everyone imports from here. To add, rename or remove a field: say so in Discord first,
open a PR that changes only this file, and record the decision in DECISIONS.md.
See docs/CP2_PLAN.md, section 1, for the full contract and examples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, get_args

Kind = Literal["mock", "stub", "fixture", "sample_data", "simulation", "boundary"]
Category = Literal["format", "null", "units_sign", "timing_batching",
                   "ordering", "volume", "errors"]
VerifyType = Literal["ask_owner", "inspect_sample", "run_check"]
Status = Literal["uncertain", "verified", "mismatch"]
CoverageResult = Literal["found", "missing_handling", "none_found"]
AddedBy = Literal["ai", "human"]

# Allowed values as tuples, for runtime checks (dataclasses do not enforce Literal).
KINDS = get_args(Kind)
CATEGORIES = get_args(Category)
VERIFY_TYPES = get_args(VerifyType)
STATUSES = get_args(Status)
COVERAGE_RESULTS = get_args(CoverageResult)


@dataclass
class SourceFile:
    """One file the user chose to scan. Produced by ①, read by ② and ③."""
    path: str           # e.g. "examples/stream_demo/trend.py"
    text: str           # the whole file content


@dataclass
class MockHit:
    """A place where outside data enters the code, or where a mock lives.

    Produced by ②. Only a hint for ③, which still reads the full files.
    """
    file: str
    line: int           # 1-based
    snippet: str        # the source line (or lines) as written
    kind: Kind


@dataclass
class Assumption:
    """One item of HANDOFF.md. Produced by ③, written by ④, updated by `mark`."""
    id: str                     # "A-01"
    assumption: str             # what the code assumes about the real environment
    file: str
    line: int                   # 1-based
    category: Category
    question: str               # what to ask the receiving engineer (fixed format, plan §1.4)
    impact: str                 # what breaks if the assumption is wrong
    evidence_wanted: str        # e.g. "a sample of real data after a reconnect"
    verify_type: VerifyType
    verify_step: str            # a concrete action, never just "check it"
    status: Status = "uncertain"
    evidence: str = ""          # filled in by a human with `mark`
    added_by: AddedBy = "ai"


@dataclass
class CoverageCell:
    """One cell of the coverage table: one data boundary x one category."""
    boundary: str                   # "examples/stream_demo/trend.py:30"
    category: Category
    result: CoverageResult
    item_id: Optional[str] = None   # the matching Assumption.id, if any


@dataclass
class DraftResult:
    """Everything ③ hands to ④ (and to the evaluation runner)."""
    items: list[Assumption]
    coverage: list[CoverageCell] = field(default_factory=list)
