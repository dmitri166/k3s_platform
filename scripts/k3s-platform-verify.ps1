# K3s Platform Verification
$env:KUBECONFIG = "$env:USERPROFILE\.kube\config-k3s"

Write-Host "Verifying K3s platform..." -ForegroundColor Cyan

# Check cluster
Write-Host "`n=== Cluster Status ===" -ForegroundColor Yellow
kubectl get nodes -o wide
kubectl get pods -A

# Check namespaces
Write-Host "`n=== Namespaces ===" -ForegroundColor Yellow
kubectl get namespaces

# Check MetalLB
Write-Host "`n=== MetalLB ===" -ForegroundColor Yellow
kubectl get pods -n metallb-system
kubectl get svc -n metallb-system

# Check ArgoCD
Write-Host "`n=== ArgoCD ===" -ForegroundColor Yellow
kubectl get pods -n argocd
kubectl get svc -n argocd

# Check LoadBalancer IPs
Write-Host "`n=== LoadBalancer IPs ===" -ForegroundColor Yellow
kubectl get svc -A | grep LoadBalancer

Write-Host "✅ Platform verification complete" -ForegroundColor Green
