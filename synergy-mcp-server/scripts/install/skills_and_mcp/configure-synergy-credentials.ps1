# Configure Synergy CCM Credentials for synergy-mcp
# This script stores your Synergy CCM credentials securely and sets environment variables

param(
    [string]$Username
)

$ErrorActionPreference = "Stop"

function Get-InventoryCcmBinary {
    param([string]$InventoryPath)

    if (-not (Test-Path $InventoryPath)) {
        return $null
    }

    $line = Select-String -Path $InventoryPath -Pattern '^\s*ccm_binary\s*:' | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $value = ($line.Line -replace '^\s*ccm_binary\s*:\s*', '').Trim()
    return $value.Trim('"').Trim("'")
}

function Test-CcmBinary {
    param([string]$CcmBinary)

    if (-not $CcmBinary) {
        return $false
    }

    if (Test-Path $CcmBinary) {
        return $true
    }

    return [bool](Get-Command $CcmBinary -ErrorAction SilentlyContinue)
}

function Set-InventoryCcmBinary {
    param(
        [string]$InventoryPath,
        [string]$CcmBinary
    )

    $escaped = $CcmBinary.Replace('\', '/').Replace('"', '\"')
    $content = Get-Content $InventoryPath
    $updated = $false
    $content = $content | ForEach-Object {
        if (-not $updated -and $_ -match '^\s*ccm_binary\s*:') {
            $updated = $true
            "  ccm_binary: `"$escaped`""
        } else {
            $_
        }
    }

    if (-not $updated) {
        $content = @('settings:', "  ccm_binary: `"$escaped`"") + $content
    }

    $content | Set-Content -Encoding UTF8 $InventoryPath
}

function Resolve-CcmBinary {
    param([string]$CurrentCcmBinary)

    if (Test-CcmBinary $CurrentCcmBinary) {
        return $CurrentCcmBinary
    }

    $candidates = @(
        "C:\Program Files (x86)\IBM\Rational\Synergy\7.2.1\bin\ccm.exe",
        "C:\Program Files\IBM\Rational\Synergy\7.2.1\bin\ccm.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $command = Get-Command ccm.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$Inventory = Join-Path $RepoRoot "synergy-mcp\inventory.yaml"
$InventoryExample = Join-Path $RepoRoot "synergy-mcp\inventory.example.yaml"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Synergy CCM Credentials Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Inventory)) {
    if (Test-Path $InventoryExample) {
        Copy-Item $InventoryExample $Inventory
        Write-Host "Created inventory: $Inventory" -ForegroundColor Gray
    } else {
        throw "Inventory not found and example inventory is missing: $InventoryExample"
    }
}

$configuredCcmBinary = Get-InventoryCcmBinary $Inventory
$resolvedCcmBinary = Resolve-CcmBinary $configuredCcmBinary

if (-not $resolvedCcmBinary) {
    Write-Host "Could not find the Synergy CCM CLI binary." -ForegroundColor Yellow
    Write-Host "Current inventory value: $configuredCcmBinary" -ForegroundColor Yellow
    do {
        $resolvedCcmBinary = Read-Host "Enter full path to ccm.exe"
        if (-not (Test-CcmBinary $resolvedCcmBinary)) {
            Write-Host "ccm.exe was not found at that path. Try again." -ForegroundColor Red
            $resolvedCcmBinary = $null
        }
    } while (-not $resolvedCcmBinary)
}

if ($resolvedCcmBinary -ne $configuredCcmBinary) {
    Set-InventoryCcmBinary -InventoryPath $Inventory -CcmBinary $resolvedCcmBinary
    Write-Host "OK ccm_binary updated in inventory: $resolvedCcmBinary" -ForegroundColor Green
} else {
    Write-Host "OK ccm_binary: $resolvedCcmBinary" -ForegroundColor Green
}

Write-Host ""

# If username not provided, prompt for it
if (-not $Username) {
    $Username = Read-Host "Enter your Synergy CCM username"
}

if (-not $Username) {
    Write-Host "Error: Username is required" -ForegroundColor Red
    exit 1
}

# Prompt for password
$password = Read-Host "Enter your Synergy CCM password" -AsSecureString
$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$passwordPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr)

# Create credential directory
$CredDir = "$env:APPDATA\synergy-mcp"
Write-Host "Creating credential directory: $CredDir" -ForegroundColor Gray
New-Item -ItemType Directory -Force -Path $CredDir | Out-Null

# Store encrypted password
$CredFile = "$CredDir\ccm_password.txt"
Write-Host "Storing encrypted password to: $CredFile" -ForegroundColor Gray
$password | ConvertFrom-SecureString | Set-Content $CredFile

# Set environment variables
Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Cyan

[Environment]::SetEnvironmentVariable("SYNERGY_MCP_USER", $Username, "User")
Write-Host "OK SYNERGY_MCP_USER = $Username" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("CCM_CRED_FILE", $CredFile, "User")
Write-Host "OK CCM_CRED_FILE = $CredFile" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("SYNERGY_MCP_PASSWORD", $passwordPlain, "User")
Write-Host "OK SYNERGY_MCP_PASSWORD = <hidden>" -ForegroundColor Green

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Your Synergy CCM credentials are now configured." -ForegroundColor Cyan
Write-Host "The following environment variables have been set for your user:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  SYNERGY_MCP_USER     = $Username"
Write-Host "  SYNERGY_MCP_PASSWORD = <hidden>"
Write-Host "  CCM_CRED_FILE        = $CredFile"
Write-Host ""
Write-Host "Encrypted password stored at:" -ForegroundColor Cyan
Write-Host "  $CredFile"
Write-Host ""
Write-Host "Note: You may need to restart VS Code or your terminal for the" -ForegroundColor Yellow
Write-Host "environment variables to take effect." -ForegroundColor Yellow
Write-Host ""
