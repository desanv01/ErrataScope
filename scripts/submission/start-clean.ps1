param([string]$PdfPath = "", [switch]$NoBuild, [switch]$NoOpen,
    [ValidatePattern('^erratascope-[a-z0-9-]+$')][string]$ProjectName = "erratascope-s01-demo")
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $root
. (Join-Path $PSScriptRoot "common.ps1")
$script:SubmissionCompose = @("compose", "-p", $ProjectName, "-f", "infra/w03/compose.yaml", "-f", "infra/submission/compose.clean.yaml")
$pdf = $PdfPath
if (-not $pdf) {
    foreach ($candidate in @(".local/w01/sources/st-es0620.pdf", ".local/w01/sources/es0620.pdf")) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $pdf = (Resolve-Path -LiteralPath $candidate).Path; break }
    }
}
if (-not $pdf) {
    New-Item -ItemType Directory -Force ".local/submission/clean" | Out-Null
    $pdf = Join-Path $root ".local/submission/clean/es0620.pdf"
    Write-Host "Downloading the pinned ST ES0620 Rev 5 source..."
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf" -OutFile $pdf -TimeoutSec 90
    } catch { throw "Source download failed. Obtain ES0620 Rev 5 from ST and rerun with -PdfPath <path>. No application data was reset." }
}
$pdf = (Resolve-Path -LiteralPath $pdf).Path
if ((Get-FileHash -LiteralPath $pdf -Algorithm SHA256).Hash.ToLowerInvariant() -ne "dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd") {
    throw "Source hash mismatch. Supply the pinned ES0620 Rev 5 PDF with -PdfPath; a changed document is not silently substituted."
}
# Build before application commands: a fresh checkout has no image or venv.
if (-not $NoBuild) { Invoke-SubmissionCompose -Arguments @("build", "api") }
Invoke-SubmissionCompose -Arguments @("up", "-d", "--wait", "db", "broker")
# Refresh only this isolated demo's two-hour tokens. Actor IDs stay stable.
Invoke-SubmissionCompose -Arguments @("stop", "api")
Invoke-SubmissionCompose -Arguments @("run", "--rm", "test", "python", "-m", "erratascope_service.cli", "bootstrap-local", "--out", "/local/dev-auth", "--force")
Invoke-SubmissionCompose -Arguments @("run", "--rm", "migrate")
Invoke-SubmissionCompose -Arguments @("up", "-d", "--wait", "--force-recreate", "api", "worker", "dispatcher")
Wait-SubmissionApi -Url "http://127.0.0.1:18081"
# A state file is not proof that importing completed. Resume idempotently.
Invoke-SubmissionCompose -Arguments @("run", "--rm", "-v", "${root}:/workspace", "-v", "$(Split-Path $pdf):/sources:ro", "-e", "CLEAN_PDF=/sources/$(Split-Path $pdf -Leaf)", "test", "python", "/workspace/scripts/submission/prepare_clean.py")
$state = Get-Content -LiteralPath ".local/submission/clean-state.json" -Raw | ConvertFrom-Json
Invoke-SubmissionCompose -Arguments @("run", "--rm", "-v", "${root}:/workspace", "api", "python", "-m", "erratascope_service.submission.demo_import", "--project-id", $state.project_id, "--source-id", $state.source_id, "--snapshot", "/workspace/docs/submission/demo/recorded-demo.json")
Invoke-SubmissionCompose -Arguments @("run", "--rm", "-v", "${root}:/workspace", "test", "python", "/workspace/scripts/submission/seed_synthetic.py")
Write-Host "Clean local demo: http://127.0.0.1:18081/ - recorded result and original offline example; zero provider calls."
Write-Host "Auth expires after two hours; rerun this launcher to refresh it. Volumes and reviews are retained."
Write-Host "Stop with: powershell -ExecutionPolicy Bypass -File scripts/submission/stop-clean.ps1 -ProjectName $ProjectName"
if (-not $NoOpen) { Start-Process "http://127.0.0.1:18081/" }
