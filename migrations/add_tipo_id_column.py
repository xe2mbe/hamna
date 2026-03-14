import os
import sqlite3

def add_tipo_id_column():
    """Add the 'tipo_id' column to the 'secciones' table if it doesn't exist"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(secciones)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'tipo_id' not in columns:
            print("[INFO] Adding 'tipo_id' column to 'secciones' table")
            
            # Add the column with a default value of 1 (assuming 1 is the ID for 'tts')
            cursor.execute('''
            ALTER TABLE secciones
            ADD COLUMN tipo_id INTEGER DEFAULT 1
            REFERENCES tipos_seccion(id)
            ''')
            
            # Update existing rows to use the default value
            cursor.execute('''
            UPDATE secciones SET tipo_id = 1 WHERE tipo_id IS NULL
            ''')
            
            conn.commit()
            print("[SUCCESS] 'tipo_id' column added to 'secciones' table")
        else:
            print("[INFO] 'tipo_id' column already exists in 'secciones' table")
        
    except Exception as e:
        print(f"[ERROR] Error during database update: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Starting database update ===")
    add_tipo_id_column()
    print("=== Database update completed ===")
