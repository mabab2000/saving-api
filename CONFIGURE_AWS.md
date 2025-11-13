# AWS Configuration and RDS Fix Guide

## Step 1: Configure AWS CLI with proper user

Run this command and enter the credentials for a user with RDS permissions:

```powershell
aws configure
```

Enter:
- AWS Access Key ID: [Your RDS-enabled user's access key]
- AWS Secret Access Key: [Your RDS-enabled user's secret key]  
- Default region name: eu-west-1
- Default output format: json

## Step 2: Verify new credentials
```powershell
aws sts get-caller-identity
```

## Step 3: Fix RDS connectivity

Once you have proper credentials, run these commands:

```powershell
# Get the security group ID for your RDS cluster
$sg_id = aws rds describe-db-clusters --db-cluster-identifier database-1 --region eu-west-1 --query 'DBClusters[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text
Write-Host "Security Group ID: $sg_id"

# Add your IP to the security group
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 5432 --cidr 105.178.32.202/32 --region eu-west-1

# Make RDS publicly accessible
aws rds modify-db-cluster --db-cluster-identifier database-1 --publicly-accessible --apply-immediately --region eu-west-1
```

## Step 4: Wait and test
Wait 2-3 minutes for changes to apply, then test:
```powershell
python test_db_connection.py
```

## Alternative: Use AWS Console
If you don't want to use CLI, go to AWS Console with your proper account:
1. RDS Console → database-1 → Modify → Set "Publicly accessible" = Yes
2. EC2 Console → Security Groups → Find RDS security group → Add inbound rule:
   - Type: PostgreSQL, Port: 5432, Source: 105.178.32.202/32

## Current Issue
The current user `alphonse.devs` doesn't have RDS permissions. You need to either:
1. Switch to a user with RDS permissions, OR
2. Give `alphonse.devs` the necessary IAM policies for RDS and EC2