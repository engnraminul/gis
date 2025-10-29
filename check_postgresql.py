#!/usr/bin/env python
"""
Check PostgreSQL users and databases
"""
import psycopg2

def check_postgresql_setup():
    """Check PostgreSQL setup and users"""
    print("=== Checking PostgreSQL Setup ===")
    
    # Common PostgreSQL configurations to try
    configs = [
        {'user': 'postgres', 'password': 'postgres', 'host': 'localhost', 'port': 5432},
        {'user': 'postgres', 'password': '', 'host': 'localhost', 'port': 5432},
        {'user': 'gis', 'password': 'gis1234', 'host': 'localhost', 'port': 5432},
    ]
    
    for i, config in enumerate(configs):
        print(f"\n{i+1}. Testing connection with user: {config['user']}")
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database='postgres'
            )
            
            cursor = conn.cursor()
            
            print(f"   ✓ Connected successfully as {config['user']}")
            
            # Check if this user can create databases
            cursor.execute("SELECT rolcreatedb FROM pg_roles WHERE rolname = %s", (config['user'],))
            result = cursor.fetchone()
            if result:
                can_create_db = result[0]
                print(f"   Can create databases: {can_create_db}")
            
            # List all databases
            cursor.execute("SELECT datname FROM pg_database ORDER BY datname")
            databases = cursor.fetchall()
            print(f"   Available databases: {[db[0] for db in databases]}")
            
            # Check if gis database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'gis'")
            gis_exists = cursor.fetchone()
            print(f"   'gis' database exists: {gis_exists is not None}")
            
            # If this user can create databases, try to create gis
            if result and result[0]:  # rolcreatedb is True
                print(f"   Attempting to create 'gis' database...")
                try:
                    cursor.execute('CREATE DATABASE "gis"')
                    print(f"   ✓ Successfully created 'gis' database!")
                    
                    cursor.close()
                    conn.close()
                    return config  # Return working config
                    
                except psycopg2.errors.DuplicateDatabase:
                    print(f"   'gis' database already exists")
                    cursor.close()
                    conn.close()
                    return config  # Return working config
                except Exception as create_error:
                    print(f"   Failed to create 'gis' database: {create_error}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
    
    return None

if __name__ == "__main__":
    working_config = check_postgresql_setup()
    if working_config:
        print(f"\n✓ Found working PostgreSQL configuration: {working_config['user']}")
    else:
        print(f"\n✗ No working PostgreSQL configuration found!")