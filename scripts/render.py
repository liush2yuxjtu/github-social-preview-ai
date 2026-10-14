#!/usr/bin/env python3
"""github-social-preview-ai renderer.

Composes crisp text (max 2 layers: headline + repo name) over a text-free AI
background using HTML + headless Chrome, then writes a 320x160 thumbnail and runs scripts/verify.py on every cover
(exit 1 if any cover fails).

Usage:
  python3 scripts/render.py examples/covers.json [--out-dir DIR] [--chrome PATH]

Config: {"defaults": {...}, "covers": [{out, bg, headline, title, ...}]}
  headline        str or list of lines (CJK friendly; lines never wrap)
  title           repo name, monospace
  bg              background image path (relative to config); art should sit on the right
  art_shift       px to push the art right (default 60)
  bg_offset_y     px vertical offset of bg (default: centered crop)
  headline_size   px (auto if omitted)  | title_size px (default 50)
  accent          [colorA, colorB] gradient rule | bg_color | text_left px (72)
  scrim_stop      % where the dark scrim fully fades (default 64)
  font_cjk / font_mono  CSS font-family overrides
"""
import argparse, html, json, os, shutil, subprocess, sys
from PIL import Image

TPL = """<!doctype html><html><head><meta charset=utf-8><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{bg_color}}}
.bg{{position:absolute;inset:0;background:url('{bg}') no-repeat;background-size:cover;background-position:calc(50% + {art_shift}px) {bgy}}}
.scrim{{position:absolute;inset:0;background:linear-gradient(90deg,{bg_color} 0%,{bg_color} {s0}%,{bg_color}d9 {s1}%,{bg_color}00 {scrim_stop}%)}}
.t{{position:absolute;left:{text_left}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;color:#fff}}
.h{{font-family:{font_cjk};white-space:nowrap;font-weight:700;font-size:{headline_size}px;line-height:1.12;margin-bottom:30px;text-shadow:0 2px 30px rgba(0,0,0,.6)}}
.r{{width:110px;height:7px;border-radius:4px;background:linear-gradient(90deg,{a0},{a1});margin-bottom:30px}}
.n{{font-family:{font_mono};font-weight:700;font-size:{title_size}px;line-height:1.1}}
</style></head><body><div class=bg></div><div class=scrim></div><div class=t>
<div class=h>{headline}</div><div class=r></div><div class=n>{title}</div></div></body></html>"""

DEF = dict(width=1280, height=640, art_shift=60, bg_offset_y=None, title_size=50, accent=["#25f4ee", "#fe2c55"],
           bg_color="#07080c", text_left=72, scrim_stop=64,
           font_cjk="'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif",
           font_mono="'JetBrains Mono','DejaVu Sans Mono',Menlo,monospace")

def find_chrome(p):
    for c in [p, "google-chrome", "chromium", "chromium-browser", "chrome",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and (shutil.which(c) or os.path.exists(c)): return shutil.which(c) or c
    sys.exit("Chrome/Chromium not found; pass --chrome")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("--out-dir"); ap.add_argument("--chrome")
    ap.add_argument("--no-verify", action="store_true", help="skip scripts/verify.py (not allowed before handing results to a user)")
    ap.add_argument("--verify-args", default="", help="extra args passed to verify.py, e.g. \"--min-thumb-px 12\"")
    a = ap.parse_args(); cfg_path = os.path.abspath(a.config); base = os.path.dirname(cfg_path)
    cfg = json.load(open(cfg_path)); chrome = find_chrome(a.chrome)
    out_dir = os.path.abspath(a.out_dir or os.path.join(base, "out")); os.makedirs(out_dir, exist_ok=True)
    failed = []
    covers = cfg["covers"] if isinstance(cfg, dict) else cfg
    for c in covers:
        o = {**DEF, **(cfg.get("defaults", {}) if isinstance(cfg, dict) else {}), **c}
        W, H = o["width"], o["height"]
        lines = o["headline"] if isinstance(o["headline"], list) else [o["headline"]]
        size = o.get("headline_size") or min(120, int((W * 0.5 - o["text_left"]) / max(len(l) for l in lines)))
        s = o["scrim_stop"]
        page = TPL.format(W=W, H=H, bg="file://" + os.path.join(base, o["bg"]), art_shift=o["art_shift"],
            bgy=f'{o["bg_offset_y"]}px' if o["bg_offset_y"] is not None else "50%",
            bg_color=o["bg_color"], s0=s - 24, s1=s - 14, scrim_stop=s, text_left=o["text_left"],
            font_cjk=o["font_cjk"], font_mono=o["font_mono"], headline_size=size, title_size=o["title_size"],
            a0=o["accent"][0], a1=o["accent"][1], headline="<br>".join(html.escape(l) for l in lines),
            title=html.escape(o["title"]))
        out = os.path.join(out_dir, o["out"]); hp = out + ".html"; open(hp, "w").write(page)
        subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={W},{H}", f"--screenshot={out}", "file://" + hp],
            check=True, capture_output=True)
        im = Image.open(out).convert("RGB").crop((0, 0, W, H)); im.save(out)
        im.resize((320, 160), Image.LANCZOS).save(out[:-4] + ".thumb.png")
        print(f"{out} {im.size} headline={size}px")
        if not a.no_verify:
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify.py"), out,
                "--html", hp, "--headline", "".join(lines), "--width", str(W), "--height", str(H), *a.verify_args.split()])
            if r.returncode: failed.append(o["out"])
    if failed:
        sys.exit(f"VERIFY FAILED for: {', '.join(failed)} -- fix config and re-render; do NOT hand these to the user")

if __name__ == "__main__": main()
