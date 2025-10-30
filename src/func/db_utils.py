import os
import sqlite3
from datetime import datetime
from pathlib import Path

def get_db_connection():
    """Create and return a database connection with timeout"""
    try:
        db_path = os.path.join(Path(__file__).parent.parent, 'database', 'hamna.db')
        # Add timeout parameter (in seconds)
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise

def get_active_event():
    """Get the currently active event with better error handling"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM eventos 
            WHERE id IN (SELECT evento_id FROM programaciones WHERE activa = 1)
            LIMIT 1
        """)
        event = cursor.fetchone()
        return dict(event) if event else None
    except sqlite3.Error as e:
        print(f"Error in get_active_event: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def save_tts_section(name, text, audio_file, duration, language, voice, event_id=None):
    """Save TTS section to the database with improved error handling
    
    Args:
        name (str): Name of the TTS section
        text (str): Text content to be converted to speech
        audio_file (str): Name of the audio file
        duration (int): Duration of the audio in seconds
        language (str): Language code (e.g., 'es-MX')
        voice (str): Voice display name
        event_id (int, optional): ID of the event to associate with this TTS section.
                                 If None, will use the active event.
    """
    conn = None
    try:
        print(f"[DEBUG] save_tts_section - Iniciando con parámetros:")
        print(f"  name: {name}")
        print(f"  text: {text[:50]}..." if len(text) > 50 else f"  text: {text}")
        print(f"  audio_file: {audio_file}")
        print(f"  duration: {duration} (type: {type(duration)})")
        print(f"  language: {language}")
        print(f"  voice: {voice}")
        print(f"  event_id: {event_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get event
        if event_id is None:
            print("[DEBUG] Obteniendo evento activo...")
            event = get_active_event()
            if not event:
                print("[ERROR] No hay un evento activo y no se proporcionó un event_id")
                return False, "No hay un evento activo y no se proporcionó un ID de evento"
            event_id = event['id']
            print(f"[DEBUG] Usando evento activo: ID {event_id}")
        else:
            # Verify the event exists
            cursor.execute("SELECT id FROM eventos WHERE id = ?", (event_id,))
            if not cursor.fetchone():
                print(f"[ERROR] No se encontró el evento con ID {event_id}")
                return False, f"No se encontró el evento con ID {event_id}"
            print(f"[DEBUG] Usando evento proporcionado: ID {event_id}")
        
        # Get TTS section type ID
        print("[DEBUG] Buscando tipo de sección TTS...")
        cursor.execute("SELECT id FROM tipos_seccion WHERE nombre = 'TTS'")
        tipo_tts = cursor.fetchone()
        if not tipo_tts:
            print("[ERROR] Tipo de sección TTS no encontrado")
            return False, "Tipo de sección TTS no encontrado"
        print(f"[DEBUG] Tipo de sección TTS encontrado: {dict(tipo_tts)}")
        
        # Insert into secciones table
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[DEBUG] Insertando en tabla secciones...")
        cursor.execute("""
            INSERT INTO secciones 
            (nombre, tipo_seccion_id, evento_id, duracion_seg, fecha_creacion, fecha_modificacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, tipo_tts['id'], event_id, duration, now, now))
        
        # Get the inserted section ID
        section_id = cursor.lastrowid
        print(f"[DEBUG] Sección creada con ID: {section_id}")
        
        # Insert into seccion_tts table
        print("[DEBUG] Insertando en tabla seccion_tts...")
        cursor.execute("""
            INSERT INTO seccion_tts 
            (seccion_id, texto, archivo, duracion_seg, idioma, voz)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (section_id, text, audio_file, duration, language, voice))
        
        # Commit the transaction
        print("[DEBUG] Haciendo commit de la transacción...")
        conn.commit()
        print("[DEBUG] Sección TTS guardada correctamente")
        return True, "Sección TTS guardada correctamente"
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error de base de datos: {str(e)}")
        if conn:
            try:
                conn.rollback()
                print("[DEBUG] Transacción revertida")
            except:
                pass
        return False, f"Error al guardar la sección TTS: {str(e)}"
        
    except Exception as e:
        print(f"[ERROR] Error inesperado: {str(e)}")
        if conn:
            try:
                conn.rollback()
                print("[DEBUG] Transacción revertida por error inesperado")
            except:
                pass
        return False, f"Error inesperado al guardar la sección TTS: {str(e)}"
        
    finally:
        if conn:
            try:
                conn.close()
                print("[DEBUG] Conexión a la base de datos cerrada")
            except:
                pass
