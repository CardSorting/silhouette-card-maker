# Authentication System - Silhouette Card Maker API

## Overview

The Silhouette Card Maker API now includes a comprehensive, industry-standard authentication system built with Flask-JWT-Extended, Flask-Login, and SQLAlchemy. This system provides secure user management, JWT token-based authentication, and role-based access control.

## Features

### 🔐 **Security Features**
- **JWT Tokens**: Industry-standard JSON Web Tokens for stateless authentication
- **Bcrypt Password Hashing**: Secure password storage with configurable rounds
- **Token Blacklisting**: Secure logout with token revocation
- **Role-based Access Control**: Admin and user roles with different permissions
- **Rate Limiting**: User-specific rate limiting with configurable multipliers

### 🏗️ **Architecture**
- **Flask-JWT-Extended**: JWT token management and validation
- **Flask-Login**: Session management and user loading
- **SQLAlchemy**: Database ORM with user and token models
- **Marshmallow**: Input validation and serialization
- **Bcrypt**: Secure password hashing

### 📊 **User Management**
- User registration and login
- Profile management
- Password change functionality
- Admin user management
- API usage tracking

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database (SQLite - No Setup Required!)

```bash
python migrate.py init
```

This will:
- **Automatically create** `app.db` SQLite file in your project root
- Create database tables
- Create default admin user (`admin`/`admin123`)
- Create test user in development mode (`testuser`/`test123`)

**No database server setup needed!** SQLite is file-based and works out of the box.

### 3. Configure Environment

Copy and customize the configuration:
```bash
cp config.env.example .env
```

Key settings for authentication:
```env
# Enable authentication
REQUIRE_AUTH=true

# JWT Configuration
JWT_SECRET_KEY=your-secure-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1 hour
JWT_REFRESH_TOKEN_EXPIRES=2592000  # 30 days

# Database (SQLite - Simple file-based database)
DATABASE_URL=sqlite:///app.db
```

### 4. Start the Application

```bash
python run.py
```

## Authentication Flow

### 1. User Registration

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
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
    "is_admin": false
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. User Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "johndoe",
    "password": "SecurePass123!"
  }'
```

### 3. API Requests with Authentication

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Authorization: Bearer <access_token>" \
  -F "front_files=@card1.jpg" \
  -F "card_size=standard"
```

### 4. Token Refresh

```bash
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

### 5. Logout

```bash
curl -X POST http://localhost:5000/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

## Database Models

### User Model

```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    api_usage_count = db.Column(db.Integer, default=0)
    rate_limit_multiplier = db.Column(db.Float, default=1.0)
```

### TokenBlacklist Model

```python
class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
```

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/auth/register` | Register new user | No |
| `POST` | `/api/auth/login` | Login user | No |
| `POST` | `/api/auth/refresh` | Refresh access token | Refresh Token |
| `POST` | `/api/auth/logout` | Logout user | Access Token |
| `POST` | `/api/auth/logout-all` | Logout from all devices | Access Token |
| `GET` | `/api/auth/profile` | Get user profile | Access Token |
| `PUT` | `/api/auth/profile` | Update user profile | Access Token |
| `POST` | `/api/auth/change-password` | Change password | Access Token |
| `GET` | `/api/auth/users` | List all users | Admin |
| `PUT` | `/api/auth/users/{id}` | Update user | Admin |

### Protected API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/generate` | Generate PDF | User |
| `POST` | `/api/offset` | PDF offset correction | User |
| `POST` | `/api/plugins/{game}/{format}` | Run plugin | User |
| `GET` | `/api/metrics` | Get performance metrics | Admin |

## Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- Maximum 128 characters
- At least one lowercase letter
- At least one uppercase letter
- At least one digit
- At least one special character (@$!%*?&)

## User Roles

### Regular User
- Can generate PDFs
- Can use plugins
- Can manage their own profile
- Rate limited to standard limits

### Admin User
- All regular user permissions
- Can view performance metrics
- Can manage other users
- Can adjust user rate limits
- Can view all users

## Rate Limiting

The system includes intelligent rate limiting:

- **Base Rate**: 100 requests per minute
- **User-specific Multipliers**: Admins can adjust individual user limits
- **Resource-intensive Operations**: Lower limits for PDF generation and plugins
- **Token-based Identification**: Authenticated users get higher limits

## Security Best Practices

### 1. Environment Configuration

```env
# Production settings
FLASK_ENV=production
REQUIRE_AUTH=true
JWT_SECRET_KEY=your-very-secure-secret-key
DATABASE_URL=postgresql://user:password@localhost/production_db
```

### 2. Password Security

- Use strong, unique passwords
- Enable password complexity requirements
- Consider implementing password expiration policies
- Use HTTPS in production

### 3. Token Management

- Access tokens expire in 1 hour
- Refresh tokens expire in 30 days
- Tokens are blacklisted on logout
- Use secure token storage in frontend

### 4. Database Security

- Use strong database passwords
- Enable SSL for database connections
- Regular database backups
- Monitor for suspicious activity

## Database Management

### Initialize Database

```bash
python migrate.py init
```

### Reset Database (WARNING: Deletes all data)

```bash
python migrate.py reset
```

### List Users

```bash
python migrate.py users
```

### Create User

```bash
python migrate.py create-user
```

## Frontend Integration (Next.js)

### 1. Install JWT Library

```bash
npm install js-cookie
```

### 2. Authentication Service

```javascript
// services/auth.js
const API_BASE = 'http://localhost:5000/api';

export const authService = {
  async login(username, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: username, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      // Store tokens securely
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data;
    }
    throw new Error('Login failed');
  },

  async register(username, email, password) {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data;
    }
    throw new Error('Registration failed');
  },

  getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  },

  async refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');
    
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${refreshToken}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      return data.access_token;
    }
    throw new Error('Token refresh failed');
  },

  async logout() {
    const token = localStorage.getItem('access_token');
    if (token) {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
};
```

### 3. API Client with Authentication

```javascript
// services/api.js
import { authService } from './auth';

export const apiClient = {
  async request(endpoint, options = {}) {
    const url = `http://localhost:5000/api${endpoint}`;
    const headers = {
      ...authService.getAuthHeaders(),
      ...options.headers
    };

    let response = await fetch(url, { ...options, headers });

    // Handle token expiration
    if (response.status === 401) {
      try {
        await authService.refreshToken();
        headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        // Redirect to login
        window.location.href = '/login';
        throw error;
      }
    }

    return response;
  },

  async generatePDF(formData) {
    return this.request('/generate', {
      method: 'POST',
      body: formData
    });
  }
};
```

## Troubleshooting

### Common Issues

1. **"Token has expired"**
   - Use the refresh token to get a new access token
   - Implement automatic token refresh in your frontend

2. **"User not found or inactive"**
   - Check if the user account is active
   - Verify the user exists in the database

3. **"Admin access required"**
   - Ensure the user has admin privileges
   - Check the `is_admin` field in the database

4. **Database connection errors**
   - Verify the `DATABASE_URL` configuration
   - Ensure the database server is running
   - Check database permissions

### Debug Commands

```bash
# Check database status
python migrate.py users

# View application logs
tail -f app.log

# Test authentication
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email": "admin", "password": "admin123"}'
```

## Production Deployment

### 1. Environment Variables

```env
FLASK_ENV=production
REQUIRE_AUTH=true
JWT_SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:password@localhost/production_db
BCRYPT_LOG_ROUNDS=12
```

### 2. Database Setup

```bash
# Create production database
createdb silhouette_card_maker_prod

# Run migrations
python migrate.py init
```

### 3. Security Checklist

- [ ] Change default admin password
- [ ] Use strong JWT secret key
- [ ] Enable HTTPS
- [ ] Configure secure database connection
- [ ] Set up monitoring and logging
- [ ] Implement backup strategy
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable CORS for production domains only

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check application logs
4. Create an issue in the repository

The authentication system is designed to be secure, scalable, and easy to integrate with modern frontend frameworks like Next.js.
