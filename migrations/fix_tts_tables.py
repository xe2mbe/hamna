import os
import sqlite3
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database"""
    if not os.path.exists(db_path):
        print(f"[INFO] Database file {db_path} does not exist, no backup needed")
        return None
        
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"hamna_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
        dst.write(src.read())
    
    print(f"[INFO] Backup created at: {backup_path}")
    return backup_path

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def fix_database():
    """Fix the database schema and data"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    # Ensure the database directory exists
    os.makedirs(db_dir, exist_ok=True)
    
    print(f"[INFO] Using database at: {db_path}")
    
    # Create a backup before making changes
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Create tipos_seccion table if it doesn't exist
        if not check_table_exists(cursor, 'tipos_seccion'):
            cursor.execute('''
            CREATE TABLE tipos_seccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
            ''')
            print("[FIX] Created 'tipos_seccion' table")
        
        # Ensure we have the default section types
        default_types = ['tts', 'audio', 'sonido']
        cursor.executemany(
            'INSERT OR IGNORE INTO tipos_seccion (nombre) VALUES (?)',
            [(tipo,) for tipo in default_types]
        )
        print(f"[FIX] Ensured default section types: {', '.join(default_types)}")
        
        # Create secciones table if it doesn't exist
        if not check_table_exists(cursor, 'secciones'):
            cursor.execute('''
            CREATE TABLE secciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                evento_id INTEGER NOT NULL,
                tipo_id INTEGER NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_creacion TEXT DEFAULT 'sistema',
                usuario_actualizacion TEXT DEFAULT 'sistema',
                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
                FOREIGN KEY (tipo_id) REFERENCES tipos_seccion(id)
            )
            ''')
            print("[FIX] Created 'secciones' table")
        
        # Create seccion_tts table if it doesn't exist
        if not check_table_exists(cursor, 'seccion_tts'):
            cursor.execute('''
            CREATE TABLE seccion_tts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seccion_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                voz TEXT NOT NULL,
                idioma TEXT NOT NULL,
                velocidad REAL DEFAULT 1.0,
                tono REAL DEFAULT 0.0,
                archivo_audio TEXT,
                duracion_seg REAL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_creacion TEXT DEFAULT 'sistema',
                usuario_actualizacion TEXT DEFAULT 'sistema',
                FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE
            )
            ''')
            print("[FIX] Created 'seccion_tts' table")
        
        # Commit all changes
        conn.commit()
        print("[SUCCESS] Database fix completed successfully")
        
    except Exception as e:
        print(f"[ERROR] Error during database fix: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Starting database fix ===")
    fix_database()
    print("=== Database fix completed ===")
