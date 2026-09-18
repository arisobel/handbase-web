param(
    [string]$Output = "dist/handbase-web.tar"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

New-Item -ItemType Directory -Force -Path "dist" | Out-Null
if (Test-Path $Output) { Remove-Item $Output -Force }

$items = @(
    "captain-definition",
    "Dockerfile",
    ".dockerignore",
    "backend",
    "frontend",
    "alembic",
    "alembic.ini"
)

tar -cf $Output @items
Write-Host "Created $Output"
