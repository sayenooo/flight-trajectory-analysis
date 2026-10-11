param(
    [string]$SourcePath = (Join-Path $HOME 'OpenSky_FRA_Approach_20250601')
)

$ErrorActionPreference = 'Stop'
$CaseRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Data = Join-Path $CaseRoot 'data\opensky'
$Figures = Join-Path $CaseRoot 'figures'
New-Item -ItemType Directory -Path $Data -Force | Out-Null

if (-not (Test-Path -LiteralPath $SourcePath -PathType Container)) {
    throw "OpenSky local folder not found: $SourcePath"
}

$files = @(Get-ChildItem -LiteralPath $SourcePath -File -Filter 'flight_*.csv')
foreach ($file in $files) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $Data $file.Name) -Force
}

$names = @(
    '01_all_EDDF_arrivals_0840_0940.csv',
    '02_diagnostic_approaches.csv',
    '7_flights_summary.csv'
)
foreach ($name in $names) {
    $source = Join-Path $SourcePath $name
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $Data $name) -Force
    }
}

$original = Join-Path $SourcePath '7_flights_vs_DLH5H.png'
if (Test-Path -LiteralPath $original -PathType Leaf) {
    Copy-Item -LiteralPath $original -Destination (Join-Path $Figures '7_flights_vs_DLH5H.png') -Force
    Write-Host 'Original 7-flight PNG imported.' -ForegroundColor Green
}

Write-Host "Imported $($files.Count) flight CSV files into: $Data" -ForegroundColor Green
Write-Host 'Next: python .\scripts\plot_seven_arrivals.py'
