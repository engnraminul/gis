from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from .forms import ProfileForm
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Profile, Backup
from .forms import ProfileForm
from Map.models import Map, MapFile
import matplotlib.pyplot as plt
import io
import urllib, base64
from Map.forms import MapForm
from django.utils.safestring import mark_safe
import os
import json
import zipfile
import shutil
import subprocess
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import tempfile
from functools import wraps


def session_safe_view(view_func):
    """Decorator to handle views that might have database restoration issues"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            # If there's a session-related database error, handle it gracefully
            error_str = str(e).lower()
            if 'django_session' in error_str and 'does not exist' in error_str:
                print(f"Session table error during view execution: {e}")
                
                # Clear the session to prevent further errors
                if hasattr(request, 'session'):
                    try:
                        request.session.flush()
                    except:
                        pass
                    request.session.modified = False
                
                # Try to redirect to login or backup list
                messages.error(request, "Database session error occurred. Please refresh the page.")
                return redirect('Login:backup_list')
            else:
                # Re-raise other exceptions
                raise e
    return wrapper


def get_or_create_user_profile(user):
    """
    Helper function to get or create a user profile.
    Creates a profile with default values if it doesn't exist.
    """
    try:
        return Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        # Create profile with default values
        profile = Profile.objects.create(
            user=user,
            full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
            email=user.email or '',
            user_status='user',
            phone='',
            address='Please update your profile information.'
        )
        return profile


# def register(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password1 = request.POST.get('password1')
#         password2 = request.POST.get('password2')

#         if password1 != password2:
#             messages.error(request, "Passwords do not match.")
#         elif User.objects.filter(username=username).exists():
#             messages.error(request, "Username is already taken.")
#         else:
#             # Create the user
#             user = User.objects.create_user(username=username, email=email, password=password1)
#             #login(request, user)
#             Profile.objects.create(user=user, user_status='visitor')

#             messages.success(request, "User registration was successful! You can login.")
#             return redirect('Login:user_login') 

#     return render(request, 'login/register.html',)




def user_login(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email')
        password = request.POST.get('password')
        user = authenticate(request, username=username_or_email, password=password)
        if user is not None:
            login(request, user)
            return redirect('Map:home')  # Redirect to desired URL after login
        else:
            # Handle invalid login
            return render(request, 'login/login.html', {'error_message': 'Invalid username/email or password'})
    else:
        return render(request, 'login/login.html')


def user_logout(request):
    logout(request)
    return redirect('Login:user_login')



@login_required
def profile(request):
    # Try to get existing profile, or create one if it doesn't exist
    user_profile = get_or_create_user_profile(request.user)
    
    # If profile was just created, show a message to the user
    if not user_profile.full_name or user_profile.address == 'Please update your profile information.':
        messages.info(request, "Please complete your profile information to get the full experience.")
    
    maps = Map.objects.filter(user=request.user)
    published_count = maps.filter(status='published').count()
    pending_count = maps.filter(status='pending').count()
    reject_count = maps.filter(status='reject').count()

    # Data for the pie chart
    labels = ['Published', 'Pending', 'Rejected']
    counts = [published_count, pending_count, reject_count]
    
    ## Create the pie chart
    #fig, ax = plt.subplots()
    #ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#36A2EB', '#FFCE56', '#FF6384'])
    #ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    ## Save the pie chart to a BytesIO object
    #buf = io.BytesIO()
    #plt.savefig(buf, format='png')
    #buf.seek(0)
    
    ## Encode the image as base64 so it can be rendered in the template
    #pie_chart_url = base64.b64encode(buf.getvalue()).decode('utf-8')
    #buf.close()

    # Pass data to the template
    context = {
        'profile': user_profile,
        'maps': maps,
        'published_count': published_count,
        'pending_count': pending_count,
        'reject_count': reject_count,
        #'pie_chart_url': pie_chart_url,
    }
    return render(request, 'login/profile.html', context)

@login_required
def dashboard(request):
    # Try to get existing profile, or create one if it doesn't exist
    user_profile = get_or_create_user_profile(request.user)
    
    # If profile was just created, show a message to the user
    if not user_profile.full_name or user_profile.address == 'Please update your profile information.':
        messages.info(request, "Please complete your profile information to get the full experience.")
    
    maps = Map.objects.filter(user=request.user)
    published_count = maps.filter(status='published').count()
    pending_count = maps.filter(status='pending').count()
    reject_count = maps.filter(status='reject').count()

    # Get user status safely
    user_status = user_profile.user_status if user_profile else 'user'
    
    # Handle form submission for map creation
    if request.method == 'POST' and request.user.is_authenticated:
        form = MapForm(request.POST, request.FILES)
        if form.is_valid():
            map_instance = form.save(commit=False)
            map_instance.user = request.user

            # Check user status for map approval
            if user_status not in ['administrator', 'admin']:
                map_instance.status = 'pending'
                messages.success(request, mark_safe('Your Map is <span style="color:#dc3545;">Pending</span> for Approval.'))
            else:
                map_instance.status = 'published'
                messages.success(request, mark_safe('Your Map is <span style="color:Green;">Published</span>.'))
            
            map_instance.save()

            # Handle multiple file uploads
            files = request.FILES.getlist('files[]')  # 'files[]' matches the input name in the form
            for file in files:
                map_file = MapFile(map=map_instance, file=file)
                map_file.save()

            return redirect('Login:dashboard')  # Redirect to the same page after submission
        else:
            messages.error(request, mark_safe('Your Map Submission Failed. Please check the form and try again.'))
    else:
        form = MapForm()  # Empty form for GET requests
    
    context = {
        'profile': user_profile,
        'maps': maps,
        'published_count': published_count,
        'pending_count': pending_count,
        'reject_count': reject_count,
        'form': form,
    }

    return render(request, 'login/dashboard.html', context)

# @login_required
# def edit_profile(request, username):
#     user = User.objects.get(username=username)
#     profile = Profile.objects.get(user=user)
#     if request.method == 'POST':
#         form = ProfileForm(request.POST, request.FILES)
#         if form.is_valid():
#             # Update profile fields with form data
#             profile.full_name = form.cleaned_data['full_name']
#             profile.phone = form.cleaned_data['phone']
#             profile.email = form.cleaned_data['email']
#             profile.address = form.cleaned_data['address']
#             if 'profile_picture' in request.FILES:
#                 profile.profile_picture = request.FILES['profile_picture']
#             profile.save()
#             #return redirect('profile')
#             return redirect('/user/profile/')
#     else:
#         form = ProfileForm(initial={
#             'full_name': profile.full_name,
#             'phone': profile.phone,
#             'email': profile.email,
#             'address': profile.address,
#         })
#         form.fields['profile_picture'].initial = profile.profile_picture.url  # Assuming profile_picture is a FileField
        
#     return render(request, 'login/edit_profile.html', {'form': form})

@login_required
def edit_profile(request, username):
    user = User.objects.get(username=username)
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        messages.error(request, "User profile does not exist. Please contact the administrator to set up your profile.")
        return render(request, 'login/profile_error.html', {
            'error_message': "User profile not found",
            'error_description': "The selected user doesn't have an associated profile. Please contact the administrator to complete the account setup."
        })
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('/user/profile/')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'login/edit_profile.html', {'form': form})


# Helper function to check if user is admin
def is_admin_user(user):
    """Check if user has admin privileges"""
    # Allow Django superusers
    if user.is_superuser:
        return True
    
    try:
        profile = Profile.objects.get(user=user)
        return profile.user_status in ['administrator', 'admin']
    except Profile.DoesNotExist:
        return False


def test_database_connection():
    """Test database connection and return status"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


def admin_required(view_func):
    """Decorator to require admin privileges for backup views"""
    def wrapper(request, *args, **kwargs):
        try:
            # Check if user is authenticated, with database safety
            if not request.user.is_authenticated:
                return redirect('Login:user_login')
            
            if not is_admin_user(request.user):
                messages.error(request, "Access denied. Administrator privileges required to access backup system.")
                return render(request, 'login/backup_access_denied.html', {
                    'error_message': "Access Denied",
                    'error_description': "You need administrator privileges to access the backup system. Please contact an administrator if you need access."
                })
            
            return view_func(request, *args, **kwargs)
            
        except Exception as e:
            # Handle database errors (like missing session table)
            error_str = str(e).lower()
            if 'django_session' in error_str and 'does not exist' in error_str:
                # Session table missing - likely during database restore
                messages.error(request, "Database session error. Please wait for system to complete setup.")
                
                # Try to apply migrations automatically
                try:
                    from django.core.management import call_command
                    print("Attempting to apply missing migrations...")
                    call_command('migrate', verbosity=0, interactive=False)
                    messages.info(request, "Database setup completed. Please refresh the page.")
                except Exception as migrate_error:
                    print(f"Migration failed: {migrate_error}")
                    messages.error(request, "Database setup failed. Please contact an administrator.")
                
                # Redirect to a safe page
                return redirect('/')
            else:
                # Other errors - re-raise
                raise e
    return wrapper


@admin_required
@session_safe_view
def backup_list(request):
    """Display list of all backups"""
    backups = Backup.objects.all()
    context = {
        'backups': backups,
        'backup_types': Backup.BACKUP_TYPE_CHOICES,
    }
    return render(request, 'login/backup_list.html', context)


@admin_required
def create_backup(request):
    """Create a new backup"""
    if request.method == 'POST':
        backup_type = request.POST.get('backup_type', 'full')
        description = request.POST.get('description', '')
        
        # Create backup record
        backup = Backup.objects.create(
            name=f"Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            backup_type=backup_type,
            created_by=request.user,
            description=description,
            status='in_progress'
        )
        
        try:
            # Create backup directory if not exists
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file_path = os.path.join(backup_dir, f"{backup.name}.zip")
            
            with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                if backup_type in ['database', 'full']:
                    # Create database dump
                    print(f"Creating database backup for type: {backup_type}")
                    print(f"Database engine: {settings.DATABASES['default']['ENGINE']}")
                    
                    db_dump_path = create_database_dump()
                    if db_dump_path:
                        print(f"Database dump created at: {db_dump_path}")
                        print(f"Dump file size: {os.path.getsize(db_dump_path)} bytes")
                        
                        # Use appropriate filename based on database type
                        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
                            zipf.write(db_dump_path, 'database.db')
                            print("Added database.db to backup")
                        else:  # PostgreSQL
                            zipf.write(db_dump_path, 'database.sql')
                            print("Added database.sql to backup")
                        os.remove(db_dump_path)  # Clean up temp file
                        print("Temporary dump file cleaned up")
                    else:
                        print("ERROR: Database dump creation failed!")
                        backup.status = 'failed'
                        backup.save()
                        messages.error(request, "Database backup creation failed!")
                        return redirect('Login:backup_list')
                
                if backup_type in ['media', 'full']:
                    # Add media files
                    media_root = settings.MEDIA_ROOT
                    for root, dirs, files in os.walk(media_root):
                        # Skip the backups directory to avoid recursive backup
                        if 'backups' in dirs:
                            dirs.remove('backups')
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, media_root)
                            zipf.write(file_path, f"media/{arcname}")
            
            # Update backup record
            backup.file_path = backup_file_path
            backup.file_size = os.path.getsize(backup_file_path)
            backup.status = 'completed'
            backup.completed_at = timezone.now()
            backup.save()
            
            messages.success(request, f"Backup '{backup.name}' created successfully!")
            
        except Exception as e:
            backup.status = 'failed'
            backup.error_message = str(e)
            backup.save()
            messages.error(request, f"Backup failed: {str(e)}")
        
        return redirect('Login:backup_list')
    
    return render(request, 'login/create_backup.html')


@admin_required
@session_safe_view
def restore_backup(request, backup_id):
    """Restore from a backup"""
    backup = get_object_or_404(Backup, id=backup_id)
    
    if request.method == 'POST':
        # Set a flag to indicate we're in restore mode
        restore_in_progress = True
        
        try:
            print(f"Starting restore of backup: {backup.name}")
            print(f"Backup file path: {backup.file_path}")
            print(f"Backup type: {backup.backup_type}")
            
            # Clear session data before restore to prevent session table access issues
            if hasattr(request, 'session'):
                request.session.clear()
                request.session.modified = False
                # Set a flag to prevent session saving during this request
                request.session._session_restore_mode = True
            
            if not backup.file_exists:
                messages.error(request, "Backup file not found on disk!")
                # Create a response that won't try to save session data
                response = redirect('Login:backup_list')
                if hasattr(request, 'session'):
                    request.session.modified = False
                return response
            
            if not os.path.exists(backup.file_path):
                messages.error(request, f"Backup file not found at: {backup.file_path}")
                return redirect('Login:backup_list')
            
            # Test if file is a valid ZIP
            try:
                with zipfile.ZipFile(backup.file_path, 'r') as test_zip:
                    file_list = test_zip.namelist()
                    print(f"Backup contains files: {file_list}")
            except zipfile.BadZipFile:
                messages.error(request, "Backup file is corrupted or not a valid ZIP file!")
                return redirect('Login:backup_list')
            
            # Inspect backup file for debugging
            inspect_backup_file(backup.file_path)
            
            # Extract backup
            temp_dir = tempfile.mkdtemp()
            print(f"Extracting backup to: {temp_dir}")
            
            try:
                with zipfile.ZipFile(backup.file_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # List extracted files
                extracted_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        extracted_files.append(os.path.join(root, file))
                print(f"Extracted files: {extracted_files}")
                
                restore_success = True
                
                # Restore database if backup includes it
                if backup.backup_type in ['database', 'full']:
                    db_file_db = os.path.join(temp_dir, 'database.db')
                    db_file_sql = os.path.join(temp_dir, 'database.sql')
                    
                    print(f"Looking for database files:")
                    print(f"  SQLite file: {db_file_db} - exists: {os.path.exists(db_file_db)}")
                    print(f"  SQL file: {db_file_sql} - exists: {os.path.exists(db_file_sql)}")
                    
                    database_restored = False
                    
                    # For PostgreSQL, always use SQL dump
                    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
                        if os.path.exists(db_file_sql):
                            print("Found database.sql file for PostgreSQL, attempting restore...")
                            if restore_database(db_file_sql, 'sql_dump'):
                                database_restored = True
                                print("PostgreSQL database restored successfully")
                            else:
                                restore_success = False
                                messages.error(request, "PostgreSQL database restore failed!")
                        elif os.path.exists(db_file_db):
                            # This might be a backup from when system was using SQLite
                            print("Found database.db file, but PostgreSQL needs SQL. Attempting conversion...")
                            messages.warning(request, "Backup contains SQLite database but system uses PostgreSQL. Database restore skipped.")
                            print("Warning: SQLite backup found but PostgreSQL system - skipping database restore")
                        else:
                            print("No database.sql file found in backup for PostgreSQL")
                            if backup.backup_type == 'database':
                                messages.error(request, "No PostgreSQL database file found in backup!")
                                restore_success = False
                            else:  # backup_type == 'full'
                                messages.warning(request, "No database file found in backup, but media files may be restored.")
                    
                    # For SQLite, prefer .db file but fall back to .sql
                    else:
                        if os.path.exists(db_file_db):
                            print("Found database.db file, attempting restore...")
                            if restore_database(db_file_db, 'sqlite_file'):
                                database_restored = True
                                print("SQLite database restored successfully")
                            else:
                                restore_success = False
                                messages.error(request, "Database restore failed!")
                        elif os.path.exists(db_file_sql):
                            print("Found database.sql file, attempting restore...")
                            if restore_database(db_file_sql, 'sql_dump'):
                                database_restored = True
                                print("SQLite database restored successfully")
                            else:
                                restore_success = False
                                messages.error(request, "Database restore failed!")
                        else:
                            print("No database file found in backup")
                            if backup.backup_type == 'database':
                                messages.error(request, "No database file found in backup!")
                                restore_success = False
                            else:  # backup_type == 'full'
                                messages.warning(request, "No database file found in backup, but media files may be restored.")
                    
                    if database_restored:
                        messages.success(request, "Database restored successfully!")
                    elif backup.backup_type == 'database' and not database_restored:
                        print("Database backup type but no database restored - this is an error")
                        restore_success = False
                
                # Restore media files if backup includes them
                if backup.backup_type in ['media', 'full']:
                    media_dir = os.path.join(temp_dir, 'media')
                    if os.path.exists(media_dir):
                        print("Found media directory, attempting restore...")
                        if not restore_media_files(media_dir):
                            restore_success = False
                            messages.error(request, "Media files restore failed!")
                    else:
                        print("No media directory found in backup")
                        if backup.backup_type == 'media':
                            messages.error(request, "No media files found in backup!")
                            restore_success = False
                
                if restore_success:
                    # After successful database restore, run migrations to ensure all Django tables exist
                    if backup.backup_type in ['database', 'full']:
                        try:
                            from django.core.management import call_command
                            print("Running migrations with --run-syncdb after restore to ensure all Django tables exist...")
                            call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
                            print("Migrations completed successfully after restore")
                        except Exception as migrate_error:
                            print(f"Migration after restore failed: {migrate_error}")
                            messages.warning(request, f"Database restored but migration failed: {migrate_error}")
                    
                    # Test database connection after restore
                    try:
                        from django.db import connections
                        connections.close_all()  # Force new connections
                        
                        # Test database connection
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT 1")
                            cursor.fetchone()
                        
                        messages.success(request, f"Backup '{backup.name}' restored successfully!")
                        print("Restore completed successfully - database connection verified")
                        
                        # After successful restore, prevent session saving completely
                        restore_success_flag = True
                        
                    except Exception as db_error:
                        print(f"Database connection test failed after restore: {db_error}")
                        messages.warning(request, f"Backup '{backup.name}' restored but database connection issues detected. You may need to restart the server.")
                        restore_success_flag = True  # Still consider it successful
                        
                else:
                    messages.error(request, f"Restore of '{backup.name}' completed with errors!")
                    print("Restore completed with errors")
                    restore_success_flag = False
                
            finally:
                # Clean up temporary directory
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temp directory: {temp_dir}")
                except:
                    print(f"Failed to clean up temp directory: {temp_dir}")
            
        except Exception as e:
            print(f"Restore failed with exception: {str(e)}")
            
            # Handle session errors specifically
            error_str = str(e).lower()
            if 'django_session' in error_str and 'does not exist' in error_str:
                print("Session table error during restore - this is expected")
                messages.info(request, f"Database restore completed. The system is applying migrations...")
                
                # Try to apply migrations with run-syncdb to recreate all tables
                try:
                    from django.core.management import call_command
                    print("Applying migrations with --run-syncdb to recreate all Django tables...")
                    call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
                    messages.success(request, f"Backup '{backup.name}' restored successfully! Database setup completed.")
                except Exception as migrate_error:
                    print(f"Migration after restore failed: {migrate_error}")
                    messages.warning(request, f"Backup restored but migrations failed: {migrate_error}")
            else:
                messages.error(request, f"Restore failed: {str(e)}")
        
        # Create a special response that bypasses session saving
        return create_session_safe_response(request)
    
    context = {'backup': backup}
    return render(request, 'login/restore_backup.html', context)


def create_session_safe_response(request):
    """Create a response that doesn't try to save session data"""
    try:
        # Clear any session data and mark as not modified
        if hasattr(request, 'session'):
            request.session.clear()
            request.session.modified = False
            request.session.accessed = False
        
        # Create the redirect response
        response = redirect('Login:backup_list')
        
        # Add a custom header to indicate session should not be saved
        response['X-No-Session-Save'] = 'true'
        
        return response
        
    except Exception as e:
        print(f"Error creating session-safe response: {e}")
        # Fallback to a simple HTTP response
        from django.http import HttpResponseRedirect
        response = HttpResponseRedirect('/user/backups/')
        response['X-No-Session-Save'] = 'true'
        return response


@admin_required
def upload_backup(request):
    """Upload and restore from backup file"""
    if request.method == 'POST' and request.FILES.get('backup_file'):
        backup_file = request.FILES['backup_file']
        description = request.POST.get('description', '')
        
        try:
            print(f"Uploading backup file: {backup_file.name}")
            print(f"File size: {backup_file.size} bytes")
            
            # Validate file is a ZIP
            if not backup_file.name.lower().endswith('.zip'):
                messages.error(request, "Please upload a ZIP file!")
                return redirect('Login:upload_backup')
            
            # Save uploaded file
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate unique filename if file exists
            base_name = backup_file.name
            counter = 1
            file_path = os.path.join(backup_dir, base_name)
            while os.path.exists(file_path):
                name, ext = os.path.splitext(base_name)
                file_path = os.path.join(backup_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # Save the file
            with open(file_path, 'wb+') as destination:
                for chunk in backup_file.chunks():
                    destination.write(chunk)
            
            print(f"File saved to: {file_path}")
            
            # Validate the uploaded ZIP file
            try:
                with zipfile.ZipFile(file_path, 'r') as test_zip:
                    file_list = test_zip.namelist()
                    print(f"Uploaded backup contains: {file_list}")
            except zipfile.BadZipFile:
                os.remove(file_path)  # Clean up invalid file
                messages.error(request, "Uploaded file is not a valid ZIP file!")
                return redirect('Login:upload_backup')
            
            # Determine backup type based on contents
            backup_type = 'full'  # Default
            if 'database.db' in file_list or 'database.sql' in file_list:
                if any('media/' in f for f in file_list):
                    backup_type = 'full'
                else:
                    backup_type = 'database'
            elif any('media/' in f for f in file_list):
                backup_type = 'media'
            
            # Create backup record
            backup = Backup.objects.create(
                name=f"Uploaded_{os.path.basename(file_path)}",
                backup_type=backup_type,
                created_by=request.user,
                description=description or f"Uploaded backup file: {backup_file.name}",
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                status='completed',
                completed_at=timezone.now()
            )
            
            print(f"Backup record created: {backup.id}")
            
            # Option to restore immediately
            if request.POST.get('restore_immediately'):
                messages.info(request, "Backup uploaded! Redirecting to restore...")
                return redirect('Login:restore_backup', backup_id=backup.id)
            
            messages.success(request, f"Backup uploaded successfully! Type detected: {backup_type}")
            
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            messages.error(request, f"Upload failed: {str(e)}")
        
        return redirect('Login:backup_list')
    
    return render(request, 'login/upload_backup.html')


def inspect_backup_file(file_path):
    """Debug function to inspect backup file contents"""
    try:
        print(f"Inspecting backup file: {file_path}")
        if not os.path.exists(file_path):
            print("ERROR: Backup file does not exist!")
            return
        
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size} bytes")
        
        with zipfile.ZipFile(file_path, 'r') as zipf:
            file_list = zipf.namelist()
            print(f"Files in backup:")
            for f in file_list:
                print(f"  - {f}")
            
            # Check if database files exist
            has_db_sql = 'database.sql' in file_list
            has_db_db = 'database.db' in file_list
            print(f"Contains database.sql: {has_db_sql}")
            print(f"Contains database.db: {has_db_db}")
            
            # Check for media files
            media_files = [f for f in file_list if f.startswith('media/')]
            print(f"Media files count: {len(media_files)}")
            
    except Exception as e:
        print(f"Error inspecting backup file: {e}")


@admin_required
def download_backup(request, backup_id):
    """Download backup file"""
    backup = get_object_or_404(Backup, id=backup_id)
    
    if not backup.file_exists:
        messages.error(request, "Backup file not found!")
        return redirect('Login:backup_list')
    
    try:
        response = FileResponse(
            open(backup.file_path, 'rb'),
            as_attachment=True,
            filename=f"{backup.name}.zip"
        )
        return response
    except Exception as e:
        messages.error(request, f"Download failed: {str(e)}")
        return redirect('Login:backup_list')


@admin_required
def delete_backup(request, backup_id):
    """Delete backup"""
    backup = get_object_or_404(Backup, id=backup_id)
    
    if request.method == 'POST':
        try:
            backup.delete_file()  # Delete file from disk
            backup.delete()  # Delete record from database
            messages.success(request, f"Backup '{backup.name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Delete failed: {str(e)}")
    
    return redirect('Login:backup_list')


# Helper functions
def create_database_dump():
    """Create database dump and return file path"""
    try:
        db_settings = settings.DATABASES['default']
        
        # For PostgreSQL database
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
            # Try Django-based backup first, then fall back to command line
            try:
                return create_postgresql_dump_with_django()
            except Exception as django_error:
                print(f"Django-based backup failed: {django_error}")
                print("Falling back to command-line backup...")
                return create_postgresql_dump_with_commands()
            
        # For SQLite database, we'll copy the entire database file
        elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            db_path = settings.DATABASES['default']['NAME']
            
            # Create a temporary copy of the database file
            temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_file.close()  # Close the file so we can copy to it
            
            shutil.copy2(db_path, temp_file.name)
            return temp_file.name
        
        return None
        
    except Exception as e:
        print(f"Database dump failed: {e}")
        return None


def create_postgresql_dump_with_django():
    """Create PostgreSQL dump using Django database connection"""
    try:
        print("Creating PostgreSQL dump using Django...")
        
        # Check if psycopg2 is available
        try:
            import psycopg2
            print("psycopg2 module is available")
        except ImportError:
            print("ERROR: psycopg2 module not available, falling back to command-line")
            raise Exception("psycopg2 not available")
        
        from django.db import connection
        
        db_settings = settings.DATABASES['default']
        print(f"Connecting to PostgreSQL: {db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8')
        temp_file_path = temp_file.name
        temp_file.close()
        
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
        
        # Get all table names
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables to backup")
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("-- PostgreSQL database dump created by Django backup system\n")
            f.write("-- Database: {}\n".format(db_settings['NAME']))
            f.write("-- Created: {}\n\n".format(timezone.now().isoformat()))
            
            # For each table, write DROP and CREATE statements
            for (table_name,) in tables:
                print(f"Backing up table: {table_name}")
                
                try:
                    # Get table schema using a simpler approach
                    cursor.execute(f"""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        ORDER BY ordinal_position;
                    """)
                    columns = cursor.fetchall()
                    
                    if columns:
                        f.write(f"-- Table: {table_name}\n")
                        f.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
                        f.write(f"CREATE TABLE {table_name} (\n")
                        col_defs = []
                        for col_name, data_type, is_nullable, col_default in columns:
                            col_def = f"    {col_name} {data_type}"
                            if is_nullable == 'NO':
                                col_def += " NOT NULL"
                            if col_default:
                                col_def += f" DEFAULT {col_default}"
                            col_defs.append(col_def)
                        f.write(",\n".join(col_defs))
                        f.write("\n);\n\n")
                    
                    # Get table data
                    cursor.execute(f'SELECT * FROM "{table_name}"')
                    rows = cursor.fetchall()
                    
                    if rows:
                        # Get column names
                        cursor.execute(f"""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            ORDER BY ordinal_position;
                        """)
                        column_names = [row[0] for row in cursor.fetchall()]
                        
                        f.write(f"-- Table: {table_name} ({len(rows)} rows)\n")
                        
                        # Write INSERT statements individually for better compatibility
                        for i, row in enumerate(rows):
                            values = []
                            for value in row:
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    escaped_value = value.replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                                elif hasattr(value, 'isoformat'):  # datetime, date, time objects
                                    values.append(f"'{value.isoformat()}'")
                                else:
                                    values.append(str(value))
                            
                            # Build column names with quotes
                            quoted_columns = [f'"{col}"' for col in column_names]
                            column_list = ', '.join(quoted_columns)
                            values_list = ', '.join(values)
                            
                            f.write(f'INSERT INTO "{table_name}" ({column_list}) VALUES ({values_list});\n')
                        
                        f.write(f"\n")
                        print(f"  - Backed up {len(rows)} rows")
                    else:
                        print(f"  - Table {table_name} is empty")
                        
                except Exception as table_error:
                    print(f"Error backing up table {table_name}: {table_error}")
                    f.write(f"-- ERROR backing up table {table_name}: {table_error}\n\n")
        
        cursor.close()
        pg_connection.close()
        
        # Check file size
        file_size = os.path.getsize(temp_file_path)
        print(f"Django-based PostgreSQL dump created: {temp_file_path} ({file_size} bytes)")
        
        if file_size == 0:
            print("ERROR: Dump file is empty!")
            os.remove(temp_file_path)
            raise Exception("Dump file is empty")
        
        return temp_file_path
        
    except Exception as e:
        print(f"Django-based PostgreSQL dump failed: {e}")
        raise


def create_postgresql_dump_with_commands():
    """Create PostgreSQL dump using command-line tools"""
    try:
        print("Creating PostgreSQL dump using command-line tools...")
        
        db_settings = settings.DATABASES['default']
        temp_file = tempfile.NamedTemporaryFile(suffix='.sql', delete=False)
        temp_file.close()  # Close so pg_dump can write to it
        
        # Set up environment variables for PostgreSQL
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        # pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '--host', db_settings['HOST'],
            '--port', str(db_settings['PORT']),
            '--username', db_settings['USER'],
            '--dbname', db_settings['NAME'],
            '--no-password',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            '--file', temp_file.name
        ]
        
        print(f"Running pg_dump command: {' '.join(pg_dump_cmd)}")
        result = subprocess.run(pg_dump_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"pg_dump failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        print(f"Command-line PostgreSQL dump created: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"Command-line PostgreSQL dump failed: {e}")
        raise


def restore_database(db_file_path, restore_type='sqlite_file'):
    """Restore database from backup file"""
    try:
        db_settings = settings.DATABASES['default']
        
        # For PostgreSQL database
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
            print(f"Restoring PostgreSQL database from: {db_file_path}")
            
            # Close all database connections
            from django.db import connections
            from django.core.management import call_command
            
            # Close connections and clear connection cache
            for conn in connections.all():
                conn.close()
            connections.close_all()
            
            # Try using Django's database operations for PostgreSQL restore
            try:
                result = restore_postgresql_with_django(db_file_path)
                
                # Force Django to reinitialize database connections
                connections.close_all()
                
                # Clear Django's cache to prevent stale references
                from django.core.cache import cache
                cache.clear()
                
                # Run migrations with --run-syncdb to ensure all Django tables exist
                print("Running migrations with --run-syncdb after restore...")
                call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
                
                # Clear connections again after migrations
                connections.close_all()
                
                print("PostgreSQL restore and migrations completed successfully")
                return result
                
            except Exception as django_error:
                print(f"Django-based restore failed: {django_error}")
                print("Falling back to command-line restore...")
                
                try:
                    result = restore_postgresql_with_commands(db_file_path)
                    
                    # Force Django to reinitialize database connections
                    connections.close_all()
                    
                    # Clear Django's cache to prevent stale references
                    from django.core.cache import cache
                    cache.clear()
                    
                    # Run migrations with --run-syncdb to ensure all Django tables exist
                    print("Running migrations with --run-syncdb after restore...")
                    call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
                    
                    # Clear connections again after migrations
                    connections.close_all()
                    
                    print("PostgreSQL command-line restore and migrations completed successfully")
                    return result
                    
                except Exception as cmd_error:
                    print(f"Command-line restore also failed: {cmd_error}")
                    raise cmd_error
            
        # For SQLite database
        elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            db_path = settings.DATABASES['default']['NAME']
            
            # Create a backup of current database before restore
            backup_db = f"{db_path}.restore_backup_{int(timezone.now().timestamp())}"
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_db)
                print(f"Current database backed up to: {backup_db}")
            
            if restore_type == 'sqlite_file':
                # Direct file replacement for SQLite
                print(f"Restoring database from: {db_file_path}")
                print(f"Target database: {db_path}")
                
                # Close all database connections
                from django.db import connections
                for conn in connections.all():
                    conn.close()
                
                # Replace the database file
                if os.path.exists(db_file_path):
                    shutil.copy2(db_file_path, db_path)
                    print("Database file replaced successfully")
                else:
                    raise Exception(f"Backup database file not found: {db_file_path}")
                    
            else:  # sql_dump (fallback)
                print("Using SQL dump restore method")
                # Close connections
                from django.db import connections
                for conn in connections.all():
                    conn.close()
                
                # Replace database with SQL dump
                if os.path.exists(db_path):
                    os.remove(db_path)
                
                # Import the SQL dump
                if os.path.exists(db_file_path):
                    with open(db_file_path, 'r') as f:
                        subprocess.run(['sqlite3', db_path], stdin=f, check=True)
                else:
                    raise Exception(f"SQL dump file not found: {db_file_path}")
            
            print("Database restore completed successfully")
            return True
        
        return False
        
    except Exception as e:
        print(f"Database restore failed: {e}")
        return False


def restore_postgresql_with_django(db_file_path):
    """Restore PostgreSQL database using Django database operations"""
    try:
        print("Attempting Django-based PostgreSQL restore...")
        
        from django.db import connection
        from django.core.management import call_command
        import psycopg2
        
        db_settings = settings.DATABASES['default']
        
        # Read the SQL file
        with open(db_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"Read SQL file, content length: {len(sql_content)} characters")
        
        # Connect directly to PostgreSQL to drop/recreate database
        admin_connection = psycopg2.connect(
            host=db_settings['HOST'],
            port=db_settings['PORT'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            database='postgres'  # Connect to postgres db for admin operations
        )
        admin_connection.autocommit = True
        admin_cursor = admin_connection.cursor()
        
        # Terminate connections to target database
        print("Terminating connections to target database...")
        admin_cursor.execute(f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{db_settings['NAME']}' AND pid <> pg_backend_pid();
        """)
        
        # Drop and recreate database
        print(f"Dropping database: {db_settings['NAME']}")
        admin_cursor.execute(f'DROP DATABASE IF EXISTS "{db_settings['NAME']}"')
        
        print(f"Creating database: {db_settings['NAME']}")
        admin_cursor.execute(f'CREATE DATABASE "{db_settings['NAME']}"')
        
        admin_cursor.close()
        admin_connection.close()
        
        # Connect to the new database and execute the restore SQL
        print("Connecting to restored database...")
        restore_connection = psycopg2.connect(
            host=db_settings['HOST'],
            port=db_settings['PORT'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            database=db_settings['NAME']
        )
        restore_connection.autocommit = True
        restore_cursor = restore_connection.cursor()
        
        # Execute the SQL content
        print("Executing restore SQL...")
        restore_cursor.execute(sql_content)
        
        restore_cursor.close()
        restore_connection.close()
        
        # Apply Django migrations with --run-syncdb to ensure all system tables exist
        print("Applying Django migrations with --run-syncdb...")
        try:
            from django.core.management import call_command
            from io import StringIO
            
            # Capture migration output
            migration_output = StringIO()
            call_command('migrate', '--verbosity=0', '--run-syncdb', stdout=migration_output, stderr=migration_output)
            print("Migrations with --run-syncdb applied successfully")
        except Exception as migration_error:
            print(f"Warning: Migration error (may be expected): {migration_error}")
            # Try without run-syncdb as fallback
            try:
                call_command('migrate', '--verbosity=0', stdout=migration_output, stderr=migration_output)
                print("Fallback migrations applied successfully")
            except Exception as fallback_error:
                print(f"Fallback migration also failed: {fallback_error}")
        
        print("Django-based PostgreSQL restore completed successfully")
        return True
        
    except Exception as e:
        print(f"Django-based PostgreSQL restore failed: {e}")
        raise


def restore_postgresql_with_commands(db_file_path):
    """Restore PostgreSQL database using command-line tools"""
    try:
        print("Attempting command-line PostgreSQL restore...")
        
        db_settings = settings.DATABASES['default']
        
        # Set up environment variables for PostgreSQL
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        # First, terminate all connections to the database
        terminate_connections_cmd = [
            'psql',
            '--host', db_settings['HOST'],
            '--port', str(db_settings['PORT']),
            '--username', db_settings['USER'],
            '--dbname', 'postgres',  # Connect to postgres db to run admin commands
            '--no-password',
            '--command', f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_settings['NAME']}' AND pid <> pg_backend_pid();"
        ]
        
        print("Terminating existing database connections...")
        result = subprocess.run(terminate_connections_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: Could not terminate connections: {result.stderr}")
        
        # Drop and recreate the database
        drop_db_cmd = [
            'psql',
            '--host', db_settings['HOST'],
            '--port', str(db_settings['PORT']),
            '--username', db_settings['USER'],
            '--dbname', 'postgres',
            '--no-password',
            '--command', f"DROP DATABASE IF EXISTS \"{db_settings['NAME']}\";"
        ]
        
        print(f"Dropping database: {db_settings['NAME']}")
        result = subprocess.run(drop_db_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Drop database failed: {result.stderr}")
            raise Exception(f"Failed to drop database: {result.stderr}")
        
        # Create fresh database
        create_db_cmd = [
            'psql',
            '--host', db_settings['HOST'],
            '--port', str(db_settings['PORT']),
            '--username', db_settings['USER'],
            '--dbname', 'postgres',
            '--no-password',
            '--command', f"CREATE DATABASE \"{db_settings['NAME']}\";"
        ]
        
        print(f"Creating database: {db_settings['NAME']}")
        result = subprocess.run(create_db_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Create database failed: {result.stderr}")
            raise Exception(f"Failed to create database: {result.stderr}")
        
        # Restore from SQL dump
        restore_cmd = [
            'psql',
            '--host', db_settings['HOST'],
            '--port', str(db_settings['PORT']),
            '--username', db_settings['USER'],
            '--dbname', db_settings['NAME'],
            '--no-password',
            '--file', db_file_path
        ]
        
        print("Restoring database from SQL dump...")
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Database restore failed: {result.stderr}")
            raise Exception(f"Failed to restore database: {result.stderr}")
        
        print("Command-line PostgreSQL restore completed successfully")
        return True
        
    except Exception as e:
        print(f"Command-line PostgreSQL restore failed: {e}")
        raise


def restore_media_files(media_backup_dir):
    """Restore media files from backup"""
    try:
        current_media = settings.MEDIA_ROOT
        
        # Create a backup of current media directory
        backup_media = f"{current_media}_restore_backup_{int(timezone.now().timestamp())}"
        
        if os.path.exists(current_media):
            print(f"Backing up current media to: {backup_media}")
            shutil.copytree(current_media, backup_media)
        
        # Clear current media directory (except backups folder)
        if os.path.exists(current_media):
            for item in os.listdir(current_media):
                item_path = os.path.join(current_media, item)
                if item != 'backups':  # Preserve backups folder
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
        else:
            os.makedirs(current_media, exist_ok=True)
        
        # Copy restored files
        print(f"Restoring media files from: {media_backup_dir}")
        for root, dirs, files in os.walk(media_backup_dir):
            for file in files:
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, media_backup_dir)
                dest_file = os.path.join(current_media, rel_path)
                
                # Create directory if not exists
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy2(src_file, dest_file)
                print(f"Restored: {rel_path}")
        
        print("Media files restore completed successfully")
        return True
        
    except Exception as e:
        print(f"Media files restore failed: {e}")
        return False

# Debug view for database connection

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
