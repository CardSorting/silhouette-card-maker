# Celery Quick Start Guide

## 🚀 Quick Start

### Development Mode (Recommended)

Start the application with integrated Celery worker:

```bash
# Start with integrated Celery worker
python start_dev_with_celery.py
```

This will start both Flask and Celery worker automatically with proper monitoring and health checks.

### Production Mode

#### Option 1: Integrated Startup
```bash
python start_with_celery.py
```

#### Option 2: Docker Compose
```bash
docker-compose up -d
```

#### Option 3: Separate Services
```bash
# Terminal 1: Start Flask app
gunicorn -c gunicorn.conf.py start_production:app

# Terminal 2: Start Celery worker
python celery_app.py
```

## 🔧 Configuration

Set these environment variables to enable Celery:

```bash
# Enable automatic worker startup
export START_CELERY_WORKER=true

# Configure worker
export CELERY_CONCURRENCY=2
export CELERY_QUEUES=pdf_generation,pdf_offset,default

# Redis configuration
export REDIS_URL=redis://:MyStrongPassword123!@108.175.14.173:6379/0
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5000/api/celery/health
```

### Worker Status (Admin)
```bash
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/celery/status
```

### Start/Stop Worker (Admin)
```bash
# Start worker
curl -X POST -H "Authorization: Bearer <token>" http://localhost:5000/api/celery/start

# Stop worker
curl -X POST -H "Authorization: Bearer <token>" http://localhost:5000/api/celery/stop
```

## 🧪 Testing

Test the Celery integration:

```bash
python test_celery_integration.py
```

## 📚 Documentation

For detailed documentation, see:
- [CELERY_INTEGRATION_GUIDE.md](CELERY_INTEGRATION_GUIDE.md) - Comprehensive guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API documentation

## 🆘 Troubleshooting

### Worker Not Starting
1. Check Redis connection: `redis-cli ping`
2. Verify environment variables
3. Check logs for errors

### Tasks Not Processing
1. Check worker status: `curl http://localhost:5000/api/celery/health`
2. Verify queue configuration
3. Monitor Redis connectivity

### Fallback Mode
If Celery is unavailable, the application automatically falls back to threading mode and continues to function normally.

## ✨ Features

- ✅ Automatic worker startup with Flask app
- ✅ Health monitoring and auto-restart
- ✅ Graceful shutdown handling
- ✅ REST API for worker management
- ✅ Production-ready Docker configuration
- ✅ Comprehensive error handling and retry logic
- ✅ Fallback to threading mode if Celery unavailable
