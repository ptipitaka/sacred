# Upload images to DigitalOcean Spaces
# Run this script ONCE to upload all scanned images to Spaces

# Configuration (set via environment variables or optional secrets file)
$DEFAULT_BUCKET = "sacred"
$DEFAULT_REGION = "sgp1"

$secretsFile = Join-Path $PSScriptRoot 'spaces-secrets.ps1'
if (Test-Path $secretsFile) {
    . $secretsFile
}

$SPACES_BUCKET = if (![string]::IsNullOrWhiteSpace($env:DO_SPACES_BUCKET)) { $env:DO_SPACES_BUCKET } else { $DEFAULT_BUCKET }
$SPACES_REGION = if (![string]::IsNullOrWhiteSpace($env:DO_SPACES_REGION)) { $env:DO_SPACES_REGION } else { $DEFAULT_REGION }

$ACCESS_KEY = $env:DO_SPACES_ACCESS_KEY
if ([string]::IsNullOrWhiteSpace($ACCESS_KEY)) {
    throw "DO_SPACES_ACCESS_KEY not set. Export it or create scripts/spaces-secrets.ps1 (ignored by git) that sets the variable."
}

$SECRET_KEY_PLAIN = $env:DO_SPACES_SECRET_KEY
if ([string]::IsNullOrWhiteSpace($SECRET_KEY_PLAIN)) {
    throw "DO_SPACES_SECRET_KEY not set. Export it or create scripts/spaces-secrets.ps1 (ignored by git) that sets the variable."
}


# Paths
$LOCAL_PATH = "c:\Dev\astro\tptk\public\tipitaka"
$REMOTE_PATH = "tipitaka"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "DigitalOcean Spaces Image Upload" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Local path: $LOCAL_PATH" -ForegroundColor Yellow
Write-Host "Remote path: s3://$SPACES_BUCKET/$REMOTE_PATH" -ForegroundColor Yellow
Write-Host ""

# Locate s3cmd (prefer virtual env, fallback to PATH)
function Get-S3CmdLauncher {
    if ($env:VIRTUAL_ENV) {
        $pythonExe = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
        $s3cmdScript = Join-Path $env:VIRTUAL_ENV 'Scripts\s3cmd'
        if ((Test-Path $pythonExe) -and (Test-Path $s3cmdScript)) {
            return @{ Mode = 'python'; Python = $pythonExe; Script = $s3cmdScript }
        }
    }

    $s3cmdCommand = Get-Command s3cmd -ErrorAction SilentlyContinue
    if ($s3cmdCommand) {
        return @{ Mode = 'direct'; Executable = $s3cmdCommand.Path }
    }

    return $null
}

$s3cmdLauncher = Get-S3CmdLauncher
if (-not $s3cmdLauncher) {
    Write-Host "❌ s3cmd not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install s3cmd first:" -ForegroundColor Yellow
    Write-Host "  1. Install Python if not already installed" -ForegroundColor White
    Write-Host "  2. Run: pip install s3cmd" -ForegroundColor White
    Write-Host ""
    exit 1
}

function Invoke-S3Cmd {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    if ($s3cmdLauncher.Mode -eq 'python') {
        & $s3cmdLauncher.Python $s3cmdLauncher.Script @Arguments
    }
    else {
        & $s3cmdLauncher.Executable @Arguments
    }
}

# Configure s3cmd
Write-Host "Configuring s3cmd..." -ForegroundColor Green
$s3cfg = @"
[default]
access_key = $ACCESS_KEY
secret_key = $SECRET_KEY_PLAIN
host_base = $SPACES_REGION.digitaloceanspaces.com
host_bucket = %(bucket)s.$SPACES_REGION.digitaloceanspaces.com
use_https = True
"@

$configFile = Join-Path $HOME '.s3cfg'
$s3cfg | Out-File -FilePath $configFile -Encoding UTF8

if ($env:APPDATA) {
    $configIni = Join-Path $env:APPDATA 's3cmd.ini'
    $s3cfg | Out-File -FilePath $configIni -Encoding UTF8
}
Write-Host "✓ s3cmd configured" -ForegroundColor Green
Write-Host ""

# Count files to upload
Write-Host "Counting files to upload..." -ForegroundColor Yellow
$fileCount = (Get-ChildItem -Path $LOCAL_PATH -Recurse -File).Count
$totalSize = (Get-ChildItem -Path $LOCAL_PATH -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host "Files to upload: $fileCount" -ForegroundColor Cyan
Write-Host "Total size: $([math]::Round($totalSize, 2)) GB" -ForegroundColor Cyan
Write-Host ""

# Confirm upload
$confirm = Read-Host "Continue with upload? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Upload cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting upload... This will take a while!" -ForegroundColor Green
Write-Host "You can close this window - the upload will continue in background." -ForegroundColor Yellow
Write-Host ""

# Upload to Spaces
$startTime = Get-Date
Invoke-S3Cmd -- `
    --config $configFile `
    sync --acl-public --no-mime-magic --progress `
    --add-header="Cache-Control: public, max-age=31536000, immutable" `
    "$LOCAL_PATH/" "s3://$SPACES_BUCKET/$REMOTE_PATH/"

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✓ Upload complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "Duration: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify files at: https://cloud.digitalocean.com/spaces" -ForegroundColor White
Write-Host "2. Enable CDN for your Space" -ForegroundColor White
Write-Host "3. Update your Astro site to use CDN URLs" -ForegroundColor White
Write-Host "4. Add GitHub Secrets for automated deployment" -ForegroundColor White
Write-Host ""
Write-Host "CDN URL will be:" -ForegroundColor Cyan
Write-Host "https://$SPACES_BUCKET.$SPACES_REGION.cdn.digitaloceanspaces.com/$REMOTE_PATH/" -ForegroundColor Green
