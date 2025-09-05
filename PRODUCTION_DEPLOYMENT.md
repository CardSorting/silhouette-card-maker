# Production Deployment Guide

## Overview

This guide covers deploying the Silhouette Card Maker API to production using industry-standard practices and tools.

## ⚠️ Important Security Notes

- **Never use the Flask development server in production**
- **Always use HTTPS in production**
- **Set strong JWT secrets and database passwords**
- **Enable authentication in production**
- **Use a reverse proxy (Nginx) for better security and performance**

## Deployment Options

### 1. Gunicorn (Recommended)

Gunicorn is a Python WSGI HTTP Server that's perfect for production deployment.

#### Quick Start

```bash
# Install Gunicorn
pip install gunicorn

# Start the application
gunicorn -c gunicorn.conf.py start_production:app
```

#### Configuration

The `gunicorn.conf.py` file contains production-optimized settings:

- **Workers**: Automatically set to `CPU cores * 2 + 1`
- **Timeout**: 30 seconds for requests
- **Memory Management**: Workers restart after 1000 requests
- **Logging**: Comprehensive access and error logs
- **Security**: Non-root user execution

#### Environment Variables

```bash
# Core settings
export FLASK_ENV=production
export DATABASE_URL=sqlite:///app.db
export JWT_SECRET_KEY=your-very-secure-secret-key
export REQUIRE_AUTH=true

# Gunicorn settings
export GUNICORN_WORKERS=4
export GUNICORN_TIMEOUT=60
export GUNICORN_BIND=0.0.0.0:5000
```

### 2. Docker Deployment

#### Quick Start

```bash
# Build and run with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Features

- **Containerized**: Isolated environment
- **Nginx Reverse Proxy**: SSL termination and load balancing
- **Health Checks**: Automatic container health monitoring
- **Volume Mounts**: Persistent database and uploads
- **Auto-restart**: Container restarts on failure

### 3. Systemd Service

#### Setup

```bash
# Copy service file
sudo cp silhouette-card-maker.service /etc/systemd/system/

# Edit the service file with your paths
sudo nano /etc/systemd/system/silhouette-card-maker.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable silhouette-card-maker
sudo systemctl start silhouette-card-maker

# Check status
sudo systemctl status silhouette-card-maker
```

#### Service Management

```bash
# Start service
sudo systemctl start silhouette-card-maker

# Stop service
sudo systemctl stop silhouette-card-maker

# Restart service
sudo systemctl restart silhouette-card-maker

# View logs
sudo journalctl -u silhouette-card-maker -f
```

### 4. Automated Deployment

#### Using the Deployment Script

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
- Create virtual environment
- Install dependencies
- Initialize database
- Test the application
- Set up systemd service
- Provide deployment options

## Production Configuration

### Environment Variables

Create a `.env` file with production settings:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-very-secure-secret-key

# Database Configuration
DATABASE_URL=sqlite:///app.db

# JWT Configuration
JWT_SECRET_KEY=your-very-secure-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Authentication
REQUIRE_AUTH=true
BCRYPT_LOG_ROUNDS=12

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# File Upload
MAX_CONTENT_LENGTH=67108864
UPLOAD_FOLDER=uploads

# Logging
LOG_LEVEL=WARNING
```

### Security Checklist

- [ ] **Strong Secrets**: Use cryptographically secure random strings
- [ ] **HTTPS Only**: Configure SSL/TLS certificates
- [ ] **Authentication**: Enable `REQUIRE_AUTH=true`
- [ ] **CORS**: Restrict to your frontend domain only
- [ ] **Firewall**: Configure proper firewall rules
- [ ] **Database**: Use strong database passwords (if using PostgreSQL/MySQL)
- [ ] **File Permissions**: Ensure proper file ownership and permissions
- [ ] **Logging**: Set up log rotation and monitoring
- [ ] **Backups**: Implement regular database backups
- [ ] **Updates**: Keep dependencies updated

### Nginx Configuration

The included `nginx.conf` provides:

- **SSL Termination**: HTTPS with modern TLS protocols
- **Security Headers**: XSS protection, content type options, etc.
- **Rate Limiting**: API rate limiting to prevent abuse
- **File Upload Limits**: 64MB maximum file size
- **Proxy Settings**: Proper headers for Flask application
- **Static Files**: Efficient serving of static assets

#### SSL Setup

```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# For production, use Let's Encrypt
certbot --nginx -d your-domain.com
```

## Monitoring and Logging

### Application Logs

```bash
# Gunicorn logs
tail -f /var/log/gunicorn/access.log
tail -f /var/log/gunicorn/error.log

# Systemd logs
sudo journalctl -u silhouette-card-maker -f

# Docker logs
docker-compose logs -f silhouette-card-maker
```

### Health Monitoring

The application provides a health check endpoint:

```bash
# Check application health
curl https://your-domain.com/api/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "2.0.0",
  "service": "Silhouette Card Maker API"
}
```

### Performance Monitoring

Access performance metrics (admin only):

```bash
# Get metrics (requires admin token)
curl -H "Authorization: Bearer <admin_token>" \
     https://your-domain.com/api/metrics
```

## Scaling Considerations

### Horizontal Scaling

For high-traffic deployments:

1. **Load Balancer**: Use Nginx or HAProxy
2. **Multiple Workers**: Increase Gunicorn workers
3. **Database**: Consider PostgreSQL for better concurrency
4. **Caching**: Implement Redis for session storage
5. **CDN**: Use CloudFlare or AWS CloudFront

### Vertical Scaling

- **CPU**: More cores = more Gunicorn workers
- **Memory**: Monitor memory usage with `/api/metrics`
- **Storage**: Ensure adequate disk space for uploads and database

## Backup Strategy

### Database Backup

```bash
# SQLite backup
cp instance/app.db backups/app-$(date +%Y%m%d-%H%M%S).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="/opt/backups"
APP_DIR="/opt/silhouette-card-maker"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR
cp $APP_DIR/instance/app.db $BACKUP_DIR/app-$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "app-*.db" -mtime +30 -delete
```

### File Uploads Backup

```bash
# Backup uploads directory
tar -czf backups/uploads-$(date +%Y%m%d-%H%M%S).tar.gz uploads/
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   sudo chown -R www-data:www-data /opt/silhouette-card-maker
   sudo chmod -R 755 /opt/silhouette-card-maker
   ```

2. **Database Locked**
   ```bash
   # Check for running processes
   lsof instance/app.db
   # Kill any hanging processes
   ```

3. **Memory Issues**
   ```bash
   # Monitor memory usage
   curl -H "Authorization: Bearer <token>" /api/metrics
   # Restart workers if needed
   sudo systemctl restart silhouette-card-maker
   ```

4. **SSL Certificate Issues**
   ```bash
   # Test SSL configuration
   openssl s_client -connect your-domain.com:443
   ```

### Performance Tuning

1. **Gunicorn Workers**
   ```bash
   # Calculate optimal workers: (2 x CPU cores) + 1
   export GUNICORN_WORKERS=8  # For 4-core server
   ```

2. **Database Optimization**
   ```bash
   # SQLite optimization
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA cache_size=10000;
   ```

3. **Nginx Optimization**
   ```nginx
   # Increase worker connections
   worker_connections 2048;
   
   # Enable gzip compression
   gzip on;
   gzip_types text/plain application/json;
   ```

## Support

For production issues:

1. Check application logs
2. Monitor system resources
3. Test health endpoints
4. Review security configuration
5. Check database integrity

The application is designed to be production-ready with proper monitoring, logging, and security features.
