# Get Service URLs Script
# This script retrieves all service URLs from the Talos platform

param(
    [switch]$Verbose,
    [switch]$Test
)

Write-Host "🌐 Getting Service URLs..." -ForegroundColor Cyan

# Function to test URL accessibility
function Test-URL {
    param(
        [string]$URL,
        [string]$ServiceName
    )
    
    if ($Test) {
        try {
            $response = Invoke-WebRequest -Uri $URL -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✅ $ServiceName is accessible" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ⚠️  $ServiceName returned status $($response.StatusCode)" -ForegroundColor Yellow
                return $false
            }
        }
        catch {
            Write-Host "  ❌ $ServiceName is not accessible: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    return $true
}

# Function to get service IP
function Get-ServiceIP {
    param(
        [string]$Service,
        [string]$Namespace
    )
    
    try {
        $ip = kubectl get svc $Service -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
        return $ip
    }
    catch {
        return $null
    }
}

# Function to get service port
function Get-ServicePort {
    param(
        [string]$Service,
        [string]$Namespace,
        [string]$DefaultPort = "80"
    )
    
    try {
        $port = kubectl get svc $Service -n $Namespace -o jsonpath='{.spec.ports[0].port}' 2>$null
        if ($port) {
            return $port
        }
    }
    catch {
        # Ignore errors
    }
    return $DefaultPort
}

# Function to get ArgoCD credentials
function Get-ArgoCDCredentials {
    try {
        $password = terraform output -raw argocd_admin_password 2>$null
        return $password
    }
    catch {
        return $null
    }
}

# Main execution
try {
    # Check prerequisites
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
    
    $requiredCommands = @("kubectl", "terraform")
    foreach ($cmd in $requiredCommands) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            Write-Host "❌ $cmd not found" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "✅ All prerequisites met" -ForegroundColor Green
    
    # Get service URLs
    Write-Host "`n🌐 Service URLs:" -ForegroundColor Cyan
    
    # ArgoCD
    $argocdIP = Get-ServiceIP -Service "argocd-server" -Namespace "argocd"
    if ($argocdIP) {
        $argocdPort = Get-ServicePort -Service "argocd-server" -Namespace "argocd"
        $argocdURL = "http://$argocdIP"
        Write-Host "  🚀 ArgoCD: $argocdURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $argocdIP, Port: $argocdPort" -ForegroundColor Gray
        }
        
        # Get credentials
        $argocdPassword = Get-ArgoCDCredentials
        if ($argocdPassword) {
            Write-Host "     Username: admin" -ForegroundColor Gray
            Write-Host "     Password: $argocdPassword" -ForegroundColor Gray
        }
        
        Test-URL -URL $argocdURL -ServiceName "ArgoCD"
    } else {
        Write-Host "  ❌ ArgoCD: Not available" -ForegroundColor Red
    }
    
    # Ingress-Nginx
    $ingressIP = Get-ServiceIP -Service "ingress-nginx-controller" -Namespace "ingress-nginx"
    if ($ingressIP) {
        $ingressPort = Get-ServicePort -Service "ingress-nginx-controller" -Namespace "ingress-nginx"
        $ingressURL = "http://$ingressIP"
        Write-Host "  🌐 Ingress: $ingressURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $ingressIP, Port: $ingressPort" -ForegroundColor Gray
        }
        
        Test-URL -URL $ingressURL -ServiceName "Ingress"
    } else {
        Write-Host "  ❌ Ingress: Not available" -ForegroundColor Red
    }
    
    # Grafana
    $grafanaIP = Get-ServiceIP -Service "grafana" -Namespace "monitoring"
    if ($grafanaIP) {
        $grafanaPort = Get-ServicePort -Service "grafana" -Namespace "monitoring"
        $grafanaURL = "http://$grafanaIP"
        Write-Host "  📊 Grafana: $grafanaURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $grafanaIP, Port: $grafanaPort" -ForegroundColor Gray
            Write-Host "     Default credentials: admin/admin123" -ForegroundColor Gray
        }
        
        Test-URL -URL $grafanaURL -ServiceName "Grafana"
    } else {
        Write-Host "  ❌ Grafana: Not available" -ForegroundColor Red
    }
    
    # Prometheus
    $prometheusIP = Get-ServiceIP -Service "prometheus-server" -Namespace "monitoring"
    if ($prometheusIP) {
        $prometheusPort = Get-ServicePort -Service "prometheus-server" -Namespace "monitoring" -DefaultPort "9090"
        $prometheusURL = "http://$prometheusIP"
        Write-Host "  📈 Prometheus: $prometheusURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $prometheusIP, Port: $prometheusPort" -ForegroundColor Gray
        }
        
        Test-URL -URL $prometheusURL -ServiceName "Prometheus"
    } else {
        Write-Host "  ❌ Prometheus: Not available" -ForegroundColor Red
    }
    
    # Vault
    $vaultIP = Get-ServiceIP -Service "vault" -Namespace "vault"
    if ($vaultIP) {
        $vaultPort = Get-ServicePort -Service "vault" -Namespace "vault"
        $vaultURL = "http://$vaultIP"
        Write-Host "  🔐 Vault: $vaultURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $vaultIP, Port: $vaultPort" -ForegroundColor Gray
        }
        
        Test-URL -URL $vaultURL -ServiceName "Vault"
    } else {
        Write-Host "  ❌ Vault: Not available" -ForegroundColor Red
    }
    
    # Loki (if accessible)
    $lokiIP = Get-ServiceIP -Service "loki" -Namespace "monitoring"
    if ($lokiIP) {
        $lokiPort = Get-ServicePort -Service "loki" -Namespace "monitoring" -DefaultPort "3100"
        $lokiURL = "http://$lokiIP"
        Write-Host "  📝 Loki: $lokiURL" -ForegroundColor White
        
        if ($Verbose) {
            Write-Host "     IP: $lokiIP, Port: $lokiPort" -ForegroundColor Gray
        }
        
        Test-URL -URL $lokiURL -ServiceName "Loki"
    } else {
        Write-Host "  ❌ Loki: Not available" -ForegroundColor Red
    }
    
    # Additional information
    Write-Host "`n📋 Additional Information:" -ForegroundColor Cyan
    Write-Host "  🐙 Kubernetes API: https://192.168.1.101:6443" -ForegroundColor White
    Write-Host "  📊 Cluster nodes: kubectl get nodes" -ForegroundColor Gray
    Write-Host "  🚀 ArgoCD apps: kubectl get applications -n argocd" -ForegroundColor Gray
    Write-Host "  📈 Monitoring: kubectl get pods -n monitoring" -ForegroundColor Gray
    Write-Host "  🔐 Secrets: kubectl get secrets -A" -ForegroundColor Gray
    
    # Access commands
    Write-Host "`n🔧 Access Commands:" -ForegroundColor Cyan
    Write-Host "  # ArgoCD CLI login:" -ForegroundColor Gray
    Write-Host "  argocd login --insecure --username admin --password <password> http://$argocdIP" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Set kubeconfig:" -ForegroundColor Gray
    Write-Host "  export KUBECONFIG=kubeconfig" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Port forward for local access:" -ForegroundColor Gray
    Write-Host "  kubectl port-forward svc/grafana 3000:3000 -n monitoring" -ForegroundColor White
    
    Write-Host "`n🎉 Service URLs retrieved successfully!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to get service URLs: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
