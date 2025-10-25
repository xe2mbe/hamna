import sqlite3
from pathlib import Path

def check_database():
    """Check the database structure"""
    db_path = Path("database/hamna.db")
    if not db_path.exists():
        print(f"Database file does not exist at {db_path.absolute()}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            try:
                # Get table info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print("Columns:")
                for col in columns:
                    print(f"  {col[1]} ({col[2]})")
                
                # Show first few rows
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    rows = cursor.fetchall()
                    if rows:
                        print("Sample data:")
                        for row in rows:
                            print(f"  {row}")
                except sqlite3.Error as e:
                    print(f"  Could not fetch sample data: {e}")
                    
            except sqlite3.Error as e:
                print(f"  Error getting columns: {e}")
    except sqlite3.Error as e:
        print(f"Error checking database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database()
