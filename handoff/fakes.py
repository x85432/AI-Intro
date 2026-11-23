"""Shared fake data in the agreed formats, so each piece can be built and tested
before the previous piece exists (plan §1.5).

    ② detector  -> test against FAKE_FILES
    ③ drafter   -> may return FAKE_RESULT for --fake
    ④ writer    -> test against FAKE_RESULT
    runner      -> test the matching logic against FAKE_RESULT

These values mirror the walkthrough in docs/CP2_PLAN.md §1.3. They are not the real
example project (examples/stream_demo/), which Daniel builds.
"""

from __future__ import annotations

from .models import Assumption, CoverageCell, DraftResult, MockHit, SourceFile

FAKE_FILES = [
    SourceFile(
        path="examples/stream_demo/simulator.py",
        text=(
            "import json\n"
            "import time\n"
            "\n"
            "from trend import TrendTracker\n"
            "\n"
            "\n"
            "def main():\n"
            "    rows = json.load(open('fixtures/readings.json'))\n"
            "    tracker = TrendTracker()\n"
            "    for row in rows:\n"
            "        tracker.update(row)\n"
            "        time.sleep(1)\n"
        ),
    ),
    SourceFile(
        path="examples/stream_demo/trend.py",
        text=(
            "from datetime import datetime\n"
            "\n"
            "\n"
            "class TrendTracker:\n"
            "    def __init__(self):\n"
            "        self.last = None\n"
            "\n"
            "    def update(self, record):\n"
            "        ts = datetime.strptime(record['ts'], '%Y-%m-%d %H:%M:%S')\n"
            "        value = record['value']\n"
            "        if self.last is None:\n"
            "            self.last = (ts, value)\n"
            "            return 'flat'\n"
            "        diff = value - self.last[1]\n"
            "        self.last = (ts, value)\n"
            "        if diff > 0.5:\n"
            "            return 'rising'\n"
            "        if diff < -0.5:\n"
            "            return 'falling'\n"
            "        return 'flat'\n"
        ),
    ),
]

FAKE_HITS = [
    MockHit(file="examples/stream_demo/simulator.py", line=8,
            snippet="rows = json.load(open('fixtures/readings.json'))", kind="boundary"),
    MockHit(file="examples/stream_demo/simulator.py", line=10,
            snippet="for row in rows:", kind="simulation"),
]

FAKE_RESULT = DraftResult(
    items=[
        Assumption(
            id="A-01",
            assumption="資料一次只來一筆，update() 每次只處理一筆",
            file="examples/stream_demo/trend.py", line=8, category="timing_batching",
            question="我的程式假設每次只收到一筆資料。真實環境是這樣嗎？如果不是，一次最多幾筆？",
            impact="如果會批次送來，趨勢判斷會錯，圖會亂掉",
            evidence_wanted="一段斷線恢復後的真實資料",
            verify_type="inspect_sample",
            verify_step="從真實環境撈一段斷線後的資料，數同一次推送有幾筆",
        ),
        Assumption(
            id="A-02",
            assumption="value 一定有值，不會是 null",
            file="examples/stream_demo/trend.py", line=14, category="null",
            question="我的程式假設 value 一定有值。真實資料會不會是 null 或缺這個欄位？",
            impact="遇到 null 時相減會直接丟出錯誤",
            evidence_wanted="一筆讀值失敗時的真實資料",
            verify_type="ask_owner",
            verify_step="問雲端團隊：感測器讀不到時，value 會送什麼？",
        ),
        Assumption(
            id="A-03",
            assumption="資料來源不會失敗，程式完全沒有處理錯誤或逾時",
            file="examples/stream_demo/simulator.py", line=8, category="errors",
            question="我的程式沒有處理讀取失敗。真實環境斷線或逾時時，會發生什麼事？會重送嗎？",
            impact="斷線時程式會直接停止，之後的資料都收不到",
            evidence_wanted="斷線或逾時時的錯誤訊息或紀錄",
            verify_type="ask_owner",
            verify_step="問雲端團隊：連線中斷時，資料會重送、遺失，還是延後補送？",
        ),
    ],
    coverage=[
        CoverageCell(boundary="examples/stream_demo/trend.py:8", category="timing_batching",
                     result="found", item_id="A-01"),
        CoverageCell(boundary="examples/stream_demo/trend.py:8", category="null",
                     result="found", item_id="A-02"),
        CoverageCell(boundary="examples/stream_demo/simulator.py:8", category="errors",
                     result="missing_handling", item_id="A-03"),
        CoverageCell(boundary="examples/stream_demo/trend.py:8", category="units_sign",
                     result="none_found"),
    ],
)
