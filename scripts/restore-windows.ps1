param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseFile,
    [string]$MediaFile = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $repoRoot "deployment\docker-compose.prod.yml"
$envFile = Join-Path $repoRoot "deployment\.env.prod"
$composeArgs = @("compose", "-f", $composeFile, "--env-file", $envFile)

function Get-EnvValue([string]$Name, [string]$Default) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -Last 1
    if (-not $line) { return $Default }
    return ($line -split "=", 2)[1].Trim().Trim('"')
}

if (-not (Test-Path $envFile)) { throw "deployment\.env.prod is missing." }
$databasePath = (Resolve-Path $DatabaseFile).Path
$mediaPath = if ($MediaFile) { (Resolve-Path $MediaFile).Path } else { "" }
$dbName = Get-EnvValue "POSTGRES_DB" "stock_tracker"
$dbUser = Get-EnvValue "POSTGRES_USER" "stock_tracker"

Write-Host "This will OVERWRITE the current Stock Tracker database."
Write-Host "Database backup: $databasePath"
if ($mediaPath) { Write-Host "Media backup: $mediaPath" }
$confirmation = Read-Host "Type YES to continue"
if ($confirmation -cne "YES") {
    Write-Host "Restore cancelled."
    exit 1
}

& docker @composeArgs up -d postgres redis backend
if ($LASTEXITCODE -ne 0) { throw "Could not start restore services." }

$dbTemp = "/tmp/stock_tracker-restore.sql.gz"
& docker @composeArgs cp $databasePath "postgres:$dbTemp"
if ($LASTEXITCODE -ne 0) { throw "Could not copy database backup into PostgreSQL." }
& docker @composeArgs exec -T postgres gzip -t $dbTemp
if ($LASTEXITCODE -ne 0) { throw "Database backup is invalid." }

& docker @composeArgs stop backend worker
if ($LASTEXITCODE -ne 0) { throw "Could not stop application services for restore." }
& docker @composeArgs exec -T postgres sh -c "gunzip -c '$dbTemp' | psql -v ON_ERROR_STOP=1 -U '$dbUser' '$dbName'"
if ($LASTEXITCODE -ne 0) { throw "Database restore failed." }
& docker @composeArgs exec -T postgres rm -f $dbTemp
& docker @composeArgs start backend worker
if ($LASTEXITCODE -ne 0) { throw "Could not restart application services." }

if ($mediaPath) {
    $mediaTemp = "/tmp/stock_tracker-media-restore.tar.gz"
    & docker @composeArgs cp $mediaPath "backend:$mediaTemp"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy uploaded-file backup." }
    & docker @composeArgs exec -T backend tar -tzf $mediaTemp
    if ($LASTEXITCODE -ne 0) { throw "Uploaded-file backup is invalid." }
    & docker @composeArgs exec -T backend tar -xzf $mediaTemp -C /app/media
    if ($LASTEXITCODE -ne 0) { throw "Uploaded-file restore failed." }
    & docker @composeArgs exec -T backend rm -f $mediaTemp
}

Write-Host "Restore complete. Open http://localhost:8080 and verify the data."
