#!/usr/bin/env python
"""
Manual database restore from backup
"""
import psycopg2
import os
import zipfile
import tempfile

def manual_restore():
    """Manually restore database from backup"""
    try:
        print("=== Manual Database Restore ===")
        
        # 1. Connect to postgres database as admin
        print("1. Connecting to PostgreSQL server...")
        admin_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='gis',
            password='gis1234',
            database='postgres'
        )
        admin_conn.autocommit = True
        admin_cursor = admin_conn.cursor()
        print("   Connected to PostgreSQL server")
        
        # 2. Create gis database
        print("2. Creating gis database...")
        try:
            admin_cursor.execute('CREATE DATABASE "gis"')
            print("   Database 'gis' created successfully")
        except psycopg2.errors.DuplicateDatabase:
            print("   Database 'gis' already exists")
        except Exception as e:
            print(f"   Error creating database: {e}")
            # Try dropping and recreating
            try:
                admin_cursor.execute('DROP DATABASE IF EXISTS "gis"')
                admin_cursor.execute('CREATE DATABASE "gis"')
                print("   Database 'gis' recreated successfully")
            except Exception as e2:
                print(f"   Failed to recreate database: {e2}")
                return False
        
        admin_cursor.close()
        admin_conn.close()
        
        # 3. Find the latest backup
        print("3. Finding latest backup...")
        backup_dir = r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir\media\backups'
        backup_files = []
        
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith('.zip'):
                    backup_path = os.path.join(backup_dir, file)
                    backup_files.append((file, backup_path, os.path.getmtime(backup_path)))
        
        if not backup_files:
            print("   No backup files found!")
            return False
        
        # Sort by modification time (latest first)
        backup_files.sort(key=lambda x: x[2], reverse=True)
        latest_backup = backup_files[0]
        
        print(f"   Using backup: {latest_backup[0]}")
        print(f"   Path: {latest_backup[1]}")
        
        # 4. Extract database.sql from backup
        print("4. Extracting database.sql from backup...")
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(latest_backup[1], 'r') as zipf:
                # List contents
                files = zipf.namelist()
                print(f"   Backup contains: {files}")
                
                if 'database.sql' not in files:
                    print("   No database.sql found in backup!")
                    return False
                
                # Extract database.sql
                zipf.extract('database.sql', temp_dir)
                db_sql_path = os.path.join(temp_dir, 'database.sql')
                
                # Check file size
                sql_size = os.path.getsize(db_sql_path)
                print(f"   Extracted database.sql ({sql_size} bytes)")
                
                if sql_size == 0:
                    print("   Database.sql is empty!")
                    return False
                    
        except Exception as extract_error:
            print(f"   Error extracting backup: {extract_error}")
            return False
        
        # 5. Restore database.sql to gis database
        print("5. Restoring database.sql to gis database...")
        gis_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='gis',
            password='gis1234',
            database='gis'
        )
        gis_conn.autocommit = True
        gis_cursor = gis_conn.cursor()
        
        # Read and execute SQL file
        with open(db_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"   Executing SQL content ({len(sql_content)} characters)...")
        
        # Split SQL into statements and execute one by one
        statements = sql_content.split(';')
        executed = 0
        
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    gis_cursor.execute(statement)
                    executed += 1
                except Exception as e:
                    print(f"   Warning: SQL statement failed: {str(e)[:100]}...")
        
        print(f"   Executed {executed} SQL statements")
        
        gis_cursor.close()
        gis_conn.close()
        
        # 6. Test database connection
        print("6. Testing database connection...")
        test_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='gis',
            password='gis1234',
            database='gis'
        )
        test_cursor = test_conn.cursor()
        
        # Check tables
        test_cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = test_cursor.fetchall()
        print(f"   Database has {len(tables)} tables: {[t[0] for t in tables[:5]]}...")
        
        test_cursor.close()
        test_conn.close()
        
        print("✓ Database restored successfully!")
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        print(f"   Cleaned up temp directory")
        
        return True
        
    except Exception as e:
        print(f"✗ Manual restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = manual_restore()
    if success:
        print("\n✓ Database is restored and ready!")
    else:
        print("\n✗ Database restore failed!")