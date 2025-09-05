# Silhouette Card Maker - Improved Flask Backend

## Overview

This is an improved Flask backend for the Silhouette Card Maker project, specifically designed to work seamlessly with a Next.js frontend. The backend provides a robust REST API with comprehensive error handling, rate limiting, authentication, and performance monitoring.

## Key Improvements

### 🚀 **API-First Design**
- RESTful API endpoints with consistent JSON responses
- Comprehensive error handling with proper HTTP status codes
- Request ID tracking for better debugging
- OpenAPI-style documentation

### 🔒 **Security & Performance**
- CORS support for Next.js frontend integration
- Rate limiting to prevent abuse
- Optional API key authentication
- Memory monitoring and optimization
- File upload validation and size limits

### 📊 **Monitoring & Logging**
- Performance metrics tracking
- Memory usage monitoring
- Structured logging with configurable levels
- Health check endpoints

### 🏗️ **Architecture**
- Blueprint-based modular structure
- Environment-based configuration
- Production-ready error handling
- Clean separation of concerns

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example configuration:
```bash
cp config.env.example .env
```

Edit `.env` with your settings:
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
API_KEY=your-api-key-here
REQUIRE_AUTH=false
```

### 3. Run the Application

```bash
python run.py
```

The API will be available at: **http://localhost:5000**

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Get configuration options |
| `GET` | `/api/version` | Get version information |
| `GET` | `/api/metrics` | Get performance metrics |

### PDF Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Generate PDF with cards |
| `POST` | `/api/offset` | Apply offset correction to PDF |

### Plugins

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/plugins` | Get available plugins |
| `POST` | `/api/plugins/{game}/{format}` | Run plugin to fetch cards |

## Usage Examples

### Generate PDF with JavaScript (Next.js)

```javascript
const formData = new FormData();
formData.append('front_files', frontImageFile1);
formData.append('front_files', frontImageFile2);
formData.append('card_size', 'standard');
formData.append('paper_size', 'letter');
formData.append('name', 'my_cards');

const response = await fetch('/api/generate', {
  method: 'POST',
  body: formData,
});

if (response.ok) {
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'cards.pdf';
  a.click();
}
```

### Generate PDF with cURL

```bash
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@card1.jpg" \
  -F "front_files=@card2.jpg" \
  -F "card_size=standard" \
  -F "paper_size=letter" \
  -F "name=my_cards" \
  --output cards.pdf
```

### Check API Health

```bash
curl http://localhost:5000/api/health
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | `development` |
| `SECRET_KEY` | Flask secret key | `your-secret-key-here` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `API_KEY` | API key for authentication | None |
| `REQUIRE_AUTH` | Enable API key authentication | `false` |
| `MAX_CONTENT_LENGTH` | Max file size in bytes | `67108864` (64MB) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis URL for rate limiting | `memory://` |

### Rate Limiting

Default rate limits:
- General endpoints: 100 requests/minute
- PDF generation: 10 requests/minute
- PDF offset: 20 requests/minute
- Plugin operations: 5 requests/minute

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "request_id": "unique-request-identifier"
}
```

### Common Error Codes

- `NO_FILES`: No files provided
- `INVALID_PARAMETER`: Invalid parameter value
- `INVALID_SIZE`: Invalid card or paper size
- `NO_FRONT_IMAGES`: No valid front images provided
- `FILE_TOO_LARGE`: File size exceeds limit
- `GENERATION_ERROR`: PDF generation failed
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
- `AUTH_REQUIRED`: API key required
- `INVALID_API_KEY`: Invalid API key

## File Upload Guidelines

### Supported File Types
- Images: PNG, JPG, JPEG, GIF, BMP, TIFF, WebP
- Documents: TXT, JSON (for decklists)

### File Size Limits
- Maximum file size: 64MB per file
- Maximum total request size: 64MB

### Best Practices
1. Use high-quality images (300+ DPI recommended)
2. Ensure images are properly oriented
3. Use consistent image dimensions for best results
4. Compress large images before upload to reduce processing time

## Performance Monitoring

The API includes built-in performance monitoring:

### Memory Usage
- Real-time memory usage tracking
- Automatic garbage collection after operations
- Memory-aware image processing optimization

### Request Metrics
- Total requests count
- Success/failure rates
- Average response times
- Memory usage history

### Access Metrics
```bash
curl http://localhost:5000/api/metrics
```

## Production Deployment

### 1. Environment Setup

```env
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
CORS_ORIGINS=https://your-frontend-domain.com
API_KEY=your-production-api-key
REQUIRE_AUTH=true
LOG_LEVEL=WARNING
```

### 2. Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### 3. Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

### 4. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-api-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Development

### Project Structure

```
app/
├── __init__.py              # Application factory
├── config.py               # Configuration classes
├── auth.py                 # Authentication system
├── performance.py          # Performance monitoring
├── utils.py                # Utility functions
├── api/                    # API blueprint
│   ├── __init__.py
│   └── routes.py           # API endpoints
├── main/                   # Main blueprint
│   ├── __init__.py
│   └── routes.py           # Web interface
├── offset/                 # Offset blueprint
│   ├── __init__.py
│   └── routes.py           # PDF offset functionality
└── calibration/            # Calibration blueprint
    ├── __init__.py
    └── routes.py           # Calibration PDF generation
```

### Adding New Endpoints

1. Create the endpoint in the appropriate blueprint
2. Add rate limiting decorators if needed
3. Add performance monitoring decorators
4. Update API documentation
5. Add tests

### Testing

```bash
# Run basic health check
curl http://localhost:5000/api/health

# Test PDF generation
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@test_image.jpg" \
  -F "card_size=standard" \
  --output test.pdf
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Check `CORS_ORIGINS` configuration
2. **File Upload Fails**: Check file size limits and extensions
3. **Rate Limit Exceeded**: Implement exponential backoff in frontend
4. **Memory Issues**: Monitor `/api/metrics` endpoint
5. **Authentication Errors**: Verify API key configuration

### Logs

Check application logs for detailed error information:
```bash
tail -f app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the API documentation
2. Review the troubleshooting section
3. Create an issue in the repository
4. Check the logs for detailed error information
