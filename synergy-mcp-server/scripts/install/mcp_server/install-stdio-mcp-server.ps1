param(
    [string]$Python = "py",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$PackageDir = Join-Path $RepoRoot "synergy-mcp"
$VenvDir = Join-Path $PackageDir ".venv"
$Inventory = Join-Path $PackageDir "inventory.yaml"
$InventoryExample = Join-Path $PackageDir "inventory.example.yaml"

if (-not (Test-Path $PackageDir)) { throw "Package directory not found: $PackageDir" }

if ($Force -and (Test-Path $VenvDir)) {
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating Python virtual environment: $VenvDir"
    & $Python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Virtual environment Python not found: $VenvPython" }

Write-Host "Installing synergy-mcp into the virtual environment ..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m pip install -e $PackageDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path $Inventory)) {
    Copy-Item $InventoryExample $Inventory
    Write-Host "Created inventory: $Inventory"
    Write-Host "Edit it before first use. Do not put passwords in inventory.yaml."
} else {
    Write-Host "Keeping existing inventory: $Inventory"
}

Write-Host ""
Write-Host "Done. Local stdio MCP server is prepared."
Write-Host "  Python:    $VenvPython"
Write-Host "  Inventory: $Inventory"
Write-Host ""
Write-Host "Next: configure credentials or attach mode, then install a client target."