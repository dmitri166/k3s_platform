# Final verification script for K3s platform optimization
Write-Host "Final verification of K3s platform optimization..." -ForegroundColor Green

# Step 1: Verify node configuration
Write-Host "Step 1: Verifying node configuration..." -ForegroundColor Yellow
kubectl get nodes -o wide

# Step 2: Verify taints
Write-Host "Step 2: Verifying taints..." -ForegroundColor Yellow
kubectl describe node cp1 | Select-String "Taints"
kubectl describe node cp2 | Select-String "Taints"

# Step 3: Verify resource allocation
Write-Host "Step 3: Verifying resource allocation..." -ForegroundColor Yellow
kubectl top nodes

# Step 4: Verify application distribution
Write-Host "Step 4: Verifying application distribution..." -ForegroundColor Yellow
kubectl get pods -A -o wide

# Step 5: Check AI Observability
Write-Host "Step 5: Checking AI Observability..." -ForegroundColor Yellow
kubectl get pods -n ai-observability -o wide

# Step 6: Check monitoring stack
Write-Host "Step 6: Checking monitoring stack..." -ForegroundColor Yellow
kubectl get pods -n monitoring -o wide

# Step 7: Verify taint effect
Write-Host "Step 7: Verifying taint effect..." -ForegroundColor Yellow
kubectl get pods --all-namespaces -o wide | Select-String "cp1"
kubectl get pods --all-namespaces -o wide | Select-String "cp2"

# Step 8: Check resource usage
Write-Host "Step 8: Checking resource usage..." -ForegroundColor Yellow
kubectl top nodes

# Step 9: Final verification
Write-Host "Step 9: Final verification..." -ForegroundColor Green
Write-Host "Control planes should have minimal workloads"
Write-Host "Workers should have most applications"
Write-Host "Total RAM should be ~11GB"
Write-Host "Total CPUs should be ~8"
Write-Host "Taints applied to control planes"
Write-Host "Applications distributed to workers"

# Step 10: Performance check
Write-Host "Step 10: Performance check..." -ForegroundColor Yellow
Write-Host "If everything looks good, optimization is complete!"