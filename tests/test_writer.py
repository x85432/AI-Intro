"""Tests for ④ writer.write and writer.parse (format: DECISIONS.md, 2026-11-24)."""

import dataclasses

import pytest

from handoff import writer
from handoff.fakes import FAKE_RESULT
from handoff.models import Assumption, DraftResult

SCOPE = ["examples/stream_demo/simulator.py", "examples/stream_demo/trend.py"]


def write_to(tmp_path, result=FAKE_RESULT):
    out = tmp_path / "HANDOFF.md"
    writer.write(result, str(out), SCOPE)
    return out


def test_write_then_parse_round_trips_fake_result(tmp_path):
    out = write_to(tmp_path)
    assert writer.parse(str(out)) == FAKE_RESULT.items


def test_round_trip_keeps_marked_items_hand_added_items_and_tricky_text(tmp_path):
    items = [
        dataclasses.replace(FAKE_RESULT.items[0], status="mismatch",
                            evidence="撈 11/25 斷線後的資料：同一次推送 120 筆 | 見 evidence/A-01.json"),
        Assumption(
            id="H-01", assumption="ts 是台灣時間 **不是 UTC**",
            file="examples/stream_demo/trend.py", line=9, category="format",
            question="### 這不是標題 - **status**: verified", impact="時間軸會差 8 小時",
            evidence_wanted="一筆真實資料的 ts", verify_type="ask_owner",
            verify_step="問雲端團隊 ts 用哪個時區", added_by="human"),
    ]
    out = write_to(tmp_path, DraftResult(items=items))
    assert writer.parse(str(out)) == items


def test_line_breaks_become_spaces(tmp_path):
    item = dataclasses.replace(FAKE_RESULT.items[1], impact="遇到 null 時\n  相減會直接丟出錯誤\n")
    out = write_to(tmp_path, DraftResult(items=[item]))
    [parsed] = writer.parse(str(out))
    assert parsed.impact == "遇到 null 時 相減會直接丟出錯誤"


def test_layout_notice_coverage_matrix_items_appendix(tmp_path):
    text = write_to(tmp_path).read_text(encoding="utf-8")
    assert "AI 草擬，可能不完整" in text
    assert "- 狀態：uncertain 3｜verified 0｜mismatch 0" in text
    assert ("| examples/stream_demo/trend.py:8 | 未檢查 | A-02 | 檢查過，沒發現 | A-01 "
            "| 未檢查 | 未檢查 | 未檢查 |") in text
    assert "| 沒有處理（A-03） |" in text
    assert "⚠" not in text
    assert text.index("## 涵蓋表") < text.index("## 項目") < text.index("## 附錄")
    assert "開放問題" not in text


def test_parse_reports_every_mistake_in_a_hand_added_item(tmp_path):
    out = write_to(tmp_path)
    hand_added = "\n".join([
        "### H-01 · timezone · examples/stream_demo/trend.py:9",
        "",
        "**我的假設**：ts 是台灣時間",
        "**問題**：ts 用哪個時區？",
        "**請給例子**：一筆真實資料",
        "**影響**：時間軸會差 8 小時",
        "",
        "- **verify_type**: ask_owner",
        "- **staus**: uncertain",
        "- **evidence**: 第一行",
        "第二行",
        "- **added_by**: human",
        "",
    ])
    text = out.read_text(encoding="utf-8").replace("## 附錄", hand_added + "\n## 附錄")
    out.write_text(text, encoding="utf-8")
    lines = text.splitlines()

    with pytest.raises(writer.HandoffFormatError) as info:
        writer.parse(str(out))
    errors = info.value.errors
    staus_line = lines.index("- **staus**: uncertain") + 1
    stray_line = lines.index("第二行") + 1
    assert any(f"第 {staus_line} 行" in e and "status" in e for e in errors)  # typo, with a hint
    assert any(f"第 {stray_line} 行" in e and "同一行" in e for e in errors)  # value on two lines
    assert any("timezone" in e for e in errors)                              # unknown category
    assert any("verify_step" in e for e in errors)                           # missing field
    assert all("H-01" in e for e in errors)


def test_parse_rejects_id_prefix_that_disagrees_with_added_by(tmp_path):
    out = write_to(tmp_path)
    text = out.read_text(encoding="utf-8").replace("- **added_by**: ai", "- **added_by**: human", 1)
    out.write_text(text, encoding="utf-8")
    with pytest.raises(writer.HandoffFormatError, match="A-01"):
        writer.parse(str(out))


def test_write_refuses_data_parse_would_reject_and_writes_nothing(tmp_path):
    bad = dataclasses.replace(FAKE_RESULT.items[0], question="")
    with pytest.raises(writer.HandoffFormatError):
        writer.write(DraftResult(items=[bad]), str(tmp_path / "HANDOFF.md"), SCOPE)
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------- mark

def test_mark_rejects_a_status_outside_the_allowed_list(tmp_path):
    out = write_to(tmp_path)
    before = out.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="uncertain, verified, mismatch"):
        writer.mark(str(out), "A-01", "done", "撈 11/25 資料，一次 120 筆")
    assert out.read_text(encoding="utf-8") == before


def test_mark_rejects_an_unknown_id_and_lists_the_existing_ones(tmp_path):
    out = write_to(tmp_path)
    before = out.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="找不到 A-09，現有的是：A-01、A-02、A-03"):
        writer.mark(str(out), "A-09", "mismatch", "撈 11/25 資料，一次 120 筆")
    assert out.read_text(encoding="utf-8") == before


def test_mark_refuses_a_malformed_file(tmp_path):
    out = write_to(tmp_path)
    text = out.read_text(encoding="utf-8").replace("- **status**: uncertain", "- **staus**: uncertain", 1)
    out.write_text(text, encoding="utf-8")
    with pytest.raises(writer.HandoffFormatError):
        writer.mark(str(out), "A-01", "mismatch", "撈 11/25 資料，一次 120 筆")
    assert out.read_text(encoding="utf-8") == text


GOOD_EVIDENCE = "撈 11/25 斷線後的資料：同一次推送 120 筆"


@pytest.mark.parametrize("status", ["verified", "mismatch"])
def test_mark_needs_a_type_and_evidence_for_verified_and_mismatch(tmp_path, status):
    out = write_to(tmp_path)
    with pytest.raises(ValueError, match="--type"):
        writer.mark(str(out), "A-01", status, GOOD_EVIDENCE)
    with pytest.raises(ValueError, match="要附證據"):
        writer.mark(str(out), "A-01", status, "  ", evidence_type="inspect_sample")


@pytest.mark.parametrize("empty", ["OK", "ok!", "沒問題。", "LGTM", "確認過", "looks good"])
def test_mark_rejects_evidence_that_says_nothing(tmp_path, empty):
    out = write_to(tmp_path)
    with pytest.raises(ValueError, match="不算證據"):
        writer.mark(str(out), "A-01", "mismatch", empty, evidence_type="inspect_sample")


def test_mark_rejects_an_unknown_type(tmp_path):
    out = write_to(tmp_path)
    with pytest.raises(ValueError, match="ask_owner, inspect_sample, run_check"):
        writer.mark(str(out), "A-01", "mismatch", GOOD_EVIDENCE, evidence_type="guess")


def test_evidence_text_puts_the_type_in_front_and_keeps_one_line():
    text = writer._evidence_text("mismatch", "沒問題，但是\n同一次推送 120 筆", "inspect_sample")
    assert text == "[inspect_sample] 沒問題，但是 同一次推送 120 筆"
    assert writer._evidence_text("uncertain", "", None) == ""


def test_mark_changes_only_status_evidence_and_the_counts(tmp_path):
    out = write_to(tmp_path)
    before = out.read_text(encoding="utf-8").split("\n")
    writer.mark(str(out), "A-01", "mismatch", GOOD_EVIDENCE, evidence_type="inspect_sample")
    after = out.read_text(encoding="utf-8").split("\n")

    changed = {(b, a) for b, a in zip(before, after) if b != a}
    assert len(before) == len(after)
    assert changed == {
        ("- 狀態：uncertain 3｜verified 0｜mismatch 0", "- 狀態：uncertain 2｜verified 0｜mismatch 1"),
        ("- **status**: uncertain", "- **status**: mismatch"),
        ("- **evidence**:", f"- **evidence**: [inspect_sample] {GOOD_EVIDENCE}"),
    }
    a01, a02, a03 = writer.parse(str(out))
    assert (a01.status, a01.evidence) == ("mismatch", f"[inspect_sample] {GOOD_EVIDENCE}")
    assert [a02, a03] == FAKE_RESULT.items[1:]


def test_mark_keeps_hand_added_items_and_other_edits(tmp_path):
    out = write_to(tmp_path)
    hand_added = "\n".join([
        "### H-01 · format · examples/stream_demo/trend.py:9", "",
        "**我的假設**：ts 是台灣時間", "", "**問題**：ts 用哪個時區？", "",
        "**請給例子**：一筆真實資料的 ts", "", "**影響**：時間軸會差 8 小時", "",
        "- **verify_type**: ask_owner", "- **verify_step**: 問雲端團隊 ts 用哪個時區",
        "- **status**: uncertain", "- **evidence**:", "- **added_by**: human", "", ""])
    text = out.read_text(encoding="utf-8").replace("## 附錄", hand_added + "## 附錄")
    text = text.replace("## 涵蓋表", "## 涵蓋表\n\n作者補充：simulator.py 只在測試時用。")
    out.write_text(text, encoding="utf-8")

    writer.mark(str(out), "H-01", "mismatch", "雲端團隊 11/26 在 Discord 回覆：ts 是 UTC",
                evidence_type="ask_owner")
    after = out.read_text(encoding="utf-8")
    assert "作者補充：simulator.py 只在測試時用。" in after
    assert "| 沒有處理（A-03） |" in after
    [h01] = [item for item in writer.parse(str(out)) if item.id == "H-01"]
    assert (h01.status, h01.added_by) == ("mismatch", "human")


def test_mark_back_to_uncertain_may_clear_the_evidence(tmp_path):
    out = write_to(tmp_path)
    writer.mark(str(out), "A-02", "mismatch", GOOD_EVIDENCE, evidence_type="run_check")
    writer.mark(str(out), "A-02", "uncertain", "")
    assert "- **evidence**: " not in out.read_text(encoding="utf-8")  # no trailing space
    assert writer.parse(str(out))[1].evidence == ""


VERIFIED_EVIDENCE = "雲端團隊 11/26 在 Discord 回覆：斷線後一次最多補送 120 筆"


def answer(monkeypatch, interactive, reply=None):
    """Pretend a person is (or is not) at a terminal and types `reply`."""
    monkeypatch.setattr(writer, "_interactive", lambda: interactive)

    def fake_input(prompt):
        if reply is None:
            raise AssertionError("mark should not have asked")
        return reply
    monkeypatch.setattr("builtins.input", fake_input)


def test_mark_refuses_verified_without_a_terminal(tmp_path, monkeypatch):
    answer(monkeypatch, interactive=False)
    out = write_to(tmp_path)
    before = out.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="互動式終端機"):
        writer.mark(str(out), "A-01", "verified", VERIFIED_EVIDENCE, evidence_type="ask_owner")
    assert out.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("reply", ["y", "Y", " yes "])
def test_mark_verified_after_a_person_says_yes(tmp_path, monkeypatch, capsys, reply):
    answer(monkeypatch, interactive=True, reply=reply)
    out = write_to(tmp_path)
    writer.mark(str(out), "A-01", "verified", VERIFIED_EVIDENCE, evidence_type="ask_owner")
    shown = capsys.readouterr().out
    assert "我的程式假設每次只收到一筆資料" in shown          # the question
    assert f"[ask_owner] {VERIFIED_EVIDENCE}" in shown       # the evidence about to be written
    assert writer.parse(str(out))[0].status == "verified"
    assert "- 狀態：uncertain 2｜verified 1｜mismatch 0" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("reply", ["", "n", "no", "好"])
def test_mark_verified_cancelled_leaves_the_file_alone(tmp_path, monkeypatch, reply):
    answer(monkeypatch, interactive=True, reply=reply)
    out = write_to(tmp_path)
    before = out.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="已取消"):
        writer.mark(str(out), "A-01", "verified", VERIFIED_EVIDENCE, evidence_type="ask_owner")
    assert out.read_text(encoding="utf-8") == before


def test_mark_mismatch_never_asks(tmp_path, monkeypatch):
    answer(monkeypatch, interactive=False)  # input() would fail the test if called
    out = write_to(tmp_path)
    writer.mark(str(out), "A-01", "mismatch", GOOD_EVIDENCE, evidence_type="inspect_sample")
    assert writer.parse(str(out))[0].status == "mismatch"
