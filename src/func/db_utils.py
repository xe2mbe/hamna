import os
import sqlite3
from datetime import datetime
from pathlib import Path

def get_db_connection():
    """Create and return a database connection with timeout"""
    try:
        # Get the absolute path to the database directory
        db_dir = os.path.join(Path(__file__).parent.parent, 'database')
        db_path = os.path.join(db_dir, 'hamna.db')
        
        # Ensure the database directory exists
        os.makedirs(db_dir, exist_ok=True)
        
        # Check if we have write permissions to the directory
        if not os.access(db_dir, os.W_OK):
            raise PermissionError(f"No write permissions for database directory: {db_dir}")
        
        # Connect to the database with a longer timeout
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys and set other PRAGMAs for better performance
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 seconds timeout
        
        return conn
    except sqlite3.Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        print(f"[DEBUG] Database path: {db_path}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
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
    except Exception as e:
        print(f"[ERROR] Error saving TTS section: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        
        # Try to get more detailed error information
        if isinstance(e, sqlite3.Error):
            print(f"[DEBUG] SQLite error details: {e.args}")
        
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                print(f"[ERROR] Error during rollback: {rollback_error}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                print(f"[WARNING] Error closing connection: {close_error}")
        
        # Print final debug info
        print("[DEBUG] Database operation completed")

def save_tts_section(name, text, audio_file, duration, language, voice, event_id=None):
    """Save TTS section to the database with improved error handling
    
    Args:
        name (str): Name of the TTS section
        text (str): Text content to be converted to speech
        audio_file (str): Path to the audio file
        duration (int): Duration of the audio in seconds
        language (str): Language code (e.g., 'es-ES')
        voice (str): Voice ID (e.g., 'es-ES-AbrilNeural')
        event_id (int, optional): ID of the event to associate with this TTS section.
                                 If None, will use the active event.
    
    Returns:
        int: The ID of the newly created TTS section, or None if failed
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
        
        # Convert duration to integer if it's not already
        duration = int(duration) if duration is not None else 0
        
        # Ensure the audio file path is relative to the database
        audio_file = os.path.normpath(audio_file)  # Normalize the path
        if os.path.isabs(audio_file):
            # Make the path relative to the media directory if it's absolute
            media_dir = os.path.join(Path(__file__).parent.parent, 'media')
            try:
                audio_file = os.path.relpath(audio_file, media_dir)
            except ValueError:
                # If the path is not under media directory, keep it as is
                pass
        
        # Get event_id if not provided
        if event_id is None:
            active_event = get_active_event()
            if not active_event:
                print("[ERROR] No active event found and no event_id provided")
                return None
            event_id = active_event['id']
        
        # Ensure the database directory exists
        db_dir = os.path.join(Path(__file__).parent.parent, 'database')
        os.makedirs(db_dir, exist_ok=True)
        
        # Get database connection with retry logic
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if the table exists, create it if it doesn't
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS seccion_tts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evento_id INTEGER NOT NULL,
                        nombre TEXT NOT NULL,
                        texto TEXT NOT NULL,
                        archivo_audio TEXT NOT NULL,
                        duracion_seg INTEGER NOT NULL,
                        idioma TEXT NOT NULL,
                        voz TEXT NOT NULL,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (evento_id) REFERENCES eventos (id) ON DELETE CASCADE
                    )
                """)
                
                # Insert the new TTS section
                cursor.execute("""
                    INSERT INTO seccion_tts (
                        evento_id, nombre, texto, archivo_audio, 
                        duracion_seg, idioma, voz, fecha_creacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (event_id, name, text, audio_file, duration, language, voice))
                
                # Get the ID of the newly created section
                tts_id = cursor.lastrowid
                
                # Commit the transaction
                conn.commit()
                
                print(f"[SUCCESS] TTS section saved successfully with ID: {tts_id}")
                return tts_id
                
            except sqlite3.OperationalError as e:
                print(f"[ATTEMPT {attempt + 1}/{max_retries}] Database error: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    print("[ERROR] Max retries reached, giving up")
                    raise
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
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
