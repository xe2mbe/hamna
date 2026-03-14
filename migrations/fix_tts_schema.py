import sqlite3
import os
from datetime import datetime

def fix_tts_schema():
    """Fix TTS schema issues in the database"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Rename 'archivo' to 'archivo_audio' in seccion_tts if it exists
        cursor.execute("PRAGMA table_info(seccion_tts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'archivo' in columns and 'archivo_audio' not in columns:
            print("[INFO] Renaming 'archivo' to 'archivo_audio' in seccion_tts")
            cursor.execute('''
            CREATE TABLE seccion_tts_new (
                seccion_id INTEGER PRIMARY KEY,
                texto TEXT,
                archivo_audio TEXT,
                duracion_seg REAL,
                idioma TEXT,
                voz TEXT,
                velocidad REAL DEFAULT 1.0,
                tono REAL DEFAULT 0.0,
                FOREIGN KEY (seccion_id) REFERENCES secciones (id) ON DELETE CASCADE
            )
            ''')
            
            # Copy data from old table to new table
            cursor.execute('''
            INSERT INTO seccion_tts_new 
            (seccion_id, texto, archivo_audio, duracion_seg, idioma, voz)
            SELECT seccion_id, texto, archivo, duracion_seg, COALESCE(idioma, 'es-ES'), voz 
            FROM seccion_tts
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE seccion_tts')
            cursor.execute('ALTER TABLE seccion_tts_new RENAME TO seccion_tts')
            
            print("[SUCCESS] Renamed 'archivo' to 'archivo_audio' in seccion_tts")
        
        # 2. Clean up tipos_seccion table
        print("\n[INFO] Cleaning up tipos_seccion table")
        
        # First, update any references to the old 'tts' type to use 'TTS' instead
        cursor.execute("SELECT id FROM tipos_seccion WHERE nombre = 'TTS'")
        tts_id = cursor.fetchone()
        
        if tts_id:
            tts_id = tts_id[0]
            print(f"[INFO] Found 'TTS' type with ID: {tts_id}")
            
            # Update secciones to use the correct tipo_id
            cursor.execute('''
            UPDATE secciones 
            SET tipo_id = ? 
            WHERE tipo_id IN (SELECT id FROM tipos_seccion WHERE LOWER(nombre) = 'tts' AND id != ?)
            ''', (tts_id, tts_id))
            
            # Remove duplicate 'tts' entries
            cursor.execute("DELETE FROM tipos_seccion WHERE LOWER(nombre) = 'tts' AND id != ?", (tts_id,))
            
            # Rename to lowercase for consistency
            cursor.execute("UPDATE tipos_seccion SET nombre = 'tts' WHERE id = ?", (tts_id,))
            
            print("[SUCCESS] Cleaned up 'tts' types")
        
        # 3. Ensure all required columns exist in secciones
        cursor.execute("PRAGMA table_info(secciones)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'fecha_creacion' not in columns:
            print("[INFO] Adding 'fecha_creacion' column to 'secciones'")
            cursor.execute('''
            ALTER TABLE secciones 
            ADD COLUMN fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            print("[SUCCESS] Added 'fecha_creacion' column")
        
        if 'fecha_modificacion' not in columns:
            print("[INFO] Adding 'fecha_modificacion' column to 'secciones'")
            cursor.execute('''
            ALTER TABLE secciones 
            ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            print("[SUCCESS] Added 'fecha_modificacion' column")
        
        # 4. Ensure foreign key constraints are enabled
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Commit all changes
        conn.commit()
        print("\n[SUCCESS] Database schema updated successfully")
        
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
    fix_tts_schema()
    print("=== Actualización completada ===")
