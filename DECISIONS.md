# Decisions Log

## 2026-09-21 — Initial code steward
**What:** 吳弘叡 is the initial code steward for the team.
**Why:** "volunteered"

## 2026-10-25 — Evaluation Design

**What:** Our evaluation compares one variable: receiving engineers
who get the tool's HANDOFF.md versus those who get only the code
and a README. We will recruit 4 participants. We will not treat
familiarity with the author as a variable.

**Why:** Whether the participant has worked with the author is
not the question we want to answer; what we want to learn is
how a handoff with our tool differs from a handoff with only
a README.

## 2026-11-23 — Plan to get the main task running
 
**What:** The first end-to-end version is the thinnest path from input to `HANDOFF.md`,
built at the walking skeleton session on 11/23 (Mon). One piece per person:
 
| # | Piece | Receives | Returns | Owner |
|---|---|---|---|---|
| 1 | CLI + input selection | file/dir paths from the user | list of file paths and their contents | 方騏為 (Cactex) |
| 2 | Mock / fixture detector | file contents | list of `{file, line, snippet, kind}` | 鄧皓澤 (DanielTeng0811) |
| 3 | LLM assumption drafter | detector output (+ optional spec) | list of `{assumption, file, line, category, verify_step}` | 鐘邦郡 (bonginn)  |
| 4 | HANDOFF.md writer | drafter output | `HANDOFF.md` with status `uncertain` on every item | 吳弘叡 (x85432) |
 
"It runs" means: on our sample project, one command produces a `HANDOFF.md` with at least
one item. Pieces 2 and 3 may be faked in the agreed format at first.
 
**Why:** `main` has no executable code yet. Building the thinnest connected path first shows
early whether the pieces fit, and gives every member a first code PR.
 
**Alternative rejected:** Each member builds one module fully before we integrate. Rejected
because we would only find mismatched interfaces at the end.
 
**Led by:** all team members.
 
## 2026-11-23 — Evaluation sample size: 4 participants (supersedes DRAFT_PLAN.md)
 
**What:** We keep the CP1 design: 4 external participants, 2 with code + README and 2 with
code + README + author-reviewed `HANDOFF.md`. `DRAFT_PLAN.md`'s "at least 6" is an earlier draft.
 
**Why:** Agreed in CP1 as realistic to recruit before the final report. Results with 4
people are reported as preliminary.
 
**Alternative rejected:** 6 participants (3 + 3), from the Phase 1 draft.
 
**Led by:** all team members.
 
## 2026-11-24 — HANDOFF.md format

**What:** `HANDOFF.md` is the only copy of the checklist: people read and edit it, and
`writer.parse` reads it back with regular expressions. There is no hidden data block and no
side JSON file. Layout, top to bottom:

1. A notice ("AI-drafted, may be incomplete"; definitions are in the appendix), the scanned
   scope and the status counts.
2. The coverage table as a matrix: one row per data boundary, one column per category. Each
   cell reads `A-01` (item found), `沒有處理（A-03）` (the code does not handle this at all),
   `檢查過，沒發現` (checked, nothing found) or `未檢查` (not checked: a gap). A legend sits
   right above the table. Plain words only, no symbols such as ⚠.
3. `## 項目`: one section per item, in the order ③ returns them; items added by hand go last.
   Heading: `### A-01 · <category> · <file>:<line>`. The four reader-facing lines use the
   fixed question format in Chinese (`**我的假設**`, `**問題**`, `**請給例子**`, `**影響**`);
   the machine fields below them use the field names from `models.py`
   (`- **status**: uncertain`).
4. The open question: 「你們的環境還有什麼常讓人踩雷、但我沒問到的？」
5. `## 附錄`: status definitions, category definitions, the evidence rules and a blank
   template for adding an item by hand.

Rules:
- One field per line. `write` and `mark` replace line breaks with spaces. Long samples go in a
  file, and the evidence holds its path. The drafter prompt asks for one sentence per field
  (bonginn).
- `parse` reads only `## 項目` and is strict: a line it does not recognise, a missing field or
  a value outside the allowed list is an error. It reports every error at once, each with the
  line number, the item id and how to fix it. `cli.py` prints these in plain words and exits
  with code 1 (Cactex).
- Items added by hand are numbered `H-01`, `H-02`, ... with `added_by: human`; AI items use
  `A-` (bonginn). `parse` rejects an item whose prefix and `added_by` disagree. Hand-added
  items do not appear in the coverage table, which shows only what the AI checked.
- `mark` also updates the status counts.

**Why:** With one file, what a person edits is exactly what the program reads, so the two
cannot disagree. One field per line keeps the regular expressions simple, and text inside a
value that looks like a heading or a label cannot be misread. A strict parser fails loudly
instead of quietly turning a hand-written `verified` into `uncertain`. The matrix shows the
unchecked cells, which is the point of the coverage table: the author sees the gaps instead of
trusting the list. Definitions go in an appendix so the receiving engineer reaches the first
item quickly. Separate prefixes stop the author and the receiver from both writing `A-04`.

**Alternative rejected:** Markdown plus a hidden JSON block, or a side `handoff.json` (two
copies drift apart). One big table, or a plain list (plan §4, decision 4). A lenient parser
that fills in defaults. Multi-line values. A coverage list with one row per checked cell (it
hides the gaps). Continuing the AI numbering for hand-added items.

**Led by:** 吳弘叡 (x85432).

## 2026-11-24 — Re-running scan does not overwrite an existing HANDOFF.md

**What:** If `HANDOFF.md` already exists, `write` refuses and says how many of its items were
marked; the user passes `--force` or another `-o` path (`cli.py` adds `--force`, Cactex). With
`force`, `write` writes a temporary file and swaps it in with `os.replace`, so a failure never
leaves a half-written file.

**Why:** Plan decision 7 scans twice: early in development and again before handoff. By the
second scan the old file may hold evidence that people recorded; overwriting it silently
loses their work.

**Alternative rejected:** Overwriting silently (loses evidence). Merging old and new items
automatically: matching them is unreliable, because line numbers drift after edits and the
LLM words the same assumption differently on each run; left for Phase 3. Checking only in
`cli.py`: anyone calling `write` directly (tests, the runner) would get no protection.

**Led by:** 吳弘叡 (x85432).

## 2026-11-24 — What `mark` records, and the evidence rules

**What:** `mark` changes one item's `status`, `evidence`, `evidence_type`, `marked_by`
(`git config user.name`) and `marked_at` (`YYYY-MM-DD HH:MM`, local time). Only the latest
mark is kept; git keeps the history, so commit `HANDOFF.md` after marking.

Evidence is a source plus a concrete result (a number, a format or an example) that answers
the item's question:

| `--type` | Source | Result | Example |
|---|---|---|---|
| `ask_owner` | who answered (role or team), when, where | their answer, close to their words | Cloud team on Discord, 11/26: after a disconnect the data is resent at once, up to 2 hours (about 120 records) |
| `inspect_sample` | where the sample came from, where it is saved | what was seen, with numbers | Sample after the 11/25 disconnect (`evidence/A-01.json`): 120 records in one push |
| `run_check` | the command and the version | its output | `pytest tests/test_batch.py` (commit abc123): trend correct for a batch of 120 |

`mark` enforces the minimum: `verified` and `mismatch` need `--type` and non-empty evidence,
and evidence that is only an empty phrase (`ok`, `沒問題`, `確認過`, `LGTM`, ...) is rejected.
Whether the source and the numbers make sense is for the PR reviewer to check. Samples saved
as evidence are de-identified excerpts, never whole real datasets.

**Why:** "Looks fine" without a source or a number is not evidence, and a handoff built on it
is what failed in Interview 2. `evidence_type` is kept apart from `verify_type` because the
receiver may verify differently from what the AI suggested. Keeping only the latest mark
keeps the format and `models.py` simple for CP2.

**Alternative rejected:** Keeping every mark as a history list in the file (a larger
interface change and harder parsing; Phase 3). Storing `--type` in `verify_type` (loses the
suggested method). No checks in the program at all.

**Led by:** 吳弘叡 (x85432).

## 2026-11-24 — The AI may find evidence but never mark an item verified

**What:** AI tools may run checks, inspect samples, record evidence (the status stays
`uncertain`) and mark an item `mismatch`. Only a person marks it `verified`:
- `writer.confirm_verified(item_id, path)` shows the evidence and asks `[y/N]`, and refuses
  when it is not run in an interactive terminal (no TTY). `cli.py` calls it before
  `writer.mark` (one line, Cactex). `--evidence` is optional when marking `verified`, so a
  person can confirm evidence that is already recorded.
- A mark made without a TTY is recorded as `marked_by: <name> [非互動]`. When a person later
  verifies with that evidence, the evidence gets a note saying where it came from:
  `（證據來自 <name> [非互動]，<time>）`.
- Without a TTY, a `verified` item can only be changed to `mismatch`, never back to
  `uncertain`. A `mismatch` item may go back to `uncertain` with new evidence.
- The AI never edits `HANDOFF.md` directly; statuses change only through `mark` (to be added
  to `AI_GUIDELINES.md`), and reviewers check status lines in diffs. `parse` rejects a
  `verified` item that lacks `marked_by`, `marked_at` or `evidence_type`, or whose
  `marked_by` has `[非互動]`, and a `mismatch` item that lacks `evidence`, `evidence_type` or
  `marked_at`.

These are speed bumps, not guarantees: the program cannot tell a person from an AI, and
anyone can fake the fields. The README will say so.

**Why:** The CP1 human-AI boundary says the AI never marks an item verified. The two
mistakes cost differently: a wrong `mismatch` costs a second look, while a wrong `verified`
hides the problem until deployment, as in Interview 2. AI agents usually run commands
without a TTY, so the confirmation is the one check that actually stops them. The logic
lives in `writer.py` so the rule and its tests stay with ④; `cli.py` only calls it.

**Alternative rejected:** Rules only, no checks in the program. The AI only pasting evidence
into chat while people type every `mark` (more copying, no safer). The confirmation logic in
`cli.py` (the rule would sit in another owner's file). Not recording that a mark was made
non-interactively. Letting non-interactive runs reset `verified` to `uncertain` (a person's
evidence would be overwritten without anyone saying what is wrong).

**Led by:** 吳弘叡 (x85432).

## 2026-11-24 — Proposed interface change for ④ (not agreed yet)

**Status:** proposed. To be raised in Discord first, then made in its own PR that changes only
`models.py`, the signature of `writer.write` and `tests/test_contract.py`.

**What:**
- `Assumption` gains `evidence_type: Optional[VerifyType] = None`, `marked_by: str = ""` and
  `marked_at: str = ""`.
- `writer.write(result, out_path, scope)` becomes
  `writer.write(result, out_path, scope, force=False)`.

Every new field and parameter has a default, so ①–③ keep working unchanged.

**Why:** Without these fields `parse` cannot read back what `mark` writes. Without `force`,
`write` cannot refuse to overwrite by default and still allow `--force`.

**Alternative rejected:** Writing these fields into the Markdown but skipping them in `parse`
(a parse-then-write round trip would drop them). Relying on `git log` for who and when (marks
are not always committed).

**Led by:** 吳弘叡 (x85432).
