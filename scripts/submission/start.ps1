param([switch]$NoBuild, [switch]$NoOpen)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $root
. (Join-Path $PSScriptRoot "common.ps1")
$script:SubmissionCompose = @("compose", "-p", "erratascope-w03", "-f", "infra/w03/compose.yaml")
if (-not $NoBuild) { Invoke-SubmissionCompose -Arguments @("build", "api") }
Invoke-SubmissionCompose -Arguments @("up", "-d", "--wait", "db", "broker")
Invoke-SubmissionCompose -Arguments @("stop", "api")
Invoke-SubmissionCompose -Arguments @("run", "--rm", "test", "python", "-m", "erratascope_service.cli", "bootstrap-local", "--out", "/local/dev-auth", "--force")
Invoke-SubmissionCompose -Arguments @("run", "--rm", "migrate")
Invoke-SubmissionCompose -Arguments @("up", "-d", "--wait", "--force-recreate", "api", "worker", "dispatcher")
Wait-SubmissionApi -Url "http://127.0.0.1:18080"
Write-Host "Retained ErrataScope workspace: http://127.0.0.1:18080/"
Write-Host "Local auth expires in two hours; rerun to refresh without resetting data."
Write-Host "New checkout? Use start-clean.ps1 to prepare the recorded demonstration."
if (-not $NoOpen) { Start-Process "http://127.0.0.1:18080/" }
