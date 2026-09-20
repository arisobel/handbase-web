<#
.SYNOPSIS
    Test, package and deploy HandBase Web to CapRover.

.DESCRIPTION
    HandBase Web ships as ONE CapRover application: the production image builds
    the React frontend and serves it from the FastAPI process. So there is one
    deployment script, not a frontend and a backend one.

    The flow is deliberately ordered so that nothing reaches CapRover unverified:

        load config -> validate layout -> tests -> frontend build
          -> package -> inspect archive -> deploy

    Each step stops the whole run on failure. There is no path that deploys a
    package whose tests failed or whose archive contains a secret.

.PARAMETER EnvironmentFile
    Deploy-time config file. Defaults to deploy/.env next to this script.
    Only CAPROVER_URL, CAPROVER_APP and CAPROVER_APP_TOKEN are accepted;
    anything else is an error, because runtime secrets belong in the CapRover
    application environment.

.PARAMETER SkipTests
    Skip pytest and the frontend type-check. Requires explicitly passing the
    switch, prints a warning, and is never implied by anything else.
    The frontend is still built, because the image needs it.

.PARAMETER SkipDeploy
    Do everything except the CapRover upload: validate, test, build, package
    and inspect the archive. Use it to prepare and review a package before
    deploying it for real.

.EXAMPLE
    .\deploy\deploy.ps1 -SkipDeploy
    Build and inspect a package without touching CapRover.

.EXAMPLE
    .\deploy\deploy.ps1
    The full flow, including the CapRover deploy.
#>
[CmdletBinding()]
param(
    [string]$EnvironmentFile,
    [switch]$SkipTests,
    [switch]$SkipDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

$AppSlug = "handbase-web"

# The only keys deploy/.env may contain. See the comment in .env.example.
$AllowedKeys = @("CAPROVER_URL", "CAPROVER_APP", "CAPROVER_APP_TOKEN")

# How many timestamped packages to keep in dist/.
$RetainPackages = 5

# Exactly what the CapRover Docker build reads, checked against Dockerfile:
#   frontend/        -> npm install && npm run build (stage 1)
#   backend/         -> requirements.txt, then the application
#   alembic/ + .ini  -> `alembic upgrade head` at container start
#   captain-definition, Dockerfile, .dockerignore -> the build itself
# Docs, tests and tooling are not in this list because the image never reads them.
$PackageEntries = @(
    "captain-definition",
    "Dockerfile",
    ".dockerignore",
    "backend",
    "frontend",
    "alembic",
    "alembic.ini"
)

# Patterns pruned while writing the archive. Matched by bsdtar/GNU tar against
# the path as stored.
$TarExcludes = @(
    "*/node_modules", "*/node_modules/*",
    "frontend/dist", "frontend/dist/*",
    "*/__pycache__", "*/__pycache__/*", "*.pyc",
    "backend/tests", "backend/tests/*",
    ".venv", ".venv/*", "venv", "venv/*",
    ".env", ".env.*", "*/.env", "*/.env.*",
    "*.log", "*.sqlite", "*.sqlite3", "*.db",
    "*.pem", "*.key", "*.token",
    "*.tsbuildinfo"
)

# Independent audit of the finished archive. This is not the same list as
# $TarExcludes on purpose: it re-checks the result rather than trusting the
# tool that produced it. Authentication and production secrets exist in this
# architecture now, so a package is inspected before it leaves the machine.
$ForbiddenPatterns = @(
    ".env", ".env.*", "*/.env", "*/.env.*",
    ".git", ".git/*", "*/.git/*",
    ".venv/*", "*/.venv/*", "venv/*", "*/venv/*",
    "node_modules", "node_modules/*", "*/node_modules/*",
    "frontend/dist", "frontend/dist/*",
    "dist", "dist/*",
    "*__pycache__*", "*.pyc",
    "*.log", "*.sqlite*", "*.db",
    "*.pem", "*.key", "*.token"
)

# A package missing any of these fails on CapRover in a confusing way, so catch
# it here instead.
$RequiredArchiveEntries = @(
    "captain-definition",
    "Dockerfile",
    "backend/app/main.py",
    "backend/requirements.txt",
    "frontend/package.json",
    "alembic.ini"
)

# Files that must exist before packaging is even attempted.
$RequiredProjectPaths = @(
    "captain-definition",
    "Dockerfile",
    ".dockerignore",
    "backend",
    "frontend",
    "alembic",
    "alembic.ini"
)

# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #

$script:StepNumber = 0

function Write-Step {
    param([string]$Message)
    $script:StepNumber++
    Write-Host ""
    Write-Host ("[{0}] {1}" -f $script:StepNumber, $Message) -ForegroundColor Cyan
}

function Write-Detail {
    param([string]$Message)
    Write-Host "    $Message"
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Yellow
}

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$FailureMessage
    )

    if ($WorkingDirectory) { Push-Location -LiteralPath $WorkingDirectory }
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FailureMessage (exit code $LASTEXITCODE)"
        }
    }
    finally {
        if ($WorkingDirectory) { Pop-Location }
    }
}

function Read-EnvFile {
    <#
        Minimal KEY=VALUE parser: blank lines and # comments are skipped, the
        first = splits the pair, and one layer of surrounding quotes is removed.
        No interpolation, no export, no multi-line values - this file holds
        three flat strings.
    #>
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    $lineNumber = 0
    foreach ($line in (Get-Content -LiteralPath $Path)) {
        $lineNumber++
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) { continue }

        $separator = $trimmed.IndexOf("=")
        if ($separator -lt 1) {
            throw "$Path line ${lineNumber}: expected KEY=VALUE, found '$trimmed'."
        }

        $key = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if ($value.Length -ge 2) {
            $first = $value[0]
            $last = $value[$value.Length - 1]
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
        $values[$key] = $value
    }
    return $values
}

function Get-DeployConfig {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][bool]$FileRequired
    )

    $config = @{}

    if (Test-Path -LiteralPath $Path) {
        Write-Detail "Config file: $Path"
        $fromFile = Read-EnvFile -Path $Path

        # Reject anything outside the allowlist. A DATABASE_URL or
        # APP_SECRET_KEY landing here is a real mistake worth stopping for: it
        # means someone is treating the deployment package as a place to keep
        # production secrets.
        $unknown = @($fromFile.Keys | Where-Object { $AllowedKeys -notcontains $_ } | Sort-Object)
        if ($unknown.Count -gt 0) {
            throw (
                "$Path contains keys that are not deploy-time configuration: " +
                ($unknown -join ", ") + ".`n" +
                "Only " + ($AllowedKeys -join ", ") + " are accepted here.`n" +
                "Runtime settings belong in the CapRover application's own environment " +
                "variables - see docs/04_technical/ENVIRONMENT_VARIABLES.md."
            )
        }

        foreach ($key in $fromFile.Keys) { $config[$key] = $fromFile[$key] }
    }
    elseif ($FileRequired) {
        throw "Config file not found: $Path`nCopy deploy/.env.example to deploy/.env and fill it in."
    }
    else {
        Write-Detail "No config file at $Path (using environment variables only)."
    }

    # The environment fills any gap, so CI can pass the token without a file.
    foreach ($key in $AllowedKeys) {
        $hasValue = $config.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace($config[$key])
        if (-not $hasValue) {
            $fromEnv = [Environment]::GetEnvironmentVariable($key)
            if (-not [string]::IsNullOrWhiteSpace($fromEnv)) {
                $config[$key] = $fromEnv
                Write-Detail "$key taken from the environment."
            }
        }
    }

    return $config
}

function Assert-DeployConfig {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    $missing = @()
    foreach ($key in $AllowedKeys) {
        if (-not $Config.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($Config[$key])) {
            $missing += $key
        }
    }
    if ($missing.Count -gt 0) {
        throw (
            "Missing deploy configuration: " + ($missing -join ", ") + ".`n" +
            "Set them in deploy/.env (see deploy/.env.example) or in the environment.`n" +
            "Use -SkipDeploy to build and inspect a package without deploying."
        )
    }

    if ($Config["CAPROVER_URL"] -notmatch '^https?://') {
        throw "CAPROVER_URL must start with http:// or https:// (got '$($Config['CAPROVER_URL'])')."
    }
    if ($Config["CAPROVER_URL"].StartsWith("http://")) {
        Write-Warn "CAPROVER_URL is plain HTTP; the app token will cross the network unencrypted."
    }
}

function Assert-ProjectLayout {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $missing = @()
    foreach ($relative in $RequiredProjectPaths) {
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot $relative))) {
            $missing += $relative
        }
    }
    if ($missing.Count -gt 0) {
        throw (
            "Required project files are missing: " + ($missing -join ", ") + ".`n" +
            "Run this script from a complete checkout of the repository."
        )
    }
    Write-Ok ("Verified " + $RequiredProjectPaths.Count + " required paths.")
}

function Get-PythonCommand {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    # Prefer the project virtualenv: it is the interpreter that actually has
    # the test dependencies installed.
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) { return $venvPython }

    $fallback = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $fallback) {
        throw "No Python found. Create .venv or put python on PATH. Use -SkipTests to bypass (not recommended)."
    }
    return $fallback.Source
}

function New-DeployPackage {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$TarPath
    )

    $tarArguments = @("-cf", $TarPath)
    foreach ($pattern in $TarExcludes) { $tarArguments += @("--exclude", $pattern) }
    $tarArguments += $PackageEntries

    # Run from the repository root so archive paths are root-relative:
    # CapRover expects captain-definition at the top of the tar, not nested.
    Invoke-Native -Executable "tar" -Arguments $tarArguments -WorkingDirectory $RepoRoot `
        -FailureMessage "Failed to create the deployment archive"

    if (-not (Test-Path -LiteralPath $TarPath)) {
        throw "tar reported success but $TarPath does not exist."
    }
}

function Test-PackageContents {
    <#
        Audit the finished archive. Runs against what tar actually wrote, so a
        mistake in the exclude list is caught rather than trusted.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$TarPath
    )

    Push-Location -LiteralPath $RepoRoot
    try {
        $entries = @(& tar -tf $TarPath)
        if ($LASTEXITCODE -ne 0) { throw "Could not read back $TarPath (exit code $LASTEXITCODE)." }
    }
    finally {
        Pop-Location
    }

    if ($entries.Count -eq 0) { throw "The archive is empty." }

    $violations = @()
    foreach ($entry in $entries) {
        $normalized = $entry -replace '\\', '/'
        $normalized = $normalized -replace '^\./', ''
        $bare = $normalized.TrimEnd('/')
        foreach ($pattern in $ForbiddenPatterns) {
            if ($bare -like $pattern) {
                $violations += ("{0}   (matched '{1}')" -f $entry, $pattern)
                break
            }
        }
    }

    if ($violations.Count -gt 0) {
        # Delete it: a package that failed inspection must not be left lying
        # around where somebody could deploy it by hand.
        Remove-Item -LiteralPath $TarPath -Force
        throw (
            "Forbidden content in the deployment archive - package deleted:`n  " +
            (($violations | Select-Object -First 25) -join "`n  ") +
            "`n(" + $violations.Count + " offending entries)"
        )
    }

    $fileEntries = @($entries | Where-Object { -not $_.EndsWith("/") })
    $present = @{}
    foreach ($entry in $fileEntries) { $present[($entry -replace '\\', '/')] = $true }

    $missing = @()
    foreach ($required in $RequiredArchiveEntries) {
        if (-not $present.ContainsKey($required)) { $missing += $required }
    }
    if ($missing.Count -gt 0) {
        Remove-Item -LiteralPath $TarPath -Force
        throw (
            "The archive is missing files the CapRover build needs - package deleted:`n  " +
            ($missing -join "`n  ")
        )
    }

    return $fileEntries
}

function Remove-OldPackages {
    param([Parameter(Mandatory = $true)][string]$DistDirectory)

    $packages = @(
        Get-ChildItem -LiteralPath $DistDirectory -Filter "$AppSlug`_*.tar" -File |
            Sort-Object LastWriteTime -Descending
    )
    if ($packages.Count -le $RetainPackages) {
        Write-Detail ("Keeping " + $packages.Count + " package(s); retention limit is $RetainPackages.")
        return
    }

    $stale = $packages | Select-Object -Skip $RetainPackages
    foreach ($item in $stale) {
        Remove-Item -LiteralPath $item.FullName -Force
        Write-Detail "Removed old package $($item.Name)"
    }
    Write-Ok ("Retained the $RetainPackages most recent package(s).")
}

function Invoke-CapRoverDeploy {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$TarPath
    )

    # The token is exported only for the duration of the CLI call, and the
    # previous value (or its absence) is restored afterwards, so running this
    # script does not quietly change the shell it was run from.
    $hadToken = Test-Path Env:CAPROVER_APP_TOKEN
    $previousToken = if ($hadToken) { $env:CAPROVER_APP_TOKEN } else { $null }

    # CapRover CLI 2.4.3 only recognizes paths beginning with "/" as absolute.
    # On Windows it treats a drive-qualified path (C:\...) as relative and joins
    # it to the working directory again. Packages are always created in dist/,
    # so pass that repo-relative path to the CLI. Avoid Path.GetRelativePath:
    # it is unavailable in the .NET runtime used by Windows PowerShell 5.1.
    $tarPathForCli = Join-Path "dist" (Split-Path -Leaf $TarPath)

    try {
        $env:CAPROVER_APP_TOKEN = $Config["CAPROVER_APP_TOKEN"]
        Invoke-Native -Executable "caprover" -WorkingDirectory $RepoRoot -Arguments @(
            "deploy",
            "--caproverUrl", $Config["CAPROVER_URL"],
            "--caproverApp", $Config["CAPROVER_APP"],
            "--tarFile", $tarPathForCli
        ) -FailureMessage "CapRover deployment failed"
    }
    finally {
        if ($hadToken) { $env:CAPROVER_APP_TOKEN = $previousToken }
        elseif (Test-Path Env:CAPROVER_APP_TOKEN) { Remove-Item Env:CAPROVER_APP_TOKEN }
    }
}

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DistDirectory = Join-Path $RepoRoot "dist"

if (-not $EnvironmentFile) { $EnvironmentFile = Join-Path $PSScriptRoot ".env" }

Write-Host ""
Write-Host "HandBase Web - CapRover deployment" -ForegroundColor White
Write-Host "Repository root: $RepoRoot"
if ($SkipDeploy) { Write-Warn "-SkipDeploy: the package will be built and inspected but not uploaded." }
if ($SkipTests) { Write-Warn "-SkipTests: tests will NOT run. Do not use this for a production deploy." }

# --- 1. deploy-time configuration ---
Write-Step "Loading deploy configuration"
$config = Get-DeployConfig -Path $EnvironmentFile -FileRequired (-not $SkipDeploy)
if ($SkipDeploy) {
    Write-Detail "Deploy configuration is not validated because -SkipDeploy was passed."
}
else {
    Assert-DeployConfig -Config $config
    Write-Ok "Target: $($config['CAPROVER_APP']) at $($config['CAPROVER_URL'])"
    Write-Detail "App token: present (not shown)"
}

# --- 2. project layout ---
Write-Step "Validating project layout"
Assert-ProjectLayout -RepoRoot $RepoRoot

if (-not $SkipDeploy) {
    if ($null -eq (Get-Command caprover -ErrorAction SilentlyContinue)) {
        throw "CapRover CLI not found. Install it with: npm install -g caprover"
    }
    Write-Ok "CapRover CLI found."
}

# --- 3. tests ---
Write-Step "Running backend tests"
if ($SkipTests) {
    Write-Warn "Skipped (-SkipTests)."
}
else {
    $python = Get-PythonCommand -RepoRoot $RepoRoot
    Write-Detail "Interpreter: $python"
    Invoke-Native -Executable $python -Arguments @("-m", "pytest") -WorkingDirectory $RepoRoot `
        -FailureMessage "Backend tests failed - nothing was packaged"
    Write-Ok "Backend tests passed."
    Write-Detail "Note: this is the fast SQLite suite. PostgreSQL integration tests run"
    Write-Detail "separately with 'pytest -m postgres' (see docs/03_validation/POSTGRES_INTEGRATION.md)."
}

# --- 4. frontend build ---
# Always runs, even with -SkipTests: `tsc -b` is the frontend's type check, and
# a build failure here would otherwise surface as a failed Docker build on the
# server instead of on this machine.
Write-Step "Building the frontend"
$frontendDirectory = Join-Path $RepoRoot "frontend"
if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory "node_modules"))) {
    Write-Detail "node_modules missing; running npm install."
    Invoke-Native -Executable "npm" -Arguments @("install") -WorkingDirectory $frontendDirectory `
        -FailureMessage "npm install failed"
}
Invoke-Native -Executable "npm" -Arguments @("run", "build") -WorkingDirectory $frontendDirectory `
    -FailureMessage "Frontend build failed - nothing was packaged"
Write-Ok "Frontend build succeeded."
Write-Detail "The image rebuilds it from source; this run is the local verification."

# --- 5. package ---
Write-Step "Creating the deployment package"
if (-not (Test-Path -LiteralPath $DistDirectory)) {
    New-Item -ItemType Directory -Path $DistDirectory | Out-Null
}
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tarName = "{0}_{1}.tar" -f $AppSlug, $timestamp
$tarPath = Join-Path $DistDirectory $tarName

New-DeployPackage -RepoRoot $RepoRoot -TarPath $tarPath
$sizeMb = [math]::Round((Get-Item -LiteralPath $tarPath).Length / 1MB, 2)
Write-Ok "Created dist/$tarName ($sizeMb MB)"

# --- 6. archive inspection ---
Write-Step "Inspecting the archive"
$files = Test-PackageContents -RepoRoot $RepoRoot -TarPath $tarPath
Write-Ok ("No forbidden content. " + $files.Count + " files, all required entries present.")

$topLevel = $files |
    ForEach-Object { ($_ -split '/')[0] } |
    Group-Object |
    Sort-Object Name
foreach ($group in $topLevel) {
    Write-Detail ("{0,-22} {1,5} file(s)" -f $group.Name, $group.Count)
}

Write-Step "Applying package retention"
Remove-OldPackages -DistDirectory $DistDirectory

# --- 7. deploy ---
Write-Step "Deploying to CapRover"
if ($SkipDeploy) {
    Write-Warn "Skipped (-SkipDeploy)."
    Write-Host ""
    Write-Host "Package ready for review: dist/$tarName" -ForegroundColor Green
    Write-Host "Inspect it with: tar -tvf dist/$tarName"
    Write-Host "Deploy it by re-running this script without -SkipDeploy."
}
else {
    Invoke-CapRoverDeploy -Config $config -RepoRoot $RepoRoot -TarPath $tarPath
    Write-Host ""
    Write-Host "Deployed dist/$tarName to $($config['CAPROVER_APP'])." -ForegroundColor Green
    Write-Host ""
    Write-Host "After the container restarts:" -ForegroundColor White
    Write-Host "  1. Alembic runs 'upgrade head' on start."
    Write-Host "  2. Check readiness:  <app url>/api/ready  must report 'ready'."
    Write-Host "  3. On a first-ever deploy, create the first OWNER - no account exists"
    Write-Host "     until you do. See docs/04_technical/BOOTSTRAP_OWNER.md."
}

Write-Host ""
