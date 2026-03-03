# K3s Cluster Cleanup
Write-Host "Cleaning K3s cluster..." -ForegroundColor Cyan

# Destroy VMs
Write-Host "Destroying VMs..." -ForegroundColor Yellow
vagrant destroy -f

# Clean VirtualBox
Write-Host "Cleaning VirtualBox..." -ForegroundColor Yellow
VBoxManage list vms | Select-String "k3s-platform" | ForEach-Object {
    $vmName = $_.ToString().Split('"')[1]
    VBoxManage unregistervm "$vmName" --delete
}

# Clean local files
Write-Host "Cleaning local files..." -ForegroundColor Yellow
Remove-Item scripts/k3s-token.txt -Force -ErrorAction SilentlyContinue
Remove-Item .\.ssh\k3s-config.yaml -Force -ErrorAction SilentlyContinue

Write-Host "✅ Cleanup complete" -ForegroundColor Green
