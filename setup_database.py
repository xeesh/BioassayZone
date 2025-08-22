#!/usr/bin/env python3
"""
Database Setup Script for Bioassay Zone Measurement Tool
USP-81 / 21 CFR Part 11 Compliant System

This script helps you set up the PostgreSQL database for local development.
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2 import sql
from werkzeug.security import generate_password_hash

def check_postgresql_installed():
    """Check if PostgreSQL is installed and running"""
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ PostgreSQL is installed:", result.stdout.strip())
            return True
    except FileNotFoundError:
        pass
    
    print("✗ PostgreSQL is not installed or not in PATH")
    return False

def check_postgresql_running():
    """Check if PostgreSQL service is running"""
    try:
        # Try to connect to default PostgreSQL service
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            database='postgres'
        )
        conn.close()
        print("✓ PostgreSQL service is running")
        return True
    except psycopg2.Error:
        print("✗ PostgreSQL service is not running or not accessible")
        return False

def create_database(db_name='bioassay_db', db_user='bioassay_user', db_password='bioassay_pass'):
    """Create database and user for the bioassay application"""
    try:
        # Connect to PostgreSQL as superuser
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create database user
        try:
            cursor.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(db_user)),
                [db_password]
            )
            print(f"✓ Created user: {db_user}")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"✓ User {db_user} already exists")
            else:
                raise
        
        # Create database
        try:
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(db_name),
                    sql.Identifier(db_user)
                )
            )
            print(f"✓ Created database: {db_name}")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"✓ Database {db_name} already exists")
            else:
                raise
        
        # Grant privileges
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(db_name),
                sql.Identifier(db_user)
            )
        )
        print(f"✓ Granted privileges to {db_user}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database setup failed: {e}")
        return False

def create_env_file(db_name='bioassay_db', db_user='bioassay_user', db_password='bioassay_pass'):
    """Create .env file with database configuration"""
    env_content = f"""# Bioassay Database Configuration
DATABASE_URL=postgresql://{db_user}:{db_password}@localhost:5432/{db_name}
PGHOST=localhost
PGPORT=5432
PGUSER={db_user}
PGPASSWORD={db_password}
PGDATABASE={db_name}

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=true
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ Created .env file with database configuration")
    print("  Make sure to change the SECRET_KEY in production!")

def main():
    print("=== Bioassay Database Setup ===")
    print()
    
    # Check prerequisites
    if not check_postgresql_installed():
        print("\nPlease install PostgreSQL first:")
        print("  Windows: Download from https://www.postgresql.org/download/windows/")
        print("  macOS:   brew install postgresql")
        print("  Ubuntu:  sudo apt-get install postgresql postgresql-contrib")
        return 1
    
    if not check_postgresql_running():
        print("\nPlease start PostgreSQL service:")
        print("  Windows: Start 'postgresql' service from Services")
        print("  macOS:   brew services start postgresql")
        print("  Ubuntu:  sudo systemctl start postgresql")
        return 1
    
    print("\n=== Creating Database ===")
    
    # Get database configuration
    db_name = input("Database name (bioassay_db): ").strip() or 'bioassay_db'
    db_user = input("Database user (bioassay_user): ").strip() or 'bioassay_user'
    db_password = input("Database password (bioassay_pass): ").strip() or 'bioassay_pass'
    
    print(f"\nCreating database '{db_name}' with user '{db_user}'...")
    
    if create_database(db_name, db_user, db_password):
        create_env_file(db_name, db_user, db_password)
        
        print("\n=== Setup Complete ===")
        print("Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Install Python dependencies: pip install -r requirements.txt")
        print("2. Run the application: python app.py")
        print("3. Open http://localhost:5000 in your browser")
        print("4. Login with default admin account:")
        print("   Username: admin")
        print("   Password: Admin123!")
        print("\n⚠️  Change the admin password after first login!")
        return 0
    else:
        print("\n✗ Database setup failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())