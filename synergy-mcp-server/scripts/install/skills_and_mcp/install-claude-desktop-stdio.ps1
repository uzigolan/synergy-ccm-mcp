param(
    [string]$Name = "synergy-ccm-mcp"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$ServerInstaller = Join-Path $RepoRoot "synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1"

& $ServerInstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$VenvPython = Join-Path $RepoRoot "synergy-mcp\.venv\Scripts\python.exe"
$PluginBuilder = Join-Path $RepoRoot "synergy-mcp-server\scripts\build_claude_plugin.py"
$PluginDist = Join-Path $RepoRoot "synergy-mcp-server\dist\plugin"

& $VenvPython $PluginBuilder --name $Name
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Start-Process explorer.exe $PluginDist

Write-Host ""
Write-Host "Done. Claude Desktop plugin built: $PluginDist"
Write-Host "Import the plugin zip from this folder in Claude Desktop. No Claude config file was modified."
