[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$WorkspaceId,
    [Parameter(Mandatory = $true)] [string]$DatasetId
)

$ErrorActionPreference = 'Stop'

if (-not $env:POWER_BI_ACCESS_TOKEN) {
    throw 'Set POWER_BI_ACCESS_TOKEN to a valid Power BI REST API bearer token before running this script.'
}

$headers = @{ Authorization = "Bearer $env:POWER_BI_ACCESS_TOKEN" }
$uri = "https://api.powerbi.com/v1.0/myorg/groups/$WorkspaceId/datasets/$DatasetId/refreshes"
Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType 'application/json' -Body '{}'
Write-Host 'Power BI Service refresh request submitted.'
