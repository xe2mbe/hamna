import os
import sqlite3
from datetime import datetime

def backup_database(db_path):
    """Crea una copia de seguridad de la base de datos"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    # Si el archivo de base de datos existe, crea una copia
    if os.path.exists(db_path):
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"[INFO] Se creó una copia de seguridad en: {backup_path}")
    return backup_path

def check_table_exists(cursor, table_name):
    """Verifica si una tabla existe en la base de datos"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def migrate_database():
    """Aplica las migraciones necesarias a la base de datos"""
    # Ruta a la base de datos
    db_path = os.path.join('data', 'hamana.db')
    
    # Crear directorio data si no existe
    os.makedirs('data', exist_ok=True)
    
    # Crear copia de seguridad
    backup_path = backup_database(db_path)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Activar claves foráneas
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # 1. Crear tabla tipos_seccion si no existe
        if not check_table_exists(cursor, 'tipos_seccion'):
            cursor.execute('''
            CREATE TABLE tipos_seccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
            ''')
            print("[MIGRACIÓN] Tabla 'tipos_seccion' creada exitosamente")
            
            # Insertar tipos de sección iniciales
            tipos_iniciales = ['tts', 'audio', 'sonido']
            for tipo in tipos_iniciales:
                cursor.execute('''
                INSERT OR IGNORE INTO tipos_seccion (nombre) VALUES (?)
                ''', (tipo,))
            print("[MIGRACIÓN] Tipos de sección iniciales insertados")
        
        # 2. Crear tabla secciones si no existe
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
                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (tipo_id) REFERENCES tipos_seccion(id) ON UPDATE CASCADE
            )
            ''')
            print("[MIGRACIÓN] Tabla 'secciones' creada exitosamente")
        
        # 3. Actualizar la tabla eventos para incluir ON UPDATE CASCADE en la clave foránea
        # Esto requiere recrear la tabla con la nueva restricción
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Verificar si la tabla eventos existe y tiene datos
        if check_table_exists(cursor, 'eventos'):
            # Crear una tabla temporal con la nueva estructura
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS new_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_creacion TEXT DEFAULT 'sistema',
                usuario_actualizacion TEXT DEFAULT 'sistema',
                FOREIGN KEY (tipo) REFERENCES eventos_types(nombre) ON UPDATE CASCADE
            )
            ''')
            
            # Copiar los datos existentes a la nueva tabla
            cursor.execute('''
            INSERT INTO new_eventos 
            SELECT * FROM eventos
            ''')
            
            # Eliminar la tabla antigua y renombrar la nueva
            cursor.execute('DROP TABLE eventos')
            cursor.execute('ALTER TABLE new_eventos RENAME TO eventos')
            
            print("[MIGRACIÓN] Tabla 'eventos' actualizada con ON UPDATE CASCADE")
        
        # Reactivar claves foráneas
        cursor.execute('PRAGMA foreign_key_check')
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Confirmar los cambios
        conn.commit()
        print("[MIGRACIÓN] Migración completada exitosamente")
        
    except Exception as e:
        print(f"[ERROR] Error durante la migración: {str(e)}")
        print(f"[INFO] Se restaurará la copia de seguridad desde: {backup_path}")
        
        # En caso de error, restaurar la copia de seguridad
        if os.path.exists(backup_path):
            with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
                dst.write(src.read())
            print("[INFO] Base de datos restaurada desde la copia de seguridad")
        
        # Re-lanzar la excepción para manejo adicional si es necesario
        raise
    
    finally:
        # Cerrar la conexión
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Iniciando migración de la base de datos...")
    migrate_database()
    print("Proceso de migración finalizado")
