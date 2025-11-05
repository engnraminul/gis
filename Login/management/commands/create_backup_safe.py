from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import User
from Login.models import Backup
import os
import zipfile
import tempfile
import shutil
from datetime import datetime
from io import StringIO


class Command(BaseCommand):
    help = 'Create backup using Django fixtures for safe restoration'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Backup name')
        parser.add_argument(
            '--type',
            choices=['database', 'media', 'full'],
            default='full',
            help='Type of backup to create',
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Backup description',
        )

    def handle(self, *args, **options):
        backup_name = options['name']
        backup_type = options['type']
        description = options['description']

        # Get current user (for CLI, we'll use first superuser)
        try:
            current_user = User.objects.filter(is_superuser=True).first()
            if not current_user:
                self.stdout.write(self.style.ERROR('No superuser found. Please create one first.'))
                return
        except:
            self.stdout.write(self.style.ERROR('Database not available. Please run migrations first.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Creating Django fixture backup: {backup_name}'))
        
        # Create backup directory
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{backup_name}_{timestamp}.zip"
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        # Create temporary directory for backup files
        temp_dir = tempfile.mkdtemp()
        
        try:
            backup_created = False
            
            # Create database backup using Django fixtures
            if backup_type in ['database', 'full']:
                self.stdout.write('Creating Django fixture backup...')
                
                # Create data.json using dumpdata
                data_file = os.path.join(temp_dir, 'data.json')
                
                # Export all app data (excluding sessions and auth tokens which are temporary)
                apps_to_backup = [
                    'Login.profile',
                    'Login.backup', 
                    'Map.map',
                    'Map.mapfile',
                    'Map.mapcolor',
                    'contenttypes',
                    'auth.user',
                    'auth.group',
                    'auth.permission',
                ]
                
                with open(data_file, 'w', encoding='utf-8') as f:
                    # Capture dumpdata output
                    call_command(
                        'dumpdata',
                        *apps_to_backup,
                        stdout=f,
                        format='json',
                        indent=2,
                        use_natural_foreign_keys=True,
                        use_natural_primary_keys=True
                    )
                
                self.stdout.write(f'Django fixture created: {data_file}')
                backup_created = True
                
                # Also create a metadata file
                metadata_file = os.path.join(temp_dir, 'metadata.json')
                metadata = {
                    'backup_name': backup_name,
                    'backup_type': backup_type,
                    'created_at': datetime.now().isoformat(),
                    'created_by': current_user.username,
                    'django_version': '4.2',
                    'backup_method': 'django_fixture',
                    'description': description
                }
                
                import json
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

            # Create media backup
            if backup_type in ['media', 'full']:
                if os.path.exists(settings.MEDIA_ROOT):
                    self.stdout.write('Creating media backup...')
                    media_backup_dir = os.path.join(temp_dir, 'media')
                    
                    # Copy media files (exclude backups folder to avoid recursion)
                    for item in os.listdir(settings.MEDIA_ROOT):
                        src_path = os.path.join(settings.MEDIA_ROOT, item)
                        if item != 'backups' and os.path.isdir(src_path):
                            dst_path = os.path.join(media_backup_dir, item)
                            shutil.copytree(src_path, dst_path)
                        elif os.path.isfile(src_path):
                            os.makedirs(media_backup_dir, exist_ok=True)
                            shutil.copy2(src_path, os.path.join(media_backup_dir, item))
                    
                    backup_created = True
                    self.stdout.write('Media files backed up')

            if backup_created:
                # Create ZIP file
                self.stdout.write('Creating ZIP archive...')
                with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                
                # Create backup record in database
                backup_record = Backup.objects.create(
                    name=backup_name,
                    description=description or f'Django fixture backup created on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    backup_type=backup_type,
                    created_by=current_user,
                    status='completed',
                    file_path=backup_filepath
                )
                
                self.stdout.write(self.style.SUCCESS(f'Backup created successfully!'))
                self.stdout.write(f'Backup ID: {backup_record.id}')
                self.stdout.write(f'File: {backup_filepath}')
                self.stdout.write(f'Size: {os.path.getsize(backup_filepath)} bytes')
                
                # Show restore command
                self.stdout.write(self.style.WARNING('\nTo restore this backup safely, use:'))
                self.stdout.write(f'python manage.py restore_backup_safe {backup_record.id}')
                self.stdout.write('or')
                self.stdout.write(f'python manage.py restore_backup_safe {backup_record.id} --preserve-users')
            
            else:
                self.stdout.write(self.style.ERROR('No backup content created'))
        
        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass