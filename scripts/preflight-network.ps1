param(
    [string]$NetworkPrefix = "192.168.56",
    [string]$AdapterName = "VirtualBox Host-Only Ethernet Adapter"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$message) {
    Write-Host "[preflight] $message" -ForegroundColor Cyan
}

function Ensure-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell (Run as Administrator)."
    }
}

function Get-HostOnlyAdapter {
    $candidates = Get-NetAdapter | Where-Object {
        $_.InterfaceDescription -like "*VirtualBox Host-Only*" -or
        $_.Name -like "*VirtualBox Host-Only*"
    }

    if (-not $candidates) {
        throw "No VirtualBox host-only adapters found. Create one in VirtualBox Tools -> Network -> Host-only Networks."
    }

    $adapter = $candidates | Where-Object {
        $_.InterfaceDescription -eq $AdapterName -or $_.Name -eq $AdapterName
    } | Select-Object -First 1

    if (-not $adapter) {
        $adapter = $candidates | Select-Object -First 1
    }

    if (-not $adapter) {
        throw "Adapter '$AdapterName' not found. Create it in VirtualBox Tools -> Network -> Host-only Networks."
    }
    return $adapter
}

function Ensure-AdapterUp([Microsoft.Management.Infrastructure.CimInstance]$adapter) {
    if ($adapter.Status -ne "Up") {
        Write-Step "Bringing adapter '$($adapter.Name)' up"
        Enable-NetAdapter -Name $adapter.Name | Out-Null
        Start-Sleep -Seconds 2
    }
}

function Ensure-HostIp([Microsoft.Management.Infrastructure.CimInstance]$adapter, [string]$networkPrefix) {
    $expectedIp = "$networkPrefix.1"
    $allHostOnlyWithExpectedIp = Get-NetAdapter | Where-Object {
        $_.InterfaceDescription -like "*VirtualBox Host-Only*" -or
        $_.Name -like "*VirtualBox Host-Only*"
    } | ForEach-Object {
        $a = $_
        Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -eq $expectedIp } |
            ForEach-Object { [PSCustomObject]@{ Name = $a.Name; ifIndex = $a.ifIndex; IPAddress = $_.IPAddress } }
    }

    if ($allHostOnlyWithExpectedIp.Count -eq 0) {
        throw "No VirtualBox host-only adapter has $expectedIp/24. Fix Host-only adapter IPv4 in VirtualBox."
    }

    if ($allHostOnlyWithExpectedIp.Count -gt 1) {
        $names = ($allHostOnlyWithExpectedIp | Select-Object -ExpandProperty Name | Sort-Object -Unique) -join ", "
        throw "Multiple VirtualBox host-only adapters have $expectedIp/24 ($names). Keep exactly one to avoid split cluster networking."
    }

    $ip = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -eq $expectedIp } |
        Select-Object -First 1

    if (-not $ip) {
        throw "Selected adapter '$($adapter.Name)' does not have $expectedIp/24."
    }
}

function Ensure-Route([Microsoft.Management.Infrastructure.CimInstance]$adapter, [string]$networkPrefix) {
    $destination = "$networkPrefix.0/24"
    $routes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $destination -ErrorAction SilentlyContinue

    if ($routes) {
        $badRoutes = $routes | Where-Object { $_.ifIndex -ne $adapter.ifIndex -or $_.NextHop -ne "0.0.0.0" }
        if ($badRoutes) {
            Write-Step "Removing conflicting route entries for $destination"
            $routes | Remove-NetRoute -Confirm:$false
            $routes = $null
        }
    }

    if (-not $routes) {
        Write-Step "Creating route $destination via ifIndex $($adapter.ifIndex)"
        New-NetRoute -AddressFamily IPv4 -DestinationPrefix $destination -InterfaceIndex $adapter.ifIndex -NextHop "0.0.0.0" -RouteMetric 5 | Out-Null
    }
}

try {
    Ensure-Admin
    $adapter = Get-HostOnlyAdapter
    Write-Step "Using adapter '$($adapter.Name)' (ifIndex=$($adapter.ifIndex))"
    Ensure-AdapterUp -adapter $adapter
    Ensure-HostIp -adapter $adapter -networkPrefix $NetworkPrefix
    Ensure-Route -adapter $adapter -networkPrefix $NetworkPrefix
    Write-Step "Network preflight completed successfully"
}
catch {
    Write-Host "[preflight] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
