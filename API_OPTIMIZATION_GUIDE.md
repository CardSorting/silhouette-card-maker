# PDF Generation API Optimization Guide

## Overview

This guide documents the enhanced and optimized PDF generation API for the Silhouette Card Maker. The optimized API includes significant performance improvements, new features, and better resource management.

## New Features

### 1. Asynchronous PDF Generation
- **Background Task Processing**: Large PDF generation requests can be processed asynchronously
- **Task Status Tracking**: Monitor progress of long-running operations
- **Non-blocking API**: Submit requests and check status separately

### 2. Streaming Output
- **Large File Support**: Stream PDFs directly to clients without loading entire file into memory
- **Memory Efficient**: Reduces memory usage for large PDFs
- **Progressive Download**: Clients can start downloading before generation completes

### 3. Intelligent Caching
- **Request-based Caching**: Cache results based on input parameters and file hashes
- **Automatic Cache Management**: LRU eviction and size-based cleanup
- **Cache Statistics**: Monitor cache performance and hit rates

### 4. Parallel Processing
- **Multi-threaded File Processing**: Process multiple files simultaneously
- **Optimized Image Handling**: Parallel image loading and processing
- **Resource-aware Processing**: Adjust parallelism based on system resources

### 5. Enhanced Performance Monitoring
- **Real-time Metrics**: Track API performance and resource usage
- **Memory Management**: Automatic memory optimization based on usage
- **Processing Time Estimation**: Predict completion times for large requests

### 6. Advanced Rate Limiting
- **Granular Limits**: Different limits for different operations
- **User-based Limiting**: Per-user rate limiting for authenticated requests
- **Burst Protection**: Prevent system overload during traffic spikes

## API Endpoints

### Core Generation Endpoints

#### POST `/api/generate` (Optimized)
Enhanced PDF generation with new optimization features.

**New Parameters:**
- `use_cache` (boolean): Enable/disable caching (default: true)
- `stream_output` (boolean): Use streaming for large files (default: false)
- `async_generation` (boolean): Process asynchronously (default: false)

**Response for Async Generation:**
```json
{
  "success": true,
  "message": "PDF generation started",
  "task_id": "uuid-string",
  "status_url": "/api/tasks/uuid-string",
  "request_id": "uuid-string"
}
```

#### GET `/api/tasks/{task_id}`
Get the status of an asynchronous task.

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "running|success|failure|cancelled",
  "progress": 75.5,
  "created_at": "2024-01-15T10:30:00.000Z",
  "started_at": "2024-01-15T10:30:05.000Z",
  "completed_at": "2024-01-15T10:32:30.000Z",
  "result": {
    "file_path": "/tmp/cards.pdf",
    "file_size": 2048576
  }
}
```

#### GET `/api/tasks/{task_id}/result`
Download the result file from a completed task.

#### DELETE `/api/tasks/{task_id}`
Cancel a running task.

### Cache Management Endpoints

#### POST `/api/cache/clear` (Admin)
Clear the PDF cache.

#### GET `/api/cache/stats` (Admin)
Get cache statistics.

**Response:**
```json
{
  "cache_size_mb": 45.2,
  "max_size_mb": 100.0,
  "entry_count": 23,
  "hit_rate": "N/A"
}
```

### Enhanced Monitoring

#### GET `/api/health`
Enhanced health check with performance metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "2.1.0",
  "service": "Silhouette Card Maker API (Optimized)",
  "memory_usage": {
    "rss": 123456789,
    "vms": 234567890,
    "percent": 45.2
  },
  "performance_metrics": {
    "total_requests": 1250,
    "success_rate": 98.4,
    "avg_response_time": 2.3
  }
}
```

#### GET `/api/metrics` (Admin)
Comprehensive performance metrics.

## Configuration

### Environment Variables

```bash
# Performance Settings
PDF_CACHE_SIZE_MB=100
MAX_CONCURRENT_TASKS=4
TASK_TIMEOUT_SECONDS=300

# Memory Management
MEMORY_WARNING_THRESHOLD=80.0
MEMORY_CRITICAL_THRESHOLD=90.0

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=1000
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_PDF_GENERATION_PER_HOUR=50

# Redis for Async Tasks
REDIS_URL=redis://localhost:6379/0

# Feature Flags
ENABLE_CACHING=true
ENABLE_STREAMING=true
ENABLE_ASYNC_GENERATION=true
ENABLE_PARALLEL_PROCESSING=true
```

### Configuration Classes

The optimized API includes multiple configuration classes:

- `OptimizedConfig`: Base configuration
- `DevelopmentConfig`: Development settings with relaxed limits
- `ProductionConfig`: Production settings with strict limits
- `TestingConfig`: Testing settings with fast cleanup

## Performance Optimizations

### 1. Memory Management
- **Automatic Memory Monitoring**: Track memory usage during processing
- **Dynamic Quality Adjustment**: Reduce quality/PPI when memory is low
- **Garbage Collection**: Force cleanup after large operations
- **Memory-aware Processing**: Adjust chunk sizes based on available memory

### 2. File Processing
- **Parallel File Upload**: Process multiple files simultaneously
- **Streaming Processing**: Process files without loading entirely into memory
- **Optimized Chunk Sizes**: Use optimal chunk sizes based on file characteristics
- **Progressive Processing**: Start output before all files are processed

### 3. Caching Strategy
- **Content-based Hashing**: Generate cache keys from file content and parameters
- **LRU Eviction**: Remove least recently used entries when cache is full
- **Size-based Management**: Limit cache size to prevent memory issues
- **Automatic Cleanup**: Remove expired entries automatically

### 4. Request Optimization
- **Parameter Validation**: Validate all parameters before processing
- **Early Error Detection**: Fail fast on invalid requests
- **Resource Estimation**: Estimate processing requirements upfront
- **Queue Management**: Manage concurrent requests efficiently

## Error Handling

### Enhanced Error Responses
All error responses now include:
- `error`: Human-readable error message
- `code`: Machine-readable error code
- `request_id`: Unique identifier for tracking
- `field`: Specific field that caused the error (when applicable)

### Error Codes
- `NO_FILES`: No files provided
- `INVALID_PARAMETER`: Invalid parameter value
- `INVALID_SIZE`: Invalid card or paper size
- `NO_FRONT_IMAGES`: No valid front images provided
- `FILE_TOO_LARGE`: File size exceeds limit
- `GENERATION_ERROR`: PDF generation failed
- `TASK_NOT_FOUND`: Async task not found
- `TASK_NOT_COMPLETED`: Task not completed successfully
- `CACHE_ERROR`: Cache operation failed

## Usage Examples

### Synchronous Generation with Caching
```bash
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@card1.png" \
  -F "front_files=@card2.png" \
  -F "card_size=standard" \
  -F "paper_size=letter" \
  -F "use_cache=true"
```

### Asynchronous Generation
```bash
# Start generation
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@cards.zip" \
  -F "async_generation=true"

# Check status
curl http://localhost:5000/api/tasks/{task_id}

# Download result
curl http://localhost:5000/api/tasks/{task_id}/result -o cards.pdf
```

### Streaming Large Files
```bash
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@large_deck.zip" \
  -F "stream_output=true" \
  -o cards.pdf
```

## Monitoring and Maintenance

### Health Checks
- Monitor memory usage and performance metrics
- Set up alerts for high memory usage or error rates
- Track cache hit rates and adjust cache size accordingly

### Cache Management
- Regularly clear cache to free up disk space
- Monitor cache statistics to optimize cache size
- Consider cache warming for frequently requested combinations

### Task Management
- Monitor active tasks and their completion rates
- Set up alerts for failed tasks
- Clean up old completed tasks regularly

## Migration Guide

### From Original API
1. Update client code to handle new response formats
2. Add error handling for new error codes
3. Consider using async generation for large requests
4. Enable caching for repeated requests

### Configuration Changes
1. Add Redis configuration for async tasks
2. Update rate limiting settings
3. Configure cache size based on available disk space
4. Set memory thresholds based on server capacity

## Best Practices

### For API Consumers
1. **Use Async for Large Requests**: Use async generation for requests with >50 files or >50MB
2. **Enable Caching**: Always enable caching for repeated requests with same parameters
3. **Handle Errors Gracefully**: Implement proper error handling for all error codes
4. **Monitor Task Status**: For async requests, poll status endpoint until completion
5. **Use Streaming for Large Files**: Enable streaming for files >100MB

### For API Administrators
1. **Monitor Memory Usage**: Set up alerts for high memory usage
2. **Tune Cache Size**: Adjust cache size based on usage patterns
3. **Configure Rate Limits**: Set appropriate rate limits based on server capacity
4. **Regular Cleanup**: Schedule regular cleanup of old tasks and cache entries
5. **Performance Monitoring**: Monitor API performance and adjust settings accordingly

## Troubleshooting

### Common Issues

#### High Memory Usage
- Reduce cache size
- Enable memory optimization
- Use streaming for large files
- Reduce concurrent task limit

#### Slow Performance
- Enable caching
- Use parallel processing
- Optimize image quality/PPI
- Check Redis performance

#### Task Failures
- Check Redis connectivity
- Verify file permissions
- Monitor disk space
- Check memory limits

### Debug Mode
Enable debug mode for detailed logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## Future Enhancements

### Planned Features
1. **Distributed Processing**: Support for multiple worker nodes
2. **Advanced Caching**: Redis-based distributed caching
3. **WebSocket Updates**: Real-time progress updates via WebSocket
4. **Batch Processing**: Process multiple requests in batches
5. **Advanced Analytics**: Detailed usage analytics and reporting

### Performance Targets
- **Response Time**: <2 seconds for cached requests
- **Throughput**: >100 requests/minute
- **Memory Usage**: <80% of available memory
- **Cache Hit Rate**: >70% for repeated requests
