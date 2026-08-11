$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $repoRoot "deployment\docker-compose.prod.yml"
$envFile = Join-Path $repoRoot "deployment\.env.prod"
$composeArgs = @("compose", "-f", $composeFile, "--env-file", $envFile)

if (-not (Test-Path $envFile)) {
    Write-Host "Generating a private local environment file..."
    $djangoSecret = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
    $databasePassword = [guid]::NewGuid().ToString("N")
    $environmentContent = @"
DJANGO_SECRET_KEY=$djangoSecret
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8080
DJANGO_SECURE_COOKIES=0
POSTGRES_DB=stock_tracker
POSTGRES_USER=stock_tracker
POSTGRES_PASSWORD=$databasePassword
HTTP_PORT=8080
BACKUP_INTERVAL_SECONDS=43200
BACKUP_RETENTION_DAYS=120
"@
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($envFile, $environmentContent + [Environment]::NewLine, $utf8NoBom)
    Write-Host "Created deployment\.env.prod with machine-specific random secrets."
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not ready. Start Docker Desktop and run this script again."
}

Write-Host "Building and starting a fresh local Stock Tracker stack..."
& docker @composeArgs up -d --build
if ($LASTEXITCODE -ne 0) { throw "Docker Compose startup failed." }

Write-Host "Waiting for the backend to finish migrations and become healthy..."
$backendReady = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    & docker @composeArgs exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/', timeout=3)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $backendReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $backendReady) { throw "Backend did not become healthy within two minutes." }

Write-Host "Checking that the Windows database has no existing users or business data..."
$freshCheckCode = "from apps.accounts.models import User; from apps.attachments.models import FileAttachment; from apps.inventory.models import StockLedgerEntry; from apps.masterdata.models import Customer, Supplier; from apps.products.models import Product; from apps.purchases.models import Purchase; from apps.sales.models import Sale; from apps.shipments.models import Shipment; print(sum(model.objects.count() for model in [User, Product, Supplier, Customer, Purchase, Shipment, Sale, StockLedgerEntry, FileAttachment]))"
$freshCheckOutput = & docker @composeArgs exec -T backend python manage.py shell -c $freshCheckCode
if ($LASTEXITCODE -ne 0) { throw "Fresh-database verification failed." }
$freshCountText = ($freshCheckOutput | Select-Object -Last 1).ToString().Trim()
$freshCount = 0
if (-not [int]::TryParse($freshCountText, [ref]$freshCount)) {
    throw "Could not interpret fresh-database verification result: $freshCountText"
}
if ($freshCount -ne 0) {
    throw "Setup stopped: the target database already contains $freshCount user/business record(s). No data was deleted. Use a truly fresh Windows installation or ask the technician to inspect the existing Docker volumes."
}

Write-Host "Loading required locations, currencies, GST rates, and categories only..."
& docker @composeArgs exec backend python manage.py seed
if ($LASTEXITCODE -ne 0) { throw "Master-data seed failed." }

Write-Host "Creating the Admin account. Follow the username/password prompts."
& docker @composeArgs exec backend python manage.py create_admin
if ($LASTEXITCODE -ne 0) { throw "Admin creation failed." }

$installerScript = Join-Path $PSScriptRoot "install-desktop-launcher-windows.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installerScript
if ($LASTEXITCODE -ne 0) { throw "Desktop shortcut installation failed." }

Write-Host "Creating the first post-setup database and uploaded-file backup pair..."
$backupScript = Join-Path $PSScriptRoot "backup-windows.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $backupScript
if ($LASTEXITCODE -ne 0) { throw "Initial backup failed." }

Write-Host ""
Write-Host "Fresh Windows setup complete. No demo or Mac testing data was imported."
Write-Host "Open Stock Tracker from the new Desktop shortcut."
