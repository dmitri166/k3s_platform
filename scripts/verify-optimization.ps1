# Verification script for K3s platform optimization
Write-Host "Verifying K3s platform optimization..." -ForegroundColor Yellow

# Verify node configuration
Write-Host "Verifying node configuration..." -ForegroundColor Yellow
kubectl get nodes -o wide

# Verify taints
Write-Host "Verifying taints..." -ForegroundColor Yellow
kubectl describe node cp1 | Select-String "Taints"
kubectl describe node cp2 | Select-String "Taints"

# Verify resource allocation
Write-Host "Verifying resource allocation..." -ForegroundColor Yellow
kubectl top nodes

# Verify application distribution
Write-Host "Verifying application distribution..." -ForegroundColor Yellow
kubectl get pods -A -o wide

# Check if AI Observability is running on workers
Write-Host "Checking AI Observability distribution..." -ForegroundColor Yellow
kubectl get pods -n ai-observability -o wide

# Check if monitoring stack is running on workers
Write-Host "Checking monitoring stack distribution..." -ForegroundColor Yellow
kubectl get pods -n monitoring -o wide

# Verify taint effect
Write-Host "Verifying taint effect..." -ForegroundColor Yellow
kubectl get pods --all-namespaces -o wide | Select-String "cp1"
kubectl get pods --all-namespaces -o wide | Select-String "cp2"

# Check resource usage
Write-Host "Checking resource usage..." -ForegroundColor Yellow
kubectl top nodes

# Final verification
Write-Host "Final verification..." -ForegroundColor Green
Write-Host "Control planes should have minimal workloads"
Write-Host "Workers should have most applications"
Write-Host "Total RAM should be ~11GB"
Write-Host "Total CPUs should be ~8"