#!/usr/bin/env python
"""
Check current database connection and tables
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir')
django.setup()

def check_current_database():
    """Check current database connection and tables"""
    try:
        print("=== Checking Current Database Connection ===")
        
        # 1. Check Django settings
        from django.conf import settings
        db_settings = settings.DATABASES['default']
        print(f"Django Database Settings:")
        print(f"  Engine: {db_settings['ENGINE']}")
        print(f"  Name: {db_settings['NAME']}")
        print(f"  User: {db_settings['USER']}")
        print(f"  Host: {db_settings['HOST']}:{db_settings['PORT']}")
        
        # 2. Test Django database connection
        print("\n=== Testing Django Database Connection ===")
        from django.db import connection
        
        # Force a new connection
        connection.close()
        
        with connection.cursor() as cursor:
            # Check current database name
            cursor.execute("SELECT current_database()")
            current_db = cursor.fetchone()[0]
            print(f"Connected to database: {current_db}")
            
            # List all tables
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            print(f"Tables in database ({len(table_names)}): {table_names}")
            
            # Check specifically for django_session
            if 'django_session' in table_names:
                cursor.execute("SELECT COUNT(*) FROM django_session")
                count = cursor.fetchone()[0]
                print(f"✓ django_session table exists with {count} records")
            else:
                print("✗ django_session table does NOT exist!")
                
                # Check if we need to run migrations
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'django_migrations'
                """)
                migrations_table_exists = cursor.fetchone()[0] > 0
                
                if migrations_table_exists:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations")
                    migration_count = cursor.fetchone()[0]
                    print(f"django_migrations table exists with {migration_count} migrations")
                else:
                    print("django_migrations table does NOT exist - need to run migrations!")
        
        # 3. Test if we can access Django session framework
        print("\n=== Testing Django Session Framework ===")
        try:
            from django.contrib.sessions.models import Session
            session_count = Session.objects.count()
            print(f"✓ Can access Session model, found {session_count} sessions")
        except Exception as session_error:
            print(f"✗ Cannot access Session model: {session_error}")
        
        return True
        
    except Exception as e:
        print(f"✗ Database check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_current_database()