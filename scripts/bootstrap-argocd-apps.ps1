$ErrorActionPreference = "Stop"

$kubeconfig = "$env:USERPROFILE\.kube\config-k3s"
$bootstrapManifest = Join-Path $PSScriptRoot "..\argocd\bootstrap\applicationset.yaml"

if (-not (Test-Path $bootstrapManifest)) {
    throw "Bootstrap manifest not found: $bootstrapManifest"
}

Write-Host "Bootstrapping ArgoCD applications from ApplicationSet..." -ForegroundColor Cyan
kubectl --kubeconfig $kubeconfig -n argocd apply -f $bootstrapManifest

Write-Host "Waiting for ApplicationSets to register..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host "`n=== ApplicationSets ===" -ForegroundColor Yellow
kubectl --kubeconfig $kubeconfig -n argocd get applicationsets

Write-Host "`n=== Applications ===" -ForegroundColor Yellow
kubectl --kubeconfig $kubeconfig -n argocd get applications

Write-Host "`nArgoCD bootstrap complete." -ForegroundColor Green
