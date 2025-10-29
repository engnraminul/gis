#!/usr/bin/env python
"""
Debug script to inspect backup files and test PostgreSQL connectivity
"""
import os
import zipfile
import psycopg2
import subprocess
import tempfile
from datetime import datetime

def inspect_backup_file(backup_path):
    """Inspect the contents of a backup file"""
    print(f"Inspecting backup file: {backup_path}")
    
    if not os.path.exists(backup_path):
        print(f"Backup file does not exist: {backup_path}")
        return
    
    print(f"File size: {os.path.getsize(backup_path)} bytes")
    
    try:
        with zipfile.ZipFile(backup_path, 'r') as zip_file:
            file_list = zip_file.namelist()
            print(f"Files in backup ({len(file_list)} total):")
            for file_name in file_list:
                file_info = zip_file.getinfo(file_name)
                print(f"  - {file_name} ({file_info.file_size} bytes)")
                
                # Check if it's a database file
                if file_name == 'database.sql':
                    print(f"    Found PostgreSQL database file!")
                    # Read first few lines
                    with zip_file.open(file_name) as db_file:
                        content = db_file.read(1000).decode('utf-8', errors='ignore')
                        print(f"    First 1000 characters:")
                        print(f"    {content[:200]}...")
    except Exception as e:
        print(f"Error reading backup file: {e}")

def test_postgresql_connection():
    """Test PostgreSQL connection and list tables"""
    print("\nTesting PostgreSQL connection...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='gis',
            user='gis',
            password='gis1234'
        )
        print("✓ PostgreSQL connection successful!")
        
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} rows")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False

def test_pg_dump():
    """Test pg_dump command"""
    print("\nTesting pg_dump command...")
    
    try:
        # Test if pg_dump is available
        result = subprocess.run(
            ['pg_dump', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ pg_dump available: {result.stdout.strip()}")
            
            # Test actual dump
            env = os.environ.copy()
            env['PGPASSWORD'] = 'gis1234'
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
                dump_result = subprocess.run([
                    'pg_dump',
                    '-h', 'localhost',
                    '-p', '5432',
                    '-U', 'gis',
                    '-d', 'gis',
                    '--verbose',
                    '--no-owner',
                    '--no-acl'
                ], stdout=temp_file, stderr=subprocess.PIPE, env=env, text=True, timeout=60)
                
                temp_file_path = temp_file.name
            
            if dump_result.returncode == 0:
                file_size = os.path.getsize(temp_file_path)
                print(f"✓ pg_dump successful! Created {file_size} bytes")
                
                # Read first few lines
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)
                    print(f"First 500 characters of dump:")
                    print(content)
                
                os.unlink(temp_file_path)
                return True
            else:
                print(f"✗ pg_dump failed: {dump_result.stderr}")
                return False
                
        else:
            print(f"✗ pg_dump not available: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ pg_dump command timed out")
        return False
    except FileNotFoundError:
        print("✗ pg_dump command not found")
        return False
    except Exception as e:
        print(f"✗ pg_dump test failed: {e}")
        return False

def create_test_backup():
    """Create a test backup using psycopg2"""
    print("\nCreating test backup using psycopg2...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='gis',
            user='gis',
            password='gis1234'
        )
        
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        sql_content = []
        sql_content.append("-- PostgreSQL database dump created by psycopg2")
        sql_content.append(f"-- Created on: {datetime.now()}")
        sql_content.append("")
        
        for table in tables:
            table_name = table[0]
            print(f"  Backing up table: {table_name}")
            
            # Get table structure
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            # Create table structure (simplified)
            sql_content.append(f"-- Table: {table_name}")
            
            # Get table data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                column_names = [desc[0] for desc in cursor.description]
                sql_content.append(f"-- Data for table: {table_name} ({len(rows)} rows)")
                
                for row in rows[:5]:  # Limit to first 5 rows for testing
                    values = []
                    for value in row:
                        if value is None:
                            values.append("NULL")
                        elif isinstance(value, str):
                            escaped_value = value.replace("'", "''")
                            values.append(f"'{escaped_value}'")
                        else:
                            values.append(str(value))
                    
                    sql_content.append(f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(values)});")
            
            sql_content.append("")
        
        cursor.close()
        conn.close()
        
        # Write to test file
        test_file = "test_backup.sql"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_content))
        
        file_size = os.path.getsize(test_file)
        print(f"✓ Test backup created: {test_file} ({file_size} bytes)")
        
        # Show first few lines
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read(500)
            print(f"First 500 characters:")
            print(content)
        
        return True
        
    except Exception as e:
        print(f"✗ Test backup failed: {e}")
        return False

if __name__ == "__main__":
    print("=== PostgreSQL Backup Debug Tool ===")
    
    # 1. Inspect existing backup
    backup_file = os.path.join('media', 'backups', 'Backup_20251029_005703.zip')
    inspect_backup_file(backup_file)
    
    # 2. Test PostgreSQL connection
    pg_connected = test_postgresql_connection()
    
    # 3. Test pg_dump
    if pg_connected:
        pg_dump_works = test_pg_dump()
    
    # 4. Create test backup
    if pg_connected:
        create_test_backup()
    
    print("\n=== Debug Complete ===")