#!/usr/bin/env python
"""
Simulate web backup creation to test the complete flow
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

def simulate_backup_creation():
    """Simulate the complete backup creation flow"""
    print("=== Simulating Complete Backup Creation ===")
    
    try:
        # Get or create a user for testing
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            user.set_password('testpass')
            user.save()
            print(f"Created test user: {user.username}")
        else:
            print(f"Using existing user: {user.username}")
        
        # Create backup record (similar to web interface)
        backup = Backup.objects.create(
            name=f"Test_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            backup_type='database',  # Test database backup first
            created_by=user,
            description='Test backup created via simulation',
            status='in_progress'
        )
        
        print(f"Created backup record: {backup.name}")
        
        try:
            # Create backup directory if not exists
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Backup directory: {backup_dir}")
            
            backup_file_path = os.path.join(backup_dir, f"{backup.name}.zip")
            print(f"Creating backup file: {backup_file_path}")
            
            with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Create database dump
                print("Creating database backup...")
                db_dump_path = create_database_dump()
                if db_dump_path:
                    dump_size = os.path.getsize(db_dump_path)
                    print(f"Database dump created: {dump_size} bytes")
                    
                    # Add to ZIP as database.sql
                    zipf.write(db_dump_path, 'database.sql')
                    print("Added database.sql to backup ZIP")
                    
                    # Clean up temp file
                    os.remove(db_dump_path)
                    print("Temporary dump file cleaned up")
                else:
                    raise Exception("Database dump creation failed!")
            
            # Update backup record
            backup.file_path = backup_file_path
            backup.file_size = os.path.getsize(backup_file_path)
            backup.status = 'completed'
            backup.save()
            
            print(f"✓ Backup completed successfully!")
            print(f"  - File: {backup_file_path}")
            print(f"  - Size: {backup.file_size} bytes")
            
            # Inspect the created backup
            print("\nInspecting created backup:")
            with zipfile.ZipFile(backup_file_path, 'r') as zipf:
                file_list = zipf.namelist()
                print(f"ZIP contains {len(file_list)} files:")
                for file_name in file_list:
                    file_info = zipf.getinfo(file_name)
                    print(f"  - {file_name} ({file_info.file_size} bytes)")
                    
                    # Check database.sql content
                    if file_name == 'database.sql':
                        with zipf.open(file_name) as db_file:
                            content = db_file.read(500).decode('utf-8', errors='ignore')
                            print(f"    First 500 characters of database.sql:")
                            print(f"    {content[:200]}...")
            
            return True
            
        except Exception as e:
            backup.status = 'failed'
            backup.error_message = str(e)
            backup.save()
            print(f"✗ Backup failed: {str(e)}")
            return False
        
    except Exception as e:
        print(f"✗ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simulate_backup_creation()
    if success:
        print("\n✓ PostgreSQL backup creation fix is working correctly!")
    else:
        print("\n✗ PostgreSQL backup creation still has issues!")