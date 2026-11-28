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
