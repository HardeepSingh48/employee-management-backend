#!/usr/bin/env python3
"""
Standalone script to create attendance performance indexes
Use this if you're not using Flask-Migrate or want direct SQL execution
"""

import os
import sys
from sqlalchemy import create_engine, text
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - reads from environment variables
def get_database_url():
    """Build database URL from environment variables"""
    # First try DATABASE_URL if it exists
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
    
    # Otherwise build from individual components
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    
    if not db_password:
        raise ValueError("Database password not found. Set DB_PASSWORD environment variable.")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

DATABASE_URL = get_database_url()

# Index definitions
INDEXES = [
    {
        'name': 'idx_attendance_employee_date',
        'table': 'attendance',
        'columns': ['employee_id', 'attendance_date'],
        'description': 'Composite index for employee + date lookups (most important)'
    },
    {
        'name': 'idx_attendance_date',
        'table': 'attendance',
        'columns': ['attendance_date'],
        'description': 'Index for date-based queries'
    },
    {
        'name': 'idx_attendance_employee',
        'table': 'attendance',
        'columns': ['employee_id'],
        'description': 'Index for employee-based queries'
    },
    {
        'name': 'idx_employee_site_id',
        'table': 'employees',
        'columns': ['site_id', 'employee_id'],
        'description': 'Index for supervisor site filtering'
    },
    {
        'name': 'idx_employee_employee_id',
        'table': 'employees',
        'columns': ['employee_id'],
        'description': 'Index for employee_id lookups'
    },
    {
        'name': 'idx_attendance_status',
        'table': 'attendance',
        'columns': ['attendance_status'],
        'description': 'Optional: Index for status queries'
    }
]

@contextmanager
def get_db_connection():
    """Create database connection with proper cleanup"""
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except Exception as e:
        trans.rollback()
        logger.error(f"Transaction rolled back due to error: {e}")
        raise
    finally:
        conn.close()
        engine.dispose()

def check_index_exists(conn, index_name, table_name):
    """Check if index already exists"""
    try:
        # PostgreSQL check
        if 'postgresql' in DATABASE_URL.lower():
            query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = :index_name 
                    AND tablename = :table_name
                )
            """)
            result = conn.execute(query, {'index_name': index_name, 'table_name': table_name})
            return result.scalar()
        
        # MySQL check
        elif 'mysql' in DATABASE_URL.lower():
            query = text("""
                SELECT COUNT(*) > 0 FROM information_schema.statistics 
                WHERE index_name = :index_name 
                AND table_name = :table_name 
                AND table_schema = DATABASE()
            """)
            result = conn.execute(query, {'index_name': index_name, 'table_name': table_name})
            return result.scalar()
        
        # SQLite check
        elif 'sqlite' in DATABASE_URL.lower():
            query = text(f"PRAGMA index_info({index_name})")
            try:
                result = conn.execute(query)
                return len(result.fetchall()) > 0
            except:
                return False
        
        return False
    except Exception as e:
        logger.warning(f"Could not check if index {index_name} exists: {e}")
        return False

def create_index(conn, index_info):
    """Create a single index"""
    name = index_info['name']
    table = index_info['table']
    columns = index_info['columns']
    description = index_info['description']
    
    # Check if index already exists
    if check_index_exists(conn, name, table):
        logger.info(f"Index {name} already exists, skipping...")
        return True
    
    try:
        # Build CREATE INDEX statement
        columns_str = ', '.join(columns)
        
        # Use IF NOT EXISTS if supported (PostgreSQL 9.5+, SQLite)
        if 'postgresql' in DATABASE_URL.lower() or 'sqlite' in DATABASE_URL.lower():
            sql = f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns_str})"
        else:
            sql = f"CREATE INDEX {name} ON {table} ({columns_str})"
        
        logger.info(f"Creating index: {name} - {description}")
        logger.info(f"SQL: {sql}")
        
        conn.execute(text(sql))
        logger.info(f"✓ Successfully created index: {name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create index {name}: {e}")
        return False

def drop_index(conn, index_info):
    """Drop a single index (for rollback)"""
    name = index_info['name']
    table = index_info['table']
    
    try:
        # Check if index exists before dropping
        if not check_index_exists(conn, name, table):
            logger.info(f"Index {name} doesn't exist, skipping drop...")
            return True
        
        # Build DROP INDEX statement
        if 'postgresql' in DATABASE_URL.lower():
            sql = f"DROP INDEX IF EXISTS {name}"
        elif 'mysql' in DATABASE_URL.lower():
            sql = f"DROP INDEX {name} ON {table}"
        elif 'sqlite' in DATABASE_URL.lower():
            sql = f"DROP INDEX IF EXISTS {name}"
        else:
            sql = f"DROP INDEX {name}"
        
        logger.info(f"Dropping index: {name}")
        conn.execute(text(sql))
        logger.info(f"✓ Successfully dropped index: {name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to drop index {name}: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    try:
        with get_db_connection() as conn:
            # Simple test query
            if 'postgresql' in DATABASE_URL.lower():
                conn.execute(text("SELECT 1"))
            elif 'mysql' in DATABASE_URL.lower():
                conn.execute(text("SELECT 1"))
            else:
                conn.execute(text("SELECT 1"))
            
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False

def create_all_indexes():
    """Create all attendance performance indexes"""
    logger.info("Starting attendance index creation...")
    logger.info(f"Database URL: {DATABASE_URL.split('@')[0]}@***")  # Hide credentials
    
    # Test connection first
    if not test_database_connection():
        logger.error("Cannot proceed without database connection")
        return False
    
    success_count = 0
    total_count = len(INDEXES)
    
    try:
        with get_db_connection() as conn:
            for index_info in INDEXES:
                if create_index(conn, index_info):
                    success_count += 1
        
        logger.info(f"\n=== Index Creation Summary ===")
        logger.info(f"Total indexes: {total_count}")
        logger.info(f"Successfully created: {success_count}")
        logger.info(f"Failed: {total_count - success_count}")
        
        if success_count == total_count:
            logger.info("✓ All indexes created successfully!")
            return True
        else:
            logger.warning(f"⚠ Only {success_count}/{total_count} indexes created")
            return False
            
    except Exception as e:
        logger.error(f"Critical error during index creation: {e}")
        return False

def drop_all_indexes():
    """Drop all indexes (rollback function)"""
    logger.info("Rolling back - dropping all indexes...")
    
    success_count = 0
    total_count = len(INDEXES)
    
    try:
        with get_db_connection() as conn:
            # Drop in reverse order
            for index_info in reversed(INDEXES):
                if drop_index(conn, index_info):
                    success_count += 1
        
        logger.info(f"Successfully dropped {success_count}/{total_count} indexes")
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"Error during index rollback: {e}")
        return False

def main():
    """Main execution function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'create':
            success = create_all_indexes()
            sys.exit(0 if success else 1)
            
        elif command == 'drop':
            success = drop_all_indexes()
            sys.exit(0 if success else 1)
            
        elif command == 'test':
            success = test_database_connection()
            sys.exit(0 if success else 1)
            
        else:
            print("Usage: python create_indexes.py [create|drop|test]")
            print("  create - Create all attendance performance indexes")
            print("  drop   - Drop all attendance performance indexes") 
            print("  test   - Test database connection")
            sys.exit(1)
    else:
        # Default action: create indexes
        success = create_all_indexes()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()