$ErrorActionPreference = 'Stop'
$captureRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../assets/capture'))
# Actual CDP recordings 04–06 contain a 1536x768 active image in a
# 1600x800 padded canvas. Remove only that observed padding, then normalize.
# No source text, values, or UI elements are replaced.
foreach ($clipName in @('01-workspace','02-citations','03-unknowns','04-review','05-export','06-synthetic')) {
    $sourcePath = Join-Path $captureRoot ($clipName + '.webm')
    $outputPath = Join-Path $captureRoot ($clipName + '.mp4')
    if (-not (Test-Path -LiteralPath $sourcePath)) { throw "Missing recording: $clipName" }
    $videoFilter = 'fps=30,format=yuv420p'
    if ($clipName -in @('04-review','05-export','06-synthetic')) {
        $videoFilter = 'crop=1536:768:0:0,scale=1600:800:flags=lanczos,fps=30,format=yuv420p'
    }
    & ffmpeg -hide_banner -loglevel error -i $sourcePath -vf $videoFilter -an -c:v libx264 -preset fast -crf 17 -movflags +faststart -y $outputPath
    if ($LASTEXITCODE -ne 0) { throw "Normalization failed: $clipName" }
}
