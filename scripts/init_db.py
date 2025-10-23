import os
import sqlite3
from pathlib import Path

def init_database():
    # Create database directory if it doesn't exist
    db_dir = Path(__file__).parent
    db_path = db_dir / "hamna.db"
    schema_path = db_dir / "init_schema.sql"
    
    # Check if database already exists
    if db_path.exists():
        print(f"Database already exists at {db_path}")
        return
    
    # Create database file
    db_path.touch()
    print(f"Created database at {db_path}")
    
    # Read and execute schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Connect to the database and execute the schema
    conn = sqlite3.connect(str(db_path))
    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Execute schema SQL
        conn.executescript(schema_sql)
        conn.commit()
        print("Database schema created successfully.")
        
        # Verify the schema was created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nTables created:")
        for table in tables:
            print(f"- {table[0]}")
            
        # Verify initial data
        cursor.execute("SELECT * FROM eventos_type;")
        print("\nEvent types:")
        for row in cursor.fetchall():
            print(f"- {row[0]}: {row[1]}")
            
        cursor.execute("SELECT * FROM tipos_seccion;")
        print("\nSection types:")
        for row in cursor.fetchall():
            print(f"- {row[0]}: {row[1]}")
            
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()
