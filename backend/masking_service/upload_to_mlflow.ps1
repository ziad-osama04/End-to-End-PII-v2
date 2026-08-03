<#
  upload_to_mlflow.ps1 -- one-command upload of the PII masking model to the
  team MLflow server (https://mlflow.me), then log evaluation metrics.

  Usage (from anywhere):
      powershell -ExecutionPolicy Bypass -File .\masking_service\upload_to_mlflow.ps1

  Credentials:
      * Uses $env:MLFLOW_TRACKING_USERNAME / $env:MLFLOW_TRACKING_PASSWORD if set.
      * Otherwise prompts you securely (password is masked, never written to disk).
      These are the SAME login you use in the mlflow.me web UI.

  Nothing secret is stored by this script.
#>

param(
    [string]$TrackingUri = "https://mlflow.me",
    # "regex-poc-1" (fast, dependency-free) or "medroberta-nl-1" (fine-tuned model)
    [string]$ModelVersion = "medroberta-nl-1"
)

$ErrorActionPreference = "Stop"

# Run from the backend/ dir (parent of this script's folder) so that
# `python -m masking_service.*` resolves.
$backendDir = Split-Path -Parent $PSScriptRoot
Set-Location $backendDir
Write-Host "Working dir : $backendDir"
Write-Host "Tracking URI: $TrackingUri"

# --- credentials ---------------------------------------------------------- #
$env:MLFLOW_TRACKING_URI = $TrackingUri
$env:MASKING_MODEL_VERSION = $ModelVersion

if (-not $env:MLFLOW_TRACKING_USERNAME) {
    $env:MLFLOW_TRACKING_USERNAME = Read-Host "MLflow username (your mlflow.me login)"
}
if (-not $env:MLFLOW_TRACKING_PASSWORD) {
    $sec = Read-Host "MLflow password (input hidden)" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    $env:MLFLOW_TRACKING_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

# --- 1. auth check -------------------------------------------------------- #
Write-Host "`n[1/3] Checking authentication..." -ForegroundColor Cyan
$check = python -c "import mlflow; mlflow.set_tracking_uri('$TrackingUri'); print('OK auth; experiments:', [e.name for e in mlflow.search_experiments()][:8])"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Authentication failed. Check your username/password and try again." -ForegroundColor Red
    exit 1
}
Write-Host $check -ForegroundColor Green

# --- 2. log + register ---------------------------------------------------- #
Write-Host "`n[2/3] Logging + registering model ($ModelVersion)..." -ForegroundColor Cyan
if ($ModelVersion -eq "medroberta-nl-1") {
    # Uploads the fine-tuned MedRoBERTa weights (downloads from HF once, then
    # bundles them into the MLflow model). First run is large + slow.
    python -m masking_service.mlflow_medroberta
} else {
    python -m masking_service.log_model
}
if ($LASTEXITCODE -ne 0) { Write-Host "upload failed." -ForegroundColor Red; exit 1 }

# --- 3. evaluation metrics ------------------------------------------------ #
Write-Host "`n[3/3] Logging evaluation metrics..." -ForegroundColor Cyan
python -m masking_service.evaluate
if ($LASTEXITCODE -ne 0) { Write-Host "evaluate failed (model still uploaded)." -ForegroundColor Yellow }

Write-Host "`nDone. Open https://mlflow.me -> Experiments / Model registry -> 'pii-masking-service'." -ForegroundColor Green
