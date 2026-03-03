# K3s Cluster Status Check
Write-Host "K3s Cluster Status" -ForegroundColor Cyan

$KubeConfigPath = "$env:USERPROFILE\.kube\config-k3s"

# Check control plane nodes
Write-Host "`n=== Control Plane Nodes ===" -ForegroundColor Yellow
1..3 | ForEach-Object {
    $ip = "192.168.56.$(100 + $_)"
    $result = Test-NetConnection -ComputerName $ip -Port 6443 -WarningAction SilentlyContinue
    Write-Host "cp$_ ($ip): $(if($result.TcpTestSucceeded) { 'Ready' } else { 'Not Ready' })"
}

# Check worker nodes
Write-Host "`n=== Worker Nodes ===" -ForegroundColor Yellow
1..2 | ForEach-Object {
    $ip = "192.168.56.$(103 + $_)"
    $result = Test-NetConnection -ComputerName $ip -Port 10250 -WarningAction SilentlyContinue
    Write-Host "worker$_ ($ip): $(if($result.TcpTestSucceeded) { 'Ready' } else { 'Not Ready' })"
}

# Check stable localhost API endpoint
Write-Host "`n=== Host API Endpoint ===" -ForegroundColor Yellow
$localApi = Test-NetConnection -ComputerName 127.0.0.1 -Port 64430 -WarningAction SilentlyContinue
Write-Host "localhost:64430: $(if($localApi.TcpTestSucceeded) { 'Reachable' } else { 'Not Reachable' })"

# Get kubeconfig from cp1 and rewrite for host localhost forwarding
Write-Host "`n=== Getting Kubeconfig ===" -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$env:USERPROFILE\.kube" -Force | Out-Null

try {
    $kubeconfigRaw = vagrant ssh cp1 -c "sudo cat /etc/rancher/k3s/k3s.yaml"
    if (-not $kubeconfigRaw) {
        throw "kubeconfig not returned from cp1"
    }

    $kubeconfigHost = $kubeconfigRaw -replace "server: https://127.0.0.1:6443", "server: https://127.0.0.1:64430" -replace "server: https://192.168.56.101:6443", "server: https://127.0.0.1:64430"
    Set-Content -Path $KubeConfigPath -Value $kubeconfigHost -Encoding utf8
    Write-Host "Kubeconfig generated at $KubeConfigPath (server: https://127.0.0.1:64430)" -ForegroundColor Green
}
catch {
    Write-Host "Failed to generate kubeconfig from cp1: $($_.Exception.Message)" -ForegroundColor Red
}
