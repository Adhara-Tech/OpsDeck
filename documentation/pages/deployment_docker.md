# Docker Compose Deployment Guide

This guide details how to deploy OpsDeck using Docker Compose, which simplifies running the application and its dependencies in containers.

## Prerequisites

- Docker
- Docker Compose

## Steps

### 1. Clone the Repository

```bash
git clone https://github.com/pixelotes/OpsDeck.git
cd OpsDeck
```

### 2. Configuration

Copy the example environment file. The `docker-compose.yml` file is configured to read environment variables from `.env`.

```bash
cp .env.example .env
```
Ensure you review `.env` and set values appropriate for production (especially `SECRET_KEY`).

### 3. Build and Run

Run the following command to build the Docker image and start the container in detached mode.

```bash
docker-compose up -d --build
```

### 4. Verify Deployment

Check the status of the container:

```bash
docker-compose ps
```

View the logs to ensure the application started correctly:

```bash
docker-compose logs -f web
```

The application is configured to automatically initialize the database on the first run (via `entrypoint.sh`).

### 5. Configure Admin Credentials (Optional)

By default, the application creates an admin user with email `admin@example.com` and password `admin123`. For production deployments, you should customize these credentials by adding the following to your `.env` file:

```bash
DEFAULT_ADMIN_EMAIL=your-admin@company.com
DEFAULT_ADMIN_INITIAL_PASSWORD=YourSecurePassword123!
```

The admin user is created automatically when the container starts for the first time. The application will prompt you to change the password on first login.

### 6. Access the Application

Open your browser and navigate to:
`http://localhost:5000`

**Default Login:**
- Email: Value of `DEFAULT_ADMIN_EMAIL` (default: `admin@example.com`)
- Password: Value of `DEFAULT_ADMIN_INITIAL_PASSWORD` (default: `admin123`)

## Data Persistence

The `docker-compose.yml` mounts a volume for data persistence:
- `./data` on host maps to `/app/data` in the container.

This ensures that your data files (attachments, logs) persist even if the container is stopped or removed.

## Production Considerations

### Database

OpsDeck requires PostgreSQL. Configure it via the `DATABASE_URL` environment variable:

1. Update `docker-compose.yml` to add PostgreSQL service:
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: opsdeck
      POSTGRES_USER: opsdeck_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  web:
    # ... existing config
    environment:
      DATABASE_URL: postgresql://opsdeck_user:secure_password_here@db:5432/opsdeck
    depends_on:
      - db

volumes:
  postgres_data:
```

2. Initialize database:
```bash
docker-compose exec web flask db upgrade
docker-compose exec web flask init-db
```

### Security Hardening

**TLS/HTTPS**
Do not expose the application directly to the internet. Use a reverse proxy:
- Nginx or Apache with TLS termination
- Let's Encrypt for free SSL certificates
- HAProxy for load balancing in multi-instance deployments

**Secrets Management**
- Never commit `.env` with production credentials to version control
- Use Docker secrets or external secrets managers (Vault, AWS Secrets Manager)
- Rotate SECRET_KEY and database passwords regularly

**Network Isolation**
Configure Docker networks to isolate services:
```yaml
networks:
  frontend:
  backend:

services:
  web:
    networks:
      - frontend
      - backend
  db:
    networks:
      - backend  # Not exposed to frontend network
```

### Backup Strategy

**Database Backups**
Automated backup script example:
```bash
#!/bin/bash
# backup-opsdeck.sh
BACKUP_DIR="/backups/opsdeck"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker-compose exec -T db pg_dump -U opsdeck_user opsdeck | gzip > "$BACKUP_DIR/opsdeck_$TIMESTAMP.sql.gz"

# Backup file uploads
tar -czf "$BACKUP_DIR/files_$TIMESTAMP.tar.gz" ./data

# Retain last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

Schedule via cron:
```cron
0 2 * * * /opt/scripts/backup-opsdeck.sh
```

### Monitoring

**Health Checks**
Add health check to `docker-compose.yml`:
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Log Aggregation**
Configure logging driver:
```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Or send to external system:
```yaml
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logserver:514"
        tag: "opsdeck"
```

### Performance Tuning

**Application Workers**
For production, run multiple Gunicorn workers:

Update `entrypoint.sh`:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app
```

Workers formula: `(2 * CPU_CORES) + 1`

**Database Connection Pool**
In production PostgreSQL config:
```python
# In application config
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

**Resource Limits**
Set container resource limits:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Troubleshooting

**Container Won't Start**
```bash
# Check logs
docker-compose logs web

# Common issues:
# - Database connection failed: Verify DATABASE_URL
# - Port conflict: Change port mapping in docker-compose.yml
# - Permission denied: Check volume mount permissions
```

**Database Migration Errors**
```bash
# Reset migrations (CAUTION: destroys data)
docker-compose exec web flask db downgrade base
docker-compose exec web flask db upgrade

# Or recreate from scratch
docker-compose down -v
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask init-db
```

**Performance Issues**
```bash
# Check resource usage
docker stats opsdeck_web_1

# Check database locks (PostgreSQL)
docker-compose exec db psql -U opsdeck_user -d opsdeck -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check slow queries
docker-compose exec web flask shell
# Then in Python shell:
from flask import current_app
current_app.config['SQLALCHEMY_ECHO'] = True  # Enables query logging
```
