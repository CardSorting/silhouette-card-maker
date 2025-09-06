# Celery Integration Guide

## Overview

This guide covers the comprehensive Celery integration for the Silhouette Card Maker application. The integration provides automatic worker startup, health monitoring, graceful shutdown, and production-ready deployment options.

## Features

### 🚀 Automatic Worker Startup
- Celery workers start automatically with the Flask application
- Configurable via environment variables
- Fallback to threading mode if Celery is unavailable

### 🔍 Health Monitoring
- Continuous worker health monitoring
- Automatic restart on failure
- Configurable restart limits and delays
- Process monitoring with resource usage tracking

### 🛑 Graceful Shutdown
- Proper signal handling for SIGTERM and SIGINT
- Graceful worker shutdown with timeout
- Clean resource cleanup

### 📊 Monitoring & Management
- REST API endpoints for worker management
- Real-time worker status and statistics
- Task queue monitoring and management
- Health check endpoints

## Architecture

### Components

1. **CeleryWorkerManager** (`app/celery_manager.py`)
   - Comprehensive worker lifecycle management
   - Health monitoring and auto-restart
   - Process monitoring and resource tracking
   - Graceful shutdown handling

2. **Celery Application** (`celery_app.py`)
   - Production-ready Celery configuration
   - Task definitions with error handling
   - Signal handlers for worker events
   - Comprehensive logging

3. **API Routes** (`app/api/celery_routes.py`)
   - Worker management endpoints
   - Health monitoring endpoints
   - Task queue management
   - Statistics and monitoring

4. **Startup Scripts**
   - `start_with_celery.py` - Production startup
   - `start_dev_with_celery.py` - Development startup
   - `celery_worker.py` - Standalone worker

## Configuration

### Environment Variables

```bash
# Celery Worker Configuration
START_CELERY_WORKER=true                    # Enable automatic worker startup
CELERY_CONCURRENCY=2                        # Number of worker processes
CELERY_QUEUES=pdf_generation,pdf_offset,default  # Queues to process
CELERY_MAX_RESTARTS=5                       # Maximum restart attempts
CELERY_RESTART_DELAY=5                      # Delay between restarts (seconds)
CELERY_HEALTH_CHECK_INTERVAL=30             # Health check interval (seconds)
CELERY_WORKER_TIMEOUT=300                   # Worker timeout (seconds)

# Redis Configuration
REDIS_URL=redis://:password@host:port/db
REDIS_HOST=108.175.14.173
REDIS_PORT=6379
REDIS_PASSWORD=MyStrongPassword123!
REDIS_DB=0
```

### Queue Configuration

The application uses three main queues:

- **pdf_generation**: PDF generation tasks
- **pdf_offset**: PDF offset tasks  
- **default**: General tasks and health checks

## Usage

### Development Mode

Start the application with integrated Celery worker:

```bash
# Using the development startup script
python start_dev_with_celery.py

# Or enable auto-start in regular run
START_CELERY_WORKER=true python run.py
```

### Production Mode

#### Option 1: Integrated Startup
```bash
python start_with_celery.py
```

#### Option 2: Separate Services
```bash
# Start Flask application
gunicorn -c gunicorn.conf.py start_production:app

# Start Celery worker separately
python celery_app.py
```

#### Option 3: Docker Compose
```bash
docker-compose up -d
```

This starts:
- Flask application
- Celery worker service
- Redis service
- Nginx reverse proxy (optional)

## API Endpoints

### Worker Management (Admin Only)

- `GET /api/celery/status` - Get worker status
- `POST /api/celery/start` - Start worker
- `POST /api/celery/stop` - Stop worker
- `POST /api/celery/restart` - Restart worker
- `GET /api/celery/health` - Health check (public)
- `GET /api/celery/tasks` - Get active tasks
- `GET /api/celery/stats` - Get worker statistics
- `POST /api/celery/purge` - Purge task queues

### Example API Usage

```bash
# Check worker status
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/celery/status

# Start worker
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"concurrency": 2, "queues": ["pdf_generation", "default"]}' \
     http://localhost:5000/api/celery/start

# Health check (no auth required)
curl http://localhost:5000/api/celery/health
```

## Monitoring

### Health Monitoring

The system continuously monitors worker health:

- Process status checking
- Heartbeat monitoring
- Resource usage tracking
- Automatic restart on failure

### Logging

Comprehensive logging is provided:

- Worker lifecycle events
- Task execution logs
- Error handling and retries
- Performance metrics

### Metrics

Available metrics include:

- Worker uptime
- Restart count
- Task completion rates
- Resource usage (CPU, memory)
- Queue depths

## Error Handling

### Automatic Retry

Tasks include automatic retry logic:

- Transient failures are retried up to 2 times
- Exponential backoff between retries
- Permanent failures are logged and reported

### Fallback Mode

If Celery is unavailable:

- Tasks fall back to threading mode
- Application continues to function
- Graceful degradation of performance

## Production Deployment

### Docker Deployment

The Docker Compose configuration includes:

- Separate Celery worker service
- Redis service with persistence
- Health checks for all services
- Proper service dependencies

### Systemd Service

For systemd deployment:

```ini
[Unit]
Description=Silhouette Card Maker with Celery
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/python start_with_celery.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Load Balancing

For high availability:

- Deploy multiple worker instances
- Use Redis for task distribution
- Configure load balancer for Flask app
- Monitor worker health across instances

## Troubleshooting

### Common Issues

1. **Worker Not Starting**
   - Check Redis connection
   - Verify environment variables
   - Check logs for errors

2. **Tasks Not Processing**
   - Verify queue configuration
   - Check worker status
   - Monitor Redis connectivity

3. **High Memory Usage**
   - Adjust `worker_max_memory_per_child`
   - Monitor task memory usage
   - Consider task optimization

### Debug Mode

Enable debug logging:

```bash
export CELERY_LOG_LEVEL=debug
python start_dev_with_celery.py
```

### Health Checks

Monitor worker health:

```bash
# Check worker status
curl http://localhost:5000/api/celery/health

# Get detailed status
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/celery/status
```

## Performance Tuning

### Worker Configuration

Optimize based on your server:

```bash
# High-performance server
CELERY_CONCURRENCY=8
CELERY_QUEUES=pdf_generation,pdf_generation,pdf_generation,pdf_offset,default

# Memory-constrained server
CELERY_CONCURRENCY=1
CELERY_MAX_RESTARTS=3
```

### Redis Configuration

Optimize Redis for your workload:

```bash
# Redis configuration
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Security Considerations

- Worker management endpoints require admin authentication
- Health check endpoints are public (read-only)
- Redis should be secured with authentication
- Use HTTPS in production
- Monitor worker access and task execution

## Migration from Threading

The system is designed for seamless migration:

1. Existing threading-based tasks continue to work
2. Celery tasks are used when available
3. Automatic fallback ensures no service interruption
4. Gradual migration of tasks to Celery is supported

## Support

For issues or questions:

1. Check the logs for error messages
2. Verify Redis connectivity
3. Test with the health check endpoints
4. Review the configuration settings
5. Check the troubleshooting section above
