import sqlite3
import os
from datetime import datetime

def add_fecha_creacion_column():
    """Add fecha_creacion and fecha_modificacion columns to secciones table if they don't exist"""
    # Get the database path
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database'))
    db_path = os.path.join(db_dir, 'hamna.db')
    
    print(f"[INFO] Using database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if fecha_creacion column exists
        cursor.execute("PRAGMA table_info(secciones)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'fecha_creacion' not in columns:
            print("[INFO] Adding 'fecha_creacion' column to 'secciones' table")
            cursor.execute("""
                ALTER TABLE secciones 
                ADD COLUMN fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("[SUCCESS] Added 'fecha_creacion' column")
        else:
            print("[INFO] 'fecha_creacion' column already exists in 'secciones' table")
        
        if 'fecha_modificacion' not in columns:
            print("[INFO] Adding 'fecha_modificacion' column to 'secciones' table")
            cursor.execute("""
                ALTER TABLE secciones 
                ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("[SUCCESS] Added 'fecha_modificacion' column")
        else:
            print("[INFO] 'fecha_modificacion' column already exists in 'secciones' table")
        
        # Update any existing rows with current timestamp
        if 'fecha_creacion' not in columns:
            print("[INFO] Setting default timestamps for existing rows")
            cursor.execute("""
                UPDATE secciones 
                SET fecha_creacion = CURRENT_TIMESTAMP,
                    fecha_modificacion = CURRENT_TIMESTAMP
                WHERE fecha_creacion IS NULL
            """)
            print(f"[SUCCESS] Updated {cursor.rowcount} rows with current timestamps")
        
        # Commit changes
        conn.commit()
        print("[SUCCESS] Database schema updated successfully")
        
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
    add_fecha_creacion_column()
    print("=== Actualización completada ===")
