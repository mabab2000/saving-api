#!/usr/bin/env powershell
# Script to fix AWS RDS connectivity by making it publicly accessible
# and updating security group rules

param(
    [Parameter(Mandatory=$true)]
    [string]$ClusterIdentifier = "database-1",
    
    [Parameter(Mandatory=$true)]
    [string]$Region = "eu-west-1",
    
    [Parameter(Mandatory=$false)]
    [string]$YourPublicIP = "105.178.32.202"
)

Write-Host "Fixing AWS RDS connectivity for cluster: $ClusterIdentifier" -ForegroundColor Green

# Step 1: Get cluster details and security group ID
Write-Host "Getting cluster information..." -ForegroundColor Yellow
try {
    $clusterInfo = aws rds describe-db-clusters --db-cluster-identifier $ClusterIdentifier --region $Region --output json | ConvertFrom-Json
    $securityGroupId = $clusterInfo.DBClusters[0].VpcSecurityGroups[0].VpcSecurityGroupId
    Write-Host "Security Group ID: $securityGroupId" -ForegroundColor Cyan
} catch {
    Write-Error "Failed to get cluster information. Check your AWS permissions and cluster name."
    exit 1
}

# Step 2: Add inbound rule to security group for your IP
Write-Host "Adding inbound rule to security group..." -ForegroundColor Yellow
try {
    aws ec2 authorize-security-group-ingress `
        --group-id $securityGroupId `
        --protocol tcp `
        --port 5432 `
        --cidr "$YourPublicIP/32" `
        --region $Region
    Write-Host "Successfully added inbound rule for IP: $YourPublicIP" -ForegroundColor Green
} catch {
    Write-Warning "Rule might already exist or permission denied. Continuing..."
}

# Step 3: Modify cluster to be publicly accessible
Write-Host "Making cluster publicly accessible..." -ForegroundColor Yellow
try {
    aws rds modify-db-cluster `
        --db-cluster-identifier $ClusterIdentifier `
        --apply-immediately `
        --region $Region `
        --publicly-accessible
    Write-Host "Cluster modification initiated. This may take a few minutes..." -ForegroundColor Green
} catch {
    Write-Error "Failed to modify cluster. Check permissions."
    exit 1
}

Write-Host "Setup complete! Wait 2-3 minutes for changes to apply, then test connection." -ForegroundColor Green
Write-Host "Run: python test_db_connection.py" -ForegroundColor Cyan