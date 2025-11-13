# Database Connection Options

This project uses PostgreSQL. If your RDS instance is in a private VPC subnet (common for security), you can't connect directly from your laptop. This document lists safe ways to connect for development.

Option A — SSH tunnel via a bastion (recommended)
1. Create an EC2 instance (bastion) in a public subnet of the same VPC as your RDS. Give it an Elastic IP.
2. Ensure the bastion's security group allows SSH from your IP and allows outbound to the RDS security group.
3. Ensure the RDS security group allows inbound Postgres (TCP/5432) from the bastion's security group (use SG id as source).
4. Use `ssh` to forward local port 5432 to the RDS host:port.
   Example (PowerShell/OpenSSH):

   ssh -i C:\path\to\key.pem -L 5432:database-1.cluster-czgossm62ngg.eu-west-1.rds.amazonaws.com:5432 ec2-user@BASTION_PUBLIC_IP

5. Update your `.env` to point to `localhost` (or set DB_HOST=localhost). Example env vars:

   DB_USER=postgres
   DB_PASSWORD=your-password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=postgres

6. Run `python test_db_connection.py` or start the app. Connections will go through the SSH tunnel.

Option B — Temporarily make RDS publicly accessible (less secure)
1. In AWS RDS Console, modify the instance/set cluster to `Publicly accessible = Yes`.
2. Modify the DB subnet group to include public subnets (with route to an internet gateway).
3. In the RDS security group, add an inbound rule: Type=PostgreSQL, Port=5432, Source=YOUR_IP/32.
4. Reboot/apply changes and then run the `test_db_connection.py` script.

Option C — Use AWS Systems Manager Session Manager (no bastion key required)
1. Make sure an EC2 instance has the SSM agent and proper IAM role.
2. Use Session Manager port forwarding to forward a local port to the RDS.

Notes:
- Do NOT open 0.0.0.0/0 to port 5432 on production DBs.
- Use `sslmode=require` if the DB requires SSL (add `?sslmode=require` to the DATABASE_URL).

If you want, I can help create the AWS security group changes or the minimal EC2 bastion and show exact commands for your setup. Paste the output of these commands if you haven't yet:

Resolve-DnsName database-1.cluster-czgossm62ngg.eu-west-1.rds.amazonaws.com
Test-NetConnection -ComputerName database-1.cluster-czgossm62ngg.eu-west-1.rds.amazonaws.com -Port 5432

