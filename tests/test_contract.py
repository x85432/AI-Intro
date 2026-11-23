"""Checks that the shared formats, the fake data and the function signatures agree.

If one of these fails after you change models.py or a function signature, the
interface changed: tell the team and record it in DECISIONS.md (plan §5).
"""

import inspect

from handoff import detector, drafter, filters, inputs, writer
from handoff.fakes import FAKE_FILES, FAKE_HITS, FAKE_RESULT
from handoff.models import (CATEGORIES, COVERAGE_RESULTS, KINDS, STATUSES,
                            VERIFY_TYPES)


def params(func):
    return list(inspect.signature(func).parameters)


def test_function_signatures_match_the_plan():
    assert params(inputs.collect) == ["paths"]
    assert params(filters.split_sensitive) == ["files"]
    assert params(detector.detect) == ["files"]
    assert params(drafter.draft) == ["files", "hits", "spec", "fake"]
    assert params(writer.write) == ["result", "out_path", "scope"]
    assert params(writer.parse) == ["path"]
    assert params(writer.mark) == ["path", "item_id", "status", "evidence", "evidence_type"]


def test_fake_hits_point_into_fake_files():
    lines = {f.path: f.text.splitlines() for f in FAKE_FILES}
    for hit in FAKE_HITS:
        assert hit.kind in KINDS
        assert hit.file in lines
        assert 1 <= hit.line <= len(lines[hit.file])
        assert hit.snippet.strip() in lines[hit.file][hit.line - 1]


def test_fake_items_use_allowed_values_and_real_lines():
    lines = {f.path: f.text.splitlines() for f in FAKE_FILES}
    ids = [item.id for item in FAKE_RESULT.items]
    assert len(ids) == len(set(ids)), "item ids must be unique"
    for item in FAKE_RESULT.items:
        assert item.category in CATEGORIES
        assert item.verify_type in VERIFY_TYPES
        assert item.status in STATUSES
        assert item.added_by in ("ai", "human")
        assert item.file in lines
        assert 1 <= item.line <= len(lines[item.file])
        assert item.question and item.verify_step


def test_coverage_cells_point_to_existing_items():
    ids = {item.id for item in FAKE_RESULT.items}
    for cell in FAKE_RESULT.coverage:
        assert cell.category in CATEGORIES
        assert cell.result in COVERAGE_RESULTS
        if cell.result == "none_found":
            assert cell.item_id is None
        else:
            assert cell.item_id in ids
