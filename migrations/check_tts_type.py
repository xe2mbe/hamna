import sqlite3
import os

def check_tts_type():
    """Check if the 'tts' type exists in the tipos_seccion table"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tipos_seccion'")
        if not cursor.fetchone():
            print("[ERROR] La tabla 'tipos_seccion' no existe")
            return False
        
        # Check if the 'tts' type exists
        cursor.execute("SELECT id, nombre FROM tipos_seccion WHERE nombre = 'tts'")
        tts_type = cursor.fetchone()
        
        if tts_type:
            print(f"[INFO] Tipo 'tts' encontrado con ID: {tts_type[0]}")
            return True
        else:
            print("[WARNING] No se encontró el tipo 'tts' en la tabla 'tipos_seccion'")
            
            # List all available types
            cursor.execute("SELECT id, nombre FROM tipos_seccion")
            types = cursor.fetchall()
            if types:
                print("\nTipos de sección disponibles:")
                for t in types:
                    print(f"- ID: {t[0]}, Nombre: {t[1]}")
            else:
                print("No hay tipos de sección en la base de datos")
            
            return False
            
    except Exception as e:
        print(f"[ERROR] Error al verificar el tipo 'tts': {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Verificando tipo 'tts' en la base de datos ===")
    if not check_tts_type():
        print("\n[ADVERTENCIA] El tipo 'tts' no está configurado correctamente.")
        print("Se requiere una entrada en la tabla 'tipos_seccion' con nombre 'tts'.")
    print("=== Verificación completada ===")
