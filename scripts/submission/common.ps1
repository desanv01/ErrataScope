$ErrorActionPreference = "Stop"
function Invoke-SubmissionCompose {
    param([Parameter(Mandatory=$true)][string[]]$Arguments)
    & docker @script:SubmissionCompose @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed (exit $LASTEXITCODE): $($Arguments[0])" }
}
function Wait-SubmissionApi {
    param([string]$Url)
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing "$Url/health/ready" -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Seconds 1 }
    }
    throw "API did not become ready at $Url. Inspect Docker Compose logs."
}
