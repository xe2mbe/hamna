import sqlite3
from pathlib import Path

def get_db_connection():
    """Create and return a database connection"""
    try:
        # Get the project root directory (one level up from 'src')
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "database" / "hamna.db"
        
        # Ensure the database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # This enables name-based access to columns
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        # Return None to indicate connection failure
        return None

def get_event_types():
    """Retrieve all event types from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM eventos_type ORDER BY nombre")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error al obtener tipos de evento: {e}")
        return []
    finally:
        conn.close()

def get_event(event_id):
    """Retrieve a specific event by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.nombre, e.tipo_evento_id, et.nombre as tipo_nombre 
            FROM eventos e
            LEFT JOIN eventos_type et ON e.tipo_evento_id = et.id
            WHERE e.id = ?
        """, (event_id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Error al obtener el evento {event_id}: {e}")
        return None
    finally:
        conn.close()

def save_event(event_id, name, event_type_id):
    """Save or update an event"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if event_id:  # Actualizar evento existente
            cursor.execute(
                """
                UPDATE eventos 
                SET nombre = ?, tipo_evento_id = ?, fecha_creacion = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (name, event_type_id, event_id)
            )
        else:  # Insertar nuevo evento
            cursor.execute(
                """
                INSERT INTO eventos (nombre, tipo_evento_id, fecha_creacion)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (name, event_type_id)
            )
            event_id = cursor.lastrowid
        
        conn.commit()
        return event_id
    except sqlite3.Error as e:
        print(f"Error al guardar el evento: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
