param(
    [string]$Name = "synergy-ccm-mcp"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$ServerInstaller = Join-Path $RepoRoot "synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1"
$ClaudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

$ConfigDir = Split-Path -Parent $ClaudeConfig
if (-not $ConfigDir) {
    throw "Could not determine parent directory for Claude config path: $ClaudeConfig"
}
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

if (Test-Path $ClaudeConfig) {
    $BackupFile = "$ClaudeConfig.$(Get-Date -Format 'yyyyMMdd-HHmmss').bak"
    Copy-Item -Force $ClaudeConfig $BackupFile
    Write-Host "Backup saved: $BackupFile"
}

& $ServerInstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$VenvPython = Join-Path $RepoRoot "synergy-mcp\.venv\Scripts\python.exe"
$Inventory = Join-Path $RepoRoot "synergy-mcp\inventory.yaml"
$PluginBuilder = Join-Path $RepoRoot "synergy-mcp-server\scripts\build_claude_plugin.py"
$PluginDist = Join-Path $RepoRoot "synergy-mcp-server\dist\plugin"

if (Test-Path $ClaudeConfig) {
    $json = Get-Content $ClaudeConfig -Raw | ConvertFrom-Json
} else {
    $json = New-Object psobject
}
if (-not $json.PSObject.Properties["mcpServers"]) {
    $json | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value (New-Object psobject)
}

$server = [pscustomobject]@{
    command = $VenvPython
    args = @("-m", "synergy_mcp")
    env = [pscustomobject]@{
        SYNERGY_MCP_INVENTORY = $Inventory
    }
}

Write-Host "Claude Desktop MCP server entry to add:" -ForegroundColor Cyan
$server | ConvertTo-Json -Depth 20 | Write-Host

if ($json.mcpServers.PSObject.Properties[$Name]) {
    $json.mcpServers.PSObject.Properties.Remove($Name)
}
$json.mcpServers | Add-Member -MemberType NoteProperty -Name $Name -Value $server

($json | ConvertTo-Json -Depth 20) | Set-Content -Encoding UTF8 $ClaudeConfig

& $VenvPython $PluginBuilder -Name $Name
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Start-Process explorer.exe $PluginDist

Write-Host ""
Write-Host "Done. Claude Desktop MCP stdio config updated: $ClaudeConfig"
Write-Host "Done. Claude Desktop plugin built: $PluginDist"
Write-Host "Fully quit Claude Desktop, relaunch it, then ask: List the Synergy databases you can see."
