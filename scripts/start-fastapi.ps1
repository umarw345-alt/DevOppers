$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'docker-common.ps1')

Assert-DockerReady

Write-Host 'Ensuring PostgreSQL is healthy...' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'start-postgres.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL startup failed; FastAPI will not start.'
}

Write-Host 'Running Alembic migrations...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('run', '--rm', 'migrations')
Write-Host 'Alembic migrations completed.' -ForegroundColor Green

Write-Host 'Building and starting FastAPI...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('up', '-d', '--build', '--no-deps', 'auth-service')
Write-Host 'FastAPI authentication service is running.' -ForegroundColor Green

