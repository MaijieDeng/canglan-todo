param([string]$Python = "")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$appName = [string]::Concat([char]0x82CD, [char]0x5C9A, [char]0x7B3A)
Set-Location -LiteralPath $projectRoot
if (-not $Python) {
    $localPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $localPython) { $Python = $localPython }
    else { $Python = 'python' }
}
$Python = (Get-Command $Python -ErrorAction Stop).Source
$runtimeDir = & $Python -c 'import sys; print(sys.base_prefix)'
$originalPath = $env:PATH
try {
    # Do not collect incompatible ICU or C++ DLLs from Conda/Poppler on PATH.
    $env:PATH = (Split-Path -Parent $Python), $runtimeDir, "$env:SystemRoot\System32", $env:SystemRoot -join ';'
    & $Python scripts/make_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name $appName --icon assets/canglan.ico `
        --exclude-module tkinter --exclude-module matplotlib --exclude-module scipy `
        --exclude-module pandas --exclude-module numpy --exclude-module IPython run.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
}
finally { $env:PATH = $originalPath }
Write-Host "Ready: dist\$appName.exe"
