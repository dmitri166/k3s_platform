# K3s Cluster Status Check
Write-Host "K3s Cluster Status" -ForegroundColor Cyan

# Check control plane nodes
Write-Host "`n=== Control Plane Nodes ===" -ForegroundColor Yellow
1..3 | ForEach-Object {
    $ip = "192.168.56.$(100 + $_)"
    $result = Test-NetConnection -ComputerName $ip -Port 6443 -WarningAction SilentlyContinue
    Write-Host "cp$_ ($ip): $(if($result.TcpTestSucceeded) { '✅ Ready' } else { '❌ Not Ready' })"
}

# Check worker nodes
Write-Host "`n=== Worker Nodes ===" -ForegroundColor Yellow
1..2 | ForEach-Object {
    $ip = "192.168.56.$(103 + $_)"
    $result = Test-NetConnection -ComputerName $ip -Port 10250 -WarningAction SilentlyContinue
    Write-Host "worker$_ ($ip): $(if($result.TcpTestSucceeded) { '✅ Ready' } else { '❌ Not Ready' })"
}

# Get kubeconfig
Write-Host "`n=== Getting Kubeconfig ===" -ForegroundColor Yellow
if (Test-Path ".\.ssh\k3s-config.yaml") {
    Copy-Item ".\.ssh\k3s-config.yaml" "$env:USERPROFILE\.kube\config-k3s" -Force
    Write-Host "✅ Kubeconfig copied to ~/.kube/config-k3s" -ForegroundColor Green
} else {
    Write-Host "❌ Kubeconfig not found" -ForegroundColor Red
}
