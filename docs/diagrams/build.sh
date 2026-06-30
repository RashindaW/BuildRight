#!/usr/bin/env bash
# Authoring-only: compile the About-page architecture TikZ diagrams to committed SVGs.
# Requires a LaTeX toolchain (pdflatex + dvisvgm; e.g. MiKTeX or TeX Live).
# NOT run at deploy time — the Docker/HF image has no LaTeX; the SVGs are committed.
set -euo pipefail
cd "$(dirname "$0")"
BUILD=".build"
OUT="../../frontend/public/diagrams"
mkdir -p "$BUILD" "$OUT"
for tex in slide-*.tex; do
  base="${tex%.tex}"
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$BUILD" "$tex" >/dev/null
  dvisvgm --pdf --no-fonts -o "$OUT/$base.svg" "$BUILD/$base.pdf"
  echo "built $OUT/$base.svg"
done
echo "Done. Commit the SVGs in $OUT — they are NOT built at deploy time."
