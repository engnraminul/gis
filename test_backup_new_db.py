#!/usr/bin/env python
"""
Test backup creation with new database settings
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

from django.contrib.auth.models import User
from Login.models import Backup
from Login.views import create_database_dump
from django.conf import settings
from datetime import datetime
import zipfile
import os

def test_backup_with_new_settings():
    """Test backup creation with new database settings"""
    print("=== Testing Backup with New Database Settings ===")
    
    try:
        # 1. Verify database settings
        print("1. Checking database settings...")
        db_settings = settings.DATABASES['default']
        print(f"   Database: {db_settings['NAME']}")
        print(f"   User: {db_settings['USER']}")
        print(f"   Host: {db_settings['HOST']}:{db_settings['PORT']}")
        
        # 2. Test database connection
        print("2. Testing database connection...")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_user")
            user_count = cursor.fetchone()[0]
            print(f"   ✓ Connected to database, found {user_count} users")
        
        # 3. Get admin user for backup
        print("3. Getting admin user...")
        admin_user = User.objects.get(username='admin')
        print(f"   ✓ Found admin user: {admin_user.username}")
        
        # 4. Test database dump creation
        print("4. Testing database dump creation...")
        db_dump_path = create_database_dump()
        
        if db_dump_path:
            file_size = os.path.getsize(db_dump_path)
            print(f"   ✓ Database dump created: {file_size} bytes")
            
            # Read first few lines to verify content
            with open(db_dump_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                print(f"   First 500 characters:")
                print(f"   {content[:200]}...")
            
            # 5. Create a test backup record and ZIP
            print("5. Creating test backup...")
            backup = Backup.objects.create(
                name=f"Test_Backup_New_DB_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                backup_type='database',
                created_by=admin_user,
                description='Test backup with new database settings',
                status='in_progress'
            )
            
            # Create backup directory
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file_path = os.path.join(backup_dir, f"{backup.name}.zip")
            
            # Create ZIP file with database dump
            with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(db_dump_path, 'database.sql')
                print(f"   ✓ Added database.sql to backup ZIP")
            
            # Update backup record
            backup.file_path = backup_file_path
            backup.file_size = os.path.getsize(backup_file_path)
            backup.status = 'completed'
            backup.save()
            
            print(f"   ✓ Backup created successfully!")
            print(f"   File: {backup_file_path}")
            print(f"   Size: {backup.file_size} bytes")
            
            # Clean up temp database dump
            os.remove(db_dump_path)
            
            # 6. Verify backup contents
            print("6. Verifying backup contents...")
            with zipfile.ZipFile(backup_file_path, 'r') as zipf:
                files = zipf.namelist()
                print(f"   Backup contains: {files}")
                
                if 'database.sql' in files:
                    file_info = zipf.getinfo('database.sql')
                    print(f"   ✓ database.sql: {file_info.file_size} bytes")
                    
                    # Test extracting and reading database.sql
                    with zipf.open('database.sql') as db_file:
                        content = db_file.read(300).decode('utf-8', errors='ignore')
                        print(f"   First 300 characters of database.sql:")
                        print(f"   {content}")
                        
                    return True
                else:
                    print("   ✗ database.sql not found in backup!")
                    return False
            
        else:
            print("   ✗ Database dump creation failed!")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backup_with_new_settings()
    if success:
        print("\n✅ Backup system is working correctly with new database settings!")
        print("✅ The 'relation django_session does not exist' error should be fixed!")
    else:
        print("\n❌ Backup system still has issues!")