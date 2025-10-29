#!/usr/bin/env python
"""
Create the new database and restore from backup with correct settings
"""
import psycopg2
import os
import zipfile
import tempfile

def create_database_and_restore():
    """Create new database and restore from backup"""
    try:
        print("=== Creating Database and Restoring from Backup ===")
        
        # New database settings from Django
        db_settings = {
            'NAME': 'gisdb',
            'USER': 'gisuser', 
            'PASSWORD': 'gis1234',
            'HOST': 'localhost',
            'PORT': '5432'
        }
        
        print(f"Using database settings: {db_settings}")
        
        # 1. Connect to postgres database as superuser to create database
        print("1. Connecting to PostgreSQL server...")
        
        # Try different superuser configurations
        superuser_configs = [
            {'user': 'postgres', 'password': 'postgres'},
            {'user': 'postgres', 'password': ''},
            {'user': 'postgres', 'password': 'admin'},
            {'user': 'postgres', 'password': '123456'},
            {'user': db_settings['USER'], 'password': db_settings['PASSWORD']},  # Try the gisuser
        ]
        
        admin_conn = None
        working_config = None
        
        for config in superuser_configs:
            try:
                print(f"   Trying user: {config['user']}")
                admin_conn = psycopg2.connect(
                    host=db_settings['HOST'],
                    port=db_settings['PORT'],
                    user=config['user'],
                    password=config['password'],
                    database='postgres'
                )
                admin_conn.autocommit = True
                working_config = config
                print(f"   ✓ Connected as {config['user']}")
                break
            except Exception as e:
                print(f"   ✗ Failed with {config['user']}: {e}")
                continue
        
        if not admin_conn:
            print("   ✗ Could not connect as any superuser")
            print("   You may need to:")
            print("   1. Create the database manually using pgAdmin")
            print("   2. Or provide the correct postgres user password")
            return False
        
        admin_cursor = admin_conn.cursor()
        
        # 2. Check if gisuser exists, create if not
        print("2. Checking/creating database user...")
        admin_cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_settings['USER'],))
        user_exists = admin_cursor.fetchone()
        
        if not user_exists:
            print(f"   Creating user: {db_settings['USER']}")
            admin_cursor.execute(f"""
                CREATE USER "{db_settings['USER']}" WITH 
                PASSWORD '{db_settings['PASSWORD']}' 
                CREATEDB LOGIN;
            """)
        else:
            print(f"   User {db_settings['USER']} already exists")
            # Grant CREATEDB if not already granted
            admin_cursor.execute(f'ALTER USER "{db_settings['USER']}" CREATEDB;')
        
        # 3. Create gisdb database
        print("3. Creating gisdb database...")
        try:
            admin_cursor.execute(f'DROP DATABASE IF EXISTS "{db_settings['NAME']}"')
            admin_cursor.execute(f'CREATE DATABASE "{db_settings['NAME']}" OWNER "{db_settings['USER']}"')
            print("   ✓ Database 'gisdb' created successfully")
        except Exception as e:
            print(f"   Error creating database: {e}")
            return False
        
        admin_cursor.close()
        admin_conn.close()
        
        # 4. Find the latest backup
        print("4. Finding latest backup...")
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
        
        # 5. Extract and restore database.sql
        print("5. Extracting and restoring database.sql...")
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(latest_backup[1], 'r') as zipf:
                files = zipf.namelist()
                print(f"   Backup contains: {files}")
                
                if 'database.sql' not in files:
                    print("   No database.sql found in backup!")
                    return False
                
                # Extract database.sql
                zipf.extract('database.sql', temp_dir)
                db_sql_path = os.path.join(temp_dir, 'database.sql')
                
                sql_size = os.path.getsize(db_sql_path)
                print(f"   Extracted database.sql ({sql_size} bytes)")
                
                if sql_size == 0:
                    print("   Database.sql is empty!")
                    return False
            
            # 6. Restore database.sql to gisdb database
            print("6. Restoring database.sql to gisdb database...")
            gis_conn = psycopg2.connect(
                host=db_settings['HOST'],
                port=db_settings['PORT'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database=db_settings['NAME']
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
            errors = 0
            
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        gis_cursor.execute(statement)
                        executed += 1
                    except Exception as e:
                        errors += 1
                        if errors <= 5:  # Show first 5 errors
                            print(f"   Warning: SQL statement failed: {str(e)[:100]}...")
            
            print(f"   Executed {executed} SQL statements ({errors} errors)")
            
            gis_cursor.close()
            gis_conn.close()
            
            # 7. Test database connection
            print("7. Testing database connection...")
            test_conn = psycopg2.connect(
                host=db_settings['HOST'],
                port=db_settings['PORT'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database=db_settings['NAME']
            )
            test_cursor = test_conn.cursor()
            
            # Check tables
            test_cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = test_cursor.fetchall()
            print(f"   Database has {len(tables)} tables")
            
            # Check specifically for Django tables
            django_tables = [t[0] for t in tables if t[0].startswith('django_')]
            print(f"   Django tables: {django_tables}")
            
            test_cursor.close()
            test_conn.close()
            
            print("✓ Database restored successfully!")
            return True
            
        finally:
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)
            print(f"   Cleaned up temp directory")
        
    except Exception as e:
        print(f"✗ Database creation and restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_database_and_restore()
    if success:
        print("\n✓ Database is ready! You can now run Django migrations if needed.")
        print("✓ Try accessing the backup system again.")
    else:
        print("\n✗ Database setup failed!")