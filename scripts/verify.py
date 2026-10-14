#!/usr/bin/env python3
"""github-social-preview-ai verifier: FAILS (exit 1) unless a cover is thumbnail-safe.

Usage:
  python3 scripts/verify.py COVER.png [--html COVER.png.html] [--headline TEXT] [options]
  (render.py runs this automatically for every cover.)

Ground truth comes from the cover's HTML: headless Chrome measures every visible
text element (getBoundingClientRect on its text, computed font-size). Pixel checks
use the PNG plus a "text hidden" render of the same HTML.

Checks (each FAIL is listed with a reason):
  size            PNG is exactly 1280x640 (configurable)
  max_text_layers <= 2 visible text elements (headline + repo name)
  thumb_320       every text element: font-size scaled to 320px width >= --min-thumb-px (11)
  card_506        same at GitHub/X card width 506px >= --min-card-px (16)
  safe_area       every text box inside a --safe px margin (40)
  art_overlap     text boxes don't sit on art: <= --max-art-frac (3%) of the box's
                  background pixels are bright/saturated art after the scrim
  contrast        WCAG contrast of rendered text pixels vs background >= --min-contrast (4.5)
  ocr             (warn-only if tesseract missing) headline recognised on the 320x160
                  thumbnail via tesseract chi_sim+eng, fuzzy ratio >= --min-ocr (0.6)
Outputs: <cover>.verify.json report and <cover>.sheet.png contact sheet
(full | 506px | 320px) — an agent MUST view the sheet before handing results over.
"""
import argparse, difflib, html as H, json, os, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np

JS = r"""<script>
(function(){
 function vis(e){const s=getComputedStyle(e);return s.display!='none'&&s.visibility!='hidden'&&+s.opacity>0}
 document.querySelectorAll('body *').forEach(e=>{if(getComputedStyle(e).webkitBackgroundClip=='text'&&window.__HIDE)e.style.background='none'});
 const out=[];
 document.querySelectorAll('body *').forEach(e=>{
  if(['SCRIPT','STYLE','PRE'].includes(e.tagName)||!vis(e))return;
  const own=[...e.childNodes].filter(n=>n.nodeType==3&&n.textContent.trim());
  if(!own.length)return;
  const r=document.createRange();r.selectNodeContents(e);const b=r.getBoundingClientRect();
  if(b.width<1||b.height<1)return;
  const s=getComputedStyle(e);
  out.push({text:e.innerText.trim(),tag:e.tagName.toLowerCase(),cls:e.className,font_size:parseFloat(s.fontSize),
   font_family:s.fontFamily,color:s.color,box:[b.left,b.top,b.right,b.bottom]});
 });
 const p=document.createElement('pre');p.id='__layout';p.style.display='none';
 p.textContent=JSON.stringify({vw:innerWidth,vh:innerHeight,items:out});document.body.appendChild(p);
})();
</script>"""
HIDE = "<style>*{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}</style>"

def chrome_bin():
    for c in ["google-chrome", "chromium", "chromium-browser", "chrome"]:
        if shutil.which(c): return shutil.which(c)
    sys.exit("Chrome/Chromium not found")

def chrome(args, W, H):
    return subprocess.run([chrome_bin(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size={W},{H}", "--virtual-time-budget=3000", *args],
        check=True, capture_output=True, text=True).stdout

def inject(src, extra, tmpdir, name):
    s = open(src, encoding="utf-8").read()
    base = f'<base href="file://{os.path.dirname(os.path.abspath(src))}/">'
    s = re.sub(r"<head>", "<head>" + base, s, count=1) if "<head>" in s else base + s
    s = s.replace("</body>", extra + "</body>") if "</body>" in s else s + extra
    p = os.path.join(tmpdir, name); open(p, "w", encoding="utf-8").write(s); return p

def lum(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722

def _font(sz):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/System/Library/Fonts/PingFang.ttc",
              "C:/Windows/Fonts/msyh.ttc"]:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default(size=sz)

def norm(t): return re.sub(r"[\s·•|,.:;!?，。：；！？、\-_/]+", "", t).lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png"); ap.add_argument("--html"); ap.add_argument("--headline")
    ap.add_argument("--width", type=int, default=1280); ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--max-text-layers", type=int, default=2)
    ap.add_argument("--min-thumb-px", type=float, default=11); ap.add_argument("--min-card-px", type=float, default=16)
    ap.add_argument("--safe", type=int, default=40); ap.add_argument("--max-art-frac", type=float, default=0.03)
    ap.add_argument("--min-contrast", type=float, default=4.5); ap.add_argument("--min-ocr", type=float, default=0.6)
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    png = os.path.abspath(a.png); html_path = a.html or png + ".html"
    W, Hh = a.width, a.height; fails, warns, checks = [], [], {}
    def res(name, ok, msg, warn=False):
        checks[name] = {"ok": ok, "msg": msg}
        if not ok: (warns if warn else fails).append(f"{name}: {msg}")

    im = Image.open(png).convert("RGB")
    res("size", im.size == (W, Hh), f"image is {im.size[0]}x{im.size[1]}, need {W}x{Hh}")
    if not os.path.exists(html_path): sys.exit(f"HTML ground truth not found: {html_path} (pass --html)")
    tmp = tempfile.mkdtemp()
    # --dump-dom windows include browser chrome; probe and pad so the viewport is exactly W x H
    lp = "file://" + inject(html_path, JS, tmp, "l.html"); pad = 0
    for _ in range(3):
        dom = chrome(["--dump-dom", lp], W, Hh + pad)
        m = re.search(r'<pre id="__layout"[^>]*>(.*?)</pre>', dom, re.S)
        if not m: sys.exit("could not extract layout from HTML")
        L = json.loads(H.unescape(m.group(1)))
        if L["vh"] == Hh and L["vw"] == W: break
        pad += Hh - L["vh"]
    else: sys.exit(f"viewport mismatch {L['vw']}x{L['vh']}")
    layout = L["items"]
    bgp = os.path.join(tmp, "bg.png")
    chrome([f"--screenshot={bgp}", "file://" + inject(html_path, HIDE + JS.replace("(function(){", "(function(){window.__HIDE=1;"), tmp, "b.html")], W, Hh)
    bg = np.asarray(Image.open(bgp).convert("RGB").crop((0, 0, W, Hh)), int)
    full = np.asarray(im.resize((W, Hh)), int)

    res("max_text_layers", len(layout) <= a.max_text_layers,
        f"{len(layout)} text elements (max {a.max_text_layers}): " + " | ".join(t["text"][:30] for t in layout))
    small320, small506, unsafe, onart, lowc = [], [], [], [], []
    for t in layout:
        fs = t["font_size"]; t["px_at_320"] = round(fs * 320 / W, 1); t["px_at_506"] = round(fs * 506 / W, 1)
        if t["px_at_320"] < a.min_thumb_px: small320.append(f'"{t["text"][:24]}" {fs:.0f}px→{t["px_at_320"]}px')
        if t["px_at_506"] < a.min_card_px: small506.append(f'"{t["text"][:24]}" {fs:.0f}px→{t["px_at_506"]}px')
        x0, y0, x1, y1 = t["box"]
        if x0 < a.safe or y0 < a.safe or x1 > W - a.safe or y1 > Hh - a.safe:
            unsafe.append(f'"{t["text"][:24]}" box={[round(v) for v in t["box"]]}')
        X0, Y0, X1, Y1 = [int(max(0, v)) for v in (x0, y0, min(x1, W), min(y1, Hh))]
        if X1 <= X0 or Y1 <= Y0: continue
        b = bg[Y0:Y1, X0:X1]; f = full[Y0:Y1, X0:X1]
        mx, mn = b.max(-1), b.min(-1)
        art = (mx > 70) & ((mx - mn) > 40)  # bright + saturated = art, not scrim
        t["art_frac"] = round(float(art.mean()), 4)
        if t["art_frac"] > a.max_art_frac: onart.append(f'"{t["text"][:24]}" {t["art_frac"]*100:.1f}% art pixels')
        diff = np.abs(f - b).sum(-1); tp = diff > 60
        if tp.sum() < 20: t["contrast"] = None; continue
        Lt = float(np.median(lum(f[tp]))); Lb = lum(b[tp])
        cr = (np.maximum(Lt, Lb) + 0.05) / (np.minimum(Lt, Lb) + 0.05)
        t["contrast"] = round(float(np.percentile(cr, 10)), 2)
        if t["contrast"] < a.min_contrast: lowc.append(f'"{t["text"][:24]}" {t["contrast"]}:1')
    res("thumb_320", not small320, f"text too small at 320px (min {a.min_thumb_px}px): " + "; ".join(small320))
    res("card_506", not small506, f"text too small at 506px card (min {a.min_card_px}px): " + "; ".join(small506))
    res("safe_area", not unsafe, f"text outside {a.safe}px safe margin: " + "; ".join(unsafe))
    res("art_overlap", not onart, "text overlaps art: " + "; ".join(onart))
    res("contrast", not lowc, f"contrast below {a.min_contrast}: " + "; ".join(lowc))

    thumb = im.resize((320, 160), Image.LANCZOS); card = im.resize((506, 253), Image.LANCZOS)
    head = a.headline or (max(layout, key=lambda t: t["font_size"])["text"] if layout else "")
    if a.no_ocr: checks["ocr"] = {"ok": None, "msg": "skipped"}
    elif not shutil.which("tesseract"):
        res("ocr", False, "tesseract not installed; OCR skipped (apt install tesseract-ocr tesseract-ocr-chi-sim)", warn=True)
    else:
        # OCR what a viewer sees at 320px: crop thumb to the text area, upscale, invert to dark-on-light
        k = 320 / W; bx = [t["box"] for t in layout] or [[0, 0, W, Hh]]
        cx0, cy0 = max(0, min(b[0] for b in bx) * k - 4), max(0, min(b[1] for b in bx) * k - 4)
        cx1, cy1 = min(320, max(b[2] for b in bx) * k + 4), min(160, max(b[3] for b in bx) * k + 4)
        crop = thumb.crop((int(cx0), int(cy0), int(cx1), int(cy1))).convert("L")
        crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
        if np.asarray(crop).mean() < 128: crop = Image.eval(crop, lambda v: 255 - v)
        tp = os.path.join(tmp, "t.png"); crop.save(tp); txt = ""
        for psm in ("6", "11"):
            txt += subprocess.run(["tesseract", tp, "-", "-l", "chi_sim+eng", "--psm", psm], capture_output=True, text=True).stdout + "\n"
        n, o = norm(head), norm(txt)
        hits = sum(1 for ch in set(n) if ch in o) / max(1, len(set(n)))
        ratio = max(difflib.SequenceMatcher(None, n, o).find_longest_match(0, len(n), 0, len(o)).size / max(1, len(n)), hits)
        checks["ocr_text"] = txt.strip()
        res("ocr", ratio >= a.min_ocr, f'headline "{head}" recognised {ratio:.0%} on 320px thumb (min {a.min_ocr:.0%})')

    # contact sheet: full | 506 | 320
    sheet = Image.new("RGB", (W + 506 + 320 + 80, Hh + 70), "#ffffff"); d = ImageDraw.Draw(sheet); fnt, fsm = _font(22), _font(15)
    x = 20
    for lbl, img in [(f"full {W}x{Hh}", im), ("GitHub/X card 506px", card), ("thumbnail 320px", thumb)]:
        sheet.paste(img, (x, 50)); d.text((x, 14), lbl, fill="#000", font=fnt); x += img.size[0] + 20
    d.text((W + 40, 330), ("PASS" if not fails else "FAIL") + "\n" + "\n".join(f[i:i+95] for f in fails[:8] for i in range(0, min(len(f), 190), 95)),
           fill="#080" if not fails else "#c00", font=fsm)
    base = png[:-4]; sheet.save(base + ".sheet.png")
    rep = {"png": png, "html": html_path, "pass": not fails, "fails": fails, "warnings": warns,
           "checks": checks, "text_elements": layout, "sheet": base + ".sheet.png"}
    json.dump(rep, open(base + ".verify.json", "w"), ensure_ascii=False, indent=1)
    print(("PASS " if not fails else "FAIL ") + png)
    for f in fails: print("  FAIL", f)
    for w in warns: print("  WARN", w)
    print("  report:", base + ".verify.json", "| sheet:", base + ".sheet.png  <- view it")
    sys.exit(0 if not fails else 1)

if __name__ == "__main__": main()
