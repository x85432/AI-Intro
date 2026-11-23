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
- **What I kept or changed:** After I verify the code, it is really well. I unchange anything.
- **Verification:** Ran `python simulator.py` and confirmed that it produced the expected `flat`, `rising`, and `falling` outputs.
- **Notes:** The AI also added a `print` statement and an `if __name__ == "__main__"` guard.

## Entry 2: Detector implementation and tests

- **Date:** 2026-11-23
- **Author:** DanielTeng0811
- **Tool and model:** Claude Code, Sonnet 5.5
- **Prompt:** “Please implement it, and I will verify it. Is this part of PR 1?”. Before implementation, the AI proposed AST traversal, a text-matching fallback for syntax errors, and rules for six detection categories. I agreed to the approach.
- **Output:** The implementation in `handoff/detector.py` and 10 tests in `tests/test_detector.py`.
- **What I kept or changed:** After I verify the code, it is really well. I unchange anything.
- **Verification:** All 14 pytest tests passed, including the contract tests. Scanning `stream_demo` returned three hits: one fixture, one boundary, and one simulation. I also asked the AI to explain `detector.py` section by section and read through the implementation myself.
- **Known limitations:** `_is_stub` may flag ordinary functions that return constants. Data entering through function parameters is not detected.
