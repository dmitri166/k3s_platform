# Talos Platform Cluster Creation Script
# This script creates the complete Talos on-premises platform

param(
    [switch]$SkipVMs,
    [switch]$SkipTalos,
    [switch]$SkipArgoCD,
    [switch]$SkipServices,
    [switch]$Force
)

Write-Host "🚀 Creating Talos Platform..." -ForegroundColor Cyan

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
    
    $requiredCommands = @("multipass", "terraform", "helm", "talosctl", "kubectl", "python")
    $missingCommands = @()
    
    foreach ($cmd in $requiredCommands) {
        if (-not (Test-Command $cmd)) {
            $missingCommands += $cmd
        }
    }
    
    if ($missingCommands.Count -gt 0) {
        Write-Host "❌ Missing required tools: $($missingCommands -join ', ')" -ForegroundColor Red
        Write-Host "Please install missing tools and try again." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ All prerequisites met" -ForegroundColor Green
}

# Function to run Terraform with error handling
function Invoke-Terraform {
    param(
        [string]$Command,
        [string]$Target = "",
        [switch]$AutoApprove
    )
    
    $terraformCmd = "terraform $Command"
    
    if ($Target) {
        $terraformCmd += " -target=$Target"
    }
    
    if ($AutoApprove) {
        $terraformCmd += " -auto-approve"
    }
    
    Write-Host "🔧 Running: $terraformCmd" -ForegroundColor Yellow
    
    try {
        $result = Invoke-Expression $terraformCmd
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform command failed with exit code $LASTEXITCODE"
        }
        Write-Host "✅ Terraform command completed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Terraform command failed: $($_.Exception.Message)" -ForegroundColor Red
        if (-not $Force) {
            Write-Host "Use -Force to continue despite errors" -ForegroundColor Yellow
            return $false
        }
        Write-Host "⚠️ Continuing despite error due to -Force flag" -ForegroundColor Yellow
        return $true
    }
}

# Function to wait for cluster readiness
function Wait-ClusterReady {
    param([int]$Timeout = 300)
    
    Write-Host "⏳ Waiting for cluster to be ready..." -ForegroundColor Yellow
    
    $elapsed = 0
    $interval = 10
    
    while ($elapsed -lt $Timeout) {
        try {
            $nodes = kubectl get nodes --no-headers 2>$null
            if ($nodes -and $nodes.Count -ge 3) {
                $readyNodes = ($nodes | Where-Object { $_ -match "Ready" }).Count
                if ($readyNodes -ge 3) {
                    Write-Host "✅ Cluster is ready with $readyNodes nodes" -ForegroundColor Green
                    return $true
                }
            }
        }
        catch {
            # Continue waiting
        }
        
        Start-Sleep $interval
        $elapsed += $interval
        Write-Host "  Waiting... ($elapsed/$Timeout seconds)" -ForegroundColor Gray
    }
    
    Write-Host "❌ Cluster did not become ready within timeout" -ForegroundColor Red
    return $false
}

# Function to get service URLs
function Get-ServiceURLs {
    Write-Host "🌐 Getting service URLs..." -ForegroundColor Yellow
    
    try {
        $argocdIP = kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
        if ($argocdIP) {
            Write-Host "  ArgoCD: http://$argocdIP" -ForegroundColor White
        }
        
        $ingressIP = kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
        if ($ingressIP) {
            Write-Host "  Applications: http://$ingressIP" -ForegroundColor White
        }
        
        $grafanaIP = kubectl get svc grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
        if ($grafanaIP) {
            Write-Host "  Grafana: http://$grafanaIP" -ForegroundColor White
        }
        
        $vaultIP = kubectl get svc vault -n vault -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
        if ($vaultIP) {
            Write-Host "  Vault: http://$vaultIP" -ForegroundColor White
        }
    }
    catch {
        Write-Host "⚠️ Could not retrieve all service URLs" -ForegroundColor Yellow
    }
}

# Function to get ArgoCD credentials
function Get-ArgoCDCredentials {
    Write-Host "🔑 Getting ArgoCD credentials..." -ForegroundColor Yellow
    
    try {
        $password = terraform output -raw argocd_admin_password 2>$null
        if ($password) {
            Write-Host "  ArgoCD Admin Password: $password" -ForegroundColor White
            Write-Host "  Use 'argocd login --insecure --username admin --password $password http://$argocdIP'" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "⚠️ Could not retrieve ArgoCD credentials" -ForegroundColor Yellow
    }
}

# Main execution
try {
    # Check prerequisites
    Test-Prerequisites
    
    # Change to terraform directory
    Set-Location terraform
    
    # Initialize Terraform (if needed)
    if (-not (Test-Path ".terraform")) {
        Write-Host "🔧 Initializing Terraform..." -ForegroundColor Yellow
        if (-not (Invoke-Terraform -Command "init")) {
            exit 1
        }
    }
    
    # Step 1: Create VMs and infrastructure
    if (-not $SkipVMs) {
        Write-Host "📦 Creating Multipass VMs and infrastructure..." -ForegroundColor Yellow
        if (-not (Invoke-Terraform -Command "apply" -AutoApprove)) {
            exit 1
        }
    }
    
    # Step 2: Install Talos and bootstrap cluster (included in main apply)
    if (-not $SkipTalos) {
        Write-Host "🔧 Talos installation and cluster bootstrap included in infrastructure" -ForegroundColor Yellow
    }
    
    # Step 3: Install MetalLB
    if (-not $SkipArgoCD) {
        Write-Host "🌐 MetalLB installation included in infrastructure" -ForegroundColor Yellow
    }
    
    # Step 4: Install ArgoCD
    if (-not $SkipArgoCD) {
        Write-Host "🚀 ArgoCD installation included in infrastructure" -ForegroundColor Yellow
    }
    
    # Wait for cluster to be ready
    if (-not (Wait-ClusterReady)) {
        if (-not $Force) {
            exit 1
        }
    }
    
    # Step 5: Deploy applications via ArgoCD
    if (-not $SkipServices) {
        Write-Host "📦 Deploying applications via ArgoCD..." -ForegroundColor Yellow
        Write-Host "  Applications will be deployed automatically via ArgoCD GitOps" -ForegroundColor Gray
        Write-Host "  Check ArgoCD UI for deployment status" -ForegroundColor Gray
    }
    
    # Step 6: Verification
    Write-Host "🔍 Verifying deployment..." -ForegroundColor Yellow
    
    try {
        kubectl get nodes
        kubectl get pods -A
        Write-Host "✅ Platform deployed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Verification completed with warnings" -ForegroundColor Yellow
    }
    
    # Get access information
    Write-Host "`n📋 Access Information:" -ForegroundColor Cyan
    Get-ServiceURLs
    Get-ArgoCDCredentials
    
    Write-Host "`n🎉 Talos platform creation completed!" -ForegroundColor Green
    Write-Host "📖 Check README.md for more information" -ForegroundColor Cyan
    
}
catch {
    Write-Host "❌ Script failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "📖 Check the error message above and try again" -ForegroundColor Yellow
    exit 1
}
finally {
    # Return to original directory
    Set-Location ..
}
