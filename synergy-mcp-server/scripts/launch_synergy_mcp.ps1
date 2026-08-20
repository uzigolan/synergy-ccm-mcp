param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [Parameter(Mandatory = $true)]
    [string]$InventoryPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}
if (-not (Test-Path $InventoryPath)) {
    throw "Synergy inventory not found: $InventoryPath"
}

foreach ($scope in @("Machine", "User")) {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($key in $vars.Keys) {
        $name = [string]$key
        if ($name -eq "CCM_CRED_FILE" -or $name -like "SYNERGY_*") {
            [Environment]::SetEnvironmentVariable($name, [string]$vars[$key], "Process")
        }
    }
}

[Environment]::SetEnvironmentVariable("SYNERGY_MCP_INVENTORY", $InventoryPath, "Process")

& $PythonPath -m synergy_mcp
exit $LASTEXITCODE
