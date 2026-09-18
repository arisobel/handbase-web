param(
    [Parameter(Mandatory=$true)][string]$AppName,
    [string]$Server = $env:CAPROVER_SERVER,
    [string]$Password = $env:CAPROVER_PASSWORD
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& "$PSScriptRoot/build-tar.ps1"

if (-not (Get-Command caprover -ErrorAction SilentlyContinue)) {
    throw "CapRover CLI not found. Install it with: npm install -g caprover"
}
if (-not $Server) {
    throw "Provide -Server or set CAPROVER_SERVER."
}

$args = @("deploy", "-h", $Server, "-a", $AppName, "-t", "dist/handbase-web.tar")
if ($Password) { $args += @("-p", $Password) }

caprover @args
