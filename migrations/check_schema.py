import sqlite3
import os

def check_schema():
    """Check the database schema for required tables and columns"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\n=== Tablas en la base de datos ===")
        for table in tables:
            print(f"- {table[0]}")
        
        # Check secciones table
        print("\n=== Estructura de 'secciones' ===")
        try:
            cursor.execute("PRAGMA table_info(secciones)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"- {col[1]} ({col[2]}){' PK' if col[5] else ''}")
        except sqlite3.Error as e:
            print(f"[ERROR] Error al obtener la estructura de 'secciones': {e}")
        
        # Check seccion_tts table
        print("\n=== Estructura de 'seccion_tts' ===")
        try:
            cursor.execute("PRAGMA table_info(seccion_tts)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"- {col[1]} ({col[2]}){' PK' if col[5] else ''}")
        except sqlite3.Error as e:
            print(f"[ERROR] Error al obtener la estructura de 'seccion_tts': {e}")
        
        # Check tipos_seccion table
        print("\n=== Contenido de 'tipos_seccion' ===")
        try:
            cursor.execute("SELECT * FROM tipos_seccion")
            tipos = cursor.fetchall()
            if tipos:
                for tipo in tipos:
                    print(f"- ID: {tipo[0]}, Nombre: {tipo[1]}")
            else:
                print("La tabla 'tipos_seccion' está vacía")
        except sqlite3.Error as e:
            print(f"[ERROR] Error al obtener el contenido de 'tipos_seccion': {e}")
        
    except Exception as e:
        print(f"[ERROR] Error al verificar el esquema: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Verificando esquema de la base de datos ===")
    check_schema()
    print("=== Verificación completada ===")
