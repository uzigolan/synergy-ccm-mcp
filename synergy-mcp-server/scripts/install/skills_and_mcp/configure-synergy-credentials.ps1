# Configure Synergy CCM Credentials for synergy-mcp
# This script stores your Synergy CCM credentials securely and sets environment variables

param(
    [string]$Username,
    [string]$CcmAddress = "your-ccm-server:5580"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Synergy CCM Credentials Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
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

# Create credential directory
$CredDir = "$env:APPDATA\synergy-mcp"
Write-Host "Creating credential directory: $CredDir" -ForegroundColor Gray
New-Item -ItemType Directory -Force -Path $CredDir | Out-Null

# Store encrypted password
$CredFile = "$CredDir\ccm_password.txt"
Write-Host "Storing encrypted password to: $CredFile" -ForegroundColor Gray
$password | ConvertFrom-SecureString | Set-Content $CredFile

# Prompt for CCM server address if not provided
if ($CcmAddress -eq "your-ccm-server:5580") {
    $CcmAddress = Read-Host "Enter your Synergy CCM server address (default: your-ccm-server:5580)"
    if (-not $CcmAddress) {
        $CcmAddress = "your-ccm-server:5580"
    }
}

# Set environment variables
Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Cyan

[Environment]::SetEnvironmentVariable("CCM_USER", $Username, "User")
Write-Host "✓ CCM_USER = $Username" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("CCM_ADDR", $CcmAddress, "User")
Write-Host "✓ CCM_ADDR = $CcmAddress" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("CCM_CRED_FILE", $CredFile, "User")
Write-Host "✓ CCM_CRED_FILE = $CredFile" -ForegroundColor Green

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Your Synergy CCM credentials are now configured." -ForegroundColor Cyan
Write-Host "The following environment variables have been set for your user:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  CCM_USER     = $Username"
Write-Host "  CCM_ADDR     = $CcmAddress"
Write-Host "  CCM_CRED_FILE = $CredFile"
Write-Host ""
Write-Host "Encrypted password stored at:" -ForegroundColor Cyan
Write-Host "  $CredFile"
Write-Host ""
Write-Host "Note: You may need to restart VS Code or your terminal for the" -ForegroundColor Yellow
Write-Host "environment variables to take effect." -ForegroundColor Yellow
Write-Host ""
