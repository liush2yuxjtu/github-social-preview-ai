---
name: github-social-preview-ai
description: Generate polished GitHub social preview images (repo cover, 1280x640 PNG, og:image / OG image / social card / link preview) with a text-free AI background plus pixel-perfect code-composed text via HTML + headless Chrome. CJK-first (Chinese/Japanese/Korean headlines), max 2 text layers (big headline + repo name), reserved clean text zone with scrim, automated verifier (scripts/verify.py: max 2 text layers, min text size at 320px thumbnail and 506px card, safe area, art overlap, WCAG contrast, OCR) with contact sheet, batch rendering from a covers.json config. Use when asked to make or redesign a GitHub repo cover, social preview, OG image, or social share card.
---

# GitHub Social Preview AI

Make repo covers that read at thumbnail size. Never let an image model draw text.

## Workflow
1. **Copy** — per repo, write ONE headline (≤ ~6 CJK chars or ≤ 4 words per line, 1–2 lines) that says what the repo does, plus the repo name. Nothing else: no subtitles, tags, version pills, eyebrows. Max 2 text layers.
2. **Background** — generate a text-free AI image (≥1280x640, 2:1 or 16:9) with your image tool. Prompt pattern:
   `<subject art> on the RIGHT 45% of the frame, LEFT 55% is empty dark negative space, cinematic, <palette>, no text, no letters, no logos, no watermark`.
   Inspect it; regenerate if any glyph-like marks or art in the left half.
3. **Config** — write `covers.json` (see `examples/covers.json`): `out`, `bg`, `headline` (list of lines), `title`, optional `headline_size`, `art_shift`, `accent`, `bg_color`, `scrim_stop`.
4. **Render** — `python3 scripts/render.py path/to/covers.json [--out-dir DIR]`. Needs Python + Pillow + numpy, tesseract (optional, for OCR), Chrome/Chromium, and a CJK font (Noto Sans CJK / PingFang / YaHei).
5. **Verify (MANDATORY — never skip, never rely on the user to spot problems)** — `render.py` runs `scripts/verify.py` on every cover and exits non-zero on any FAIL. You can also run it alone: `python3 scripts/verify.py out/x.png [--html out/x.png.html] [--headline "..."]`.
   It measures the HTML layout in headless Chrome and checks: exact 1280x640; ≤ 2 text elements; every text element ≥ 11px at the 320px thumbnail and ≥ 16px at the 506px GitHub/X card; text inside a 40px safe margin; text box not over art (≤ 3% art pixels); WCAG contrast ≥ 4.5; headline recognised by OCR (tesseract chi_sim+eng) on the 320px thumbnail (warns if tesseract missing — install `tesseract-ocr tesseract-ocr-chi-sim`).
   Rules for the agent:
   - You MUST get a PASS for every cover. On FAIL, read the reasons in `<cover>.verify.json`, fix the config (fewer/larger text, `headline_size`, `art_shift`, `scrim_stop`, shorter headline) or regenerate the background, re-render, re-verify.
   - You MUST open and look at `<cover>.sheet.png` (full | 506px | 320px side by side) after it passes, and fix anything still off (art cropped at edges, awkward breaks, art too dark).
   - You MUST NOT hand covers to the user, upload, or call the task done until verify passes AND you have viewed the sheet. Never use `--no-verify` or loosen thresholds just to pass.
6. **Ship** — upload under repo **Settings → General → Social preview** (no API for this; must be done in the UI). Keep PNG < 1 MB.

## Design rules
- Left text zone ~ 50% width, dark scrim gradient into the art; art lives on the right.
- Headline 90–120px bold sans (CJK font), repo name ~50px monospace; one accent rule between them.
- High contrast (light text on dark), 1–2 accent colors taken from the art.
