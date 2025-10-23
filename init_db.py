import sqlite3
import os
from datetime import datetime

def init_database():
    """
    Inicializa la base de datos SQLite con las tablas de eventos_types y eventos.
    """
    # Crear el directorio data si no existe
    os.makedirs('data', exist_ok=True)
    
    # Conectar a la base de datos (se crea si no existe)
    db_path = os.path.join('data', 'hamana.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Renombrar la tabla eventos a eventos_types si existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eventos'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE eventos RENAME TO eventos_types")
            print("[INFO] Tabla 'eventos' renombrada a 'eventos_types'")
        
        # Crear tabla de tipos de eventos si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_creacion TEXT DEFAULT 'sistema',
            usuario_actualizacion TEXT DEFAULT 'sistema'
        )
        ''')
        
        # Crear tabla de eventos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
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
        
        # Crear tabla de tipos de sección
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_seccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
        ''')
        
        # Insertar tipos de sección iniciales si no existen
        tipos_iniciales = ['tts', 'audio', 'sonido']
        for tipo in tipos_iniciales:
            cursor.execute('''
            INSERT OR IGNORE INTO tipos_seccion (nombre) VALUES (?)
            ''', (tipo,))
        
        # Crear tabla de secciones
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS secciones (
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
        
        # Crear triggers para actualizar automáticamente las fechas de actualización
        for table in ['eventos_types', 'eventos']:
            cursor.execute(f'''
            CREATE TRIGGER IF NOT EXISTS update_{table}_timestamp
            AFTER UPDATE ON {table}
            BEGIN
                UPDATE {table} 
                SET fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END;
            ''')
        
        # Insertar tipos de eventos iniciales si no existen
        eventos_iniciales = [
            ('programa', 'Evento de programa regular', 'sistema'),
            ('boletin', 'Boletín informativo', 'sistema'),
            ('anuncio', 'Anuncio general', 'sistema')
        ]
        
        for nombre, descripcion, usuario in eventos_iniciales:
            # Verificar si el tipo de evento ya existe
            cursor.execute('SELECT id FROM eventos_types WHERE nombre = ?', (nombre,))
            if not cursor.fetchone():
                cursor.execute('''
                INSERT INTO eventos_types (nombre, descripcion, usuario_creacion, usuario_actualizacion)
                VALUES (?, ?, ?, ?)
                ''', (nombre, descripcion, usuario, usuario))
        
        # Guardar los cambios
        conn.commit()
        print(f"[ÉXITO] Base de datos inicializada correctamente en: {os.path.abspath(db_path)}")
        
        # Mostrar los tipos de eventos creados
        print("\nTipos de eventos en la base de datos:")
        print("-" * 50)
        cursor.execute('SELECT id, nombre, descripcion, activo FROM eventos_types')
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, Nombre: {row[1]}, Descripción: {row[2]}, Activo: {'Sí' if row[3] else 'No'}")
        
        # Mostrar la estructura de la tabla eventos
        print("\nEstructura de la tabla 'eventos':")
        print("-" * 50)
        cursor.execute("PRAGMA table_info(eventos)")
        for column in cursor.fetchall():
            print(f"Columna: {column[1]}, Tipo: {column[2]}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error al inicializar la base de datos: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
