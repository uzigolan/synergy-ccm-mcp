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
$McpDir = Join-Path $RepoRoot ".vscode"
$McpFile = Join-Path $McpDir "mcp.json"
New-Item -ItemType Directory -Force -Path $McpDir | Out-Null

if (Test-Path $McpFile) {
    $json = Get-Content $McpFile -Raw | ConvertFrom-Json
} else {
    $json = New-Object psobject
}
if (-not $json.PSObject.Properties["servers"]) {
    $json | Add-Member -MemberType NoteProperty -Name "servers" -Value (New-Object psobject)
}

$server = [pscustomobject]@{
    type = "stdio"
    command = $VenvPython
    args = @("-m", "synergy_mcp")
    env = [pscustomobject]@{
        SYNERGY_MCP_INVENTORY = $Inventory
    }
}
if ($json.servers.PSObject.Properties[$Name]) {
    $json.servers.PSObject.Properties.Remove($Name)
}
$json.servers | Add-Member -MemberType NoteProperty -Name $Name -Value $server

($json | ConvertTo-Json -Depth 20) | Set-Content -Encoding UTF8 $McpFile

Write-Host ""
Write-Host "Done. VS Code MCP config updated: $McpFile"
Write-Host "Reload VS Code, start Copilot Agent mode, then ask: List the Synergy databases you can see."