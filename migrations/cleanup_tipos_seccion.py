import sqlite3
import os

def cleanup_tipos_seccion():
    """Clean up duplicate entries in the tipos_seccion table"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, check the current content of tipos_seccion
        print("\n=== Current content of tipos_seccion ===")
        cursor.execute("SELECT id, nombre FROM tipos_seccion ORDER BY id")
        tipos = cursor.fetchall()
        for tipo in tipos:
            print(f"- ID: {tipo[0]}, Nombre: {tipo[1]}")
        
        # Define the standard types we want to keep
        standard_types = [
            (1, 'tts'),
            (2, 'audio'),
            (3, 'sonido')
        ]
        
        # Delete non-standard entries
        print("\n[INFO] Cleaning up tipos_seccion table...")
        cursor.execute("DELETE FROM tipos_seccion WHERE id > 3")
        print(f"[INFO] Deleted {cursor.rowcount} non-standard entries")
        
        # Update any references to the old entries
        print("[INFO] Updating references in secciones table...")
        
        # Map old type names to new IDs
        type_map = {
            'TTS': 1,
            'Audio': 2,
            'Sonido': 3,
            'tts': 1,
            'audio': 2,
            'sonido': 3
        }
        
        # Get all sections with their current tipo_id
        cursor.execute("SELECT id, tipo_id, (SELECT nombre FROM tipos_seccion WHERE id = secciones.tipo_id) as tipo_nombre FROM secciones")
        sections = cursor.fetchall()
        
        updated_count = 0
        for section in sections:
            section_id, tipo_id, tipo_nombre = section
            if tipo_nombre and tipo_nombre.lower() in type_map:
                new_tipo_id = type_map[tipo_nombre.lower()]
                if new_tipo_id != tipo_id:
                    cursor.execute("UPDATE secciones SET tipo_id = ? WHERE id = ?", (new_tipo_id, section_id))
                    updated_count += 1
        
        print(f"[INFO] Updated {updated_count} section references")
        
        # Commit changes
        conn.commit()
        print("\n=== Final content of tipos_seccion ===")
        cursor.execute("SELECT id, nombre FROM tipos_seccion ORDER BY id")
        for tipo in cursor.fetchall():
            print(f"- ID: {tipo[0]}, Nombre: {tipo[1]}")
        
        print("\n[SUCCESS] Database cleanup completed successfully")
        
    except Exception as e:
        print(f"[ERROR] Error cleaning up tipos_seccion: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Limpiando la tabla tipos_seccion ===")
    cleanup_tipos_seccion()
    print("=== Limpieza completada ===")
