#!/usr/bin/env python
"""
Quick test of the fixed backup creation through Django
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

from Login.views import create_database_dump
import zipfile

def test_fixed_backup():
    """Test the fixed backup creation"""
    print("=== Testing Fixed Backup Creation ===")
    
    try:
        # Test database dump creation
        print("Creating database dump...")
        db_dump_path = create_database_dump()
        
        if db_dump_path:
            file_size = os.path.getsize(db_dump_path)
            print(f"✓ Database dump created: {db_dump_path} ({file_size} bytes)")
            
            # Read first few lines to verify content
            with open(db_dump_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                print(f"First 500 characters:")
                print(content)
            
            # Clean up
            os.remove(db_dump_path)
            print("Temporary file cleaned up")
            
            return True
        else:
            print("✗ Database dump creation failed")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fixed_backup()