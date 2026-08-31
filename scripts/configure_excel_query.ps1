[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workbookPath = Join-Path $projectRoot 'dashboards\excel\Automated_Bank_Reconciliation_MIS.xlsx'

$queryFormula = @'
let
    ProjectRootTable = Excel.CurrentWorkbook(){[Name="ProjectRoot"]}[Content],
    ProjectRoot = ProjectRootTable{0}[Column1],
    Source = Csv.Document(File.Contents(ProjectRoot & "\data\output\reconciliation_results.csv"),[Delimiter=",", Columns=16, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"bank_transaction_id", type text}, {"ledger_id", type text}, {"bank_date", type date}, {"ledger_date", type date}, {"bank_amount", Int64.Type}, {"ledger_amount", type number}, {"amount_difference", type number}, {"date_difference_days", Int64.Type}, {"bank_description", type text}, {"ledger_description", type text}, {"match_status", type text}, {"match_reason", type text}, {"confidence_score", Int64.Type}, {"confidence_tier", type text}, {"duplicate_flag", type text}, {"duplicate_note", type text}})
in
    #"Changed Type"
'@

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$workbook = $null

try {
    $workbook = $excel.Workbooks.Open($workbookPath, 0, $false)
    $controlChecks = $workbook.Worksheets.Item('Control Checks')
    $controlChecks.Range('XFD1').Formula = '=LEFT(CELL("filename",A1),FIND("\dashboards\excel\",CELL("filename",A1))-1)'

    $existingName = $null
    try { $existingName = $workbook.Names.Item('ProjectRoot') } catch { }
    if ($existingName) { $existingName.Delete() }
    $workbook.Names.Add('ProjectRoot', "='Control Checks'!`$XFD`$1") | Out-Null

    $workbook.Queries.Item('reconciliation_results_v4').Formula = $queryFormula
    $excel.CalculateFullRebuild()
    $workbook.Save()
    $workbook.Close($true)
}
finally {
    if ($workbook) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($workbook)
    }
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)
}

Write-Host 'The Excel query now uses the project folder instead of a machine-specific path.'
