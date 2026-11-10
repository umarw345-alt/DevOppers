$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'docker-common.ps1')

Assert-DockerReady

$env:RUN_INTEGRATION_TESTS = '1'

Push-Location (Join-Path $ProjectRoot 'backend')
try {
    & uv run pytest tests/test_integration.py -q
    if ($LASTEXITCODE -ne 0) {
        throw "Integration tests failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
