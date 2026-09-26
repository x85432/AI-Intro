# Problem Grounding
Who specifically has the problem?
Two people on each side of the handoff. One is a developer or analyst (often junior, a contractor, or on a different team) who writes business logic against mocked API responses or sample data because they lack production credentials. The other is the platform or backend engineer who has those credentials and must connect the code to real cloud APIs and data.

# What do they currently do instead?
The author writes a README or explains in a meeting, and the receiving engineer reads the code and tries running it in the real environment. When something breaks, the two go back and forth on Slack/Teams. Assumptions baked into the mocks (field names, response shapes, auth flow, pagination, rate limits, null handling) are rarely written down, so they surface one error at a time.

What would be observably different if the tool worked?
The receiving engineer would get the code running against real APIs with fewer back-and-forth messages and fewer mock-vs-real mismatch bugs, because the handoff would list up front every assumption that needs verifying in the real environment.

# Evaluation Plan Draft
Success definition
We will know our tool works if receiving engineers using the tool's handoff package reach a first successful run against the real API faster, with fewer clarification messages to the author, and find more of the mock-vs-real mismatches before running the code, compared with engineers who receive only the code and a README.

AI vs. human decisions: The AI scans the code to find mocks, stubs, hard-coded sample data, and implicit assumptions, then drafts a "verify in real environment" checklist and handoff notes. The author confirms or corrects each item before handoff, and the receiving engineer decides how to fix each mismatch. Humans stay in the loop, so success means the AI's flagged assumptions are real and relevant enough to be worth reviewing. We measure this as the share of real mismatches the checklist caught (recall) and the share of flagged items that turned out to matter (precision).

# Target users
Working engineers and developers from our own workplaces, internships, and professional networks. Participants with backend or cloud experience play the receiving engineer role. Real company code usually can't be shared, so we will build a small test project ourselves: logic written against a mock API, plus a "real" API (a public API or one we host) whose responses differ from the mock in several planted ways.

# Method
Structured observation with a short follow-up interview. Each participant receives the handoff package and must get the code working against the real API. We log time to first successful run, number of questions asked, and which planted mismatches they found before versus after running. A 10-minute interview afterward covers what they trusted in the handoff and what was missing. Pilot with 1–2 people around CP1, main sessions after that.

# Minimum evidence threshold
At least 6 receiving-engineer participants (3 with the tool's package, 3 with code + README only). Convincing evidence would be: the AI checklist catches most planted mismatches (for example, 5 of 6 or better), the tool group reaches a working run faster in most sessions, and participants rate most flagged items as useful rather than noise.