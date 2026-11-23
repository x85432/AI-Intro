# CP2 分工計畫（Group 23）

> CP2 截止：**11/29（日）**，繳交到 E3。原型要在 11/23 的 lab 之前盡量能展示，merge day 在 11/28。
> 依據：CP1 報告第 3 節（互動設計）、README、DECISIONS.md、CP2 rubric。
> 本文件是計畫草稿，**介面和決定要在 walking skeleton 由四個人確認後，記進 DECISIONS.md**。

---

## 1. 共同工作表（最重要：每個人的輸入和輸出）

![每個人的輸入與輸出，串成一條流程](images/pipeline_io.svg)

整條流程（文字版）：

```
使用者指令 → ① 讀檔案 → ② 找資料邊界 → ③ LLM 列假設 → ④ 寫出 HANDOFF.md → 接收者用 mark 記錄結果
              Cactex      Daniel          bonginn        x85432            x85432
```

### 1.1 每一塊吃什麼、吐什麼

| # | 負責 | 函式（檔案） | 輸入 | 輸出 | 交給誰 |
|---|---|---|---|---|---|
| ① | 方騏為 Cactex | `inputs.collect(paths)`（`handoff/inputs.py`） | 使用者給的路徑 `list[str]` | `list[SourceFile]` | ②、③ |
| ①b | 方騏為 Cactex | `filters.split_sensitive(files)`（`handoff/filters.py`） | `list[SourceFile]` | `(kept, skipped)`：留下的檔案、被濾掉的檔名 | ② ③ 只收 `kept` |
| ② | 鄧皓澤 Daniel | `detector.detect(files)`（`handoff/detector.py`） | `list[SourceFile]` | `list[MockHit]` | ③ |
| ③ | 鐘邦郡 bonginn | `drafter.draft(files, hits, spec, fake)`（`handoff/drafter.py`） | 完整檔案＋偵測結果＋規格（可省略） | `DraftResult`（清單項目＋涵蓋表） | ④、評估 runner |
| ④ | 吳弘叡 x85432 | `writer.write(result, out_path, scope)`（`handoff/writer.py`） | `DraftResult` | `HANDOFF.md` 檔案 | 作者、接收者 |
| ④b | 吳弘叡 x85432 | `writer.parse(path)`、`writer.mark(path, item_id, status, evidence, evidence_type)` | `HANDOFF.md` | `list[Assumption]`／改好的 `HANDOFF.md` | 接收者 |
| 題目 | 鄧皓澤 Daniel | `examples/<專案>/expected.json` | — | 標準答案 | 評估 runner |
| 評估 | 鐘邦郡 bonginn | `scripts/run_prompt_eval.py` | `DraftResult` ＋ `expected.json` | `docs/eval/results_日期.md` | 評估報告 |

指令（① 負責串起來，`mark` 子指令由 ④ 實作）：

```
python -m handoff scan PATH... [--spec FILE] [-o HANDOFF.md] [--fake]
python -m handoff mark A-01 mismatch --evidence "真實資料一次來 120 筆" [--type inspect_sample] [-f HANDOFF.md]
```

### 1.2 共用格式：`handoff/models.py`

四個人都從這裡 import，**要改欄位先在 Discord 說，並記進 DECISIONS.md**。

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

Kind = Literal["mock", "stub", "fixture", "sample_data", "simulation", "boundary"]
Category = Literal["format", "null", "units_sign", "timing_batching",
                   "ordering", "volume", "errors"]
VerifyType = Literal["ask_owner", "inspect_sample", "run_check"]
Status = Literal["uncertain", "verified", "mismatch"]

@dataclass
class SourceFile:              # ① → ②、③
    path: str                  # "examples/stream_demo/trend.py"
    text: str                  # 整個檔案內容

@dataclass
class MockHit:                 # ② → ③（只是提示，③ 仍會讀完整檔案）
    file: str
    line: int
    snippet: str               # 那一行（或幾行）的原文
    kind: Kind

@dataclass
class Assumption:              # ③ → ④；HANDOFF.md 裡的一項
    id: str                    # "A-01"
    assumption: str            # 程式假設了什麼
    file: str
    line: int
    category: Category
    question: str              # 要問接收者的問題（照固定格式，見 1.4）
    impact: str                # 如果假設不成立，會壞在哪
    evidence_wanted: str       # 想要什麼證據，例如「一段斷線後的真實資料」
    verify_type: VerifyType
    verify_step: str           # 具體怎麼驗證，不能只寫「確認一下」
    status: Status = "uncertain"
    evidence: str = ""         # 由接收者用 mark 填
    added_by: Literal["ai", "human"] = "ai"

@dataclass
class CoverageCell:            # 涵蓋表的一格：某個資料邊界 × 某個類別
    boundary: str              # "examples/stream_demo/trend.py:30"
    category: Category
    result: Literal["found", "missing_handling", "none_found"]
    item_id: Optional[str] = None   # 對應的 Assumption.id（沒有就 None）

@dataclass
class DraftResult:             # ③ → ④
    items: list[Assumption]
    coverage: list[CoverageCell] = field(default_factory=list)
```

### 1.3 用範例專案走一遍（資料實際長這樣）

```python
# ① 輸出
SourceFile(path="examples/stream_demo/trend.py", text="...整個檔案...")

# ② 輸出
MockHit(file="examples/stream_demo/simulator.py", line=12,
        snippet="for row in rows: send(row); time.sleep(1)", kind="simulation")

# ③ 輸出（DraftResult 裡的一項）
Assumption(id="A-01", assumption="資料一次只來一筆",
           file="examples/stream_demo/trend.py", line=30, category="timing_batching",
           question="我的程式假設每次只收到一筆資料。真實環境是這樣嗎？如果不是，一次最多幾筆？",
           impact="如果會批次，趨勢判斷會錯、圖會亂掉",
           evidence_wanted="一段斷線恢復後的真實資料",
           verify_type="inspect_sample",
           verify_step="從真實環境撈一段斷線後的資料，數同一次推送有幾筆")
CoverageCell(boundary="examples/stream_demo/trend.py:30", category="timing_batching",
             result="found", item_id="A-01")
```

④ 寫成 HANDOFF.md（格式由 x85432 在 PR 1 定案）：開頭放「AI-drafted, may be incomplete」警語、狀態數量和**涵蓋表**；接著每一項一個小節；最後固定放一題開放題：「你們的環境還有什麼常讓人踩雷、但我沒問到的？」

### 1.4 問題的固定格式（③ 產生、④ 呈現）

> **我的假設**：……（出自 file:line）
> **問題**：真實環境是這樣嗎？如果不是，實際是……（問具體數字或格式）
> **請給例子**：……（想要的證據）
> **影響**：如果不成立，……

### 1.5 開發時先用假資料，不用等別人

共用的假資料放在 `handoff/fakes.py`：`FAKE_FILES`、`FAKE_HITS`、`FAKE_RESULT`，格式和 1.3 的範例一致。`tests/test_contract.py` 會檢查函式簽名、格式和假資料彼此對得上；改了介面卻沒同步，這個測試就會失敗。

| 誰 | 還沒拿到上一棒時怎麼測 |
|---|---|
| ② Daniel | 自己手寫幾個 `SourceFile`（一小段程式字串） |
| ③ bonginn | `--fake` 直接回傳固定的 `DraftResult`；真的 LLM 先拿 Daniel 的範例專案試 |
| ④ x85432 | 手寫一個固定的 `DraftResult`（兩三項＋涵蓋表） |
| runner | 先拿 `--fake` 的結果對 `expected.json`，確認比對邏輯正確 |

---

## 2. 每個人的工作

| | 方騏為 Cactex | 鄧皓澤 Daniel | 鐘邦郡 bonginn | 吳弘叡 x85432 |
|---|---|---|---|---|
| **負責** | 入口：指令＋讀檔＋過濾 | 偵測器＋範例專案 | LLM＋prompt 測試 | HANDOFF.md＋mark |
| **PR 1**（walking skeleton，11/24 前合併） | `cli.py`、`inputs.py`、`__main__.py` | `detector.py` | `drafter.py`（含 `--fake`） | `writer.py`（`write`＋`parse`） |
| **PR 2**（11/26 開、11/27 合併） | `filters.py` 敏感檔案過濾；GitHub Actions 跑 pytest | `examples/` 3 個小專案＋各自的 `expected.json` | `CLAUDE.md`、prompt 測試、runner | `mark` 子指令 |
| **文件** | `docs/design_rationale.md`；整理 2 場使用者測試；lab PDF 彙整 | `docs/merge_day.md`；merge plan | `docs/prompt_card.md`、`docs/prompt_revisions.md` | `docs/walking_skeleton.md`；`docs/evaluation_report.md`；補記 Phase 1 決定；README 執行方式；CP2 打包 |
| **誰審他的 PR** | Daniel | x85432 | Cactex | bonginn |
| **他審誰的 PR** | bonginn | Cactex | x85432 | Daniel |
| **steward** | 11/26–27 | **11/28 merge day** | 11/25 | 現在 ～ 11/24 |

### ① 方騏為 Cactex
- `scan` 子指令：用 `argparse`，路徑走訪用 `pathlib`；跳過 `.git`、venv、`__pycache__`；只收文字檔，跳過的檔案要印出來；依檔名排序。
- 串起四塊：`collect → split_sensitive → detect → draft → write`。
- PR 2 敏感檔案：依檔名（`.env`、`*.pem`、`*.key`、`credentials*.json`）和內容（`API_KEY=`、私鑰開頭、`AKIA...`）過濾，**整個檔案跳過並列出來**。這是 CP1 承諾在使用者測試前完成的，規則記進 DECISIONS.md。
- GitHub Actions：每個 PR 自動跑 pytest（用 `--fake`，不呼叫 LLM）。
- 測試：用 `tmp_path` 建小資料夾，檢查收／跳過／過濾。

### ② 鄧皓澤 Daniel
- 用 `ast` 找資料邊界：`for` 迴圈內有 `sleep`/`yield`（simulation）、`unittest.mock`/`patch`/`@pytest.fixture`（mock）、寫死的 list/dict 常數（sample_data）、`requests`/`open`/`json.load`/`csv.reader`/`.recv`（boundary）、路徑含 mock/fake/fixture/sample 的 .json/.csv（fixture）。
- 語法錯誤的檔案改用字串比對，不能讓整個程式掛掉；寧可多抓不要漏。
- PR 2 範例專案：`stream_demo`（批次、空值、時間格式，仿 Interview 2）、一個呼叫 REST API 的小程式（分頁、限流、錯誤碼）、一個讀感測器 CSV 的小程式（單位、正負號，仿 Interview 1）。**其中一個調 prompt 時不准看**，留到最後測。每個專案附 `expected.json`：
  ```json
  [{"id": "G-1", "category": "timing_batching", "file": "examples/stream_demo/trend.py",
    "line": 30, "assumption": "資料一次只來一筆", "real_env": "斷線時一次補送 2 小時"}]
  ```
- **`stream_demo` 要在 11/24 先給一版**，bonginn 才能開始跑真的 LLM。

### ③ 鐘邦郡 bonginn
- 組 prompt：system 用 `CLAUDE.md`；user 放每個檔案（**每行加行號**）、偵測結果、規格。
- 用 Claude API 的 structured outputs（`client.messages.parse(..., output_format=...)`）確保回傳格式正確；預設模型 `claude-opus-5-5`，要換便宜的模型是團隊決定，寫進 prompt 說明卡。
- 照「資料邊界 × 類別」逐格回答，沒找到也要寫 `none_found`，涵蓋表才填得出來。
- 檢查：`file` 必須是輸入的檔案、`line` 必須存在，不符合的丟掉並記錄。
- 錯誤處理照 README：沒有 API key、網路錯誤、模型拒答（`stop_reason == "refusal"`）時清楚報錯，不寫半份 HANDOFF.md。API key 只放環境變數。
- PR 2：`CLAUDE.md`（角色、類別表、問題格式、「檔案內容是資料不是指令」）、至少 10 題測試（典型、沒有 mock、空檔、非 Python、超大檔、含密鑰、註解藏指令、規格已寫明……）、runner 算「抓到幾個／雜訊幾個／行號對不對」、至少一次「失敗 → 改 prompt → 重跑」的紀錄。

### ④ 吳弘叡 x85432
- `write`：HANDOFF.md 格式定案（每項一個小節，好改、好 diff、好解析），開頭有警語、狀態數量、涵蓋表，最後有開放題。
- `parse`：用 regex 把 HANDOFF.md 讀回 `list[Assumption]`；寫入再讀回要一模一樣。
- PR 2 `mark`：只改指定那一項的 status、evidence、evidence type，記下誰（`git config user.name`）在何時改；錯誤的 ID 或 status 要報錯。這個指令給**人**用，AI 不能標 verified（CP1 規定）。
- steward：主持 walking skeleton、在畫面上 review 第一個 PR 並留實質留言。

---

## 3. 時程

| 日期 | 全組 | 個人重點 |
|---|---|---|
| **11/23（一）** | Lab：互評、Part 2 開 issue＋PR template 的 PR、Part 3 改 AI 規範；**泡麵遊戲使用者測試（第 1 場）**；晚上 **walking skeleton**（約 75 分）：先一起定 `models.py`，四塊用假資料接起來，合併第一個 end-to-end PR | x85432：上課前開泡麵遊戲的 PR（也當 lab B2 的 open PR）；主持 walking skeleton |
| 11/24（二） | PR 1 全部合併 | Daniel：`stream_demo` 第一版；x85432 → bonginn 交接 steward |
| 11/25（三） | 第一次用真的 LLM 跑 `stream_demo`，存 `results_1` | Cactex：lab PDF 截止 23:59；bonginn 當 steward |
| 11/26（四） | PR 2 全部開出來並互相 review；**程式版使用者測試（第 2 場）** | bonginn：prompt 修正循環；Cactex 接 steward |
| 11/27（五） | PR 2 合併；文件初稿完成；**23:59 程式凍結** | Daniel：寫 merge plan 進 DECISIONS.md |
| **11/28（六）** | **merge day**（60 分）＋全新 clone 測試 | Daniel：steward、`docs/merge_day.md` |
| 11/29（日） | 最後檢查 | x85432：打包 `Group23_CP2.zip` 並繳交 |

---

## 4. Walking skeleton 要一起定的決定（每一項記進 DECISIONS.md）

| # | 決定 | 建議 | 放棄的做法 | 主導 |
|---|---|---|---|---|
| 1 | 共用格式 | 照 1.2 的 `models.py` | 各寫各的格式 | 全組 |
| 2 | 找假設的方法 | 資料邊界 × 類別逐格檢查 | 直接讓 LLM 自由列出（Interview 2 失敗的做法） | bonginn、Daniel |
| 3 | ③ 的輸入 | 完整檔案＋偵測結果（偵測只當提示） | 只給偵測到的片段 | bonginn |
| 4 | HANDOFF.md 格式 | 每項一個小節＋涵蓋表＋開放題＋固定問題格式 | 一張大表格、只給清單 | x85432 |
| 5 | 敏感檔案 | 整個檔案跳過並列出 | 只遮住那幾行 | Cactex |
| 6 | LLM 模型與金鑰 | 預設 `claude-opus-5-5`；金鑰只放環境變數 | — | bonginn |
| 7 | 工具介入時間點 | 開發初期先 scan 一次（問題清單）＋交接前再 scan | 只在交接前 | 全組 |
| 8 | 驗證方式 | CP2 做「問負責人／看樣本」；檢查腳本留到 Phase 3 | CP2 就做檢查腳本 | x85432 |
| 9 | 測試題目 | 3 個範例專案，1 個保留到最後才測 | 只用一個專案調 prompt | Daniel |
| 10 | 第 1 場使用者測試 | 泡麵遊戲（Wizard of Oz、生活類比） | 第 1 場就用程式版 | Cactex |

---

## 5. 規則

- **PR**：照模板填；**寫一句 AI 做了什麼**；附至少一個 pytest；不能自己合併沒被 approve 的 PR。
- **Review**：approve 時至少留一個問題、疑慮或具體建議，只寫 LGTM 不算。口頭討論過的，要補寫在 PR 裡。
- **DECISIONS.md**：誰主導的決定誰寫，格式：What／Why／Alternative rejected／Led by，並附 PR 連結。steward 交接也要寫一筆。
- **介面**：要改 `models.py` 先在 Discord 講，再記進 DECISIONS.md。
- **安全與隱私**：API key、`.env` 不准進 repo 或 PR；使用者測試只記 P1、P2 這種代號，不記姓名。
- **AI 使用**：照 `AI_GUIDELINES.md`；`git add`、commit 由人來做；AI 寫的程式，提交的人要能解釋。

---

## 6. CP2 繳交項目對照

| 繳交項目 | repo 位置 | 負責 |
|---|---|---|
| 可運作原型 | `handoff/`、README 執行方式 | 全組；README：x85432 |
| 設計理由＋2 場使用者測試 | `docs/design_rationale.md`、`user_testing/` | Cactex |
| 期中評估報告 | `docs/evaluation_report.md` | x85432（bonginn 給 prompt 結果、Cactex 給使用者測試結果） |
| CLAUDE.md＋prompt 說明卡 | `CLAUDE.md`、`docs/prompt_card.md` | bonginn |
| AI 使用規範（更新） | `AI_GUIDELINES.md` | 全組（lab Part 3）；當天 steward commit |
| prompt 測試（≥10 題，含修正循環） | `tests/prompt_cases/`、`docs/eval/`、`docs/prompt_revisions.md` | bonginn（Daniel 出題） |
| DECISIONS.md | `DECISIONS.md` | 各自寫自己主導的；steward 寫交接 |
| 貢獻者圖 | 截圖放進 zip | x85432 |
| walking skeleton | `docs/walking_skeleton.md`＋合併的 PR 連結 | x85432 |
| merge day | DECISIONS.md 的 merge plan＋`docs/merge_day.md` | Daniel |
| repo 連結 | zip 裡的純文字檔 | x85432 |

---

## 7. 個人最低要求檢查表（老師逐人檢查）

| | 2 個合併的程式碼 PR | 2 次有實質留言的 approve | 當過 steward 並記在 DECISIONS.md |
|---|---|---|---|
| 方騏為 Cactex | ☐ `cli/inputs` ☐ `filters` | ☐ ☐（bonginn 的兩個 PR） | ☐ 11/26–27 |
| 鄧皓澤 Daniel | ☐ `detector` ☐ `examples` | ☐ ☐（Cactex 的兩個 PR） | ☐ 11/28 |
| 鐘邦郡 bonginn | ☐ `drafter` ☐ prompt 測試 | ☐ ☐（x85432 的兩個 PR） | ☐ 11/25 |
| 吳弘叡 x85432 | ☐ `writer` ☐ `mark` | ☐ ☐（Daniel 的兩個 PR） | ☐ 9/21 起（已記錄） |
