#!/usr/bin/env python
"""
Set up the database with initial data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

from django.contrib.auth.models import User
from Login.models import Profile

def setup_initial_data():
    """Set up initial data in the new database"""
    try:
        print("=== Setting up Initial Data ===")
        
        # 1. Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("✓ Database connection working")
        
        # 2. Check admin user
        try:
            admin_user = User.objects.get(username='admin')
            print(f"✓ Admin user exists: {admin_user.username}")
        except User.DoesNotExist:
            print("✗ Admin user not found")
            return False
        
        # 3. Create Profile for admin user
        profile, created = Profile.objects.get_or_create(
            user=admin_user,
            defaults={
                'full_name': 'Administrator',
                'email': 'admin@example.com',
                'user_status': 'administrator',
                'phone': '+1234567890',
                'address': 'Admin Office'
            }
        )
        
        if created:
            print("✓ Created Profile for admin user")
        else:
            print("✓ Profile for admin user already exists")
        
        # 4. Test the backup system by checking tables
        print("\n=== Testing Database Tables ===")
        
        # Check essential tables
        essential_tables = [
            'django_session',
            'auth_user', 
            'Login_profile',
            'Login_backup'
        ]
        
        with connection.cursor() as cursor:
            for table in essential_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cursor.fetchone()[0]
                    print(f"✓ {table}: {count} records")
                except Exception as e:
                    print(f"✗ {table}: {e}")
        
        print("\n✓ Database is ready for backup system!")
        return True
        
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_initial_data()
    if success:
        print("\n✅ Database setup complete!")
        print("You can now:")
        print("1. Start the Django server: python manage.py runserver")
        print("2. Login with: admin / admin123")
        print("3. Test the backup system")
    else:
        print("\n❌ Database setup failed!")