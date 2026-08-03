<#
  call_example.ps1 -- call the running masking API (POST /v1/mask) without
  pasting a long curl line.

  Usage (from the project root or anywhere):
      powershell -ExecutionPolicy Bypass -File .\backend\masking_service\call_example.ps1
      # override any of these:
      ... -Text "patient Jan Peeters, IBAN BE68539007547034" -Version medroberta-nl-1

  The server must already be running:
      $env:MASKING_API_TOKEN="change-me-internal-token"
      $env:MASKING_MODEL_VERSION="medroberta-nl-1"
      uvicorn masking_service.app:app --host 0.0.0.0 --port 9000
#>

param(
    [string]$Text    = "patient Dirk Willaert, tel 0475123456",
    [string]$Version = $(if ($env:MASKING_MODEL_VERSION) { $env:MASKING_MODEL_VERSION } else { "medroberta-nl-1" }),
    [string]$Token   = $(if ($env:MASKING_API_TOKEN) { $env:MASKING_API_TOKEN } else { "change-me-internal-token" }),
    [int]$Port       = 9000,
    [ValidateSet("text/plain", "text/csv", "application/json")]
    [string]$MediaType = "text/plain"
)

$headers = @{
    "Authorization"   = "Bearer $Token"
    "X-Request-ID"    = [guid]::NewGuid().ToString()
    "X-Source-Key"    = "example/key"
    "X-Source-ETag"   = "example-etag"
    "X-Model-Version" = $Version
}

$uri = "http://localhost:$Port/v1/mask"
Write-Host "POST $uri  (version=$Version, media=$MediaType)" -ForegroundColor Cyan

try {
    $resp = Invoke-WebRequest -Uri $uri -Method Post -Headers $headers `
        -ContentType $MediaType -Body $Text -TimeoutSec 120 -UseBasicParsing
} catch {
    $r = $_.Exception.Response
    if ($r) {
        $code = [int]$r.StatusCode
        Write-Host "HTTP $code" -ForegroundColor Red
        $reader = New-Object System.IO.StreamReader($r.GetResponseStream())
        Write-Host $reader.ReadToEnd()
    } else {
        Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Is the server running on port $Port? Start it with uvicorn (see header of this script)." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""
Write-Host "HTTP $([int]$resp.StatusCode)" -ForegroundColor Green
Write-Host ("model     : " + $resp.Headers["X-Masking-Model-Version"])
Write-Host ("entities  : " + $resp.Headers["X-Masking-Entity-Count"])
Write-Host ("sha256    : " + $resp.Headers["X-Masked-Content-SHA256"])
Write-Host "--- masked output ---" -ForegroundColor Cyan
Write-Host $resp.Content
