# Silhouette Card Maker API Documentation

## Overview

The Silhouette Card Maker API is a RESTful service for generating card PDFs with registration marks for silhouette cutting machines. This API is designed to work seamlessly with a Next.js frontend.

## Base URL

- Development: `http://localhost:5000/api`
- Production: `https://your-domain.com/api`

## Authentication

The API supports JWT-based authentication with the following features:

- **JWT Access Tokens**: Short-lived tokens (1 hour) for API access
- **JWT Refresh Tokens**: Long-lived tokens (30 days) for token renewal
- **Token Blacklisting**: Secure logout with token revocation
- **Role-based Access**: Admin and user roles with different permissions
- **Password Security**: Bcrypt hashing with configurable rounds

### Authentication Flow

1. **Register/Login**: Get access and refresh tokens
2. **API Requests**: Include access token in Authorization header
3. **Token Refresh**: Use refresh token to get new access token
4. **Logout**: Revoke tokens to invalidate them

### Headers

Include the JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Rate Limiting

- Default: 100 requests per minute per IP
- Configurable via environment variables

## Endpoints

### Health Check

#### GET `/api/health`

Check the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "2.0.0",
  "service": "Silhouette Card Maker API"
}
```

### Configuration

#### GET `/api/config`

Get available configuration options for the API.

**Response:**
```json
{
  "card_sizes": ["standard", "japanese", "poker", "bridge", "tarot"],
  "paper_sizes": ["letter", "a4", "tabloid", "a3", "archb"],
  "max_file_size": 67108864,
  "allowed_extensions": ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"],
  "plugin_games": {
    "mtg": ["simple", "mtga", "mtgo", "archidekt", "deckstats", "moxfield", "scryfall_json"],
    "yugioh": ["ydke", "ydk"],
    "lorcana": ["dreamborn"]
  }
}
```

### Authentication Endpoints

#### POST `/api/auth/register`

Register a new user account.

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-15T10:30:00.000Z"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### POST `/api/auth/login`

Authenticate user and get tokens.

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "username_or_email": "johndoe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### POST `/api/auth/refresh`

Refresh access token using refresh token.

**Headers:** `Authorization: Bearer <refresh_token>`

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### POST `/api/auth/logout`

Logout user by revoking current token.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "Logout successful"
}
```

#### GET `/api/auth/profile`

Get current user profile.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-15T10:30:00.000Z",
    "last_login": "2024-01-15T12:00:00.000Z",
    "api_usage_count": 42
  }
}
```

### PDF Generation

#### POST `/api/generate`

Generate a PDF with card images and registration marks.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `front_files` (file[]): Front card images (required)
- `back_files` (file[]): Back card images (optional)
- `double_sided_files` (file[]): Double-sided back images (optional)
- `card_size` (string): Card size - default: "standard"
- `paper_size` (string): Paper size - default: "letter"
- `only_fronts` (boolean): Generate only front pages - default: false
- `crop` (string): Crop specification (optional)
- `extend_corners` (integer): Extend corners by pixels - default: 0
- `ppi` (integer): Pixels per inch - default: 300
- `quality` (integer): JPEG quality (1-100) - default: 75
- `skip_indices` (string): Comma-separated indices to skip (optional)
- `name` (string): Output filename prefix (optional)
- `output_images` (boolean): Output images instead of PDF - default: false
- `load_offset` (boolean): Load saved offset - default: false

**Success Response:**
- **Content-Type:** `application/pdf` (for PDF output)
- **Content-Type:** `application/json` (for image output)

**Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

**Error Codes:**
- `NO_FILES`: No files provided
- `INVALID_PARAMETER`: Invalid parameter value
- `INVALID_SIZE`: Invalid card or paper size
- `NO_FRONT_IMAGES`: No valid front images provided
- `FILE_TOO_LARGE`: File size exceeds limit
- `GENERATION_ERROR`: PDF generation failed

### PDF Offset Correction

#### POST `/api/offset`

Apply offset correction to an existing PDF.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `pdf_file` (file): PDF file to offset (required)
- `x_offset` (integer): X-axis offset in pixels - default: 0
- `y_offset` (integer): Y-axis offset in pixels - default: 0
- `ppi` (integer): Pixels per inch - default: 300

**Success Response:**
- **Content-Type:** `application/pdf`

**Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

### Plugins

#### GET `/api/plugins`

Get available plugins and their supported formats.

**Response:**
```json
{
  "plugins": {
    "mtg": ["simple", "mtga", "mtgo", "archidekt", "deckstats", "moxfield", "scryfall_json"],
    "yugioh": ["ydke", "ydk"],
    "lorcana": ["dreamborn"]
  },
  "total_plugins": 3
}
```

#### POST `/api/plugins/{game}/{format}`

Run a plugin to fetch card images from a decklist.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `decklist_file` (file): Decklist file (required)
- `plugin_*` (string): Plugin-specific options (optional)

**Success Response:**
```json
{
  "success": true,
  "message": "Plugin completed successfully",
  "plugin_output": "Plugin output text",
  "images_generated": 60,
  "request_id": "uuid"
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

### Version Information

#### GET `/api/version`

Get API version and feature information.

**Response:**
```json
{
  "version": "2.0.0",
  "app": "Silhouette Card Maker Flask (Refactored)",
  "api_version": "2.0.0",
  "features": [
    "PDF Generation",
    "Image Output",
    "Plugin System",
    "Offset Correction",
    "Calibration",
    "Multiple Card Sizes",
    "Multiple Paper Sizes",
    "Blueprint Architecture",
    "REST API",
    "CORS Support"
  ]
}
```

## Error Handling

All API endpoints return consistent error responses with the following structure:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "request_id": "unique-request-identifier"
}
```

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (endpoint or resource not found)
- `405`: Method Not Allowed
- `413`: Payload Too Large (file size exceeded)
- `500`: Internal Server Error

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

## CORS Configuration

The API is configured to accept requests from:
- Development: `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:3001`
- Production: Configurable via `CORS_ORIGINS` environment variable

## Environment Variables

- `FLASK_ENV`: Environment (development, production, testing)
- `SECRET_KEY`: Flask secret key
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `MAX_CONTENT_LENGTH`: Maximum file size in bytes
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `REDIS_URL`: Redis URL for rate limiting (optional)

## Example Usage

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

## Support

For issues and questions, please refer to the project repository or create an issue.
