import sqlite3
import os

def fix_audio_columns():
    """Fix the audio file columns in seccion_tts table"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check the current structure of seccion_tts
        cursor.execute("PRAGMA table_info(seccion_tts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # If both columns exist, migrate data to archivo_audio and drop archivo
        if 'archivo' in columns and 'archivo_audio' in columns:
            print("[INFO] Both 'archivo' and 'archivo_audio' columns exist. Migrating data...")
            
            # Copy data from archivo to archivo_audio where archivo_audio is NULL
            cursor.execute("""
                UPDATE seccion_tts 
                SET archivo_audio = archivo 
                WHERE (archivo_audio IS NULL OR archivo_audio = '') AND archivo IS NOT NULL
            """)
            print(f"[INFO] Migrated {cursor.rowcount} rows from 'archivo' to 'archivo_audio'")
            
            # Now drop the archivo column
            print("[INFO] Dropping 'archivo' column")
            
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
            cursor.execute("""
                CREATE TABLE seccion_tts_new (
                    seccion_id INTEGER PRIMARY KEY,
                    texto TEXT NOT NULL,
                    duracion_seg REAL,
                    idioma TEXT,
                    voz TEXT,
                    archivo_audio TEXT,
                    FOREIGN KEY (seccion_id) REFERENCES secciones (id) ON DELETE CASCADE
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO seccion_tts_new 
                (seccion_id, texto, duracion_seg, idioma, voz, archivo_audio)
                SELECT seccion_id, texto, duracion_seg, idioma, voz, archivo_audio 
                FROM seccion_tts
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE seccion_tts")
            cursor.execute("ALTER TABLE seccion_tts_new RENAME TO seccion_tts")
            
            print("[SUCCESS] Consolidated audio file columns to 'archivo_audio'")
        
        # If only 'archivo' exists, rename it to 'archivo_audio'
        elif 'archivo' in columns and 'archivo_audio' not in columns:
            print("[INFO] Renaming 'archivo' column to 'archivo_audio'")
            
            # SQLite doesn't support RENAME COLUMN directly, so we need to recreate the table
            cursor.execute("""
                CREATE TABLE seccion_tts_new (
                    seccion_id INTEGER PRIMARY KEY,
                    texto TEXT NOT NULL,
                    duracion_seg REAL,
                    idioma TEXT,
                    voz TEXT,
                    archivo_audio TEXT,
                    FOREIGN KEY (seccion_id) REFERENCES secciones (id) ON DELETE CASCADE
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO seccion_tts_new 
                (seccion_id, texto, duracion_seg, idioma, voz, archivo_audio)
                SELECT seccion_id, texto, duracion_seg, idioma, voz, archivo 
                FROM seccion_tts
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE seccion_tts")
            cursor.execute("ALTER TABLE seccion_tts_new RENAME TO seccion_tts")
            
            print("[SUCCESS] Renamed 'archivo' to 'archivo_audio'")
        
        # Commit changes
        conn.commit()
        print("[SUCCESS] Database schema updated successfully")
        
    except Exception as e:
        print(f"[ERROR] Error updating database schema: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Actualizando esquema de la base de datos ===")
    fix_audio_columns()
    print("=== Actualización completada ===")
