"""Render docs/images/solution.gif: how the handoff goes when our tool is used, as a black box.

    python3 docs/images/make_solution_gif.py             # writes docs/images/solution.gif
    python3 docs/images/make_solution_gif.py --frame 12  # writes one PNG at t=12s, for checking

The tool is shown only by what goes in and what comes out. The bottom bars contrast the
weekly break-ask-fix rounds from problem.gif with checking everything before the first
deploy. The bar lengths illustrate the intent; they are not measured results.
To change wording, edit CAPTIONS, PILLS and the timing constants below.
"""

import os

from gif_common import (CAPTION_BG, CORAL, FONT, NEUTRAL, PURPLE, RED, TEAL,
                        arrow, build_gif, caption_at, ease, rect, text)

W, H = 680, 488
TOTAL = 20.5

PILLS = ["one-by-one arrival", "fields never null", "angle sign", "timestamp format"]
MISMATCH = [True, True, False, True]  # what the receiving engineer finds for each item

SCAN = 2.6       # inputs flow into the tool
DRAFT = 5.0      # HANDOFF.md appears, items listed one by one
REVIEW = 7.4     # author reviews and hands over
VERIFY = 9.0     # receiving engineer checks each item
FIX = 11.6       # mismatches fixed before deploy
DEPLOY = 13.0    # deploy once
CUT = 14.2       # the weekly rounds are cut off
FINAL = 15.8

CAPTIONS = [  # (start time, line 1, line 2)
    (0.0, "Without a list, each hidden assumption costs a week of break, ask, fix.", ""),
    (SCAN, "Before integration, the author runs our tool on code, mocks and specs.", ""),
    (DRAFT, "It drafts HANDOFF.md: each assumption, where it is, and how to check it.", ""),
    (REVIEW, "The author reviews the list and hands it over in the PR.", ""),
    (VERIFY, "The receiving engineer checks each item against the real environment.", ""),
    (FIX, "Mismatches are fixed before the first deploy, not after.", ""),
    (DEPLOY, "Deploy once.", ""),
    (CUT, "The gap is closed before deployment, not one failure at a time.", ""),
    (FINAL, "Goal: catch mismatches before integration and deploy once.",
     "Whether this shortens real handoffs is what our evaluation will measure."),
]

PILL_Y = [106, 134, 162, 190]
ROW_Y = [174, 192, 210, 228]


def listed_at(i):
    return DRAFT + 0.3 + 0.45 * i


def verified_at(i):
    return VERIFY + 0.2 + 0.55 * i


def fixed_at(i):
    k = sum(MISMATCH[:i])
    return FIX + 0.3 + 0.35 * k


def item_state(i, t):
    """hidden -> listed -> ok / mismatch -> fixed."""
    if MISMATCH[i] and t >= fixed_at(i):
        return "fixed"
    if t >= verified_at(i):
        return "mismatch" if MISMATCH[i] else "ok"
    if t >= listed_at(i):
        return "listed"
    return "hidden"


def frame_svg(t):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']

    # Team boundary (the card later sits on top of it, bridging the gap)
    p.append(text(340, 26, "team boundary", 12, fill=NEUTRAL["sub"]))
    p.append('<line x1="340" y1="40" x2="340" y2="250" stroke="#888780" '
             'stroke-width="1" stroke-dasharray="5 5"/>')

    # Left: author side
    p.append(rect(20, 40, 230, 210, PURPLE["fill"], PURPLE["stroke"], rx=16))
    p.append(text(135, 58, "Author (mock side)", 14, 500, PURPLE["text"]))
    p.append(rect(36, 74, 198, 162, NEUTRAL["fill"], NEUTRAL["stroke"]))
    p.append(text(135, 90, "Code + mocks + spec", 14, 500, NEUTRAL["text"]))
    for i, label in enumerate(PILLS):
        st = item_state(i, t)
        y = PILL_Y[i]
        if st in ("ok", "fixed"):
            c, dash, shown = TEAL, None, "✓ " + label
        elif st == "mismatch":
            c, dash, shown = RED, None, "✗ " + label
        elif st == "listed":
            c, dash, shown = PURPLE, None, label
        else:
            c, dash, shown = CORAL, "4 3", label
        p.append(rect(50, y, 170, 22, c["fill"], c["stroke"], rx=5, dash=dash))
        p.append(text(135, y + 11, shown, 12, fill=c["text"]))

    # Inputs flowing into the tool
    for i in range(4):
        s = SCAN + 0.2 + 0.4 * i
        if s <= t <= s + 0.9:
            e = ease((t - s) / 0.9)
            x = 222 + (276 - 222) * e
            y = PILL_Y[i] + 11 + (98 - PILL_Y[i] - 11) * e
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{PURPLE["dot"]}"/>')

    # The tool, as a black box
    busy = SCAN <= t < DRAFT + 0.4
    p.append(rect(272, 74, 136, 48, "#2C2C2A", PURPLE["dot"] if busy else "#2C2C2A",
                  sw=2.5 if busy else 1))
    p.append(text(340, 91, "Our tool", 14, 500, "#FFFFFF"))
    p.append(text(340, 108, "(black box)", 12, fill="#D3D1C7"))

    # HANDOFF.md card, sitting across the team boundary
    card = ease((t - DRAFT) / 0.4)
    if card > 0:
        y0 = 124 + 10 * card
        reviewing = REVIEW <= t
        stroke = PURPLE["stroke"] if reviewing else NEUTRAL["stroke"]
        p.append(f'<g opacity="{card:.3f}">')
        p.append(rect(256, y0, 168, 112, "#FFFFFF", stroke, rx=8, sw=1.5 if reviewing else 1))
        p.append(text(266, y0 + 14, "HANDOFF.md", 12, 500, NEUTRAL["text"], anchor="start"))
        tag = ease((t - (REVIEW + 0.6)) / 0.3)
        if tag > 0:
            p.append(text(414, y0 + 14, "reviewed ✓", 11, fill=PURPLE["text"],
                          anchor="end", op=tag))
        p.append(f'<line x1="262" y1="{y0 + 25:.1f}" x2="418" y2="{y0 + 25:.1f}" '
                 f'stroke="{NEUTRAL["stroke"]}" stroke-width="0.8"/>')
        for i, label in enumerate(PILLS):
            st = item_state(i, t)
            if st == "hidden":
                continue
            op = ease((t - listed_at(i)) / 0.25)
            icon, color = {"listed": ("○", NEUTRAL["text"]),
                           "ok": ("✓", TEAL["stroke"]),
                           "fixed": ("✓", TEAL["stroke"]),
                           "mismatch": ("✗", RED["stroke"])}[st]
            ry = ROW_Y[i] + (y0 - 134)
            p.append(text(268, ry, icon + "  " + label, 12, fill=color, anchor="start", op=op))
        p.append("</g>")

    # Right: real environment
    p.append(rect(430, 40, 230, 210, TEAL["fill"], TEAL["stroke"], rx=16))
    p.append(text(545, 58, "Real environment", 14, 500, TEAL["text"]))
    p.append(rect(446, 74, 198, 62, NEUTRAL["fill"], NEUTRAL["stroke"]))
    p.append(text(545, 89, "Cloud data stream", 14, 500, NEUTRAL["text"]))
    if t >= DEPLOY + 0.4:
        p.append(text(545, 106, "batches handled ✓", 12, 500, TEAL["stroke"]))
    else:
        p.append(text(545, 106, "arrives in batches", 12, fill=NEUTRAL["sub"]))
    spawn = 0.3
    while spawn <= t:
        for k in range(5):
            x = 462 + (t - spawn) * 110 - k * 7
            if 460 <= x <= 630:
                p.append(f'<circle cx="{x:.1f}" cy="123" r="3.5" fill="{TEAL["dot"]}"/>')
        spawn += 1.6
    p.append(rect(446, 146, 198, 90, NEUTRAL["fill"], NEUTRAL["stroke"]))
    p.append(text(545, 164, "Receiving engineer", 14, 500, NEUTRAL["text"]))
    p.append(text(545, 182, "checks each item", 12, fill=NEUTRAL["sub"]))
    status, scolor = "", NEUTRAL["sub"]
    if VERIFY <= t < FIX:
        cur = max([i for i in range(4) if t >= verified_at(i) - 0.5] or [0])
        status = "checking: " + PILLS[cur]
    elif FIX <= t < DEPLOY:
        status, scolor = f"{sum(MISMATCH)} mismatches sent back", RED["stroke"]
    elif t >= DEPLOY:
        status, scolor = "deployed once, works ✓", TEAL["stroke"]
    if status:
        p.append(text(545, 212, status, 12, 500, scolor))

    # Handover arrow to the receiving engineer
    hand = ease((t - (REVIEW + 1.0)) / 0.4)
    if hand > 0:
        p.append(arrow(426, 190, 443, 190, PURPLE["stroke"], op=hand, sw=1.5))

    # Bottom: path length, without vs with the list
    p.append(text(20, 290, "Without a list", 12, 500, NEUTRAL["text"], anchor="start"))
    for i in range(3):
        g = ease((t - (0.3 + 0.45 * i)) / 0.4)
        if g > 0:
            x = 140 + i * 168
            p.append(rect(x, 278, 160 * g, 24, CORAL["fill"], CORAL["stroke"], rx=5))
            if g > 0.9:
                p.append(text(x + 80, 290, f"Round {i + 1} · ~1 week", 12, fill=CORAL["text"]))

    p.append(text(20, 330, "With the list", 12, 500, NEUTRAL["text"], anchor="start"))
    segs = [("scan", 48, SCAN + 0.2, SCAN + 2.0, PURPLE),
            ("review", 52, REVIEW, REVIEW + 1.2, TEAL),
            ("verify", 62, VERIFY, FIX - 0.2, TEAL),
            ("fix", 38, FIX, DEPLOY - 0.2, TEAL),
            ("deploy ✓", 66, DEPLOY, DEPLOY + 0.8, TEAL)]
    x = 140
    for label, w, s, e, c in segs:
        g = ease((t - s) / (e - s))
        if g > 0:
            p.append(rect(x, 318, w * g, 24, c["fill"], c["stroke"], rx=5))
            if g > 0.9:
                p.append(text(x + w / 2, 330, label, 12, fill=c["text"]))
        x += w + 4

    # The cut: the weekly rounds past the end of the short path fade away
    cut = ease((t - CUT) / 0.5)
    if cut > 0:
        end = x - 4 + 6
        p.append(f'<line x1="{end}" y1="270" x2="{end}" y2="{270 + 82 * cut:.1f}" '
                 f'stroke="{RED["stroke"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        fade = ease((t - CUT - 0.4) / 0.5)
        if fade > 0:
            p.append(rect(end + 2, 276, 640 - end, 28, "#FFFFFF", "#FFFFFF", rx=0, op=0.72 * fade))
            p.append(f'<line x1="{end + 4}" y1="290" x2="636" y2="290" stroke="#888780" '
                     f'stroke-width="1.2" opacity="{fade:.3f}"/>')
            p.append(text((end + 640) / 2, 364, "weekly rework rounds avoided (goal)", 12, 500,
                          RED["text"], op=fade))

    # Caption
    cap = caption_at(CAPTIONS, t)
    fade = ease((t - cap[0]) / 0.3)
    p.append(rect(20, 384, 640, 64, CAPTION_BG, CAPTION_BG, rx=10))
    if cap[2]:
        p.append(text(340, 405, cap[1], 14, 500, NEUTRAL["text"], op=fade))
        p.append(text(340, 427, cap[2], 13, fill=NEUTRAL["sub"], op=fade))
    else:
        p.append(text(340, 416, cap[1], 14, 500, NEUTRAL["text"], op=fade))
    p.append(text(660, 470, "Illustration of the intended workflow, not a measured result", 11,
                  fill=NEUTRAL["sub"], anchor="end"))
    p.append("</svg>")
    return "".join(p)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build_gif(frame_svg, TOTAL, (W, H), os.path.join(here, "solution.gif"))
