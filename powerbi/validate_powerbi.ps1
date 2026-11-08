[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$PowerBiRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $PowerBiRoot
$SourceRoot = Join-Path $PowerBiRoot 'source'
$ReportRoot = Join-Path $SourceRoot 'Masterplop_Executive.Report'
$ModelRoot = Join-Path $SourceRoot 'Masterplop_Executive.SemanticModel'
$DataRoot = Join-Path $SourceRoot 'data'
$PreviewRoot = Join-Path $WorkspaceRoot 'docs\assets\powerbi'

function Assert-Equal {
    param(
        [Parameter(Mandatory)] [string] $Name,
        $Actual,
        $Expected
    )

    if ([string]$Actual -ne [string]$Expected) {
        throw ($Name + ": esperado '$Expected', obtenido '$Actual'.")
    }
}

function Assert-Exists {
    param([Parameter(Mandatory)] [string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "No existe el artefacto requerido: $Path"
    }
}

function Assert-GitNotIgnored {
    param([Parameter(Mandatory)] [string] $RepositoryPath)

    & git -C $WorkspaceRoot check-ignore -q -- $RepositoryPath
    if ($LASTEXITCODE -eq 0) {
        throw "El artefacto público está ignorado por Git: $RepositoryPath"
    }
}

function Assert-GitIgnored {
    param([Parameter(Mandatory)] [string] $RepositoryPath)

    & git -C $WorkspaceRoot check-ignore -q -- $RepositoryPath
    if ($LASTEXITCODE -ne 0) {
        throw "El artefacto local no está protegido por .gitignore: $RepositoryPath"
    }
}

$requiredArtifacts = @(
    (Join-Path $PowerBiRoot 'Masterplop_Executive.pbix'),
    (Join-Path $PowerBiRoot 'Masterplop_Executive.pdf'),
    (Join-Path $PowerBiRoot 'generate_masterplop_powerbi.js'),
    (Join-Path $PowerBiRoot 'README_POWERBI.md'),
    (Join-Path $PowerBiRoot 'VALIDACION_POWERBI.md'),
    (Join-Path $SourceRoot 'Masterplop_Executive.pbip'),
    $ReportRoot,
    $ModelRoot,
    $DataRoot,
    (Join-Path $PreviewRoot '01-resumen-ejecutivo.png'),
    (Join-Path $PreviewRoot '02-analisis-transaccional.png'),
    (Join-Path $PreviewRoot '03-campana-mayo-2024.png')
)
$requiredArtifacts | ForEach-Object { Assert-Exists -Path $_ }

$jsonFiles = Get-ChildItem -LiteralPath $SourceRoot -Recurse -File |
    Where-Object { $_.Extension -in '.json', '.pbir', '.pbip' }
foreach ($file in $jsonFiles) {
    $null = Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8 | ConvertFrom-Json
}

$pagesRoot = Join-Path $ReportRoot 'definition\pages'
$tablesRoot = Join-Path $ModelRoot 'definition\tables'
$executiveTmdl = Join-Path $tablesRoot 'executive.tmdl'
$pageCount = @(Get-ChildItem -LiteralPath $pagesRoot -Directory).Count
$visualCount = @(Get-ChildItem -LiteralPath $pagesRoot -Recurse -Filter 'visual.json').Count
$tableCount = @(Get-ChildItem -LiteralPath $tablesRoot -Filter '*.tmdl').Count
$measureCount = (Select-String -LiteralPath $executiveTmdl -Pattern '^\s*measure ').Count
$csvCount = @(Get-ChildItem -LiteralPath $DataRoot -Filter '*.csv').Count
$embeddedQueryCount = (Get-ChildItem -LiteralPath $tablesRoot -Filter '*.tmdl' |
    Select-String -Pattern 'Binary\.FromText\(EmbeddedCsv, BinaryEncoding\.Base64\)').Count

Assert-Equal -Name 'Cantidad de páginas' -Actual $pageCount -Expected 3
Assert-Equal -Name 'Cantidad de visuales' -Actual $visualCount -Expected 49
Assert-Equal -Name 'Cantidad de tablas TMDL' -Actual $tableCount -Expected 15
Assert-Equal -Name 'Cantidad de medidas DAX' -Actual $measureCount -Expected 39
Assert-Equal -Name 'Cantidad de extractos agregados' -Actual $csvCount -Expected 15
Assert-Equal -Name 'Consultas M portables embebidas' -Actual $embeddedQueryCount -Expected 15

$restrictedFiles = Get-ChildItem -LiteralPath $SourceRoot -Recurse -File |
    Where-Object { $_.Extension -in '.json', '.pbir', '.pbip', '.tmdl', '.csv', '.m', '.txt' }
$restrictedPattern = 'card_id|db_transac\.csv|C:\\Users|File\.Contents|password|secret|token'
$restrictedMatches = $restrictedFiles | Select-String -Pattern $restrictedPattern -CaseSensitive:$false
if ($restrictedMatches) {
    throw "Se encontraron referencias restringidas o no portables: $($restrictedMatches.Path -join ', ')"
}

$pbixPath = Join-Path $PowerBiRoot 'Masterplop_Executive.pbix'
$pbixAscii = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($pbixPath))
if ($pbixAscii -match 'card_id|db_transac\.csv|C:\\Users') {
    throw 'El escaneo binario básico del PBIX encontró una referencia restringida.'
}

$executive = Import-Csv -LiteralPath (Join-Path $DataRoot 'executive.csv')
Assert-Equal -Name 'Tarjetas activas' -Actual $executive.active_cards -Expected '59997'
Assert-Equal -Name 'Transacciones' -Actual $executive.transaction_count -Expected '2400000'
Assert-Equal -Name 'Gasto neto global' -Actual $executive.total_net_spend_usd -Expected '430124709.40'
Assert-Equal -Name 'Ticket promedio' -Actual $executive.avg_transaction_amount_usd -Expected '179.22'
Assert-Equal -Name 'Cashback oficial' -Actual $executive.total_cashback_usd -Expected '178471.62'
Assert-Equal -Name 'Tarjetas beneficiadas' -Actual $executive.beneficiary_card_count -Expected '4029'

$volume = Import-Csv -LiteralPath (Join-Path $DataRoot 'volume.csv')
$volumeExpected = @{
    '2024-T1-Credit' = '46747'
    '2024-T1-Debit' = '8224'
    '2024-T2-Credit' = '51037'
    '2024-T2-Debit' = '8960'
}
foreach ($row in $volume) {
    $typeKey = if ($row.product_type.StartsWith('Cr')) { 'Credit' } else { 'Debit' }
    $key = "$($row.period_year)-T$($row.period_quarter)-$typeKey"
    Assert-Equal -Name "Volumen $key" -Actual $row.active_cards -Expected $volumeExpected[$key]
}

$ticket = Import-Csv -LiteralPath (Join-Path $DataRoot 'quarterly_ticket.csv')
Assert-Equal -Name 'Ticket crédito 2024 T1' -Actual (($ticket | Where-Object period_quarter -eq '1').net_spend_per_active_card_usd) -Expected '3229.40'
Assert-Equal -Name 'Ticket crédito 2024 T2' -Actual (($ticket | Where-Object period_quarter -eq '2').net_spend_per_active_card_usd) -Expected '5019.38'

$cashback = Import-Csv -LiteralPath (Join-Path $DataRoot 'cashback.csv')
Assert-Equal -Name 'Transacciones elegibles' -Actual $cashback.eligible_transaction_count -Expected '28915'
Assert-Equal -Name 'Transacciones positivas elegibles' -Actual $cashback.positive_eligible_transaction_count -Expected '28885'
Assert-Equal -Name 'Transacciones negativas elegibles' -Actual $cashback.negative_eligible_transaction_count -Expected '30'
Assert-Equal -Name 'Gasto elegible' -Actual $cashback.net_eligible_spend_usd -Expected '7319379.70'
Assert-Equal -Name 'Tarjetas topadas' -Actual $cashback.capped_card_count -Expected '2676'
Assert-Equal -Name 'Costo cashback' -Actual $cashback.total_cashback_usd -Expected '178471.62'

$sensitivity = Import-Csv -LiteralPath (Join-Path $DataRoot 'cashback_sensitivity.csv')
$isXb = Import-Csv -LiteralPath (Join-Path $DataRoot 'cashback_is_xb.csv')
Assert-Equal -Name 'Escenario sin devoluciones' -Actual $sensitivity.positive_only_cashback_usd -Expected '178608.88'
Assert-Equal -Name 'Escenario is_xb incorrecto' -Actual $isXb.incorrect_is_xb_cashback_usd -Expected '135160.88'

$quality = Import-Csv -LiteralPath (Join-Path $DataRoot 'quality.csv')
Assert-Equal -Name 'MCG sin clasificar' -Actual $quality.unclassified_mcg_transactions -Expected '12000'
Assert-Equal -Name 'Discrepancias is_xb' -Actual $quality.is_xb_country_discrepancies -Expected '1440451'
Assert-Equal -Name 'Controles de calidad fallidos' -Actual $quality.failed_data_quality_checks -Expected '0'
Assert-Equal -Name 'Controles KPI fallidos' -Actual $quality.failed_kpi_checks -Expected '0'
Assert-Equal -Name 'Controles cashback fallidos' -Actual $quality.failed_cashback_checks -Expected '0'

$publicPaths = @(
    'powerbi/Masterplop_Executive.pbix',
    'powerbi/Masterplop_Executive.pdf',
    'powerbi/source/Masterplop_Executive.pbip',
    'docs/assets/powerbi/01-resumen-ejecutivo.png'
)
$publicPaths | ForEach-Object { Assert-GitNotIgnored -RepositoryPath $_ }

$localOnlyPaths = @(
    'powerbi/Masterplop_Executive.pbip',
    'powerbi/Masterplop_Executive.Report/definition/report.json',
    'powerbi/Masterplop_Executive.SemanticModel/.pbi/cache.abf',
    'powerbi/data/executive.csv',
    'powerbi/source/Masterplop_Executive.SemanticModel/.pbi/cache.abf'
)
$localOnlyPaths | ForEach-Object { Assert-GitIgnored -RepositoryPath $_ }

[pscustomobject]@{
    Status = 'OK'
    JsonFilesParsed = $jsonFiles.Count
    Pages = $pageCount
    Visuals = $visualCount
    Tables = $tableCount
    Measures = $measureCount
    EmbeddedPortableQueries = $embeddedQueryCount
    AggregateCsvFiles = $csvCount
    PbixSizeBytes = (Get-Item -LiteralPath $pbixPath).Length
    PdfSizeBytes = (Get-Item -LiteralPath (Join-Path $PowerBiRoot 'Masterplop_Executive.pdf')).Length
    PrivacyScan = 'Sin card_id, fuente cruda, rutas personales ni credenciales'
    GitPublication = 'Artefactos públicos visibles; cachés y legado protegidos'
} | Format-List
