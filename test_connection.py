#!/usr/bin/env python3
"""
Test PostgreSQL connection with different password formats.
"""

import psycopg2
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test different connection formats
CONNECTION_TESTS = [
    {
        'name': 'URL-encoded password (@ as %40)',
        'url': 'postgresql://dreambees:Zy2H%40sg0Ykl6ngf@108.175.14.173:5432/dream_'
    },
    {
        'name': 'Original password with @',
        'url': 'postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_'
    },
    {
        'name': 'Password with quotes',
        'url': 'postgresql://dreambees:"Zy2H%@sg0Ykl6ngf"@108.175.14.173:5432/dream_'
    },
    {
        'name': 'Direct connection parameters',
        'params': {
            'host': '108.175.14.173',
            'port': 5432,
            'database': 'dream_',
            'user': 'dreambees',
            'password': 'Zy2H%@sg0Ykl6ngf'
        }
    }
]

def test_url_connection(url):
    """Test connection using URL format"""
    try:
        parsed = urlparse(url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password
        )
        conn.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def test_direct_connection(params):
    """Test connection using direct parameters"""
    try:
        conn = psycopg2.connect(**params)
        conn.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    """Test all connection methods"""
    logger.info("Testing PostgreSQL connection methods...")
    
    for i, test in enumerate(CONNECTION_TESTS, 1):
        logger.info(f"\n--- Test {i}: {test['name']} ---")
        
        if 'url' in test:
            success, message = test_url_connection(test['url'])
        else:
            success, message = test_direct_connection(test['params'])
        
        if success:
            logger.info(f"✓ {test['name']}: {message}")
        else:
            logger.error(f"✗ {test['name']}: {message}")
    
    logger.info("\n--- Connection Test Summary ---")
    logger.info("If all tests fail, please check:")
    logger.info("1. PostgreSQL server is running")
    logger.info("2. Username and password are correct")
    logger.info("3. Database exists")
    logger.info("4. User has proper permissions")
    logger.info("5. Firewall allows connections on port 5432")

if __name__ == '__main__':
    main()
