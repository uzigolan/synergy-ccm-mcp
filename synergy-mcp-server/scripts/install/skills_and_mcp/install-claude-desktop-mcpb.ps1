param(
    [string]$Name = "synergy-ccm-mcp"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$ServerInstaller = Join-Path $RepoRoot "synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1"
$ClaudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
$ClaudeConfigDir = Split-Path -Parent $ClaudeConfig
New-Item -ItemType Directory -Force -Path $ClaudeConfigDir | Out-Null
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
$Dist = Join-Path $RepoRoot "synergy-mcp-server\dist"
$McpbDir = Join-Path $Dist "claude-desktop-mcpb"
$LocalJsonDir = Join-Path $Dist "claude-desktop-local-mcp"
$TempDir = Join-Path $Dist "claude-desktop-mcpb-work"
$McpbFile = Join-Path $McpbDir "synergy-ccm-mcp-local.mcpb"
$McpbZip = Join-Path $McpbDir "synergy-ccm-mcp-local.zip"
$LocalJsonFile = Join-Path $LocalJsonDir "synergy-ccm-mcp-local-mcp-server.json"

New-Item -ItemType Directory -Force -Path $McpbDir, $LocalJsonDir | Out-Null
Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

$server = [pscustomobject]@{
    command = $VenvPython
    args = @("-m", "synergy_mcp")
    env = [pscustomobject]@{ SYNERGY_MCP_INVENTORY = $Inventory }
}

Write-Host "Claude Desktop MCP server entry to add:" -ForegroundColor Cyan
$serverJson = $server | ConvertTo-Json -Depth 20
Write-Host $serverJson

$mcpServers = New-Object psobject
$mcpServers | Add-Member -MemberType NoteProperty -Name $Name -Value $server
[pscustomobject]@{ mcpServers = $mcpServers } | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $LocalJsonFile

$manifestServers = New-Object psobject
$manifestServers | Add-Member -MemberType NoteProperty -Name $Name -Value $server
$manifest = [pscustomobject]@{
    name = "synergy-ccm-mcp"
    display_name = "Synergy CCM MCP"
    version = "0.1.0"
    description = "Read-only IBM Rational Synergy MCP server over local stdio."
    mcpServers = $manifestServers
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 (Join-Path $TempDir "manifest.json")
Compress-Archive -Path (Join-Path $TempDir "*") -DestinationPath $McpbZip -Force
Move-Item -Force $McpbZip $McpbFile
Remove-Item -Recurse -Force $TempDir

& $VenvPython $PluginBuilder --name $Name
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Start-Process explorer.exe $PluginDist

Write-Host ""
Write-Host "Done. Claude Desktop artifacts created:"
Write-Host "  MCPB:           $McpbFile"
Write-Host "  Local MCP JSON: $LocalJsonFile"
Write-Host "Done. Claude Desktop plugin built: $PluginDist"
Write-Host "Import the MCPB in Claude Desktop Settings -> Extensions, then fully restart Claude Desktop."