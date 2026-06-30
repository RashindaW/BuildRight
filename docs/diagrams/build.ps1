# Authoring-only: compile the About-page architecture TikZ diagrams to committed SVGs.
# Requires pdflatex + dvisvgm (MiKTeX or TeX Live). NOT run at deploy time.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$build = ".build"
$out = "../../frontend/public/diagrams"
New-Item -ItemType Directory -Force -Path $build, $out | Out-Null
Get-ChildItem -Filter "slide-*.tex" | ForEach-Object {
  $base = $_.BaseName
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$build $_.Name | Out-Null
  dvisvgm --pdf --no-fonts -o "$out/$base.svg" "$build/$base.pdf"
  Write-Host "built $out/$base.svg"
}
Write-Host "Done. Commit the SVGs in $out."
