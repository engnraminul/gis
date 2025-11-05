# Backup Restore Fix - Session and Auth Tables

## Issue
After restoring a database backup, users encountered this error when trying to login:

```
ProgrammingError at /user/login/
relation "auth_user" does not exist
LINE 1: ...user"."is_active", "auth_user"."date_joined" FROM "auth_user...
```

## Root Cause
The backup restore process was dropping and recreating the entire database from the SQL backup, but the backup only contained the data that existed at the time of backup creation. Essential Django system tables like `auth_user`, `django_session`, etc. were missing from the restored database.

## Fix Applied
Modified the restore functions in `Login/views.py` to ensure that after database restoration, Django migrations are run with the `--run-syncdb` flag:

### Changes Made:

1. **Enhanced `restore_database()` function**: Added migration step with `--run-syncdb` after successful database restore

2. **Updated `restore_postgresql_with_django()` function**: Changed migration command to include `--run-syncdb` flag

3. **Enhanced `restore_backup()` function**: Added migration step specifically for database/full backups after restoration

4. **Improved error handling**: Session errors during restore now trigger automatic migration with `--run-syncdb`

### Key Fix Points:

```python
# Before (old code)
call_command('migrate', verbosity=0, interactive=False)

# After (fixed code)  
call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
```

## Why `--run-syncdb` is Essential
The `--run-syncdb` flag ensures that Django creates all system tables that don't have explicit migrations, including:
- `auth_user` - User authentication table
- `django_session` - Session management table  
- Other Django system tables

Without this flag, these essential tables would be missing after restore, causing authentication and session errors.

## Testing
✅ Verified that migrations with `--run-syncdb` work correctly
✅ Confirmed `auth_user` table is accessible after the fix
✅ Django User ORM functionality works after restore
✅ Session handling works properly

## Result
Users can now restore backups without encountering the "relation auth_user does not exist" error. The system automatically ensures all Django system tables are available after database restoration.