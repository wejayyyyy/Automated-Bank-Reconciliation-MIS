[CmdletBinding()]
param(
    [switch]$SkipExcel
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$enginePath = Join-Path $projectRoot 'src\reconciliation_engine.py'
$workbookPath = Join-Path $projectRoot 'dashboards\excel\Automated_Bank_Reconciliation_MIS.xlsx'

Write-Host '1/2 Generating the reconciliation output...'
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $projectPython) {
    & $projectPython $enginePath
}
else {
    $py = Get-Command py -ErrorAction SilentlyContinue
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 $enginePath
    }
    elseif ($python) {
        & $python.Source $enginePath
    }
    else {
        throw 'Python 3 was not found. Install Python 3, then run: py -3 -m pip install -r requirements.txt'
    }
}
if ($LASTEXITCODE -ne 0) { throw "The reconciliation engine failed with exit code $LASTEXITCODE." }

if ($SkipExcel) {
    Write-Host '2/2 Excel refresh skipped.'
    exit 0
}

if (-not (Test-Path -LiteralPath $workbookPath)) {
    throw "Workbook not found: $workbookPath"
}

Write-Host '2/2 Refreshing and saving the Excel dashboard...'
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$workbook = $null
$transactionDetail = $null
$resultTable = $null
$queryTable = $null

try {
    $workbook = $excel.Workbooks.Open($workbookPath, 0, $false)
    $excel.CalculateFullRebuild()
    $transactionDetail = $workbook.Worksheets.Item('Transaction Detail')
    $resultTable = $transactionDetail.ListObjects.Item('reconciliation_results_v4')
    $queryTable = $resultTable.QueryTable
    $queryTable.BackgroundQuery = $false
    [void]$queryTable.Refresh($false)
    $excel.CalculateFullRebuild()
    $workbook.Save()
    $workbook.Close($true)
}
finally {
    if ($queryTable) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($queryTable)
    }
    if ($resultTable) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($resultTable)
    }
    if ($transactionDetail) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($transactionDetail)
    }
    if ($workbook) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($workbook)
    }
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)
}

Write-Host 'Finished. The Excel dashboard now reflects the latest reconciliation output.'
