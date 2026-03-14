import sqlite3
import os

def add_nombre_to_seccion_tts():
    """
    Agrega la columna 'nombre' a la tabla 'seccion_tts' si no existe
    """
    # Obtener la ruta de la base de datos
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Usando base de datos en: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(seccion_tts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'nombre' not in columns:
            print("[INFO] Agregando columna 'nombre' a la tabla 'seccion_tts'")
            cursor.execute("""
                ALTER TABLE seccion_tts 
                ADD COLUMN nombre TEXT
            """)
            
            # Actualizar los registros existentes con un valor por defecto
            cursor.execute("""
                UPDATE seccion_tts 
                SET nombre = 'Sección sin nombre' 
                WHERE nombre IS NULL
            """)
            
            conn.commit()
            print("[INFO] Columna 'nombre' agregada exitosamente")
        else:
            print("[INFO] La columna 'nombre' ya existe en la tabla 'seccion_tts'")
            
    except sqlite3.Error as e:
        print(f"[ERROR] Error al modificar la tabla 'seccion_tts': {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_nombre_to_seccion_tts()
