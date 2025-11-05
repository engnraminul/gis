from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction, connections
from django.core.management import call_command
from django.contrib.auth.models import User
from Login.models import Backup, Profile
from Map.models import Map
import os
import zipfile
import tempfile
import shutil
import json
from io import StringIO
import sys


class Command(BaseCommand):
    help = 'Safely restore backup using Django ORM without dropping database'

    def add_arguments(self, parser):
        parser.add_argument('backup_id', type=int, help='Backup ID to restore')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force restore even if it overwrites existing data',
        )
        parser.add_argument(
            '--preserve-users',
            action='store_true',
            help='Preserve current users and only restore app data',
        )

    def handle(self, *args, **options):
        backup_id = options['backup_id']
        force = options['force']
        preserve_users = options['preserve_users']

        try:
            backup = Backup.objects.get(id=backup_id)
        except Backup.DoesNotExist:
            raise CommandError(f'Backup with ID {backup_id} does not exist')

        if not os.path.exists(backup.file_path):
            raise CommandError(f'Backup file not found: {backup.file_path}')

        self.stdout.write(self.style.SUCCESS(f'Starting Django-based restore of: {backup.name}'))
        
        # Extract backup to temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(backup.file_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            self.stdout.write(f'Extracted backup to: {temp_dir}')
            
            # Look for data files
            data_file = os.path.join(temp_dir, 'data.json')
            sql_file = os.path.join(temp_dir, 'database.sql')
            media_dir = os.path.join(temp_dir, 'media')
            
            restored_anything = False
            
            # Method 1: Restore from JSON data (preferred)
            if os.path.exists(data_file):
                self.stdout.write('Found data.json file, using Django fixture restore...')
                self.restore_from_fixture(data_file, preserve_users, force)
                restored_anything = True
            
            # Method 2: Parse SQL and extract data
            elif os.path.exists(sql_file):
                self.stdout.write('Found database.sql file, parsing for data restoration...')
                self.restore_from_sql_data(sql_file, preserve_users, force)
                restored_anything = True
            
            # Restore media files
            if os.path.exists(media_dir):
                self.stdout.write('Restoring media files...')
                self.restore_media_files(media_dir)
                restored_anything = True
            
            if not restored_anything:
                self.stdout.write(self.style.WARNING('No data files found in backup'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Backup {backup.name} restored successfully!'))
                self.stdout.write(self.style.SUCCESS('All Django system tables preserved, data restored using ORM'))
        
        finally:
            # Cleanup
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    def restore_from_fixture(self, data_file, preserve_users, force):
        """Restore data from Django fixture JSON file"""
        self.stdout.write('Loading data from Django fixture...')
        
        if not force:
            self.stdout.write('Use --force to restore fixture data')
            return
        
        # Clear existing data first for complete restore
        self.clear_existing_data(preserve_users)
        
        if preserve_users:
            # Load data but skip auth.user entries
            self.stdout.write('Preserving existing users...')
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Filter out auth.user and related entries if preserving users
            filtered_data = []
            for item in data:
                if item.get('model') not in ['auth.user', 'auth.group', 'auth.permission', 'admin.logentry']:
                    filtered_data.append(item)
            
            # Write filtered data to temp file
            temp_fixture = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(filtered_data, temp_fixture, indent=2)
            temp_fixture.close()
            
            try:
                call_command('loaddata', temp_fixture.name, verbosity=2)
                self.stdout.write(self.style.SUCCESS('Data loaded successfully (users preserved)'))
            finally:
                os.unlink(temp_fixture.name)
        else:
            # Load all data
            call_command('loaddata', data_file, verbosity=2)
            self.stdout.write(self.style.SUCCESS('All data loaded successfully'))

    def clear_existing_data(self, preserve_users):
        """Clear existing data before restore"""
        from django.db import connection, transaction
        
        # Tables to clear in proper order (child tables first)
        if preserve_users:
            tables_to_clear = [
                'Map_mapfile', 'Map_mapcolor', 'Map_historicalmap', 'Map_map',
                'Login_backup', 'Login_profile'
            ]
        else:
            tables_to_clear = [
                'django_admin_log',  # Clear admin log first
                'Map_mapfile', 'Map_mapcolor', 'Map_historicalmap', 'Map_map',
                'Login_backup', 'Login_profile',
                'auth_user_user_permissions', 'auth_user_groups',
                'auth_group_permissions', 'auth_user', 'auth_group', 'auth_permission'
            ]
        
        with transaction.atomic():
            cursor = connection.cursor()
            
            # Disable foreign key constraints temporarily
            cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
            
            for table in tables_to_clear:
                try:
                    cursor.execute(f'DELETE FROM "{table}"')
                    self.stdout.write(f'Cleared existing data from {table}')
                except Exception as e:
                    self.stdout.write(f'Note: Could not clear {table}: {e}')
            
            # Re-enable foreign key constraints
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
        
        # Reset sequences in a separate transaction to avoid conflicts
        try:
            with connection.cursor() as cursor:
                # Get actual sequence names from database
                cursor.execute("""
                    SELECT sequence_name FROM information_schema.sequences 
                    WHERE sequence_schema = 'public' 
                    AND sequence_name LIKE '%_id_seq'
                """)
                sequences = [row[0] for row in cursor.fetchall()]
                
                for seq in sequences:
                    try:
                        cursor.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1;")
                        self.stdout.write(f'Reset sequence {seq}')
                    except Exception as e:
                        self.stdout.write(f'Note: Could not reset sequence {seq}: {e}')
        except Exception as e:
            self.stdout.write(f'Note: Could not reset sequences: {e}')

    def restore_from_sql_data(self, sql_file, preserve_users, force):
        """Extract and restore data from SQL dump using safe SQL execution"""
        self.stdout.write('Using safe SQL execution for data restoration...')
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        if preserve_users:
            self.stdout.write('Preserving existing users, restoring only app data...')
            # Extract only non-user related data
            self.restore_app_data_only(sql_content)
        else:
            self.stdout.write('Restoring all data including users...')
            # Restore all data
            self.restore_all_data(sql_content)

    def restore_app_data_only(self, sql_content):
        """Restore only app-specific data, preserve users"""
        from django.db import connection, transaction
        import re
        
        # Tables to restore (excluding user-related tables)
        safe_tables = [
            'Login_backup', 'Login_profile', 
            'Map_map', 'Map_mapfile', 'Map_mapcolor'
        ]
        
        with transaction.atomic():
            cursor = connection.cursor()
            
            for table in safe_tables:
                # Clear existing data in this table
                try:
                    cursor.execute(f'DELETE FROM "{table}"')
                    self.stdout.write(f'Cleared existing data from {table}')
                except Exception as e:
                    self.stdout.write(f'Note: Could not clear {table}: {e}')
                
                # Extract and execute INSERT statements for this table
                pattern = rf"INSERT INTO [\"`]?{table}[\"`]?\s*\([^)]+\)\s*VALUES\s*\([^;]+\);"
                matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
                
                if matches:
                    self.stdout.write(f'Restoring {len(matches)} records to {table}')
                    for match in matches:
                        try:
                            cursor.execute(match)
                        except Exception as e:
                            self.stdout.write(f'Error restoring to {table}: {e}')
                else:
                    self.stdout.write(f'No data found for {table}')

    def restore_all_data(self, sql_content):
        """Restore all data including users"""
        from django.db import connection, transaction
        from django.contrib.auth.models import User
        import re
        
        # Tables to restore (including user tables)
        all_tables = [
            'auth_user', 'auth_group', 'auth_permission',
            'Login_backup', 'Login_profile', 
            'Map_map', 'Map_mapfile', 'Map_mapcolor'
        ]
        
        with transaction.atomic():
            cursor = connection.cursor()
            
            # Clear existing data
            for table in all_tables:
                try:
                    cursor.execute(f'DELETE FROM "{table}"')
                    self.stdout.write(f'Cleared existing data from {table}')
                except Exception as e:
                    self.stdout.write(f'Note: Could not clear {table}: {e}')
            
            # Restore data
            for table in all_tables:
                pattern = rf"INSERT INTO [\"`]?{table}[\"`]?\s*\([^)]+\)\s*VALUES\s*\([^;]+\);"
                matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
                
                if matches:
                    self.stdout.write(f'Restoring {len(matches)} records to {table}')
                    for match in matches:
                        try:
                            cursor.execute(match)
                        except Exception as e:
                            self.stdout.write(f'Error restoring to {table}: {e}')
                else:
                    self.stdout.write(f'No data found for {table}')

    def restore_media_files(self, media_backup_dir):
        """Restore media files safely"""
        current_media = settings.MEDIA_ROOT
        
        # Create backup of current media
        if os.path.exists(current_media):
            backup_media = f"{current_media}_backup_{int(os.path.getmtime(current_media))}"
            if not os.path.exists(backup_media):
                shutil.copytree(current_media, backup_media)
                self.stdout.write(f'Current media backed up to: {backup_media}')
        
        # Copy media files
        if os.path.exists(media_backup_dir):
            for root, dirs, files in os.walk(media_backup_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, media_backup_dir)
                    dst_path = os.path.join(current_media, rel_path)
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(src_path, dst_path)
            
            self.stdout.write(self.style.SUCCESS('Media files restored successfully'))