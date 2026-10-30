param([ValidatePattern('^erratascope-[a-z0-9-]+$')][string]$ProjectName = "erratascope-s01-demo")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $root
docker compose -p $ProjectName -f infra/w03/compose.yaml -f infra/submission/compose.clean.yaml stop
if ($LASTEXITCODE -ne 0) { throw "Could not stop the specified demo project." }
Write-Host "Stopped clean demo project services. Demo volumes were retained."
