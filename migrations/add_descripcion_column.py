import os
import sqlite3

def add_descripcion_column():
    """Add the 'descripcion' column to the 'secciones' table if it doesn't exist"""
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
        
        if 'descripcion' not in columns:
            print("[INFO] Adding 'descripcion' column to 'secciones' table")
            cursor.execute('''
            ALTER TABLE secciones
            ADD COLUMN descripcion TEXT
            ''')
            conn.commit()
            print("[SUCCESS] 'descripcion' column added to 'secciones' table")
        else:
            print("[INFO] 'descripcion' column already exists in 'secciones' table")
        
        # Check if archivo_audio exists in seccion_tts
        cursor.execute("PRAGMA table_info(seccion_tts)")
        tts_columns = [column[1] for column in cursor.fetchall()]
        
        if 'archivo_audio' not in tts_columns:
            print("[INFO] Adding 'archivo_audio' column to 'seccion_tts' table")
            cursor.execute('''
            ALTER TABLE seccion_tts
            ADD COLUMN archivo_audio TEXT
            ''')
            conn.commit()
            print("[SUCCESS] 'archivo_audio' column added to 'seccion_tts' table")
        else:
            print("[INFO] 'archivo_audio' column already exists in 'seccion_tts' table")
        
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
    add_descripcion_column()
    print("=== Database update completed ===")
