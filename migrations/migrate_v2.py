import os
import sqlite3
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    if os.path.exists(db_path):
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"[INFO] Backup created at: {backup_path}")
    return backup_path

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def migrate_database():
    """Apply necessary database migrations"""
    # Use the database in the project root's database directory
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    os.makedirs(db_dir, exist_ok=True)
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # 1. Create eventos table if it doesn't exist
        if not check_table_exists(cursor, 'eventos'):
            cursor.execute('''
            CREATE TABLE eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_creacion TEXT DEFAULT 'sistema',
                usuario_actualizacion TEXT DEFAULT 'sistema'
            )
            ''')
            print("[MIGRATION] 'eventos' table created successfully")
        
        # 2. Create tipos_seccion table
        if not check_table_exists(cursor, 'tipos_seccion'):
            cursor.execute('''
            CREATE TABLE tipos_seccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
            ''')
            print("[MIGRATION] 'tipos_seccion' table created successfully")
            
            # Insert default section types
            default_types = ['tts', 'audio', 'sonido']
            cursor.executemany(
                'INSERT OR IGNORE INTO tipos_seccion (nombre) VALUES (?);',
                [(tipo,) for tipo in default_types]
            )
            print("[MIGRATION] Default section types inserted")
        
        # 3. Create secciones table
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
            print("[MIGRATION] 'secciones' table created successfully")
        
        # 4. Create seccion_tts table
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
            print("[MIGRATION] 'seccion_tts' table created successfully")
        
        # Commit changes
        conn.commit()
        print("[MIGRATION] Database migration completed successfully")
        
    except Exception as e:
        print(f"[ERROR] Error during migration: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_database()
    print("Migration process completed")
