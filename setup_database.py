#!/usr/bin/env python3
"""
Database setup script for BioassayZone
Handles both SQLite (development) and PostgreSQL (production) setup
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_sqlite():
    """Setup SQLite database for development"""
    try:
        db_path = 'instance/bioassay.db'
        os.makedirs('instance', exist_ok=True)
        
        # Create SQLite database
        conn = sqlite3.connect(db_path)
        conn.close()
        
        logger.info(f"SQLite database created at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup SQLite: {e}")
        return False

def setup_postgresql():
    """Setup PostgreSQL database for production"""
    try:
        # Get environment variables
        db_host = os.getenv('PGHOST', 'localhost')
        db_port = os.getenv('PGPORT', '5432')
        db_user = os.getenv('PGUSER', 'postgres')
        db_password = os.getenv('PGPASSWORD')
        db_name = os.getenv('PGDATABASE', 'bioassay_db')
        
        if not db_password:
            logger.error("PGPASSWORD environment variable not set")
            logger.info("Please set PGPASSWORD environment variable or use .env file")
            return False
        
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database='postgres'  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        db_exists = cursor.fetchone()
        
        if not db_exists:
            # Create database
            cursor.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Database '{db_name}' created successfully")
        else:
            logger.info(f"Database '{db_name}' already exists")
        
        cursor.close()
        conn.close()
        
        # Now connect to the new database and create user
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create bioassay user if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'bioassay_user'")
        user_exists = cursor.fetchone()
        
        if not user_exists:
            cursor.execute("CREATE USER bioassay_user WITH PASSWORD 'bioassay_pass'")
            logger.info("User 'bioassay_user' created successfully")
        else:
            logger.info("User 'bioassay_user' already exists")
        
        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO bioassay_user")
        cursor.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO bioassay_user")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bioassay_user")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bioassay_user")
        
        # Set default privileges for future tables
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bioassay_user")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bioassay_user")
        
        cursor.close()
        conn.close()
        
        logger.info("PostgreSQL setup completed successfully")
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        logger.info("Make sure PostgreSQL is running and credentials are correct")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        db_url = os.getenv('DATABASE_URL')
        if db_url and db_url.startswith('postgresql://'):
            # Test PostgreSQL connection
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL connection successful: {version}")
                return True
        else:
            # Test SQLite connection
            db_path = 'instance/bioassay.db'
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.close()
                logger.info("SQLite connection successful")
                return True
            else:
                logger.error("SQLite database file not found")
                return False
                
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def create_env_file():
    """Create .env file with database configuration"""
    try:
        env_content = """# BioassayZone Environment Configuration

# Database Configuration
DATABASE_URL=postgresql://bioassay_user:bioassay_pass@localhost:5432/bioassay_db

# PostgreSQL Environment Variables
PGHOST=localhost
PGPORT=5432
PGUSER=bioassay_user
PGPASSWORD=bioassay_pass
PGDATABASE=bioassay_db

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_ENV=production
FLASK_DEBUG=0

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bioassay.log
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        logger.info(".env file created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("Starting BioassayZone database setup...")
    
    # Check if we're using PostgreSQL or SQLite
    db_url = os.getenv('DATABASE_URL')
    
    if db_url and db_url.startswith('postgresql://'):
        logger.info("PostgreSQL configuration detected")
        
        # Try to setup PostgreSQL
        if setup_postgresql():
            logger.info("PostgreSQL setup completed")
        else:
            logger.error("PostgreSQL setup failed, falling back to SQLite")
            if setup_sqlite():
                logger.info("SQLite setup completed as fallback")
            else:
                logger.error("Both PostgreSQL and SQLite setup failed")
                sys.exit(1)
    else:
        logger.info("No PostgreSQL configuration, setting up SQLite")
        if setup_sqlite():
            logger.info("SQLite setup completed")
        else:
            logger.error("SQLite setup failed")
            sys.exit(1)
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        create_env_file()
    
    # Test database connection
    if test_database_connection():
        logger.info("Database setup completed successfully!")
        logger.info("You can now run the application with: python app.py")
    else:
        logger.error("Database connection test failed")
        sys.exit(1)

if __name__ == '__main__':
    main()