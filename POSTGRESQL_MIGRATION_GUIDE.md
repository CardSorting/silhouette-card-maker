# PostgreSQL Migration Guide

This guide will help you migrate the Silhouette Card Maker application from SQLite to PostgreSQL.

## Overview

The migration includes:
- Updated configuration files to use PostgreSQL
- Migration scripts to transfer data from SQLite to PostgreSQL
- Database initialization scripts
- Test scripts to verify the migration

## Prerequisites

1. **PostgreSQL Server**: Ensure PostgreSQL is running and accessible
2. **Database Access**: You need credentials to create databases and tables
3. **Python Dependencies**: Install the required PostgreSQL driver

## Step 1: Install Dependencies

Install the PostgreSQL driver:

```bash
pip install psycopg2-binary==2.9.9
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Step 2: Database Configuration

The application is now configured to use PostgreSQL by default. The connection string is:

```
postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_
```

### Environment Variables

You can override the database URL using environment variables:

```bash
export DATABASE_URL="postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_"
export TEST_DATABASE_URL="postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_test"
```

## Step 3: Clear Existing Database (Optional but Recommended)

If you have existing data in PostgreSQL that you want to clear before migration:

### Option A: Automated Clearing
```bash
./clear_database.sh
```

### Option B: Manual Clearing
```bash
python clear_postgresql.py
```

This will:
- Drop all existing tables and data
- Remove all sequences and indexes
- Clean up the database schema
- Prepare for fresh migration

⚠️ **Warning**: This will permanently delete all existing data in the PostgreSQL database!

## Step 4: Initialize PostgreSQL Database

### Option A: Fresh Installation

If you're starting fresh (no existing SQLite data):

```bash
python init_postgresql.py
```

This script will:
- Create the database if it doesn't exist
- Initialize Flask-Migrate
- Create all tables
- Create an admin user (username: `admin`, password: `admin123`)

### Option B: Migrate from SQLite

If you have existing SQLite data to migrate:

1. **First, initialize the PostgreSQL database:**
   ```bash
   python init_postgresql.py
   ```

2. **Then migrate your data:**
   ```bash
   python migrate_to_postgresql.py
   ```

The migration script will:
- Connect to your existing SQLite database (`instance/app.db`)
- Extract all data and table schemas
- Create corresponding tables in PostgreSQL
- Transfer all data
- Verify the migration was successful

## Step 5: Test the Migration

Run the test script to verify everything is working:

```bash
python test_postgresql.py
```

This will test:
- Database connectivity
- Table creation
- User operations
- API log operations
- Basic performance

## Step 6: Start the Application

Once the migration is complete, start the application:

```bash
python run.py
```

Or for production:

```bash
gunicorn -c gunicorn.conf.py run:app
```

## Configuration Details

### Database Connection Settings

The application now uses optimized PostgreSQL connection settings:

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,      # Verify connections before use
    'pool_recycle': 300,        # Recycle connections every 5 minutes
    'pool_size': 10,            # Maintain 10 connections in pool
    'max_overflow': 20          # Allow up to 20 additional connections
}
```

### Performance Optimizations

PostgreSQL-specific optimizations include:
- Connection pooling for better performance
- Proper indexing on frequently queried columns
- Optimized data types for PostgreSQL
- Better handling of auto-incrementing primary keys

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
- Verify PostgreSQL is running
- Check the connection string
- Ensure firewall allows connections on port 5432
- Verify username/password are correct

#### 2. Database Does Not Exist
```
psycopg2.OperationalError: database "dream_" does not exist
```

**Solution:**
- Run `python init_postgresql.py` to create the database
- Or manually create the database in PostgreSQL

#### 3. Permission Denied
```
psycopg2.OperationalError: permission denied for database
```

**Solution:**
- Ensure the user has CREATE DATABASE privileges
- Check user permissions in PostgreSQL

#### 4. Migration Fails
```
Failed to migrate data for table users
```

**Solution:**
- Check that SQLite database exists at `instance/app.db`
- Verify PostgreSQL connection
- Check for data type incompatibilities
- Review migration logs for specific errors

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python test_postgresql.py
```

## Data Type Mappings

The migration script automatically converts SQLite data types to PostgreSQL equivalents:

| SQLite Type | PostgreSQL Type |
|-------------|-----------------|
| INTEGER     | INTEGER         |
| TEXT        | TEXT            |
| REAL        | REAL            |
| BLOB        | BYTEA           |
| BOOLEAN     | BOOLEAN         |
| DATETIME    | TIMESTAMP       |

## Performance Considerations

### Indexing

The migration creates indexes for better performance:

```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_jwt_blacklist_jti ON jwt_blacklist(jti);
```

### Connection Pooling

PostgreSQL connection pooling is configured for optimal performance:
- **Pool Size**: 10 connections
- **Max Overflow**: 20 additional connections
- **Pool Recycle**: 300 seconds (5 minutes)
- **Pre-ping**: Enabled to verify connections

## Backup and Recovery

### Backup PostgreSQL Database

```bash
pg_dump -h 108.175.14.173 -U dreambees -d dream_ > backup.sql
```

### Restore from Backup

```bash
psql -h 108.175.14.173 -U dreambees -d dream_ < backup.sql
```

## Monitoring

### Check Database Status

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'dream_';

-- Check database size
SELECT pg_size_pretty(pg_database_size('dream_'));

-- Check table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Application Monitoring

The application includes built-in monitoring:
- Health check endpoint: `GET /api/health`
- Performance metrics: `GET /api/metrics` (admin only)
- Database connection status in health checks

## Rollback Plan

If you need to rollback to SQLite:

1. **Update configuration:**
   ```python
   SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
   ```

2. **Remove PostgreSQL-specific settings:**
   ```python
   SQLALCHEMY_ENGINE_OPTIONS = {
       'pool_pre_ping': True,
       'pool_recycle': 300,
   }
   ```

3. **Restart the application**

## Security Considerations

### Database Security

1. **Change Default Passwords**: Update the admin user password
2. **Use Environment Variables**: Store sensitive data in environment variables
3. **Network Security**: Ensure PostgreSQL is only accessible from trusted networks
4. **SSL/TLS**: Consider enabling SSL for database connections

### Application Security

1. **Update Secret Keys**: Change default secret keys in production
2. **Rate Limiting**: Configure appropriate rate limits
3. **Authentication**: Ensure proper authentication is enabled
4. **Input Validation**: All inputs are validated before database operations

## Support

If you encounter issues during migration:

1. Check the logs for detailed error messages
2. Verify all prerequisites are met
3. Test database connectivity manually
4. Review the troubleshooting section above

For additional support, check the application logs and PostgreSQL logs for more detailed error information.
