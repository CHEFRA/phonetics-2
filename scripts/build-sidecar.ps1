param(
    [string]$ApiDir = (Join-Path $PSScriptRoot "..\api")
)

$ErrorActionPreference = "Stop"

Set-Location $ApiDir

uv sync --all-extras --group dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

uv run pyinstaller --noconfirm --clean rpc_server.spec --distpath dist --workpath build/pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "sidecar 输出目录: $ApiDir\dist\phonetics-sidecar"
