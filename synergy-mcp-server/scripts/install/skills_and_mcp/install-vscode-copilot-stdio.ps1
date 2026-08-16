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
$SkillsSrc = Join-Path $RepoRoot "synergy-mcp-server\skills"
$SkillsDest = Join-Path $env:USERPROFILE ".copilot\skills"
$ResolvedMcpFile = Join-Path $env:APPDATA "Code\User\mcp.json"

$McpDir = Split-Path -Parent $ResolvedMcpFile
if (-not $McpDir) {
    throw "Could not determine parent directory for MCP config path: $ResolvedMcpFile"
}
New-Item -ItemType Directory -Force -Path $McpDir | Out-Null

if (Test-Path $ResolvedMcpFile) {
    $json = Get-Content $ResolvedMcpFile -Raw | ConvertFrom-Json
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

($json | ConvertTo-Json -Depth 20) | Set-Content -Encoding UTF8 $ResolvedMcpFile

New-Item -ItemType Directory -Force -Path $SkillsDest | Out-Null
$selectedSkills = @()
if (Test-Path $SkillsSrc) {
    $selectedSkills = @(
        Get-ChildItem -Path $SkillsSrc -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
            Sort-Object Name
    )
    foreach ($skill in $selectedSkills) {
        Copy-Item -Recurse -Force $skill.FullName $SkillsDest
    }
}

$selectedNames = @($selectedSkills | ForEach-Object { $_.Name })
Get-ChildItem -Path $SkillsDest -Directory -Filter "synergy-*" -ErrorAction SilentlyContinue |
    ForEach-Object {
        if ($selectedNames -notcontains $_.Name) {
            Remove-Item -Recurse -Force $_.FullName
        }
    }

Write-Host ""
Write-Host "Done. VS Code MCP config updated: $ResolvedMcpFile"
Write-Host "Done. Copilot skills refreshed: $SkillsDest"
Write-Host "Reload VS Code, start Copilot Agent mode, then ask: /synergy-core"