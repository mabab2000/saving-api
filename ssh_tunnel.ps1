<#
PowerShell helper to open an SSH tunnel to a bastion host and forward local port 5432 to the RDS host.
Usage:
  1. Update the variables below with your bastion public IP, path to PEM/private key, and RDS host.
  2. Run: .\ssh_tunnel.ps1
  3. Leave the session open while testing DB connections to localhost:5432
#>

# === Edit these ===
$bastionUser = 'ec2-user'
$bastionHost = 'BASTION_PUBLIC_IP'   # replace with your bastion public IP or DNS
$keyPath = 'C:\path\to\your-key.pem' # path to your SSH private key (PEM)
$rdsHost = 'database-1.cluster-czgossm62ngg.eu-west-1.rds.amazonaws.com'
$rdsPort = 5432
$localPort = 5432

Write-Host "Opening SSH tunnel to $bastionHost (forwarding localhost:$localPort -> $rdsHost:$rdsPort)"

# Use the system ssh if available (OpenSSH). Windows 10+ typically has it.
$sshCmd = "ssh -i `"$keyPath`" -N -L $localPort`:$rdsHost`:$rdsPort $bastionUser@$bastionHost"
Write-Host "Running: $sshCmd"

# Start SSH in the current console (blocking). If you prefer a background job, use Start-Process.
cmd /c $sshCmd

# Note: Keep this window open while the tunnel is active.
Write-Host "SSH tunnel closed."