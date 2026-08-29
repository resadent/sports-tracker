# setup-lan-access.ps1
# Exposes the WSL2 Sports Tracker API on the Windows host's LAN interface so
# devices on your home network (192.168.1.x) can reach the dashboard.
#
# Windows Firewall allows inbound TCP 8000, then netsh port-proxies
# 0.0.0.0:8000 -> <current WSL2 VM IP>:8000. The WSL2 NAT IP changes on every
# reboot, so re-run this script (as admin) after a reboot to refresh it.
#
# Usage (run in an ADMIN PowerShell):
#   powershell -ExecutionPolicy Bypass -File C:\Users\edu\setup-lan-access.ps1
#   powershell -ExecutionPolicy Bypass -File C:\Users\edu\setup-lan-access.ps1 -Remove
#
# The -Remove switch deletes the firewall rule and port proxy again.

param([switch]$Remove)

$ErrorActionPreference = "Stop"
$Port   = 8000
$Listen = "0.0.0.0"
$Rule   = "Sports Tracker (TCP $Port)"

if ($Remove) {
    if (Get-NetFirewallRule -DisplayName $Rule -ErrorAction SilentlyContinue) {
        Remove-NetFirewallRule -DisplayName $Rule
        Write-Host "Removed firewall rule: $Rule"
    }
    & netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=$Listen 2>$null | Out-Null
    Write-Host "Removed port proxy 0.0.0.0:$Port"
    exit 0
}

# 1) Discover the current WSL2 VM IP (changes on reboot).
$raw  = (wsl.exe bash -c "ip -4 -o addr show eth0" 2>$null) -join " "
$wslIp = [regex]::Match($raw, "inet\s+(\d+\.\d+\.\d+\.\d+)").Groups[1].Value
if (-not $wslIp) {
    throw "Could not detect the WSL2 IP. Open WSL and run: ip -4 -o addr show eth0"
}
Write-Host "WSL2 VM IP: $wslIp"

# 2) Windows Firewall: allow inbound TCP on $Port (idempotent).
if (-not (Get-NetFirewallRule -DisplayName $Rule -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $Rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Any | Out-Null
    Write-Host "Firewall rule added: $Rule"
} else {
    Write-Host "Firewall rule already present: $Rule"
}

# 3) Port proxy: 0.0.0.0:$Port -> $wslIp:$Port (idempotent).
& netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=$Listen 2>$null | Out-Null
& netsh interface portproxy add v4tov4 listenport=$Port listenaddress=$Listen connectaddress=$wslIp connectport=$Port
if ($LASTEXITCODE -ne 0) { throw "netsh portproxy add failed (exit $LASTEXITCODE)" }
Write-Host "Port proxy set: $Listen`:$Port -> $wslIp`:$Port"

# 4) Report the LAN URLs.
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like "192.168.1.*" } |
    Select-Object -First 1).IPAddress
if (-not $lanIp) { $lanIp = "YOUR_HOST_LAN_IP" }

Write-Host ""
Write-Host "Configured. From any device on your LAN open:"
Write-Host "  http://$lanIp`:$Port"
Write-Host ""
Write-Host "Note: re-run this script after every reboot (the WSL2 IP changes)."
