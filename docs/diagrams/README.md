# About-page architecture diagrams (LaTeX/TikZ → SVG)

These TikZ diagrams power the **About page architecture slideshow**. They are compiled to
SVG **locally** and the resulting SVGs are committed to `frontend/public/diagrams/`. The
deploy image (Docker / Hugging Face Spaces) has **no LaTeX toolchain**, so diagrams are
never built at deploy time — this keeps the offline-first guarantee.

## Files
- `slide-NN-<slug>.tex` — one standalone TikZ diagram per About slide.
- `slides_meta.json` — title / subtitle / body / alt copy for each slide (consumed by the
  React slides data).
- `gen_tex.py` — regenerates the `.tex` from the design spec + normalizes the palette to
  Industrial Slate + Safety Amber. Normally you just edit the `.tex` directly.

## Rebuild
Requires `pdflatex` + `dvisvgm` (MiKTeX or TeX Live).

- Unix / macOS / Git Bash: `./build.sh`
- Windows PowerShell: `pwsh build.ps1`

The build outlines text to paths (`dvisvgm --no-fonts`) so the SVGs render identically on
any machine without font dependencies. Commit the regenerated SVGs.
