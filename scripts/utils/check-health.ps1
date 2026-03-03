# K3s Platform Health Check Script
# This script checks the health of all platform components

param(
    [switch]$Verbose,
    [switch]$Wait
)

Write-Host "Checking K3s Platform Health..." -ForegroundColor Cyan

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

# Function to check component health
function Test-ComponentHealth {
    param(
        [string]$Component,
        [string]$Namespace,
        [string]$Selector,
        [int]$ExpectedReplicas = 1
    )
    
    Write-Host "🔍 Checking $Component..." -ForegroundColor Yellow
    
    try {
        $pods = kubectl get pods -n $Namespace --selector=$Selector --no-headers 2>$null
        if ($pods) {
            $readyPods = ($pods | Where-Object { $_ -match "Running|Ready" }).Count
            $totalPods = $pods.Count
            
            if ($Verbose) {
                Write-Host "  Pods: $readyPods/$totalPods ready" -ForegroundColor Gray
                foreach ($pod in $pods) {
                    Write-Host "    $pod" -ForegroundColor Gray
                }
            }
            
            if ($readyPods -ge $ExpectedReplicas) {
                Write-Host "  ✅ $Component is healthy" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ⚠️  $Component has $readyPods/$ExpectedReplicas ready pods" -ForegroundColor Yellow
                return $false
            }
        } else {
            Write-Host "  ❌ $Component not found" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ❌ Error checking $Component: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to check service health
function Test-ServiceHealth {
    param(
        [string]$Service,
        [string]$Namespace,
        [string]$ExpectedType = "LoadBalancer"
    )
    
    Write-Host "🔍 Checking $Service service..." -ForegroundColor Yellow
    
    try {
        $svc = kubectl get svc $Service -n $Namespace -o json 2>$null
        if ($svc) {
            $svcType = $svc.spec.type
            $svcIP = $svc.status.loadBalancer.ingress[0].ip
            
            if ($Verbose) {
                Write-Host "  Type: $svcType" -ForegroundColor Gray
                if ($svcIP) {
                    Write-Host "  IP: $svcIP" -ForegroundColor Gray
                }
            }
            
            if ($svcType -eq $ExpectedType) {
                if ($ExpectedType -eq "LoadBalancer" -and $svcIP) {
                    Write-Host "  ✅ $Service service is healthy" -ForegroundColor Green
                    return $true
                } elseif ($ExpectedType -ne "LoadBalancer") {
                    Write-Host "  ✅ $Service service is healthy" -ForegroundColor Green
                    return $true
                } else {
                    Write-Host "  ⚠️  $Service service has no LoadBalancer IP" -ForegroundColor Yellow
                    return $false
                }
            } else {
                Write-Host "  ⚠️  $Service service type is $svcType (expected $ExpectedType)" -ForegroundColor Yellow
                return $false
            }
        } else {
            Write-Host "  ❌ $Service service not found" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ❌ Error checking $Service service: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to check cluster health
function Test-ClusterHealth {
    Write-Host "🔍 Checking cluster health..." -ForegroundColor Yellow
    
    try {
        $nodes = kubectl get nodes --no-headers 2>$null
        if ($nodes) {
            $readyNodes = ($nodes | Where-Object { $_ -match "Ready" }).Count
            $totalNodes = $nodes.Count
            
            if ($Verbose) {
                Write-Host "  Nodes: $readyNodes/$totalNodes ready" -ForegroundColor Gray
                foreach ($node in $nodes) {
                    Write-Host "    $node" -ForegroundColor Gray
                }
            }
            
            if ($readyNodes -eq $totalNodes -and $totalNodes -ge 3) {
                Write-Host "  ✅ Cluster is healthy" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ⚠️  Cluster has $readyNodes/$totalNodes ready nodes" -ForegroundColor Yellow
                return $false
            }
        } else {
            Write-Host "  ❌ Cluster not accessible" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ❌ Error checking cluster: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to check ArgoCD applications
function Test-ArgoCDApplications {
    Write-Host "🔍 Checking ArgoCD applications..." -ForegroundColor Yellow
    
    try {
        $apps = kubectl get applications -n argocd --no-headers 2>$null
        if ($apps) {
            $healthyApps = ($apps | Where-Object { $_ -match "Healthy|Synced" }).Count
            $totalApps = $apps.Count
            
            if ($Verbose) {
                Write-Host "  Applications: $healthyApps/$totalApps healthy" -ForegroundColor Gray
                foreach ($app in $apps) {
                    Write-Host "    $app" -ForegroundColor Gray
                }
            }
            
            if ($healthyApps -ge $totalApps * 0.8) { # 80% healthy threshold
                Write-Host "  ✅ ArgoCD applications are healthy" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ⚠️  Only $healthyApps/$totalApps ArgoCD applications are healthy" -ForegroundColor Yellow
                return $false
            }
        } else {
            Write-Host "  ❌ ArgoCD applications not accessible" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ❌ Error checking ArgoCD applications: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
try {
    # Check prerequisites
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
    if (-not (Test-Command "kubectl")) {
        Write-Host "❌ kubectl not found" -ForegroundColor Red
        exit 1
    }
    
    # Check cluster connectivity
    if (-not (Test-ClusterHealth)) {
        if ($Wait) {
            Write-Host "⏳ Waiting for cluster to become healthy..." -ForegroundColor Yellow
            Start-Sleep 30
            if (-not (Test-ClusterHealth)) {
                Write-Host "❌ Cluster still not healthy after waiting" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "❌ Cluster is not healthy. Use -Wait to wait for recovery." -ForegroundColor Red
            exit 1
        }
    }
    
    # Check core components
    $healthyComponents = @()
    $totalComponents = 0
    
    # MetalLB
    $totalComponents++
    if (Test-ComponentHealth -Component "MetalLB" -Namespace "metallb-system" -Selector "app.kubernetes.io/name=metallb") {
        $healthyComponents++
    }
    
    # ArgoCD
    $totalComponents++
    if (Test-ComponentHealth -Component "ArgoCD" -Namespace "argocd" -Selector "app.kubernetes.io/name=argocd-server") {
        $healthyComponents++
    }
    
    # Ingress-Nginx
    $totalComponents++
    if (Test-ComponentHealth -Component "Ingress-Nginx" -Namespace "ingress-nginx" -Selector "app.kubernetes.io/name=ingress-nginx") {
        $healthyComponents++
    }
    
    # Cert-Manager
    $totalComponents++
    if (Test-ComponentHealth -Component "Cert-Manager" -Namespace "cert-manager" -Selector "app.kubernetes.io/name=cert-manager") {
        $healthyComponents++
    }
    
    # Prometheus
    $totalComponents++
    if (Test-ComponentHealth -Component "Prometheus" -Namespace "monitoring" -Selector "app.kubernetes.io/name=prometheus") {
        $healthyComponents++
    }
    
    # Grafana
    $totalComponents++
    if (Test-ComponentHealth -Component "Grafana" -Namespace "monitoring" -Selector "app.kubernetes.io/name=grafana") {
        $healthyComponents++
    }
    
    # Loki
    $totalComponents++
    if (Test-ComponentHealth -Component "Loki" -Namespace "monitoring" -Selector "app.kubernetes.io/name=loki") {
        $healthyComponents++
    }
    
    # OPA Gatekeeper
    $totalComponents++
    if (Test-ComponentHealth -Component "OPA Gatekeeper" -Namespace "gatekeeper-system" -Selector "app.kubernetes.io/name=gatekeeper") {
        $healthyComponents++
    }
    
    # Falco
    $totalComponents++
    if (Test-ComponentHealth -Component "Falco" -Namespace "falco" -Selector "app.kubernetes.io/name=falco") {
        $healthyComponents++
    }
    
    # Velero
    $totalComponents++
    if (Test-ComponentHealth -Component "Velero" -Namespace "velero" -Selector "app.kubernetes.io/name=velero") {
        $healthyComponents++
    }
    
    # Vault
    $totalComponents++
    if (Test-ComponentHealth -Component "Vault" -Namespace "vault" -Selector "app.kubernetes.io/name=vault") {
        $healthyComponents++
    }
    
    # External Secrets
    $totalComponents++
    if (Test-ComponentHealth -Component "External Secrets" -Namespace "external-secrets" -Selector "app.kubernetes.io/name=external-secrets") {
        $healthyComponents++
    }
    
    # Check services
    Write-Host "`n🌐 Checking services..." -ForegroundColor Cyan
    $healthyServices = @()
    $totalServices = 0
    
    # ArgoCD service
    $totalServices++
    if (Test-ServiceHealth -Service "argocd-server" -Namespace "argocd") {
        $healthyServices++
    }
    
    # Ingress service
    $totalServices++
    if (Test-ServiceHealth -Service "ingress-nginx-controller" -Namespace "ingress-nginx") {
        $healthyServices++
    }
    
    # Grafana service
    $totalServices++
    if (Test-ServiceHealth -Service "grafana" -Namespace "monitoring") {
        $healthyServices++
    }
    
    # Vault service
    $totalServices++
    if (Test-ServiceHealth -Service "vault" -Namespace "vault") {
        $healthyServices++
    }
    
    # Check ArgoCD applications
    Write-Host "`n🚀 Checking ArgoCD applications..." -ForegroundColor Cyan
    $argocdHealthy = Test-ArgoCDApplications
    
    # Summary
    Write-Host "`n📊 Health Check Summary:" -ForegroundColor Cyan
    Write-Host "  Cluster: ✅ Healthy" -ForegroundColor Green
    Write-Host "  Components: $healthyComponents/$totalComponents healthy" -ForegroundColor $(if ($healthyComponents -eq $totalComponents) { "Green" } else { "Yellow" })
    Write-Host "  Services: $healthyServices/$totalServices healthy" -ForegroundColor $(if ($healthyServices -eq $totalServices) { "Green" } else { "Yellow" })
    Write-Host "  ArgoCD Apps: $(if ($argocdHealthy) { "✅ Healthy" } else { "⚠️ Issues" })" -ForegroundColor $(if ($argocdHealthy) { "Green" } else { "Yellow" })
    
    # Overall health
    $overallHealthy = ($healthyComponents -ge $totalComponents * 0.8) -and ($healthyServices -ge $totalServices * 0.8) -and $argocdHealthy
    
    if ($overallHealthy) {
        Write-Host "`n🎉 Overall platform health: ✅ HEALTHY" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`n⚠️  Overall platform health: ⚠️  ISSUES DETECTED" -ForegroundColor Yellow
        Write-Host "   Run with -Verbose for detailed information" -ForegroundColor Gray
        exit 1
    }
}
catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
