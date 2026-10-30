param()
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $root
docker compose -p erratascope-w03 -f infra/w03/compose.yaml stop
Write-Host "Stopped ErrataScope project services. Volumes were retained."
