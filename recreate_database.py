#!/usr/bin/env python
"""
Recreate the gis database
"""
import psycopg2

def recreate_database():
    """Recreate the gis database"""
    try:
        print("Connecting to PostgreSQL server...")
        
        # Connect to postgres database to create gis database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='gis',
            password='gis1234',
            database='postgres'  # Connect to postgres db for admin operations
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected successfully!")
        
        # Check if gis database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'gis'")
        exists = cursor.fetchone()
        
        if exists:
            print("Database 'gis' already exists")
        else:
            print("Creating database 'gis'...")
            cursor.execute('CREATE DATABASE "gis"')
            print("Database 'gis' created successfully!")
        
        cursor.close()
        conn.close()
        
        # Test connection to gis database
        print("Testing connection to gis database...")
        test_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='gis',
            password='gis1234',
            database='gis'
        )
        test_conn.close()
        print("✓ Successfully connected to gis database!")
        
        return True
        
    except Exception as e:
        print(f"Failed to recreate database: {e}")
        return False

if __name__ == "__main__":
    success = recreate_database()
    if success:
        print("\n✓ Database is ready!")
    else:
        print("\n✗ Database setup failed!")