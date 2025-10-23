import os
import sqlite3
from datetime import datetime

def clear_tables():
    """
    Vacía las tablas 'eventos' y 'secciones' de manera segura.
    """
    # Ruta a la base de datos
    db_path = os.path.join('data', 'hamana.db')
    
    # Verificar si la base de datos existe
    if not os.path.exists(db_path):
        print(f"[ERROR] No se encontró la base de datos en: {db_path}")
        return
    
    # Crear copia de seguridad
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"[INFO] Se creó una copia de seguridad en: {backup_path}")
    except Exception as e:
        print(f"[ERROR] No se pudo crear la copia de seguridad: {e}")
        return
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Activar claves foráneas
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Lista de tablas a vaciar en el orden correcto (para respetar claves foráneas)
        tables_to_clear = ['secciones', 'eventos']
        
        # Iniciar transacción
        cursor.execute('BEGIN TRANSACTION')
        
        # Vaciar cada tabla
        for table in tables_to_clear:
            cursor.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name=?', (table,))
            if cursor.fetchone():
                cursor.execute(f'DELETE FROM {table}')
                print(f"[INFO] Se vació la tabla: {table}")
                
                # Reiniciar el contador de autoincremento (SQLITE specific)
                cursor.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')
            else:
                print(f"[INFO] La tabla {table} no existe, se omite")
        
        # Confirmar los cambios
        conn.commit()
        print("[ÉXITO] Tablas vaciadas correctamente")
        
    except sqlite3.Error as e:
        # En caso de error, hacer rollback
        if 'conn' in locals():
            conn.rollback()
        print(f"[ERROR] Ocurrió un error: {e}")
        print(f"[INFO] Se restaurará la base de datos desde la copia de seguridad")
        
        try:
            # Restaurar desde la copia de seguridad
            with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
                dst.write(src.read())
            print("[INFO] Base de datos restaurada desde la copia de seguridad")
        except Exception as restore_error:
            print(f"[ERROR] No se pudo restaurar la copia de seguridad: {restore_error}")
        
    finally:
        # Cerrar la conexión
        if 'conn' in locals():
            conn.close()
        
        # Preguntar si se desea eliminar la copia de seguridad
        try:
            if os.path.exists(backup_path):
                delete = input("¿Desea eliminar la copia de seguridad? (s/n): ").strip().lower()
                if delete == 's':
                    os.remove(backup_path)
                    print("[INFO] Copia de seguridad eliminada")
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo eliminar la copia de seguridad: {e}")

if __name__ == "__main__":
    print("=== Vaciado de tablas de eventos y secciones ===")
    print("ADVERTENCIA: Esta acción eliminará todos los registros de las tablas 'eventos' y 'secciones'.")
    confirm = input("¿Está seguro de continuar? (s/n): ").strip().lower()
    
    if confirm == 's':
        clear_tables()
    else:
        print("Operación cancelada por el usuario")
