$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $repoRoot "deployment\docker-compose.prod.yml"
$envFile = Join-Path $repoRoot "deployment\.env.prod"
$backupDir = Join-Path $repoRoot "data\backups"
$composeArgs = @("compose", "-f", $composeFile, "--env-file", $envFile)

function Get-EnvValue([string]$Name, [string]$Default) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -Last 1
    if (-not $line) { return $Default }
    return ($line -split "=", 2)[1].Trim().Trim('"')
}

if (-not (Test-Path $envFile)) { throw "deployment\.env.prod is missing." }
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$dbName = Get-EnvValue "POSTGRES_DB" "stock_tracker"
$dbUser = Get-EnvValue "POSTGRES_USER" "stock_tracker"
$retentionDays = [int](Get-EnvValue "BACKUP_RETENTION_DAYS" "120")
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dbTempSql = "/tmp/stock_tracker-$stamp.sql"
$dbTempGz = "$dbTempSql.gz"
$mediaTemp = "/tmp/stock_tracker-media-$stamp.tar.gz"
$dbOutput = Join-Path $backupDir "stock_tracker-$stamp.sql.gz"
$mediaOutput = Join-Path $backupDir "stock_tracker-media-$stamp.tar.gz"

Write-Host "Creating database backup: $dbOutput"
& docker @composeArgs exec -T postgres pg_dump --clean --if-exists -U $dbUser $dbName --file=$dbTempSql
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed." }
& docker @composeArgs exec -T postgres gzip -f $dbTempSql
if ($LASTEXITCODE -ne 0) { throw "Database compression failed." }
& docker @composeArgs exec -T postgres gzip -t $dbTempGz
if ($LASTEXITCODE -ne 0) { throw "Database archive validation failed." }
& docker @composeArgs cp "postgres:$dbTempGz" $dbOutput
if ($LASTEXITCODE -ne 0) { throw "Database archive copy failed." }
& docker @composeArgs exec -T postgres rm -f $dbTempGz

Write-Host "Creating uploaded-file backup: $mediaOutput"
& docker @composeArgs exec -T backend tar -czf $mediaTemp -C /app/media .
if ($LASTEXITCODE -ne 0) { throw "Uploaded-file archive failed." }
& docker @composeArgs exec -T backend tar -tzf $mediaTemp
if ($LASTEXITCODE -ne 0) { throw "Uploaded-file archive validation failed." }
& docker @composeArgs cp "backend:$mediaTemp" $mediaOutput
if ($LASTEXITCODE -ne 0) { throw "Uploaded-file archive copy failed." }
& docker @composeArgs exec -T backend rm -f $mediaTemp

$cutoff = (Get-Date).AddDays(-$retentionDays)
Get-ChildItem $backupDir -File | Where-Object {
    ($_.Name -like "stock_tracker-*.sql.gz" -or $_.Name -like "stock_tracker-media-*.tar.gz") -and
    $_.LastWriteTime -lt $cutoff
} | Remove-Item -Force

Write-Host "Backup complete. Retention: $retentionDays days."
Write-Host $dbOutput
Write-Host $mediaOutput
