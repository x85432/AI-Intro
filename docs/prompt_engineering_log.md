# Prompt Engineering Log

Every prompt that produces code, tests, or documentation that ends up in the repo goes here
(see `AI_GUIDELINES.md`, Section 2). Each entry records the prompt, the model, and what we kept
versus changed. Add new entries at the bottom.

## Entry 1: Minimal `examples/stream_demo/`

- **Date:** 2026-11-23
- **Author:** DanielTeng0811
- **Tool and model:** Claude Code, Sonnet 5.5
- **Prompt:**  “Can you help me implement it?”, after I provided the stream demo specification and `FAKE_FILES` as a reference. The request was to create minimal versions of `trend.py`, `simulator.py`, and `fixtures/readings.json` based on `FAKE_FILES` in `handoff/fakes.py`.
- **Output:** The three files listed above.
- **What I kept or changed:** Kept unchanged after reviewing the generated code.
- **Verification:** Ran `python simulator.py` and confirmed that it produced the expected `flat`, `rising`, and `falling` outputs.
- **Notes:** The AI also added a `print` statement and an `if __name__ == "__main__"` guard. `trend.py` and `fixtures/readings.json` were later replaced by the full version in Entry 3.

## Entry 2: Detector implementation and tests

- **Date:** 2026-11-23
- **Author:** DanielTeng0811
- **Tool and model:** Claude Code, Sonnet 5.5
- **Prompt:** “Please implement it, and I will verify it. Is this part of PR 1?”. Before implementation, the AI proposed AST traversal, a text-matching fallback for syntax errors, and rules for six detection categories. I agreed to the approach.
- **Output:** The implementation in `handoff/detector.py` and 10 tests in `tests/test_detector.py`.
- **What I kept or changed:** Kept unchanged after reviewing the generated code.
- **Verification:** All 14 pytest tests passed, including the contract tests. Scanning `stream_demo` returned three hits: one fixture, one boundary, and one simulation. I also asked the AI to explain `detector.py` section by section and read through the implementation myself.
- **Known limitations:** `_is_stub` may flag ordinary functions that return constants. Data entering through function parameters is not detected.

## Entry 3: Full `stream_demo` with six planted assumptions and `expected.json`

- **Date:** 2026-11-23
- **Author:** DanielTeng0811
- **Tool and model:** Claude Code, Sonnet 5.5
- **Prompt:** “Then please go ahead and do it first”, after I described the six assumptions to plant (batching, null, format, ordering, units, volume/interval) and the `expected.json` format from `docs/CP2_PLAN.md`. The request was to extend `examples/stream_demo/` so it contains all six assumptions, with no hint comments, plus an answer key.
- **Output:** A rewritten `examples/stream_demo/trend.py` (moving average over the last 5 readings), a new `examples/stream_demo/fixtures/readings.json` (13 readings with clearer trends), and `examples/stream_demo/expected.json` (6 entries: `id`, `category`, `file`, `line`, `assumption`, `real_env`).
- **What I kept or changed:** I read all generated files and kept the code. I made one change after generation: the AI had added an extra `basis` field to each `expected.json` entry. I had it removed, because that field is not in the agreed format and could break the prompt-test runner. G-1 is from Interview 2 and G-2 to G-6 are illustrative; this is stated in the PR description instead.
- **Verification:** Ran `python simulator.py` and saw `rising`, `flat` and `falling` outputs. Checked that every `line` in `expected.json` points to the intended line in `trend.py` and that every entry has exactly the six agreed fields.
- **Known limitations:** The assumptions are planted by the AI's design, so the same kind of tool may find them more easily than a real project's. Line numbers must be updated if `trend.py` changes.
