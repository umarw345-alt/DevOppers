$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'docker-common.ps1')

Assert-DockerReady

Write-Host 'Starting PostgreSQL...' -ForegroundColor Cyan
Invoke-Compose -Arguments @('up', '-d', 'postgres')

$containerId = (docker compose -f (Join-Path $ProjectRoot 'docker-compose.yml') ps -q postgres).Trim()
if (-not $containerId) {
    throw 'PostgreSQL container was not created.'
}

Write-Host 'Waiting for PostgreSQL health check...' -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(60)
do {
    $health = (docker inspect --format '{{.State.Health.Status}}' $containerId 2>$null).Trim()
    if ($health -eq 'healthy') {
        Write-Host 'PostgreSQL is healthy.' -ForegroundColor Green
        exit 0
    }

    if ($health -eq 'unhealthy' -or (Get-Date) -ge $deadline) {
        docker compose -f (Join-Path $ProjectRoot 'docker-compose.yml') logs --tail 40 postgres
        throw "PostgreSQL did not become healthy. Last reported state: $health"
    }

    Start-Sleep -Seconds 2
} while ($true)
