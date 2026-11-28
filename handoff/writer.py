"""④ Write HANDOFF.md, read it back, and record a human's verification.
Owner: 吳弘叡 x85432.

The format is decided in DECISIONS.md (2026-11-24, "HANDOFF.md format"):
HANDOFF.md is the only copy, one field per line, and `parse` is strict.
"""

from __future__ import annotations

import difflib
import os
import re
import sys
import tempfile
from collections import Counter
from typing import Optional

from .models import (CATEGORIES, COVERAGE_RESULTS, STATUSES, VERIFY_TYPES,
                     Assumption, CoverageCell, DraftResult)

ITEMS_HEADING = "## 項目"

# The four reader-facing lines (plan §1.4), in order: label -> Assumption field.
TEXT_LABELS = {"我的假設": "assumption", "問題": "question",
               "請給例子": "evidence_wanted", "影響": "impact"}
# The machine fields, in order. Their labels are the Assumption field names.
META_FIELDS = ("verify_type", "verify_step", "status", "evidence", "added_by")
# Every other field must be filled in.
MAY_BE_EMPTY = {"evidence"}
ALLOWED = {"category": CATEGORIES, "verify_type": VERIFY_TYPES,
           "status": STATUSES, "added_by": ("ai", "human")}
# AI items are numbered A-01, A-02...; items added by hand H-01, H-02...
ID_PREFIX = {"ai": "A", "human": "H"}

HEADING_RE = re.compile(
    r"^### (?P<id>\S+) · (?P<category>\S+) · (?P<file>.+):(?P<line>\d+)$")
TEXT_RE = re.compile(r"^\*\*(?P<label>[^*]+)\*\*：(?P<value>.*)$")
META_RE = re.compile(r"^- \*\*(?P<label>[^*]+)\*\*:(?P<value>.*)$")
ID_RE = re.compile(r"^[AH]-\d{2,}$")

CELL_TEXT = {"found": "{id}", "missing_handling": "沒有處理（{id}）",
             "none_found": "檢查過，沒發現"}
NOT_CHECKED = "未檢查"


class HandoffFormatError(ValueError):
    """HANDOFF.md does not follow the format. `errors` lists every problem found."""

    def __init__(self, path: str, errors: list[str]):
        self.errors = errors
        super().__init__(f"{path} 的格式有 {len(errors)} 個問題：\n"
                         + "\n".join(f"- {e}" for e in errors))


# ---------------------------------------------------------------- write

def write(result: DraftResult, out_path: str, scope: list[str]) -> None:
    """Write HANDOFF.md.

    Layout: notice, scanned scope, status counts; the coverage table as a
    matrix; one section per item under "## 項目"; an appendix with
    definitions, the evidence rules and a template for items added by hand.

    The text is checked with the same rules as `parse` before anything is
    written, so every file `write` produces can be read back. It is written to
    a temporary file first and then swapped in, so a failure never leaves a
    half-written HANDOFF.md.
    """
    text = _render(result, scope)
    _parse_text(text, f"{out_path}（未寫出）")
    _atomic_write(out_path, text)


STATUS_LINE_PREFIX = "- 狀態："


def _status_line(counts: Counter) -> str:
    """'- 狀態：uncertain 3｜verified 0｜mismatch 0'. Used by write and by mark."""
    return STATUS_LINE_PREFIX + "｜".join(f"{s} {counts[s]}" for s in STATUSES)


def _one_line(value: object) -> str:
    """Every field stays on one line: line breaks become spaces."""
    return re.sub(r"\s*[\r\n]+\s*", " ", str(value)).strip()


def _render(result: DraftResult, scope: list[str]) -> str:
    counts = Counter(item.status for item in result.items)
    lines = [
        "# HANDOFF.md",
        "",
        "> **AI 草擬，可能不完整。** 以下項目由 AI 根據程式碼列出，可能漏掉，也可能有錯。",
        "> 作者請審過一遍，刪掉不對的、補上漏掉的；接收者請逐項驗證。名詞定義和證據規範在文末附錄。",
        "",
        "- 掃描範圍：" + ("、".join(_one_line(s) for s in scope) or "（未提供）"),
        _status_line(counts),
        "",
        "## 涵蓋表",
        "",
        *_render_coverage(result.coverage, {item.id for item in result.items}),
        "",
        ITEMS_HEADING,
        "",
    ]
    for item in result.items:
        lines += _render_item(item)
    lines += APPENDIX
    return "\n".join(lines) + "\n"


def _render_coverage(coverage: list[CoverageCell], item_ids: set[str]) -> list[str]:
    if not coverage:
        return ["這次沒有涵蓋表資料：AI 沒有回報它檢查了哪些格子。"]

    problems = []
    cells: dict[tuple[str, str], list[str]] = {}
    for cell in coverage:
        if cell.category not in CATEGORIES or cell.result not in COVERAGE_RESULTS:
            problems.append(f"{cell.boundary}：category {cell.category!r} 或 "
                            f"result {cell.result!r} 不在允許的值裡")
            continue
        if cell.result != "none_found" and cell.item_id not in item_ids:
            problems.append(f"{cell.boundary} × {cell.category}：指到不存在的項目 {cell.item_id!r}")
            continue
        text = CELL_TEXT[cell.result].format(id=cell.item_id)
        cells.setdefault((_one_line(cell.boundary), cell.category), []).append(text)
    if problems:
        raise ValueError("涵蓋表的資料有問題，沒有寫出任何檔案：\n"
                         + "\n".join(f"- {p}" for p in problems))

    def cell_text(text: str) -> str:
        return text.replace("|", r"\|")

    boundaries = list(dict.fromkeys(_one_line(c.boundary) for c in coverage))
    lines = [
        "怎麼看這張表：每一列是資料進入程式的一個位置，每一欄是一類可能出錯的假設（類別說明見附錄）。",
        "",
        "- `A-01`：找到一個假設，詳細內容在下方同編號的項目",
        "- `沒有處理（A-03）`：程式完全沒處理這類情況，詳細內容在該項目",
        "- `檢查過，沒發現`：AI 檢查過這一格，沒找到假設，但不代表一定沒有",
        "- `未檢查`：這一格沒被檢查過，是涵蓋的缺口，請自己看一下",
        "",
        "| 資料邊界 | " + " | ".join(CATEGORIES) + " |",
        "|---" * (len(CATEGORIES) + 1) + "|",
    ]
    for boundary in boundaries:
        row = [cell_text(boundary)] + [
            cell_text("、".join(cells.get((boundary, category), [NOT_CHECKED])))
            for category in CATEGORIES]
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _render_item(item: Assumption) -> list[str]:
    lines = [f"### {_one_line(item.id)} · {_one_line(item.category)} · "
             f"{_one_line(item.file)}:{item.line}", ""]
    # A blank line after each, or Markdown would join the four into one paragraph.
    for label, name in TEXT_LABELS.items():
        lines += [f"**{label}**：{_one_line(getattr(item, name))}", ""]
    for name in META_FIELDS:
        lines.append(f"- **{name}**: {_one_line(getattr(item, name))}".rstrip())
    lines.append("")
    return lines


APPENDIX = [
    "## 附錄：名詞與規範",
    "",
    "### 狀態",
    "",
    "- `uncertain`：還沒驗證。",
    "- `verified`：在真實環境確認過，假設成立，並附上證據。只能由人標記。",
    "- `mismatch`：確認過，真實環境和假設不一樣，並附上證據。",
    "",
    "狀態請用 `python -m handoff mark` 修改，不要直接改 status 那一行。",
    "",
    "### 類別",
    "",
    "- `format`：欄位名稱、型別、時間格式",
    "- `null`：值可能缺少或是 null",
    "- `units_sign`：單位（例如 °C 或 °F）、正負號",
    "- `timing_batching`：資料一次來一筆，還是一次來一批",
    "- `ordering`：資料順序錯亂或重複",
    "- `volume`：一次來多少筆、分頁上限",
    "- `errors`：失敗、逾時、流量限制",
    "",
    "### 證據規範",
    "",
    "每條證據都要寫「來源＋具體結果」（數字、格式或例子），而且要能回答該項目的問題。"
    "「沒問題」「確認過」「OK」這類話不算證據。",
    "",
    "| 驗證方式 | 來源要寫 | 結果要寫 |",
    "|---|---|---|",
    "| `ask_owner` | 誰回答（角色或團隊）、什麼時候、在哪裡 | 對方的回答，盡量照原話 |",
    "| `inspect_sample` | 樣本從哪裡撈、存在哪裡（只存去識別化的片段） | 看到什麼，要帶數字 |",
    "| `run_check` | 跑了什麼指令、哪個版本 | 輸出結果 |",
    "",
    "### 手動新增項目",
    "",
    "複製上面任一項，貼到「## 項目」最後面再改。編號用 `H-01`、`H-02`……，"
    "`added_by` 寫 `human`，`status` 寫 `uncertain`，每個欄位都寫在同一行。"
    "空白範本在 handoff 工具的 README。",
]


def _atomic_write(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".handoff-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ---------------------------------------------------------------- parse

def parse(path: str) -> list[Assumption]:
    """Read HANDOFF.md back into Assumption objects (write then parse must round-trip).

    Reads only the "## 項目" section and is strict: an unknown line, a missing or
    repeated field, or a value outside the allowed list is an error. Every
    problem is reported at once in a HandoffFormatError, with line numbers.
    """
    with open(path, encoding="utf-8") as f:
        return _parse_text(f.read(), path)


def _parse_text(text: str, path: str) -> list[Assumption]:
    lines = text.splitlines()
    if ITEMS_HEADING not in lines:
        raise HandoffFormatError(path, [f"找不到「{ITEMS_HEADING}」這一段"])
    start = lines.index(ITEMS_HEADING) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")),
               len(lines))

    errors: list[str] = []
    blocks: list[tuple[int, str, list[tuple[int, str]]]] = []
    for i in range(start, end):
        lineno, line = i + 1, lines[i]
        if line.startswith("### "):
            blocks.append((lineno, line, []))
        elif blocks:
            blocks[-1][2].append((lineno, line))
        elif line.strip():
            errors.append(f"第 {lineno} 行：項目要用 `### A-01 · ...` 標題開頭，"
                          f"不認得這一行：{line.strip()[:40]}")

    items: list[Assumption] = []
    seen_ids: dict[str, int] = {}
    for heading_lineno, heading, body in blocks:
        item = _parse_item(heading_lineno, heading, body, errors)
        if item is None:
            continue
        if item.id in seen_ids:
            errors.append(f"第 {heading_lineno} 行：編號 {item.id} 重複"
                          f"（第 {seen_ids[item.id]} 行已經用過）")
            continue
        seen_ids[item.id] = heading_lineno
        items.append(item)

    if errors:
        raise HandoffFormatError(path, errors)
    return items


def _parse_item(heading_lineno: int, heading: str, body: list[tuple[int, str]],
                errors: list[str]) -> Optional[Assumption]:
    """Parse one item section. Adds every problem to `errors`; returns None if any."""
    before = len(errors)
    m = HEADING_RE.match(heading)
    item_id = m["id"] if m else heading[4:].split(" ")[0]

    def error(lineno: int, message: str) -> None:
        errors.append(f"第 {lineno} 行（{item_id}）：{message}")

    if not m:
        error(heading_lineno, "標題格式不對，應該像 "
                              "`### A-01 · timing_batching · path/to/file.py:8`")

    fields: dict[str, str] = {}
    for lineno, line in body:
        if not line.strip():
            continue
        text_match, meta_match = TEXT_RE.match(line), META_RE.match(line)
        if text_match:
            label, known = text_match["label"], TEXT_LABELS
        elif meta_match:
            label, known = meta_match["label"], META_FIELDS
        else:
            error(lineno, f"不認得這一行：{line.strip()[:40]}。每個欄位要寫在同一行，"
                          "格式像 `**問題**：...` 或 `- **status**: ...`")
            continue
        if label not in known:
            guess = difflib.get_close_matches(label, list(known), n=1)
            hint = f"，是不是要寫 {guess[0]}？" if guess else ""
            error(lineno, f"不認得欄位「{label}」{hint}")
            continue
        name = TEXT_LABELS.get(label, label)
        if name in fields:
            error(lineno, f"欄位「{label}」重複出現")
            continue
        fields[name] = (text_match or meta_match)["value"].strip()

    if m:
        fields["category"] = m["category"]
    labels = {name: label for label, name in TEXT_LABELS.items()}
    for name in (*TEXT_LABELS.values(), *META_FIELDS):
        label = labels.get(name, name)
        if name not in fields:
            error(heading_lineno, f"缺少欄位「{label}」")
        elif not fields[name] and name not in MAY_BE_EMPTY:
            error(heading_lineno, f"欄位「{label}」不能是空的")
    for name, allowed in ALLOWED.items():
        value = fields.get(name)
        if value and value not in allowed:
            error(heading_lineno, f"{name} 寫的是 {value!r}，"
                                  f"只能是：{', '.join(allowed)}")

    if m and int(m["line"]) < 1:
        error(heading_lineno, "行號從 1 開始")
    if m and not ID_RE.match(item_id):
        error(heading_lineno, "編號要像 A-01（AI 列的）或 H-01（人加的）")
    expected = ID_PREFIX.get(fields.get("added_by", ""))
    if m and expected and ID_RE.match(item_id) and item_id[0] != expected:
        error(heading_lineno, f"added_by 是 {fields['added_by']}，編號應該用 "
                              f"{expected}- 開頭")

    if len(errors) > before:
        return None
    return Assumption(id=item_id, file=m["file"], line=int(m["line"]), **fields)


# ---------------------------------------------------------------- mark (PR 2)

def mark(path: str, item_id: str, status: str, evidence: str,
         evidence_type: Optional[str] = None) -> None:
    """Update one item's status and evidence in HANDOFF.md.

    Four layers: check the arguments and find the item (1), apply the evidence
    rules (2), ask a person to confirm before `verified` (4), then rewrite only
    this item's two lines and the status counts (3).

    CP2 version: `evidence_type` is kept at the front of the evidence text, and
    who marked it and when are not recorded yet; both wait for the proposed
    interface change (DECISIONS.md, 2026-11-24).
    """
    # Layer 1: check the arguments, then find the item. cli.py also limits
    # `status`, but tests and the runner call mark directly, so check here too.
    if status not in STATUSES:
        raise ValueError(f"status 寫的是 {status!r}，只能是：{', '.join(STATUSES)}")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    items = _parse_text(text, path)  # a malformed file stops here, before anything changes
    ids = [item.id for item in items]
    if item_id not in ids:
        existing = "、".join(ids) or "（沒有任何項目）"
        raise ValueError(f"{path} 裡找不到 {item_id}，現有的是：{existing}")

    # Layer 2: the evidence rules; `evidence` becomes the text that is written.
    evidence = _evidence_text(status, evidence, evidence_type)

    # Layer 4: only a person marks an item verified (CP1 human-AI boundary).
    # Runs before layer 3, so a "no" leaves the file untouched.
    if status == "verified":
        item = next(item for item in items if item.id == item_id)
        _confirm_verified(item, evidence)

    # Layer 3: change only this item's status and evidence lines and the status
    # counts at the top. The coverage table, hand-added items and any other
    # edits stay exactly as they were. Same safety as write: check, then swap in.
    new_text = _replace_fields(text, item_id, {"status": status, "evidence": evidence})
    counts = Counter(status if item.id == item_id else item.status for item in items)
    new_text = _replace_status_line(new_text, counts)
    _parse_text(new_text, f"{path}（未寫出）")
    _atomic_write(path, new_text)


def _interactive() -> bool:
    """True when a person is typing in a terminal.

    AI agents usually run commands without one, so this is the check that
    actually stops them; piping "y" in (`echo y | ...`) does not count either.
    """
    return sys.stdin.isatty()


def _confirm_verified(item: Assumption, evidence: str) -> None:
    """Show the item and the evidence, then ask [y/N]. Raise unless the answer is yes."""
    if not _interactive():
        raise ValueError(f"標成 verified 要由人在終端機按 y 確認，這次不是在互動式終端機執行，"
                         f"所以沒有改動 {item.id}。可以先標 mismatch，或保留 uncertain 並附上證據。")
    print(f"{item.id} · {item.category} · {item.file}:{item.line}")
    print(f"問題：{item.question}")
    print(f"證據：{evidence}")
    try:
        answer = input("標成 verified 代表你在真實環境確認過，假設成立。確定嗎？[y/N] ")
    except EOFError:
        answer = ""
    if answer.strip().lower() not in ("y", "yes"):
        raise ValueError(f"已取消，{item.id} 沒有改動。")


def _replace_fields(text: str, item_id: str, values: dict[str, str]) -> str:
    """Replace machine fields (`- **status**: ...`) inside one item's section.

    Only called on text that `parse` accepted, so the item and its fields exist.
    """
    lines = text.split("\n")
    start = lines.index(ITEMS_HEADING)
    heading = next(i for i in range(start + 1, len(lines))
                   if (m := HEADING_RE.match(lines[i])) and m["id"] == item_id)
    end = next((i for i in range(heading + 1, len(lines))
                if lines[i].startswith(("### ", "## "))), len(lines))
    for i in range(heading + 1, end):
        m = META_RE.match(lines[i])
        if m and m["label"] in values:
            lines[i] = f"- **{m['label']}**: {values[m['label']]}".rstrip()
    return "\n".join(lines)


def _replace_status_line(text: str, counts: Counter) -> str:
    """Update "- 狀態：..." above "## 項目". If someone deleted it, leave it out."""
    lines = text.split("\n")
    for i in range(lines.index(ITEMS_HEADING)):
        if lines[i].startswith(STATUS_LINE_PREFIX):
            lines[i] = _status_line(counts)
            break
    return "\n".join(lines)


# Evidence that says nothing (DECISIONS.md, 2026-11-24, "What `mark` records").
# Compared after removing spaces and punctuation, so "OK!" and "沒問題。" match too.
EMPTY_EVIDENCE = {"ok", "okay", "lgtm", "looksgood", "fine", "checked", "done",
                  "沒問題", "確認過", "已確認", "沒事", "正常", "可以"}


def _evidence_text(status: str, evidence: Optional[str],
                   evidence_type: Optional[str]) -> str:
    """Check the evidence and return the one line `mark` writes.

    `verified` and `mismatch` need `evidence_type` and real evidence. Until the
    interface change adds an `evidence_type` field, the type is kept at the
    front of the text: "[inspect_sample] 撈 11/25 資料，一次 120 筆".
    """
    text = _one_line(evidence or "")
    if evidence_type is not None and evidence_type not in VERIFY_TYPES:
        raise ValueError(f"--type 寫的是 {evidence_type!r}，只能是：{', '.join(VERIFY_TYPES)}")
    if status in ("verified", "mismatch"):
        if evidence_type is None:
            raise ValueError(f"標成 {status} 要附 --type，只能是：{', '.join(VERIFY_TYPES)}")
        if not text:
            raise ValueError(f"標成 {status} 要附證據：寫來源和具體結果（數字、格式或例子）")
        if re.sub(r"[\W_]+", "", text).lower() in EMPTY_EVIDENCE:
            raise ValueError(f"「{text}」不算證據：要寫來源和具體結果（數字、格式或例子），"
                             "規範在 HANDOFF.md 的附錄")
    if evidence_type is not None and text:
        text = f"[{evidence_type}] {text}"
    return text
