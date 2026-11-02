$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'docker-common.ps1')

Assert-DockerReady

Write-Host 'Ensuring FastAPI and PostgreSQL are ready...' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'start-fastapi.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'FastAPI startup failed; KrakenD will not start.'
}

Write-Host 'Starting KrakenD gateway...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('up', '-d', 'krakend')

Write-Host 'Checking gateway health...' -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(30)
do {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8080/health' -Method Get -TimeoutSec 5
        if ($health.status -eq 'ok') {
            Write-Host 'KrakenD is healthy at http://localhost:8080.' -ForegroundColor Green
            Write-Host 'You can now start the web client with: npm run web' -ForegroundColor Green
            exit 0
        }
    }
    catch {
        # KrakenD may need a few seconds to finish starting.
    }

    if ((Get-Date) -ge $deadline) {
        Invoke-Compose -Arguments @('logs', '--tail', '40', 'krakend')
        throw 'KrakenD did not become healthy within 30 seconds.'
    }

    Start-Sleep -Seconds 2
} while ($true)

