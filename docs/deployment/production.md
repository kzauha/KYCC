# Production Deployment

This guide covers deploying KYCC to a production environment.

## Overview

Production deployment involves:

1. Infrastructure setup
2. Database configuration
3. Backend deployment
4. Frontend deployment
5. Monitoring and logging
6. Security hardening

---

## Infrastructure Requirements

### Minimum Requirements

| Component | Specification |
|-----------|---------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Storage | 20 GB SSD |
| OS | Ubuntu 22.04 LTS |

### Recommended Requirements

| Component | Specification |
|-----------|---------------|
| CPU | 4+ cores |
| RAM | 8+ GB |
| Storage | 100 GB SSD |
| OS | Ubuntu 22.04 LTS |

---

## Database Setup

### PostgreSQL Installation

```bash
# Install PostgreSQL 15
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Database Configuration

```bash
# Connect as postgres user
sudo -u postgres psql

# Create database and user
CREATE USER kycc WITH PASSWORD 'secure_password_here';
CREATE DATABASE kycc_db OWNER kycc;
GRANT ALL PRIVILEGES ON DATABASE kycc_db TO kycc;

# Enable extensions
\c kycc_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\q
```

### PostgreSQL Performance Tuning

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
# Memory
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 50MB
maintenance_work_mem = 512MB

# Connections
max_connections = 100

# Write ahead log
wal_buffers = 64MB
checkpoint_completion_target = 0.9

# Query planner
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Connection Security

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```
# IPv4 local connections
host    kycc_db    kycc    127.0.0.1/32    scram-sha-256
host    kycc_db    kycc    10.0.0.0/8      scram-sha-256
```

---

## Backend Deployment

### System Setup

```bash
# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install system dependencies
sudo apt install gcc libpq-dev nginx

# Create application user
sudo useradd -m -s /bin/bash kycc
sudo mkdir -p /opt/kycc
sudo chown kycc:kycc /opt/kycc
```

### Application Setup

```bash
# Switch to application user
sudo su - kycc

# Clone repository
cd /opt/kycc
git clone https://github.com/AnshumanAtrey/KYCC.git .

# Create virtual environment
cd backend
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Environment Configuration

Create `/opt/kycc/backend/.env`:

```bash
DATABASE_URL=postgresql://kycc:secure_password@localhost:5432/kycc_db
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
SECRET_KEY=your-secret-key-here
```

### Database Migrations

```bash
cd /opt/kycc/backend
source venv/bin/activate
alembic upgrade head
```

### Gunicorn Configuration

Create `/opt/kycc/backend/gunicorn.conf.py`:

```python
# Gunicorn configuration

bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
errorlog = "/var/log/kycc/gunicorn-error.log"
accesslog = "/var/log/kycc/gunicorn-access.log"
loglevel = "info"
```

### Systemd Service

Create `/etc/systemd/system/kycc-backend.service`:

```ini
[Unit]
Description=KYCC Backend API
After=network.target postgresql.service

[Service]
User=kycc
Group=kycc
WorkingDirectory=/opt/kycc/backend
Environment="PATH=/opt/kycc/backend/venv/bin"
EnvironmentFile=/opt/kycc/backend/.env
ExecStart=/opt/kycc/backend/venv/bin/gunicorn main:app -c gunicorn.conf.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kycc-backend
sudo systemctl start kycc-backend
```

---

## Nginx Configuration

### SSL Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com
```

### Nginx Site Configuration

Create `/etc/nginx/sites-available/kycc`:

```nginx
upstream kycc_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # API endpoints
    location /api {
        proxy_pass http://kycc_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Health check
    location /health {
        proxy_pass http://kycc_backend/health;
    }

    # Static files (frontend)
    location / {
        root /opt/kycc/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1000;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/kycc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Frontend Deployment

### Build Frontend

```bash
cd /opt/kycc/frontend
npm install
npm run build
```

### Deploy to Nginx

```bash
# Built files are in /opt/kycc/frontend/dist
# Nginx serves them from the location / block
```

---

## Dagster Deployment

### Systemd Service

Create `/etc/systemd/system/kycc-dagster.service`:

```ini
[Unit]
Description=KYCC Dagster Pipeline
After=network.target postgresql.service

[Service]
User=kycc
Group=kycc
WorkingDirectory=/opt/kycc/backend
Environment="PATH=/opt/kycc/backend/venv/bin"
Environment="DAGSTER_HOME=/opt/kycc/backend/dagster_home"
EnvironmentFile=/opt/kycc/backend/.env
ExecStart=/opt/kycc/backend/venv/bin/dagster dev -h 127.0.0.1 -p 3000 -f dagster_home/definitions.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx Proxy for Dagster

Add to Nginx configuration:

```nginx
location /dagster {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

---

## Logging

### Create Log Directory

```bash
sudo mkdir -p /var/log/kycc
sudo chown kycc:kycc /var/log/kycc
```

### Log Rotation

Create `/etc/logrotate.d/kycc`:

```
/var/log/kycc/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 kycc kycc
    sharedscripts
    postrotate
        systemctl reload kycc-backend
    endscript
}
```

---

## Monitoring

### Health Check Endpoint

Backend provides `/health` endpoint:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Monitoring Script

Create `/opt/kycc/scripts/health_check.sh`:

```bash
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$RESPONSE" != "200" ]; then
    echo "Health check failed: HTTP $RESPONSE"
    systemctl restart kycc-backend
fi
```

Add to crontab:

```bash
*/5 * * * * /opt/kycc/scripts/health_check.sh
```

---

## Security Checklist

1. **Firewall Configuration**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Database Security**
   - Use strong passwords
   - Restrict connections to localhost/VPC
   - Enable SSL for database connections

3. **Application Security**
   - Set SECRET_KEY environment variable
   - Configure CORS properly
   - Enable rate limiting

4. **SSL/TLS**
   - Use Let's Encrypt for certificates
   - Enable HSTS
   - Use TLS 1.2+

5. **Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

---

## Backup Strategy

### Database Backup

```bash
#!/bin/bash
# /opt/kycc/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/kycc/backups

mkdir -p $BACKUP_DIR
pg_dump -U kycc kycc_db | gzip > $BACKUP_DIR/kycc_db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

### Cron Schedule

```bash
0 2 * * * /opt/kycc/scripts/backup.sh
```

---

## Deployment Commands Summary

```bash
# Pull latest code
cd /opt/kycc
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart kycc-backend

# Update frontend
cd ../frontend
npm install
npm run build
```
