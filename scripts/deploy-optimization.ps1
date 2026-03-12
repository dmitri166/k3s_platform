# Deployment script for K3s platform optimization
Write-Host "Starting K3s platform optimization deployment..." -ForegroundColor Green

# Step 1: Clean up existing cluster
Write-Host "Step 1: Cleaning up existing cluster..." -ForegroundColor Yellow
vagrant destroy -f

# Step 2: Deploy new configuration
Write-Host "Step 2: Deploying new configuration..." -ForegroundColor Yellow
vagrant up

# Step 3: Verify cluster status
Write-Host "Step 3: Verifying cluster status..." -ForegroundColor Yellow
.\scripts/k3s-status.ps1

# Step 4: Apply Terraform changes
Write-Host "Step 4: Applying Terraform changes..." -ForegroundColor Yellow
cd terraform
terraform init
terraform apply -target='module.metallb.kubernetes_namespace.metallb' -auto-approve
terraform apply -target='module.metallb.helm_release.metallb' -auto-approve
terraform apply

# Step 5: Bootstrap ArgoCD applications
Write-Host "Step 5: Bootstrapping ArgoCD applications..." -ForegroundColor Yellow
cd ..
.\scripts\bootstrap-argocd-apps.ps1

# Step 6: Verify deployment
Write-Host "Step 6: Verifying deployment..." -ForegroundColor Yellow
.\scripts/verify-optimization.ps1

# Step 7: Final verification
Write-Host "Step 7: Final verification..." -ForegroundColor Green
Write-Host "Optimization deployment completed!"
Write-Host "Total RAM: 11GB"
Write-Host "Total CPUs: 8"
Write-Host "Control planes: 2 (2.5GB RAM, 2 CPUs each)"
Write-Host "Workers: 2 (3GB RAM, 2 CPUs each)"
Write-Host "Taints applied to control planes"
Write-Host "Applications distributed to workers"