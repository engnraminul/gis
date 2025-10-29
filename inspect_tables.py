#!/usr/bin/env python
"""
Simple PostgreSQL table inspector
"""
import psycopg2

def inspect_postgresql_tables():
    """Inspect PostgreSQL tables"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='gis',
            user='gis',
            password='gis1234'
        )
        print("✓ PostgreSQL connection successful!")
        
        cursor = conn.cursor()
        
        # Get all tables with proper quoting
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            try:
                # Use proper quoting for table names
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} rows")
            except Exception as e:
                print(f"  - {table_name}: Error - {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    inspect_postgresql_tables()