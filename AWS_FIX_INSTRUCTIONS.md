# AWS RDS Connection Fix Instructions

## Option 1: Fix AWS RDS (Run with proper AWS permissions)

You need to run these commands with an AWS account that has RDS and EC2 permissions:

```bash
# 1. Get your RDS cluster's security group ID
aws rds describe-db-clusters --db-cluster-identifier database-1 --region eu-west-1 --query 'DBClusters[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text

# 2. Add your IP to the security group (replace SG-XXXXXX with actual security group ID from step 1)
aws ec2 authorize-security-group-ingress \
  --group-id SG-XXXXXX \
  --protocol tcp \
  --port 5432 \
  --cidr 105.178.32.202/32 \
  --region eu-west-1

# 3. Make the RDS cluster publicly accessible
aws rds modify-db-cluster \
  --db-cluster-identifier database-1 \
  --apply-immediately \
  --region eu-west-1 \
  --publicly-accessible
```

## Option 2: Use Local PostgreSQL (Quick Solution)

Start a local PostgreSQL database using Docker:

```powershell
# Start local PostgreSQL
docker-compose up -d postgres

# Update your .env file to use local database
# DATABASE_URL=postgresql://postgres:localdev123@localhost:5432/saving_api
```

## Option 3: AWS Console Steps

1. Go to AWS RDS Console (eu-west-1 region)
2. Find cluster "database-1" → Click it
3. Under "Connectivity & security" → Note the VPC Security Group ID
4. Go to EC2 Console → Security Groups → Find that security group
5. Edit Inbound Rules → Add:
   - Type: PostgreSQL
   - Port: 5432
   - Source: 105.178.32.202/32
6. Go back to RDS → Modify cluster → Set "Publicly accessible" to Yes
7. Apply changes immediately

Wait 2-3 minutes after making changes, then test with:
```powershell
python test_db_connection.py
```