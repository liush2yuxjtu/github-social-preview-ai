---
name: github-social-preview-ai
description: Generate polished GitHub social preview images (repo cover, 1280x640 PNG, og:image / OG image / social card / link preview) with a text-free AI background plus pixel-perfect code-composed text via HTML + headless Chrome. CJK-first (Chinese/Japanese/Korean headlines), max 2 text layers (big headline + repo name), reserved clean text zone with scrim, 320x160 thumbnail readability check, batch rendering from a covers.json config. Use when asked to make or redesign a GitHub repo cover, social preview, OG image, or social share card.
---

# GitHub Social Preview AI

Make repo covers that read at thumbnail size. Never let an image model draw text.

## Workflow
1. **Copy** — per repo, write ONE headline (≤ ~6 CJK chars or ≤ 4 words per line, 1–2 lines) that says what the repo does, plus the repo name. Nothing else: no subtitles, tags, version pills, eyebrows. Max 2 text layers.
2. **Background** — generate a text-free AI image (≥1280x640, 2:1 or 16:9) with your image tool. Prompt pattern:
   `<subject art> on the RIGHT 45% of the frame, LEFT 55% is empty dark negative space, cinematic, <palette>, no text, no letters, no logos, no watermark`.
   Inspect it; regenerate if any glyph-like marks or art in the left half.
3. **Config** — write `covers.json` (see `examples/covers.json`): `out`, `bg`, `headline` (list of lines), `title`, optional `headline_size`, `art_shift`, `accent`, `bg_color`, `scrim_stop`.
4. **Render** — `python3 scripts/render.py path/to/covers.json [--out-dir DIR]`. Needs Python + Pillow, Chrome/Chromium, and a CJK font (Noto Sans CJK / PingFang / YaHei).
5. **Check** — view every PNG AND its `.thumb.png` (320x160). Pass only if: headline readable in the thumbnail, repo name readable, no text over the art, no art cropped at edges, exactly 1280x640. Fix by tuning `headline_size` (lines never wrap — shrink if a line runs into the art), `art_shift` (push art right / pull back if cropped), `scrim_stop`. Re-render and re-check.
6. **Ship** — upload under repo **Settings → General → Social preview** (no API for this; must be done in the UI). Keep PNG < 1 MB.

## Design rules
- Left text zone ~ 50% width, dark scrim gradient into the art; art lives on the right.
- Headline 90–120px bold sans (CJK font), repo name ~50px monospace; one accent rule between them.
- High contrast (light text on dark), 1–2 accent colors taken from the art.
