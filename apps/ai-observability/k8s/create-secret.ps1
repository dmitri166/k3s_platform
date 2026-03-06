# create-secret.ps1
# Creates the API keys as Kubernetes Secrets in the ai-observability namespace.
# Run ONCE before ArgoCD deploys the Deployment. This file is NOT committed to Git.
#
# Usage:
#   .\create-secret.ps1
#
# Or override the keys:
#   $env:GROQ_API_KEY = "your-key-here"; $env:SLACK_APP_TOKEN = "your-token"; .\create-secret.ps1

$ErrorActionPreference = "Stop"

$Namespace  = "ai-observability"
$SecretName = "ai-observability-secrets"

$keys = @("GROQ_API_KEY", "SLACK_APP_TOKEN", "SLACK_BOT_TOKEN", "GRAFANA_API_KEY")

$secrets = @()

foreach ($key in $keys) {
    $value = $null
    switch ($key) {
        "GROQ_API_KEY" { if ($env:GROQ_API_KEY) { $value = $env:GROQ_API_KEY } }
        "SLACK_APP_TOKEN" { if ($env:SLACK_APP_TOKEN) { $value = $env:SLACK_APP_TOKEN } }
        "SLACK_BOT_TOKEN" { if ($env:SLACK_BOT_TOKEN) { $value = $env:SLACK_BOT_TOKEN } }
        "GRAFANA_API_KEY" { if ($env:GRAFANA_API_KEY) { $value = $env:GRAFANA_API_KEY } }
    }
    
    if (-not $value) {
        Write-Host ""
        $secureValue = Read-Host -Prompt "Enter your $key (input will be hidden)" -AsSecureString
        $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue))
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "Error: $key cannot be empty. Aborting." -ForegroundColor Red
        exit 1
    }

    $secrets += "--from-literal=$key=$value"
}

Write-Host "Creating namespace '$Namespace' if it does not exist ..." -ForegroundColor Cyan
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

Write-Host "Creating/updating Secret '$SecretName' in namespace '$Namespace' ..." -ForegroundColor Cyan
$command = "kubectl create secret generic $SecretName " + ($secrets -join " ") + " --namespace=$Namespace --dry-run=client -o yaml | kubectl apply -f -"
Invoke-Expression $command

Write-Host ""
Write-Host "✅  Secret '$SecretName' is ready in namespace '$Namespace'." -ForegroundColor Green
Write-Host "    Verify with: kubectl get secret $SecretName -n $Namespace" -ForegroundColor Gray
