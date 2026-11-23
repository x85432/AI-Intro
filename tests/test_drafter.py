"""Tests for ③ drafter. None of them call the real API."""

from types import SimpleNamespace

import pytest

from handoff import drafter
from handoff.drafter import DrafterError, _Cell, _Item, _Output
from handoff.fakes import FAKE_FILES, FAKE_HITS, FAKE_RESULT
from handoff.models import CATEGORIES

TREND = "examples/stream_demo/trend.py"


def item(key="k1", file=TREND, line=8, category="timing_batching"):
    return _Item(key=key, assumption="一次只來一筆", file=file, line=line, category=category,
                 question="q", impact="i", evidence_wanted="e",
                 verify_type="inspect_sample", verify_step="s")


# ------------------------------------------------------------------- fake mode

def test_fake_returns_a_copy_of_the_fake_result():
    result = drafter.draft(FAKE_FILES, FAKE_HITS, fake=True)
    assert result == FAKE_RESULT
    result.items[0].status = "verified"          # changing it must not touch the shared fake
    assert FAKE_RESULT.items[0].status == "uncertain"


def test_fake_needs_no_api_key(no_key):
    assert drafter.draft([], [], fake=True).items


# ---------------------------------------------------------------------- prompt

def test_prompt_numbers_lines_and_lists_hints_and_spec():
    prompt = drafter.build_prompt(FAKE_FILES, FAKE_HITS, spec="資料每秒一筆")
    assert "   8 |     def update(self, record):" in prompt
    assert "examples/stream_demo/simulator.py:10 [simulation] for row in rows:" in prompt
    assert "<spec>\n資料每秒一筆\n</spec>" in prompt
    for category in CATEGORIES:
        assert category in prompt


def test_prompt_without_hits_asks_the_model_to_find_boundaries():
    assert "find them yourself" in drafter.build_prompt(FAKE_FILES, [])


def test_boundaries_are_unique_and_in_order():
    hits = FAKE_HITS + FAKE_HITS[:1]
    assert drafter.boundaries_from_hits(hits) == [
        "examples/stream_demo/simulator.py:8", "examples/stream_demo/simulator.py:10"]


# ------------------------------------------------------------ checking output

def test_items_are_numbered_and_linked_to_coverage():
    out = _Output(items=[item("x"), item("y", line=14, category="null")],
                  coverage=[_Cell(boundary=f"{TREND}:8", category="null",
                                  result="found", item_key="y"),
                            _Cell(boundary=f"{TREND}:8", category="units_sign",
                                  result="none_found")])
    result = drafter.to_result(out, FAKE_FILES)
    assert [i.id for i in result.items] == ["A-01", "A-02"]
    assert all(i.status == "uncertain" and i.added_by == "ai" for i in result.items)
    assert result.coverage[0].item_id == "A-02"
    assert result.coverage[1].item_id is None


@pytest.mark.parametrize("bad", [item(file="not/an/input.py"), item(line=999), item(line=0)])
def test_items_pointing_nowhere_are_dropped(bad):
    out = _Output(items=[bad], coverage=[
        _Cell(boundary=f"{TREND}:8", category="timing_batching", result="found", item_key="k1")])
    result = drafter.to_result(out, FAKE_FILES)
    assert result.items == []
    assert result.coverage == []     # a cell must not point at a dropped item


def test_duplicate_keys_and_cells_are_dropped():
    out = _Output(items=[item("k1"), item("k1", line=9)],
                  coverage=[_Cell(boundary="b:1", category="null", result="none_found")] * 2)
    result = drafter.to_result(out, FAKE_FILES)
    assert len(result.items) == 1
    assert len(result.coverage) == 1


# ------------------------------------------------------------------- failures

@pytest.fixture
def no_key(monkeypatch):
    for var in drafter.API_KEY_VARS:
        monkeypatch.delenv(var, raising=False)


def test_missing_api_key_is_a_clear_error(no_key):
    with pytest.raises(DrafterError, match="GEMINI_API_KEY"):
        drafter.draft(FAKE_FILES, FAKE_HITS)


def test_no_files_is_an_error():
    with pytest.raises(DrafterError, match="no files"):
        drafter.draft([], [])


def test_too_large_input_is_refused(monkeypatch):
    monkeypatch.setattr(drafter, "MAX_PROMPT_CHARS", 100)
    with pytest.raises(DrafterError, match="too large"):
        drafter.draft(FAKE_FILES, FAKE_HITS)


def gemini_response(text=None, finish_reason="STOP", block_reason=None, candidates=True):
    return SimpleNamespace(
        text=text,
        prompt_feedback=SimpleNamespace(block_reason=block_reason),
        candidates=[SimpleNamespace(finish_reason=finish_reason)] if candidates else [],
    )


def fake_client(response=None, error=None, calls=None):
    def generate_content(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        if error is not None:
            raise error
        return response
    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


@pytest.mark.parametrize("response, message", [
    (gemini_response(block_reason="PROHIBITED_CONTENT"), "refused"),
    (gemini_response(text="{}", finish_reason="SAFETY"), "refused"),
    (gemini_response(text='{"items": [', finish_reason="MAX_TOKENS"), "cut off"),
    (gemini_response(candidates=False), "no answer"),
    (gemini_response(text=""), "empty"),
    (gemini_response(text='{"items": "oops"}'), "expected format"),
])
def test_bad_model_answers_raise(monkeypatch, with_key, response, message):
    monkeypatch.setattr(drafter, "_make_client", lambda: fake_client(response))
    with pytest.raises(DrafterError, match=message):
        drafter.draft(FAKE_FILES, FAKE_HITS)


def test_network_error_is_a_clear_error(monkeypatch, with_key):
    monkeypatch.setattr(drafter, "_make_client",
                        lambda: fake_client(error=ConnectionError("no route to host")))
    with pytest.raises(DrafterError, match="could not reach"):
        drafter.draft(FAKE_FILES, FAKE_HITS)


def test_successful_call_uses_model_schema_and_system_prompt(monkeypatch, with_key):
    monkeypatch.setenv("HANDOFF_MODEL", "some-model")
    calls = []
    out = _Output(items=[item()], coverage=[])
    monkeypatch.setattr(drafter, "_make_client",
                        lambda: fake_client(gemini_response(text=out.model_dump_json()), calls=calls))
    result = drafter.draft(FAKE_FILES, FAKE_HITS)
    assert result.items[0].id == "A-01"
    assert calls[0]["model"] == "some-model"
    config = calls[0]["config"]
    assert config.response_schema is _Output
    assert config.response_mime_type == "application/json"
    assert config.system_instruction == drafter.SYSTEM_PROMPT