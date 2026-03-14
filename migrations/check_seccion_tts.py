import sqlite3
import os

def check_seccion_tts():
    """Check the structure of the seccion_tts table"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='seccion_tts'")
        if not cursor.fetchone():
            print("[ERROR] La tabla 'seccion_tts' no existe")
            return False
        
        # Get table structure
        print("\n=== Estructura de la tabla 'seccion_tts' ===")
        cursor.execute("PRAGMA table_info(seccion_tts)")
        columns = cursor.fetchall()
        
        if not columns:
            print("La tabla 'seccion_tts' no tiene columnas")
            return False
            
        print("Columnas:")
        for col in columns:
            print(f"- {col[1]} ({col[2]}){' PK' if col[5] else ''} {'NOT NULL' if col[3] else ''} {f'DEFAULT {col[4]}' if col[4] else ''}")
        
        # Check for any data in the table
        cursor.execute("SELECT COUNT(*) FROM seccion_tts")
        count = cursor.fetchone()[0]
        print(f"\nTotal de registros en 'seccion_tts': {count}")
        
        if count > 0:
            # Show first few rows
            print("\nPrimeras 5 filas:")
            cursor.execute("SELECT * FROM seccion_tts LIMIT 5")
            rows = cursor.fetchall()
            
            # Print column headers
            col_names = [desc[0] for desc in cursor.description]
            print(" | ".join(col_names))
            print("-" * 80)
            
            # Print rows
            for row in rows:
                print(" | ".join(str(x) if x is not None else "NULL" for x in row))
        
        return True
            
    except Exception as e:
        print(f"[ERROR] Error al verificar la tabla 'seccion_tts': {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Verificando tabla 'seccion_tts' ===")
    check_seccion_tts()
    print("=== Verificación completada ===")
