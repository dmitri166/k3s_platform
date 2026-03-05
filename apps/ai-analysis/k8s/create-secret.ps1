# create-secret.ps1
# Creates the Groq API key as a Kubernetes Secret in the ai-analysis namespace.
# Run ONCE before ArgoCD deploys the CronJob. This file is NOT committed to Git.
#
# Usage:
#   .\create-secret.ps1
#
# Or override the key:
#   $env:GROQ_API_KEY = "your-key-here"; .\create-secret.ps1

$ErrorActionPreference = "Stop"

$Namespace  = "ai-analysis"
$SecretName = "groq-api-key"

if ($env:GROQ_API_KEY) {
    $ApiKey = $env:GROQ_API_KEY
} else {
    Write-Host ""
    $apiKeySecure = Read-Host -Prompt "Enter your Groq API Key (input will be hidden)" -AsSecureString
    $ApiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKeySecure))
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Host "Error: API key cannot be empty. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "Creating namespace '$Namespace' if it does not exist ..." -ForegroundColor Cyan
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

Write-Host "Creating/updating Secret '$SecretName' in namespace '$Namespace' ..." -ForegroundColor Cyan
kubectl create secret generic $SecretName `
    --from-literal=GROQ_API_KEY="$ApiKey" `
    --namespace=$Namespace `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host ""
Write-Host "✅  Secret '$SecretName' is ready in namespace '$Namespace'." -ForegroundColor Green
Write-Host "    Verify with: kubectl get secret $SecretName -n $Namespace" -ForegroundColor Gray
