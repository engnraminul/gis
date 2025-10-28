# PostgreSQL Setup Guide for GIS Project

This guide will help you set up PostgreSQL with proper permissions for the Django GIS project.

## Problem
The error `permission denied for schema public` occurs when the PostgreSQL user doesn't have sufficient privileges to create tables.

## Solutions

### Option 1: Grant Permissions to Existing User
If you want to keep using the 'gis' user, run these SQL commands as a superuser:

```sql
-- Connect to PostgreSQL as superuser (postgres)
psql -U postgres

-- Grant privileges to the gis user
GRANT CREATE ON SCHEMA public TO gis;
GRANT USAGE ON SCHEMA public TO gis;
GRANT ALL PRIVILEGES ON DATABASE gis TO gis;

-- Make gis user owner of the database
ALTER DATABASE gis OWNER TO gis;
```

### Option 2: Create Database and User with Proper Privileges
```sql
-- Connect as superuser
psql -U postgres

-- Create database
CREATE DATABASE gis;

-- Create user with necessary privileges
CREATE USER gis WITH PASSWORD 'gis123';
ALTER USER gis CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE gis TO gis;

-- Connect to the gis database
\c gis

-- Grant schema permissions
GRANT CREATE ON SCHEMA public TO gis;
GRANT USAGE ON SCHEMA public TO gis;
```

### Option 3: Use Superuser (Not Recommended for Production)
Update settings.py to use the postgres superuser:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'gis',
        'USER': 'postgres',  # Use superuser
        'PASSWORD': 'your_postgres_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Testing the Connection
```bash
# Test connection
python manage.py dbshell

# If successful, run migrations
python manage.py migrate
```

## Recommended for Development
For development purposes, SQLite is recommended as it:
- Requires no setup
- Works out of the box
- Is included with Python
- Perfect for development and testing

For production, PostgreSQL with PostGIS extension is recommended for GIS applications.

## Current Configuration
The project is currently configured to use SQLite for easier development setup.