#!/usr/bin/env python
"""
Test backup creation with detailed debugging
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

import zipfile
import tempfile
import psycopg2
from datetime import datetime
from django.conf import settings

def test_postgresql_dump_creation():
    """Test PostgreSQL dump creation with debugging"""
    print("=== Testing PostgreSQL Dump Creation ===")
    
    try:
        db_settings = settings.DATABASES['default']
        print(f"Database settings: {db_settings}")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8')
        temp_file_path = temp_file.name
        temp_file.close()
        print(f"Temporary file created: {temp_file_path}")
        
        # Connect directly to PostgreSQL
        pg_connection = psycopg2.connect(
            host=db_settings['HOST'],
            port=db_settings['PORT'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            database=db_settings['NAME']
        )
        
        print("PostgreSQL connection established")
        cursor = pg_connection.cursor()
        
        # Get all table names using the correct query
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables to backup: {[t[0] for t in tables]}")
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("-- PostgreSQL database dump created by Django backup system\n")
            f.write("-- Database: {}\n".format(db_settings['NAME']))
            f.write("-- Created: {}\n\n".format(datetime.now().isoformat()))
            
            # For each table, write data
            for (table_name,) in tables:
                print(f"Processing table: {table_name}")
                
                try:
                    # Get table data with proper quoting
                    cursor.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor.fetchall()
                    
                    if rows:
                        print(f"  - Found {len(rows)} rows")
                        
                        # Get column names
                        cursor.execute(f"""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            ORDER BY ordinal_position;
                        """)
                        column_names = [row[0] for row in cursor.fetchall()]
                        print(f"  - Columns: {column_names}")
                        
                        f.write(f"-- Table: {table_name} ({len(rows)} rows)\n")
                        
                        # Write INSERT statements in batches
                        for i, row in enumerate(rows):
                            values = []
                            for value in row:
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    escaped_value = value.replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                                elif isinstance(value, datetime):
                                    values.append(f"'{value.isoformat()}'")
                                else:
                                    values.append(str(value))
                            
                            f.write(f"INSERT INTO \"{table_name}\" ({', '.join([f'\"{col}\"' for col in column_names])}) VALUES ({', '.join(values)});\n")
                        
                        f.write(f"\n")
                        print(f"  - Wrote {len(rows)} INSERT statements")
                    else:
                        print(f"  - Table {table_name} is empty")
                        f.write(f"-- Table: {table_name} (empty)\n\n")
                        
                except Exception as table_error:
                    print(f"Error processing table {table_name}: {table_error}")
                    f.write(f"-- ERROR processing table {table_name}: {table_error}\n\n")
        
        cursor.close()
        pg_connection.close()
        
        # Check file size
        file_size = os.path.getsize(temp_file_path)
        print(f"Dump file created: {temp_file_path} ({file_size} bytes)")
        
        # Read first few lines to verify content
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read(1000)
            print(f"First 1000 characters of dump file:")
            print(content)
        
        if file_size > 0:
            print("✓ PostgreSQL dump creation successful!")
            return temp_file_path
        else:
            print("✗ Dump file is empty!")
            return None
        
    except Exception as e:
        print(f"PostgreSQL dump creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_backup_zip_creation():
    """Test creating a backup ZIP file"""
    print("\n=== Testing Backup ZIP Creation ===")
    
    # Create database dump
    db_dump_path = test_postgresql_dump_creation()
    
    if not db_dump_path:
        print("Cannot create backup ZIP - database dump failed")
        return None
    
    try:
        # Create ZIP file
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_file_path = os.path.join(backup_dir, f"Test_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        print(f"Creating backup ZIP: {backup_file_path}")
        
        with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database dump
            print(f"Adding database dump to ZIP: {db_dump_path}")
            zipf.write(db_dump_path, 'database.sql')
            print("Database dump added to ZIP")
            
            # Add a few media files as test
            media_root = settings.MEDIA_ROOT
            test_files_added = 0
            for root, dirs, files in os.walk(media_root):
                if 'backups' in dirs:
                    dirs.remove('backups')  # Skip backups directory
                for file in files:
                    if test_files_added >= 3:  # Only add first 3 files for testing
                        break
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, media_root)
                    zipf.write(file_path, f"media/{arcname}")
                    print(f"Added media file: {arcname}")
                    test_files_added += 1
                if test_files_added >= 3:
                    break
        
        # Clean up temp database dump
        os.remove(db_dump_path)
        print("Temporary database dump cleaned up")
        
        # Check final ZIP file
        file_size = os.path.getsize(backup_file_path)
        print(f"Backup ZIP created: {backup_file_path} ({file_size} bytes)")
        
        # Inspect ZIP contents
        with zipfile.ZipFile(backup_file_path, 'r') as zipf:
            file_list = zipf.namelist()
            print(f"ZIP contains {len(file_list)} files:")
            for file_name in file_list:
                file_info = zipf.getinfo(file_name)
                print(f"  - {file_name} ({file_info.file_size} bytes)")
        
        print("✓ Backup ZIP creation successful!")
        return backup_file_path
        
    except Exception as e:
        print(f"Backup ZIP creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_backup_zip_creation()