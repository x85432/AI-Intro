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

## 2026-11-23 — LLM for the drafter: Gemini instead of Claude

**What:** The drafter (③) calls the Gemini API through the `google-genai` SDK. Default model
`gemini-3.6-flash`, overridable with `HANDOFF_MODEL`. The key is read from `GEMINI_API_KEY`
in the environment and never stored in the repo. Output is constrained with Gemini's
structured output (JSON schema), then checked against the input files.

**Why:** Gemini is free and unlimited for our team.

**Alternative rejected:** Claude API with `claude-opus-5-5` and `messages.parse`, as first
planned in docs/CP2_PLAN.md §4 #6.

**Led by:** 鐘邦郡 (bonginn)

**Follow-up:** `handoff/README.md` and `docs/CP2_PLAN.md` still mention Claude / `ANTHROPIC_API_KEY`.
 