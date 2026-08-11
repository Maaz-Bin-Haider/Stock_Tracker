$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$launcher = Join-Path $repoRoot "scripts\open-stock-tracker-windows.cmd"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "SwissTech Stock Tracker.lnk"

if (-not (Test-Path $launcher)) {
    throw "Windows launcher not found: $launcher"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Start and open SwissTech Stock Tracker"
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
Write-Host "The Admin can double-click it to start and open Stock Tracker."
