# Database Clearing Guide

This guide explains how to clear the PostgreSQL database before performing a fresh migration.

## Overview

The database clearing functionality allows you to completely remove all existing data and tables from the PostgreSQL database, preparing it for a fresh migration or installation.

## ⚠️ Important Warning

**This operation will permanently delete ALL data in the PostgreSQL database!**

Make sure you have backups of any important data before proceeding.

## Available Scripts

### 1. Automated Clearing Script
```bash
./clear_database.sh
```

**Features:**
- Checks for Python and PostgreSQL dependencies
- Installs missing dependencies automatically
- Provides colored output and progress indicators
- Handles errors gracefully

### 2. Python Clearing Script
```bash
python clear_postgresql.py
```

**Features:**
- Direct database clearing without additional checks
- Detailed logging of all operations
- Interactive confirmation prompt
- Can be run with `FORCE_CLEAR=true` to skip confirmation

### 3. Integrated Migration Script
```bash
./migrate.sh
```

**Features:**
- Automatically clears database before migration
- Complete migration process in one command
- Includes all necessary steps

## What Gets Cleared

The clearing process removes:

1. **All Tables**: Every table in the `public` schema
2. **All Data**: All rows in all tables
3. **All Sequences**: Auto-increment sequences
4. **All Indexes**: Custom indexes (except system indexes)
5. **Foreign Key Constraints**: All relationships between tables
6. **Schema Objects**: Custom schema objects

## What Gets Preserved

The clearing process preserves:

1. **Database Structure**: The database itself remains intact
2. **User Permissions**: Database user accounts and permissions
3. **System Tables**: PostgreSQL system tables and schemas
4. **Configuration**: Database configuration settings

## Usage Examples

### Clear Database Before Fresh Migration
```bash
# Clear the database
./clear_database.sh

# Then run fresh migration
./migrate.sh
```

### Clear Database Manually
```bash
# Interactive mode (asks for confirmation)
python clear_postgresql.py

# Non-interactive mode (skips confirmation)
FORCE_CLEAR=true python clear_postgresql.py
```

### Clear and Initialize in One Step
```bash
# This will clear, then initialize
./migrate.sh
```

## Verification

After clearing, the script verifies that:

1. **No Tables Remain**: All user tables are removed
2. **No Sequences Remain**: All custom sequences are removed
3. **Schema is Clean**: Only system objects remain

## Error Handling

The clearing script handles common errors:

- **Connection Issues**: Provides clear error messages for connection problems
- **Permission Errors**: Explains permission requirements
- **Partial Failures**: Continues with other operations if some fail
- **Verification Failures**: Reports any remaining objects

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```
psycopg2.OperationalError: permission denied for database
```

**Solution:**
- Ensure the database user has DROP privileges
- Check that the user owns the tables being dropped
- Verify database connection parameters

#### 2. Connection Refused
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
- Verify PostgreSQL is running
- Check connection parameters in the script
- Ensure firewall allows connections

#### 3. Tables Still Exist After Clearing
```
Warning: 2 tables still exist: ['users', 'api_logs']
```

**Solution:**
- Check for foreign key constraints preventing drops
- Verify user has sufficient privileges
- Run the script again with elevated privileges

### Debug Mode

Enable detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python clear_postgresql.py
```

## Safety Features

### Confirmation Prompt
By default, the script asks for confirmation:
```
Are you sure you want to clear the database? (yes/no):
```

### Force Mode
Skip confirmation for automated scripts:
```bash
FORCE_CLEAR=true python clear_postgresql.py
```

### Verification
The script verifies the database is completely empty after clearing.

## Integration with Migration

The clearing functionality is integrated into the migration process:

1. **Clear Database**: Remove all existing data
2. **Install Dependencies**: Ensure PostgreSQL driver is available
3. **Initialize Database**: Create fresh tables and schema
4. **Migrate Data**: Transfer data from SQLite (if exists)
5. **Test Setup**: Verify everything works correctly

## Best Practices

### Before Clearing
1. **Backup Important Data**: Export any data you need to preserve
2. **Stop Applications**: Ensure no applications are using the database
3. **Verify Permissions**: Confirm you have DROP privileges
4. **Test Connection**: Verify you can connect to the database

### After Clearing
1. **Verify Empty State**: Confirm all tables are removed
2. **Run Tests**: Use the test script to verify the database is ready
3. **Initialize Fresh**: Run the initialization script
4. **Monitor Logs**: Check for any errors during the process

## Recovery

If you accidentally clear the database:

1. **Restore from Backup**: If you have a recent backup
2. **Re-run Migration**: Use the migration script to restore from SQLite
3. **Manual Recovery**: Recreate tables and data manually

## Security Considerations

- **Access Control**: Ensure only authorized users can run clearing scripts
- **Audit Logging**: Consider logging clearing operations for audit trails
- **Backup Strategy**: Implement regular backups before clearing operations
- **Environment Isolation**: Use separate databases for development/testing

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify database connectivity and permissions
3. Review the troubleshooting section above
4. Test with a small database first
5. Contact your database administrator if needed
