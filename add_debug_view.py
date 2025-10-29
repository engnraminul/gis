#!/usr/bin/env python
"""
Create a debug view to test database connection
"""
import os

# Add a debug view to check database connection
debug_view_content = '''
from django.http import JsonResponse
from django.db import connection
from django.conf import settings

def debug_database_connection(request):
    """Debug view to check database connection"""
    try:
        # Get database settings
        db_settings = settings.DATABASES['default']
        
        # Test database connection
        with connection.cursor() as cursor:
            # Check current database
            cursor.execute("SELECT current_database()")
            current_db = cursor.fetchone()[0]
            
            # List tables
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            
            # Check django_session specifically
            if 'django_session' in table_names:
                cursor.execute("SELECT COUNT(*) FROM django_session")
                session_count = cursor.fetchone()[0]
                django_session_status = f"EXISTS with {session_count} records"
            else:
                django_session_status = "DOES NOT EXIST"
        
        return JsonResponse({
            'status': 'success',
            'database_config': {
                'engine': db_settings['ENGINE'],
                'name': db_settings['NAME'],
                'user': db_settings['USER'],
                'host': db_settings['HOST'],
                'port': db_settings['PORT']
            },
            'actual_database': current_db,
            'tables_count': len(table_names),
            'django_session_status': django_session_status,
            'all_tables': table_names
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
'''

# Add this to the Login views.py file
with open(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir\Login\views.py', 'a', encoding='utf-8') as f:
    f.write('\n\n# Debug view for database connection\n')
    f.write(debug_view_content)

print("Added debug view to Login/views.py")

# Add URL pattern
url_pattern = "path('debug-db/', views.debug_database_connection, name='debug_database_connection'),"

with open(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir\Login\urls.py', 'r', encoding='utf-8') as f:
    urls_content = f.read()

# Insert the debug URL pattern
if 'debug-db/' not in urls_content:
    # Find urlpatterns and add our pattern
    lines = urls_content.split('\n')
    for i, line in enumerate(lines):
        if 'urlpatterns = [' in line:
            lines.insert(i+1, f"    {url_pattern}")
            break
    
    with open(r'c:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir\Login\urls.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print("Added debug URL to Login/urls.py")
else:
    print("Debug URL already exists")

print("\nDebug view added!")
print("Access it at: http://127.0.0.1:8000/user/debug-db/")
print("This will show the actual database connection details from the web interface")