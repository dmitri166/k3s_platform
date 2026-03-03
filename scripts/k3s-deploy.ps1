# K3s Deployment Script
Write-Host "Deploying K3s HA Cluster..." -ForegroundColor Cyan

# Validate host-only networking before provisioning VMs.
Write-Host "Running host network preflight..." -ForegroundColor Yellow
.\scripts\preflight-network.ps1

# Clean up any existing VMs
Write-Host "Cleaning existing VMs..." -ForegroundColor Yellow
vagrant destroy -f

# Start deployment
Write-Host "Starting K3s cluster deployment..." -ForegroundColor Green
vagrant up

# Wait for deployment to complete
Write-Host "Waiting for cluster initialization..." -ForegroundColor Yellow
Start-Sleep 180

# Verify cluster status
Write-Host "Verifying cluster status..." -ForegroundColor Green
.\scripts\k3s-status.ps1
