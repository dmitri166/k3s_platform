# K3s Deployment Script
Write-Host "Deploying K3s HA Cluster..." -ForegroundColor Cyan

$networkMode = if ($env:K3S_NETWORK_MODE) { $env:K3S_NETWORK_MODE.ToLower() } else { "bridged" }
$env:K3S_NETWORK_MODE = $networkMode

if ($networkMode -eq "hostonly") {
    # Validate host-only networking before provisioning VMs.
    Write-Host "Running host network preflight..." -ForegroundColor Yellow
    .\scripts\preflight-network.ps1

    # Keep one deterministic host-only adapter for all VMs (VirtualBox adapter name).
    $networkPrefix = if ($env:K3S_NET_PREFIX) { $env:K3S_NET_PREFIX } else { "192.168.56" }
    $expectedIp = "$networkPrefix.1"

    $vboxIfs = VBoxManage list hostonlyifs 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $vboxIfs) {
        throw "Unable to query VirtualBox host-only adapters via VBoxManage."
    }

    $matchingAdapters = @()
    $currentName = $null
    foreach ($line in $vboxIfs) {
        if ($line -match '^\s*Name:\s+(.+)$') {
            $currentName = $Matches[1].Trim()
            continue
        }

        if ($line -match '^\s*IP\s*Address:\s+(.+)$') {
            $ip = $Matches[1].Trim()
            if ($currentName -and $ip -eq $expectedIp) {
                $matchingAdapters += $currentName
            }
        }
    }

    if ($matchingAdapters.Count -ne 1) {
        throw "Host-only mode requires exactly one VirtualBox host-only adapter with IP $expectedIp. Found: $($matchingAdapters -join ', ')."
    }

    $hostOnlyAdapter = $matchingAdapters[0]
    $env:HOSTONLY_ADAPTER = $hostOnlyAdapter
    Write-Host "Using host-only adapter: $hostOnlyAdapter" -ForegroundColor Yellow
}
elseif ($networkMode -eq "bridged") {
    if (-not $env:BRIDGE_ADAPTER) {
        throw "BRIDGE_ADAPTER is required in bridged mode. Example: `$env:BRIDGE_ADAPTER='Wi-Fi'"
    }
    Write-Host "Using bridged adapter: $($env:BRIDGE_ADAPTER)" -ForegroundColor Yellow
}
else {
    throw "K3S_NETWORK_MODE must be 'bridged' or 'hostonly'."
}

# Clean up any existing VMs
Write-Host "Cleaning existing VMs..." -ForegroundColor Yellow
vagrant destroy -f

# Start deployment
Write-Host "Starting K3s cluster deployment..." -ForegroundColor Green
vagrant up --no-parallel

# Wait for deployment to complete
Write-Host "Waiting for cluster initialization..." -ForegroundColor Yellow
Start-Sleep 180

# Verify cluster status
Write-Host "Verifying cluster status..." -ForegroundColor Green
.\scripts\k3s-status.ps1
