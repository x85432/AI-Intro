# Section 1 - What AI tools we plan to use, and what we will use each for

**Definition:** "Spec" means a written requirements document, either from the course or one we wrote ourselves.

1. **With a spec**, we use Claude Code with `Opus` in plan mode to draft the implementation plan, not to start coding before the code steward approves the plan.

2. **Without a spec**, we use Claude `Sonnet` to brainstorm ideas and find related literature, not to decide what we build. A human must verify every source it cites.

3. **Without a spec**, after brainstorming we use Claude Code with `Opus` in plan mode to turn the chosen idea into a plan, not to make the final architecture decision. That is a team discussion, recorded in `DECISIONS.md`.

4. **For implementation**, we use Claude Code with `Sonnet` to build the approved plan on a feature branch, not to push to `main`, and not for authentication, payment, or personal-data logic, which a human writes. A PR is merged only after an approval from someone other than its author that comments on at least one specific file or line of the diff: a question, a concern, or an explanation in the reviewer's own words. An approval with no comment does not count.

5. **For testing**, we use Claude `Sonnet` to generate test skeletons, not to declare the work done. If the AI wrote the tests, the PR's "What I changed afterwards" names at least one test case a human added or changed, and why. If it says "None", the steward requests changes.

6. **For quick questions**, we use Claude `Haiku` for syntax lookups, error messages, and first-draft docstrings, not for code that gets merged without review.

7. **For commits**, AI never runs `git add` or `git commit` for us. A human chooses which files to stage and reviews what is staged. We may ask Claude for message suggestions, but a human condenses them into our fixed format: `feature: ...`, `fix: ...`, or `modify: ...`. Each commit does one thing only.

8. **We never use AI** to write our PR descriptions or the reasoning in `DECISIONS.md`, and we never paste API keys, passwords, `.env` files, or personal data into any AI tool.

---

# Section 2 - How we will document AI interactions

1. **Prompt engineering log:** Every prompt that produces code, tests, or documentation that ends up in the repo, even partially, goes in the prompt engineering log. Each entry records the prompt text, the model used, and what we kept vs. changed.

2. **No log needed:** One-off questions, such as syntax lookups or error message explanations, do not need an entry unless they lead to a change in the repo.

3. **Collaboration log:** When the team discusses, compares, or revises an AI output before adopting it (for example, AI proposes a different approach or compares technical options), we record the process in the collaboration log.

4. **`DECISIONS.md`:** If an AI suggestion changes our approach or influences a technical decision, the final decision and the reason go in `DECISIONS.md`, written by a human.

5. **PR description:** Every PR fills in the template's "AI assistance" section (tool and model, what it generated, what we changed afterwards) and links its prompt-log entry. "No AI used" is allowed; an empty section or leftover placeholder text is not, and the steward does not approve until it is filled in. The description itself is written by a human (see Section 1).

---

# Section 3 - How we will handle disagreements about AI output quality

1. **Who decides**: If two teammates disagree about whether AI-generated output (code, tests, docs, or a plan) is good enough to adopt, the code steward has final say, not whoever wrote the prompt and not whoever has more experience. If the code steward is the one who generated the output, another teammate they name in DECISIONS.md makes the call instead.

2. **Evidence required before a merge decision**: The code passes the existing test suite and the PR review checklist, and someone other than its author can explain what it does and why (same rule as Section 1, #4). For AI-generated plans, the evidence is that the plan traces back to the spec, or to the chosen idea recorded in DECISIONS.md when there is no spec.

3. **Sources and claims**: If the disagreement is about whether an AI-cited paper, API, or fact is real or correct, the person who wants to use it must verify it against the original source. Unverified AI claims don't go into the repo or the report.

4. **Style vs. correctness**: If the disagreement is about style or preference rather than correctness, we defer to our style guide and linter config instead of debating case by case.

5. **Tie-breaking**: A vote is not evidence, and "it looks fine" is not evidence. If the criteria above don't settle it, the code steward's call is final and gets one sentence in DECISIONS.md explaining why, written by a human.

---

# Revision history

- **2026-11-25 (Week 12 lab):** rewrote Section 1 #4, Section 1 #5 and Section 2 #5 so a teammate can check each one from a PR. Evidence: the approvals on #9–#13 had no comment, and #13 was merged two minutes after it was opened; #12 and #15 say "What I changed afterwards: None"; #9–#11 say nothing about AI use, and only #14 links a prompt-log entry; Group 11's review found unfilled placeholder text in #13 (issue #19).
