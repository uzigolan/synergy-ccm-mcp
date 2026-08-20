param(
    [string]$Name = "synergy-ccm-mcp"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$ServerInstaller = Join-Path $RepoRoot "synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1"

& $ServerInstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$VenvPython = Join-Path $RepoRoot "synergy-mcp\.venv\Scripts\python.exe"
$Inventory = Join-Path $RepoRoot "synergy-mcp\inventory.yaml"
$Launcher = Join-Path $RepoRoot "synergy-mcp-server\scripts\launch_synergy_mcp.ps1"
$PluginBuilder = Join-Path $RepoRoot "synergy-mcp-server\scripts\build_claude_plugin.py"
$PluginDist = Join-Path $RepoRoot "synergy-mcp-server\dist\plugin"

& $VenvPython $PluginBuilder --name $Name
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$server = [pscustomobject]@{
    command = "powershell.exe"
    args = @(
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $Launcher,
        "-PythonPath",
        $VenvPython,
        "-InventoryPath",
        $Inventory
    )
}

Start-Process explorer.exe $PluginDist

Write-Host ""
Write-Host "Done. Claude Desktop plugin built: $PluginDist"
Write-Host "Import the plugin zip from this folder in Claude Desktop."
Write-Host ""
Write-Host "Add this entry manually under the top-level mcpServers object in Claude Desktop config:" -ForegroundColor Cyan
Write-Host "`"$Name`": $($server | ConvertTo-Json -Depth 20)"
Write-Host ""
Write-Host "The installer did not modify claude_desktop_config.json."
