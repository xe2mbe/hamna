import sqlite3
import os

def add_duracion_seg_column():
    """Add the 'duracion_seg' column to the 'seccion_tts' table if it doesn't exist"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(seccion_tts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'duracion_seg' not in columns:
            print("[INFO] Adding 'duracion_seg' column to 'seccion_tts' table")
            
            # Add the column with a default value of 0
            cursor.execute('''
            ALTER TABLE seccion_tts
            ADD COLUMN duracion_seg REAL DEFAULT 0
            ''')
            
            conn.commit()
            print("[SUCCESS] 'duracion_seg' column added to 'seccion_tts' table")
        else:
            print("[INFO] 'duracion_seg' column already exists in 'seccion_tts' table")
        
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
    add_duracion_seg_column()
    print("=== Database update completed ===")
