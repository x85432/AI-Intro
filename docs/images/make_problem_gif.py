"""Render docs/images/problem.gif: the problem our tool addresses, as a short animation.

    python3 docs/images/make_problem_gif.py            # writes docs/images/problem.gif
    python3 docs/images/make_problem_gif.py --frame 9  # writes one PNG at t=9s, for checking

To change wording, edit CAPTIONS, PILLS and ROUNDS below. Drawing helpers and the
SVG -> GIF pipeline live in gif_common.py.
"""

import os

from gif_common import (CAPTION_BG, CORAL, FIXED, FONT, NEUTRAL, PURPLE, RED, TEAL,
                        build_gif, caption_at, ease, rect, text)

W, H = 680, 484
TOTAL = 20.0

PILLS = [  # (label, x, y) inside the code box
    ("one-by-one arrival", 48, 192),
    ("fields never null", 174, 192),
    ("angle sign", 48, 228),
    ("timestamp format", 174, 228),
]

# Each round: which pill breaks, what the other team says, and phase lengths in seconds.
ROUNDS = [
    dict(start=7.2, pill=0, reply="Data can arrive in 2-hour batches.",
         deploy=1.0, brk=1.0, ask=1.2, fix=0.8),
    dict(start=11.2, pill=1, reply="Oh, that field can be null.",
         deploy=0.6, brk=0.7, ask=0.8, fix=0.6),
    dict(start=13.9, pill=3, reply="Timestamps are in UTC.",
         deploy=0.5, brk=0.7, ask=1.0, fix=None),
]
FINAL_START = 16.1

CAPTIONS = [  # (start time, line 1, line 2)
    (0.0, "The author develops against a local mock that sends one record at a time.", ""),
    (2.6, "The code quietly relies on assumptions nobody wrote down.", ""),
    (4.8, "The real environment is run by another team, and it behaves differently.", ""),
    (7.2, "After deployment, data arrives in batches and the code breaks.", ""),
    (9.2, "Asking the other team reveals why. Fix, redeploy, wait about a week.", ""),
    (11.2, "Redeploy, and the next unwritten assumption breaks.", ""),
    (13.9, "And the next one.", ""),
    (FINAL_START, "Unwritten assumptions surface only after deployment, one at a time.",
     "Each costs a round of questions and rework (about a week), and some stay hidden."),
]



def round_phase(t):
    """Return (round index, phase name, progress in phase) or (None, None, 0)."""
    for i, r in enumerate(ROUNDS):
        edges = [("deploy", r["deploy"]), ("break", r["brk"]), ("ask", r["ask"])]
        if r["fix"]:
            edges.append(("fix", r["fix"]))
        start = r["start"]
        for name, length in edges:
            if start <= t < start + length:
                return i, name, (t - start) / length
            start += length
    return None, None, 0.0


def pill_state(i, t):
    for r in ROUNDS:
        if r["pill"] != i:
            continue
        broke_at = r["start"] + r["deploy"]
        fixed_at = broke_at + r["brk"] + r["ask"] if r["fix"] else None
        if fixed_at is not None and t >= fixed_at + r["fix"] * 0.5:
            return "fixed"
        if t >= broke_at:
            return "broken"
    return "hidden"


def frame_svg(t):
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="{FONT}">')
    p.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

    # Team boundary
    p.append(text(340, 26, "team boundary", 12, fill=NEUTRAL["sub"]))
    p.append(f'<line x1="340" y1="40" x2="340" y2="270" stroke="#888780" '
             f'stroke-width="1" stroke-dasharray="5 5"/>')

    # Left: author side
    p.append(rect(20, 40, 300, 230, PURPLE["fill"], PURPLE["stroke"], rx=16))
    p.append(text(170, 62, "Author (develops against a mock)", 14, 500, PURPLE["text"]))
    p.append(rect(40, 82, 260, 64, NEUTRAL["fill"], NEUTRAL["stroke"]))
    p.append(text(170, 98, "Local simulation", 14, 500, NEUTRAL["text"]))
    p.append(text(170, 116, "sends one record at a time", 12, fill=NEUTRAL["sub"]))
    spawn = 0.2
    while spawn <= t:
        x = 58 + (t - spawn) * 110
        if x <= 282:
            p.append(f'<circle cx="{x:.1f}" cy="134" r="4" fill="{PURPLE["dot"]}"/>')
        spawn += 0.5

    p.append(rect(40, 158, 260, 104, NEUTRAL["fill"], NEUTRAL["stroke"]))
    p.append(text(170, 176, "Code", 14, 500, NEUTRAL["text"]))
    for i, (label, x, y) in enumerate(PILLS):
        appear = ease((t - (2.6 + 0.45 * i)) / 0.3)
        if appear <= 0:
            continue
        state = pill_state(i, t)
        if state == "broken":
            c, dash, shown = RED, None, "✗ " + label
        elif state == "fixed":
            c, dash, shown = FIXED, None, "✓ " + label
        else:
            c, dash, shown = CORAL, "4 3", label
        p.append(rect(x, y, 118, 26, c["fill"], c["stroke"], rx=5, dash=dash, op=appear))
        p.append(text(x + 59, y + 13, shown, 12, fill=c["text"], op=appear))

    # Right: real environment
    right = ease((t - 4.8) / 0.6)
    if right > 0:
        p.append(f'<g opacity="{right:.3f}">')
        p.append(rect(360, 40, 300, 230, TEAL["fill"], TEAL["stroke"], rx=16))
        p.append(text(510, 62, "Real environment (another team)", 14, 500, TEAL["text"]))
        p.append(rect(380, 82, 260, 64, NEUTRAL["fill"], NEUTRAL["stroke"]))
        p.append(text(510, 98, "Cloud data stream", 14, 500, NEUTRAL["text"]))
        p.append(text(510, 116, "sometimes 2 hours arrive at once", 12, fill=NEUTRAL["sub"]))
        spawn = 5.2
        while spawn <= t:
            for k in range(5):
                x = 398 + (t - spawn) * 120 - k * 8
                if 396 <= x <= 624:
                    p.append(f'<circle cx="{x:.1f}" cy="134" r="4" fill="{TEAL["dot"]}"/>')
            spawn += 1.5
        p.append(rect(380, 158, 260, 104, NEUTRAL["fill"], NEUTRAL["stroke"]))
        p.append(text(510, 178, "Cloud engineer", 14, 500, NEUTRAL["text"]))
        p.append(text(510, 196, "doesn't know what the code relies on", 12, fill=NEUTRAL["sub"]))
        ri, phase, prog = round_phase(t)
        if phase in ("ask", "fix"):
            op = ease(prog / 0.25) if phase == "ask" else 1 - ease((prog - 0.5) / 0.5)
            reply = ROUNDS[ri]["reply"]
        elif t >= FINAL_START:
            op, reply = 1.0, ROUNDS[-1]["reply"]
        else:
            op, reply = 0.0, ""
        if op > 0:
            p.append(rect(392, 214, 236, 34, "#FFFFFF", TEAL["stroke"], rx=10, op=op))
            p.append(text(510, 231, "“" + reply + "”", 12, fill=TEAL["text"], op=op))
        p.append("</g>")

    # Deploy: the code travels across the boundary
    ri, phase, prog = round_phase(t)
    if phase == "deploy":
        e = ease(prog)
        x = 250 + (470 - 250) * e
        y = 210 + (112 - 210) * e
        op = 1 - ease((prog - 0.8) / 0.2)
        p.append(rect(x, y, 60, 22, PURPLE["fill"], PURPLE["stroke"], rx=5, op=op))
        p.append(text(x + 30, y + 11, "deploy", 12, 500, PURPLE["text"], op=op))

    # Bottom: the rework loop
    steps_op = ease((t - 6.6) / 0.5)
    if steps_op > 0:
        labels = [("Deploy", "works locally"), ("It breaks", "plot is garbled"),
                  ("Ask the other team", "only then learn why"), ("Fix & redeploy", "wait for new data")]
        active = {"deploy": 0, "break": 1, "ask": 2, "fix": 3}.get(phase)
        for i, (title, sub) in enumerate(labels):
            x = 20 + i * 161
            if active == i:
                c = RED if i == 1 else PURPLE
                fill, stroke, tc, sc = c["fill"], c["stroke"], c["text"], c["text"]
                sw = 1.5
            else:
                fill, stroke, tc, sc = NEUTRAL["fill"], NEUTRAL["stroke"], NEUTRAL["text"], NEUTRAL["sub"]
                sw = 1
            p.append(f'<g opacity="{steps_op:.3f}">')
            p.append(rect(x, 288, 135, 54, fill, stroke, sw=sw))
            p.append(text(x + 67.5, 305, title, 13, 500, tc))
            p.append(text(x + 67.5, 324, sub, 12, fill=sc))
            if i < 3:
                ax = x + 139
                p.append(f'<line x1="{ax}" y1="315" x2="{ax + 18}" y2="315" stroke="#888780" '
                         f'stroke-width="1.2"/><path d="M{ax + 13} 311 L{ax + 18} 315 L{ax + 13} 319" '
                         f'fill="none" stroke="#888780" stroke-width="1.2"/>')
            p.append("</g>")
        shown_round = None
        for i, r in enumerate(ROUNDS):
            if t >= r["start"]:
                shown_round = i
        if shown_round is not None:
            n = shown_round + 1
            label = "Round 1 · about 1 week" if n == 1 else f"Round {n} · about {n} weeks so far"
            p.append(text(340, 362, label, 13, 500, NEUTRAL["text"]))

    # Caption
    cap = caption_at(CAPTIONS, t)
    fade = ease((t - cap[0]) / 0.3)
    p.append(rect(20, 382, 640, 66, CAPTION_BG, CAPTION_BG, rx=10))
    if cap[2]:
        p.append(text(340, 404, cap[1], 14, 500, NEUTRAL["text"], op=fade))
        p.append(text(340, 426, cap[2], 13, fill=NEUTRAL["sub"], op=fade))
    else:
        p.append(text(340, 415, cap[1], 14, 500, NEUTRAL["text"], op=fade))
    p.append(text(660, 468, "Example based on our Interview 2 (CP1)", 11,
                  fill=NEUTRAL["sub"], anchor="end"))
    p.append("</svg>")
    return "".join(p)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build_gif(frame_svg, TOTAL, (W, H), os.path.join(here, "problem.gif"))
