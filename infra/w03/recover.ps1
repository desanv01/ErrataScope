# W03 deterministic crash/restart recovery.
# Only this Compose project's services are touched; volumes are preserved.

$ErrorActionPreference = 'Stop'
$project = 'erratascope-w03'
$composeFile = Join-Path $PSScriptRoot 'compose.yaml'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$local = Join-Path $root '.local\w03'
$evidence = Join-Path $root 'docs\evidence\W03'
$mainDb = 'postgresql+psycopg://erratascope_app:dev_app_password@db:5432/erratascope'
$mainMigrator = 'postgresql+psycopg://erratascope_migrator:dev_migrator_password@db:5432/erratascope'
New-Item -ItemType Directory -Force -Path $local, $evidence | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'recover_helper.py') (Join-Path $local 'recover_helper.py') -Force

function Invoke-Compose {
    & docker compose -p $project -f $composeFile @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed with $LASTEXITCODE" }
}

$stages = [System.Collections.Generic.List[object]]::new()

Write-Host 'stage: base services'
Invoke-Compose up -d --wait db broker api dispatcher
Invoke-Compose stop worker | Out-Null

Write-Host 'stage: seed synthetic job'
Invoke-Compose run --rm `
    -e "W03_DATABASE_URL=$mainDb" -e "W03_QUEUE_NAME=w03" -e "W03_ARTIFACT_ROOT=/var/lib/erratascope/app-artifacts" `
    -e "W03_TEST_MODE=1" -e "W03_MIGRATOR_DATABASE_URL=$mainMigrator" `
    test python /local/recover_helper.py seed --output /local/recovery-seed-attempt-05.json
$stages.Add([ordered]@{ stage = 'seed'; ok = ($LASTEXITCODE -eq 0) })

Write-Host 'stage: crash after bytes staged, before transaction commit'
& docker compose -p $project -f $composeFile run --rm `
    -e "W03_DATABASE_URL=$mainDb" -e "W03_QUEUE_NAME=w03" -e "W03_ARTIFACT_ROOT=/var/lib/erratascope/app-artifacts" `
    -e "W03_TEST_MODE=1" -e "W03_TEST_FAILPOINT=crash_after_stage" `
    test python /local/recover_helper.py crash --seed /local/recovery-seed-attempt-05.json
$crashExit = $LASTEXITCODE
if ($crashExit -ne 43) { throw "expected failpoint exit 43, got $crashExit" }
$stages.Add([ordered]@{ stage = 'crash_after_stage'; exit = $crashExit; expected = 43 })

Write-Host 'stage: expire lease, reconcile and redispatch'
Invoke-Compose run --rm `
    -e "W03_DATABASE_URL=$mainDb" -e "W03_QUEUE_NAME=w03" -e "W03_ARTIFACT_ROOT=/var/lib/erratascope/app-artifacts" -e "W03_TEST_MODE=1" `
    test python /local/recover_helper.py recover --seed /local/recovery-seed-attempt-05.json
$stages.Add([ordered]@{ stage = 'reconcile'; ok = ($LASTEXITCODE -eq 0) })

Write-Host 'stage: restart worker with existing volumes'
Invoke-Compose up -d --wait worker
$stages.Add([ordered]@{ stage = 'worker_restart'; ok = ($LASTEXITCODE -eq 0) })

Write-Host 'stage: verify recovered job and committed receipt'
Invoke-Compose run --rm `
    -e "W03_DATABASE_URL=$mainDb" -e "W03_QUEUE_NAME=w03" -e "W03_ARTIFACT_ROOT=/var/lib/erratascope/app-artifacts" `
    test python /local/recover_helper.py verify --seed /local/recovery-seed-attempt-05.json --output /local/recovery-verify-attempt-05.json
$stages.Add([ordered]@{ stage = 'verify_after_restart'; ok = ($LASTEXITCODE -eq 0) })

Write-Host 'stage: restart API and verify retrieval from existing volumes'
Invoke-Compose restart api | Out-Null
Invoke-Compose run --rm `
    -e "W03_DATABASE_URL=$mainDb" -e "W03_QUEUE_NAME=w03" -e "W03_ARTIFACT_ROOT=/var/lib/erratascope/app-artifacts" `
    test python /local/recover_helper.py http --seed /local/recovery-seed-attempt-05.json --output /local/recovery-http-attempt-05.json
$stages.Add([ordered]@{ stage = 'api_restart_retrieval'; ok = ($LASTEXITCODE -eq 0) })

Copy-Item (Join-Path $local 'recovery-verify-attempt-05.json') (Join-Path $evidence 'recovery-restart-attempt-05.json') -Force
Copy-Item (Join-Path $local 'recovery-http-attempt-05.json') (Join-Path $evidence 'recovery-api-retrieval-attempt-05.json') -Force
$evidenceBody = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    compose_project = $project
    stages = $stages
    source = 'infra/w03/recover.ps1'
    provider_calls = 0
}
$evidenceBody | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $evidence 'recovery-attempt-05.json') -Encoding utf8
if ($crashExit -ne 43) { throw "expected failpoint exit 43, got $crashExit" }
Write-Host 'recovery passed'




