$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'docker-common.ps1')

Assert-DockerReady

Write-Host 'Ensuring PostgreSQL is healthy...' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'start-postgres.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL startup failed; FastAPI will not start.'
}

Write-Host 'Running Alembic migrations...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('run', '--rm', '--build', 'migrations')
Write-Host 'Alembic migrations completed.' -ForegroundColor Green

Write-Host 'Building and starting FastAPI...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('up', '-d', '--build', '--no-deps', 'api')

Write-Host 'Checking API health...' -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(30)
do {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -Method Get -TimeoutSec 5
        if ($health.status -eq 'ok') {
            Write-Host 'FastAPI is healthy at http://localhost:8000.' -ForegroundColor Green
            Write-Host 'You can now start the web client with: npm run web' -ForegroundColor Green
            exit 0
        }
    }
    catch {
        # FastAPI may need a few seconds to finish starting.
    }

    if ((Get-Date) -ge $deadline) {
        Invoke-Compose -Arguments @('logs', '--tail', '40', 'api')
        throw 'FastAPI did not become healthy within 30 seconds.'
    }

    Start-Sleep -Seconds 2
} while ($true)
