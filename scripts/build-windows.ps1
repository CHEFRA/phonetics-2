param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$ApiDir = (Join-Path $Root "api"),
    [string]$WebDir = (Join-Path $Root "web")
)

$ErrorActionPreference = "Stop"

# 1. Python 侧：同步依赖并打包 RPC 子进程
& (Join-Path $PSScriptRoot "build-sidecar.ps1") -ApiDir $ApiDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2. Web 侧：安装依赖、构建渲染进程、出 NSIS 安装包
Set-Location $WebDir

npm install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

npx electron-builder --win nsis --config electron-builder.yml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "安装包输出目录: $WebDir\release"
