$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name PTS-Automation `
    --add-data "ui\assets;ui\assets" `
    run.py

if (Test-Path "dist\logs") {
    Remove-Item "dist\logs" -Recurse -Force
}
New-Item -ItemType Directory -Force -Path "dist\input", "dist\output" | Out-Null
Copy-Item "input\*" "dist\input" -Force

Write-Host "Built dist\PTS-Automation.exe"
Write-Host "Place any required Excel/Minitab files in dist\input, then run the executable."