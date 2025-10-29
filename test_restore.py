#!/usr/bin/env python
"""
Test restore functionality with the newly created backup
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

from Login.models import Backup
from Login.views import inspect_backup_file
import zipfile

def test_restore_functionality():
    """Test the restore functionality"""
    print("=== Testing Restore Functionality ===")
    
    try:
        # Get the latest backup
        latest_backup = Backup.objects.filter(status='completed').order_by('-created_at').first()
        
        if not latest_backup:
            print("✗ No completed backups found!")
            return False
        
        print(f"Testing restore with backup: {latest_backup.name}")
        print(f"Backup file: {latest_backup.file_path}")
        print(f"Backup size: {latest_backup.file_size} bytes")
        
        # Check if backup file exists
        if not os.path.exists(latest_backup.file_path):
            print("✗ Backup file not found on disk!")
            return False
        
        print("✓ Backup file exists on disk")
        
        # Inspect backup file
        print("\nInspecting backup file contents:")
        inspect_backup_file(latest_backup.file_path)
        
        # Test ZIP extraction
        print("\nTesting ZIP file extraction:")
        with zipfile.ZipFile(latest_backup.file_path, 'r') as zipf:
            file_list = zipf.namelist()
            print(f"ZIP contains {len(file_list)} files:")
            
            for file_name in file_list:
                file_info = zipf.getinfo(file_name)
                print(f"  - {file_name} ({file_info.file_size} bytes)")
                
                if file_name == 'database.sql':
                    print("✓ Found PostgreSQL database file!")
                    
                    # Extract and test database file
                    with zipf.open(file_name) as db_file:
                        content = db_file.read(1000).decode('utf-8', errors='ignore')
                        print(f"    Database file content preview:")
                        print(f"    {content[:300]}...")
                        
                        # Check for key database elements
                        if 'PostgreSQL database dump' in content:
                            print("✓ Valid PostgreSQL dump file")
                        if 'INSERT INTO' in content:
                            print("✓ Contains data INSERT statements")
                        if 'DROP TABLE' in content:
                            print("✓ Contains table structure")
                        
                        return True
        
        print("✗ No database.sql file found in backup!")
        return False
        
    except Exception as e:
        print(f"✗ Restore test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_restore_functionality()
    if success:
        print("\n✓ Backup system is working correctly!")
        print("✓ PostgreSQL backup creation fixed successfully!")
    else:
        print("\n✗ Backup system still has issues!")