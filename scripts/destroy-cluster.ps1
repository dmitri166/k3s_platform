# Talos Platform Cluster Destruction Script
# This script destroys the complete Talos on-premises platform

param(
    [switch]$Force,
    [switch]$SkipBackup
)

Write-Host "🔥 Destroying Talos Platform..." -ForegroundColor Red

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

# Function to backup important data
function Backup-Data {
    Write-Host "💾 Backing up important data..." -ForegroundColor Yellow
    
    $backupDir = "backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup Terraform state
    if (Test-Path "terraform\terraform.tfstate") {
        Copy-Item "terraform\terraform.tfstate" "$backupDir\terraform.tfstate" -Force
        Write-Host "  ✅ Terraform state backed up" -ForegroundColor Green
    }
    
    # Backup kubeconfig
    if (Test-Path "kubeconfig") {
        Copy-Item "kubeconfig" "$backupDir\kubeconfig" -Force
        Write-Host "  ✅ kubeconfig backed up" -ForegroundColor Green
    }
    
    # Backup talosconfig
    if (Test-Path "talosconfig") {
        Copy-Item "talosconfig" "$backupDir\talosconfig" -Force
        Write-Host "  ✅ talosconfig backed up" -ForegroundColor Green
    }
    
    # Export ArgoCD applications
    try {
        if (Test-Command "kubectl") {
            kubectl get applications -n argocd -o yaml > "$backupDir\argocd-applications.yaml" 2>$null
            Write-Host "  ✅ ArgoCD applications backed up" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  ⚠️ Could not backup ArgoCD applications" -ForegroundColor Yellow
    }
    
    Write-Host "💾 Backup completed: $backupDir" -ForegroundColor Green
}

# Function to confirm destruction
function Confirm-Destruction {
    if (-not $Force) {
        Write-Host "⚠️  WARNING: This will destroy the entire Talos platform!" -ForegroundColor Red
        Write-Host "   All VMs, data, and configurations will be permanently lost." -ForegroundColor Red
        Write-Host ""
        $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
        
        if ($confirmation -ne "yes") {
            Write-Host "❌ Destruction cancelled" -ForegroundColor Yellow
            exit 0
        }
    }
}

# Main execution
try {
    # Confirm destruction
    Confirm-Destruction
    
    # Check prerequisites
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
    $requiredCommands = @("multipass", "terraform", "kubectl")
    $missingCommands = @()
    
    foreach ($cmd in $requiredCommands) {
        if (-not (Test-Command $cmd)) {
            $missingCommands += $cmd
        }
    }
    
    if ($missingCommands.Count -gt 0) {
        Write-Host "❌ Missing required tools: $($missingCommands -join ', ')" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ All prerequisites met" -ForegroundColor Green
    
    # Backup data
    if (-not $SkipBackup) {
        Backup-Data
    }
    
    # Change to terraform directory
    Set-Location terraform
    
    # Check if Terraform is initialized
    if (-not (Test-Path ".terraform")) {
        Write-Host "🔧 Initializing Terraform..." -ForegroundColor Yellow
        if (-not (Invoke-Terraform -Command "init")) {
            exit 1
        }
    }
    
    # Step 1: Destroy ArgoCD applications first
    Write-Host "🔥 Destroying ArgoCD applications..." -ForegroundColor Yellow
    try {
        if (Test-Command "kubectl") {
            kubectl delete applications --all -n argocd --ignore-not-found=true 2>$null
            Write-Host "✅ ArgoCD applications deleted" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "⚠️ Could not delete ArgoCD applications" -ForegroundColor Yellow
    }
    
    # Step 2: Destroy all infrastructure
    Write-Host "🔥 Destroying all infrastructure..." -ForegroundColor Yellow
    if (-not (Invoke-Terraform -Command "destroy" -AutoApprove)) {
        exit 1
    }
    
    # Step 3: Clean up local files
    Write-Host "🧹 Cleaning up local files..." -ForegroundColor Yellow
    
    # Remove kubeconfig
    if (Test-Path "..\kubeconfig") {
        Remove-Item "..\kubeconfig" -Force
        Write-Host "  ✅ kubeconfig removed" -ForegroundColor Green
    }
    
    # Remove talosconfig
    if (Test-Path "..\talosconfig") {
        Remove-Item "..\talosconfig" -Force
        Write-Host "  ✅ talosconfig removed" -ForegroundColor Green
    }
    
    # Clean up Multipass VMs (if any remain)
    try {
        $vms = multipass list --format csv | ConvertFrom-Csv
        foreach ($vm in $vms) {
            if ($vm.Name -match "^(cp|worker)\d+$") {
                multipass delete $vm.Name --purge 2>$null
                Write-Host "  ✅ VM $($vm.Name) removed" -ForegroundColor Green
            }
        }
    }
    catch {
        Write-Host "  ⚠️ Could not clean up Multipass VMs" -ForegroundColor Yellow
    }
    
    Write-Host "`n🔥 Talos platform destruction completed!" -ForegroundColor Red
    Write-Host "💾 Check backup directory for saved data" -ForegroundColor Cyan
    
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
