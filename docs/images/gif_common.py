"""Shared drawing helpers and the SVG -> PNG -> GIF pipeline for the README animations.

Frames are drawn as SVG strings, rendered by headless Chrome, and joined by ffmpeg.
Only the Python standard library is needed, plus Chrome and ffmpeg.
"""

import argparse
import hashlib
import os
import queue
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FPS = 10
OUT_WIDTH = 800
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

PURPLE = dict(fill="#EEEDFE", stroke="#534AB7", text="#3C3489", dot="#7F77DD")
TEAL = dict(fill="#E1F5EE", stroke="#0F6E56", text="#085041", dot="#1D9E75")
NEUTRAL = dict(fill="#FFFFFF", stroke="#B4B2A9", text="#2C2C2A", sub="#5F5E5A")
CORAL = dict(fill="#FAECE7", stroke="#D85A30", text="#712B13")
RED = dict(fill="#FCEBEB", stroke="#E24B4A", text="#791F1F")
FIXED = dict(fill="#F1EFE8", stroke="#888780", text="#444441")
CAPTION_BG = "#F1EFE8"


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rect(x, y, w, h, fill, stroke, rx=8, sw=1, dash=None, op=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op:.3f}"/>')


def text(x, y, s, size=14, weight=400, fill="#2C2C2A", anchor="middle", op=1.0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="central" '
            f'opacity="{op:.3f}">{esc(s)}</text>')


def arrow(x1, y1, x2, y2, color="#888780", op=1.0, sw=1.2):
    """Straight arrow with an open chevron head at (x2, y2)."""
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    hx1 = x2 - 6 * math.cos(ang - 0.5)
    hy1 = y2 - 6 * math.sin(ang - 0.5)
    hx2 = x2 - 6 * math.cos(ang + 0.5)
    hy2 = y2 - 6 * math.sin(ang + 0.5)
    return (f'<g opacity="{op:.3f}" stroke="{color}" stroke-width="{sw}" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
            f'<path d="M{hx1:.1f} {hy1:.1f} L{x2:.1f} {y2:.1f} L{hx2:.1f} {hy2:.1f}"/></g>')


def caption_at(captions, t):
    """Pick the caption whose start time is the latest one <= t; returns (start, l1, l2)."""
    return [c for c in captions if c[0] <= t][-1]


def render(svg_path, png_path, profile, w, h):
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--window-size={w},{h}",
         f"--user-data-dir={profile}", f"--screenshot={png_path}", "file://" + svg_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_gif(frame_svg, total, size, default_out):
    """Command-line entry: render every frame of frame_svg(t) and join them into a GIF.

    --frame T renders a single PNG at time T instead, for checking the layout.
    """
    w, h = size
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--work", default=None, help="folder for frames (default: a temp folder)")
    ap.add_argument("--frame", type=float, default=None, help="render one PNG at this time")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()

    work = args.work or tempfile.mkdtemp(prefix="readme_gif_")
    os.makedirs(work, exist_ok=True)

    if args.frame is not None:
        svg = os.path.join(work, "single.svg")
        png = os.path.join(work, f"frame_{args.frame:.1f}.png")
        with open(svg, "w") as f:
            f.write(frame_svg(args.frame))
        render(svg, png, os.path.join(work, "profile0"), w, h)
        print(png)
        return

    n = int(total * FPS)
    unique, order = {}, []
    for i in range(n):
        svg = frame_svg(i / FPS)
        key = hashlib.sha1(svg.encode()).hexdigest()
        if key not in unique:
            path = os.path.join(work, f"u{len(unique):04d}.svg")
            with open(path, "w") as f:
                f.write(svg)
            unique[key] = path
        order.append(unique[key])
    print(f"{n} frames, {len(unique)} unique", file=sys.stderr)

    # Chrome refuses to start if another instance holds the same profile, so each running
    # render borrows a free profile folder from this pool and returns it afterwards.
    profiles = queue.Queue()
    for k in range(args.jobs):
        profiles.put(os.path.join(work, f"profile{k}"))

    def work_one(path):
        profile = profiles.get()
        try:
            for attempt in range(3):
                try:
                    render(path, path[:-4] + ".png", profile, w, h)
                    return
                except subprocess.CalledProcessError:
                    if attempt == 2:
                        raise
        finally:
            profiles.put(profile)

    with ThreadPoolExecutor(args.jobs) as ex:
        list(ex.map(work_one, unique.values()))

    seq = os.path.join(work, "seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    for i, path in enumerate(order):
        shutil.copyfile(path[:-4] + ".png", os.path.join(seq, f"f{i:04d}.png"))

    vf = (f"scale={OUT_WIDTH}:-1:flags=lanczos,split[a][b];"
          "[a]palettegen=max_colors=128:stats_mode=diff[p];"
          "[b][p]paletteuse=dither=none:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(seq, "f%04d.png"), "-vf", vf, "-loop", "0", args.out],
                   check=True)
    print(args.out)
