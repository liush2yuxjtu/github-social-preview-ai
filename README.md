# github-social-preview-ai

**AI-art GitHub social preview (repo cover / OG image) generator — an Agent Skill for Claude Code & friends.**
**AI 背景 + 代码排版的 GitHub 仓库封面（Social Preview）生成 Skill。**

![douyin-video-skill](examples/out/douyin-video-skill.png)
![douyin-read-skill](examples/out/douyin-read-skill.png)

## Why / 为什么
- Image models garble text → background is **text-free AI art**; text is composed in **HTML + headless Chrome** with real fonts (great CJK).
- **Max 2 text layers**: big headline + repo name. Reads at **320x160** thumbnail size (auto-generated `.thumb.png` for checking).
- Reserved clean **text zone + scrim** — text never overlaps the art.
- **Batch** many repos from one `covers.json`.

- 图像模型写字会糊 → 背景用**无文字 AI 图**，文字用 **HTML + 无头 Chrome** 真字体排版（中文友好）。
- **最多两层文字**：大标题 + 仓库名，缩到 **320x160** 依然清晰（自动输出缩略图供检查）。
- 左侧预留干净文字区 + 渐变遮罩，文字不压图。
- 一份 `covers.json` 批量出图。

## Install / 安装
```sh
# Claude Code (personal skills)
git clone https://github.com/liush2yuxjtu/github-social-preview-ai ~/.claude/skills/github-social-preview-ai
# or project-level: .claude/skills/  ·  other agents: .agents/skills/ or .cursor/skills/
# or: npx skills add liush2yuxjtu/github-social-preview-ai
```
Requirements / 依赖: Python 3 + Pillow, Google Chrome / Chromium, a CJK font (e.g. Noto Sans CJK).

## Usage / 用法
Ask your agent: *"Make a GitHub social preview for this repo"* / *"给这个仓库做个 GitHub 封面"*. Or run directly:
```sh
python3 scripts/render.py examples/covers.json --out-dir out
```
```json
{"defaults": {"art_shift": 60, "accent": ["#25f4ee", "#fe2c55"]},
 "covers": [{"out": "my-repo.png", "bg": "bg/my-repo.jpg", "headline": ["一句话", "说清用途"], "title": "my-repo"}]}
```
Then upload in **Settings → General → Social preview**. / 然后在仓库 **Settings → Social preview** 上传。

## Credits / 致谢
Inspired by [sjh9714/repo-cover](https://github.com/sjh9714/repo-cover) (CJK-first HTML cards, deterministic checks) and the [og-image skill in prompt-to-asset](https://github.com/MohamedAbdallah-14/prompt-to-asset/blob/main/.claude/skills/og-image/SKILL.md) ("never let diffusion draw the text").

## License
MIT
