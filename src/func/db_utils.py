import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

def get_db_connection():
    """Create and return a database connection with timeout"""
    try:
        # Get the absolute path to the database directory in the project root
        db_dir = os.path.abspath(os.path.join(Path(__file__).parent.parent.parent, 'database'))
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
    """Save a TTS section to the database
    
    Args:
        name (str): Name of the TTS section
        text (str): Text content of the TTS section
        audio_file (str): Path to the audio file
        duration (int): Duration of the audio in seconds
        language (str): Language code (e.g., 'es-ES')
        voice (str): Voice ID to use for TTS
        event_id (int, optional): ID of the event this section belongs to
        
    Returns:
        tuple: (success, message) where message is the ID on success or an error message
    """
    print(f"[DEBUG] save_tts_section called with:")
    print(f"  name: {name}")
    print(f"  text length: {len(text) if text else 0}")
    print(f"  audio_file: {audio_file}")
    print(f"  duration: {duration}")
    print(f"  language: {language}")
    print(f"  voice: {voice}")
    print(f"  event_id: {event_id}")
    
    # Convert duration to integer if it's not already
    try:
        duration = int(duration) if duration is not None else 0
    except (ValueError, TypeError):
        print(f"[WARNING] Invalid duration value: {duration}, using 0")
        duration = 0
    
    # Ensure the audio file path is relative to the media directory
    audio_file = os.path.normpath(str(audio_file))  # Convert to string and normalize the path
    
    # Get the absolute path to the media directory
    media_dir = os.path.abspath(os.path.join(Path(__file__).parent.parent.parent, 'media'))
    
    # Check if the audio file exists
    if not os.path.exists(audio_file):
        # Try to find the file in the media directory
        rel_path = os.path.relpath(audio_file, media_dir) if os.path.isabs(audio_file) else audio_file
        possible_paths = [
            audio_file,  # Original path
            os.path.join(media_dir, 'audios', 'tts', os.path.basename(audio_file)),
            os.path.join(media_dir, rel_path)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                audio_file = path
                break
        else:
            print(f"[WARNING] Audio file not found: {audio_file}")
    
    # Make the path relative to the media directory if it's absolute
    if os.path.isabs(audio_file):
        try:
            audio_file = os.path.relpath(audio_file, media_dir)
            # Convert to forward slashes for consistency
            audio_file = audio_file.replace('\\', '/')
            print(f"[DEBUG] Converted to relative path: {audio_file}")
        except ValueError as e:
            print(f"[WARNING] Could not convert to relative path: {e}")
    
    print(f"[DEBUG] Using audio file path: {audio_file}")
    
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
            
            # Get the ID of the 'tts' type from tipos_seccion
            cursor.execute("SELECT id FROM tipos_seccion WHERE nombre = 'tts'")
            tipo_tts = cursor.fetchone()
            
            if not tipo_tts:
                error_msg = "No se encontró el tipo de sección 'tts' en la base de datos"
                print(f"[ERROR] {error_msg}")
                return False, error_msg
            
            try:
                # First, check which column exists: tipo_id or tipo_seccion_id
                cursor.execute("PRAGMA table_info(secciones)")
                seccion_columns = [col[1] for col in cursor.fetchall()]
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
                
                # Get the ID of the 'tts' type from tipos_seccion
                cursor.execute("SELECT id FROM tipos_seccion WHERE nombre = 'tts'")
                tipo_tts = cursor.fetchone()
                
                if not tipo_tts:
                    error_msg = "No se encontró el tipo de sección 'tts' en la base de datos"
                    print(f"[ERROR] {error_msg}")
                    return False, error_msg
                
                try:
                    # First, check which column exists: tipo_id or tipo_seccion_id
                    cursor.execute("PRAGMA table_info(secciones)")
                    seccion_columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'tipo_seccion_id' in seccion_columns:
                        column_name = 'tipo_seccion_id'
                    elif 'tipo_id' in seccion_columns:
                        column_name = 'tipo_id'
                    else:
                        error_msg = "No se encontró ninguna columna para el tipo de sección en la tabla 'secciones'"
                        print(f"[ERROR] {error_msg}")
                        return False, error_msg
                    
                    print(f"[DEBUG] Usando columna '{column_name}' para el tipo de sección")
                    
                    # Insert into secciones table
                    cursor.execute(f"""
                        INSERT INTO secciones (
                            nombre, descripcion, evento_id, {column_name}
                        ) VALUES (?, ?, ?, ?)
                    """, (name, "Sección TTS generada automáticamente", event_id, tipo_tts[0]))
                    
                    # Get the ID of the newly created section
                    seccion_id = cursor.lastrowid
                    print(f"[DEBUG] Nueva sección creada con ID: {seccion_id}")
                    
                    # Ensure duration is a float
                    try:
                        duration_float = float(duration) if duration is not None else 0.0
                    except (ValueError, TypeError):
                        print(f"[WARNING] Invalid duration value: {duration}, using 0.0")
                        duration_float = 0.0
                    
                    print(f"[DEBUG] Inserting into seccion_tts with values: seccion_id={seccion_id}, "
                          f"texto={text[:30]}..., voz={voice}, idioma={language}, "
                          f"archivo_audio={audio_file}, duracion_seg={duration_float}")
                    
                    # Insert into seccion_tts table
                    try:
                        # First, check if the 'archivo_audio' column exists
                        cursor.execute("PRAGMA table_info(seccion_tts)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # Always store the path relative to the media directory
                        media_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'media'))
                        audio_file = os.path.abspath(audio_file)  # Ensure we have an absolute path
                        
                        # Calculate the relative path from media directory to the audio file
                        try:
                            relative_audio_path = os.path.relpath(audio_file, media_path)
                            # Convert to forward slashes for consistency
                            relative_audio_path = relative_audio_path.replace('\\', '/')
                            print(f"[DEBUG] Storing relative path in DB: {relative_audio_path}")
                        except ValueError:
                            # If the paths are on different drives, just use the absolute path
                            print(f"[WARNING] Could not create relative path, using absolute path instead")
                            relative_audio_path = audio_file
                        
                        # Use the appropriate column name based on what exists
                        if 'archivo_audio' in columns:
                            column_name = 'archivo_audio'
                        elif 'archivo' in columns:
                            column_name = 'archivo'
                        else:
                            error_msg = "No se encontró ninguna columna para el archivo de audio en la tabla 'seccion_tts'"
                            print(f"[ERROR] {error_msg}")
                            return False, error_msg
                            
                        print(f"[DEBUG] Usando columna '{column_name}' para el archivo de audio")
                        print(f"[DEBUG] Ruta del archivo de audio: {relative_audio_path}")
                        
                        # Verify the file exists (try both the original and constructed paths)
                        file_exists = os.path.exists(audio_file)  # Check original path first
                        
                        if not file_exists and not os.path.isabs(relative_audio_path):
                            # Try constructing the full path from the relative path
                            constructed_path = os.path.abspath(os.path.join(media_path, relative_audio_path))
                            file_exists = os.path.exists(constructed_path)
                            if file_exists:
                                print(f"[DEBUG] Found audio file at: {constructed_path}")
                        
                        if not file_exists:
                            error_msg = f"El archivo de audio no existe en la ruta: {audio_file}"
                            if not os.path.isabs(relative_audio_path):
                                error_msg += f" o en: {os.path.join(media_path, relative_audio_path)}"
                            print(f"[ERROR] {error_msg}")
                            return False, error_msg
                        
                        # Verificar si la columna 'nombre' existe en la tabla seccion_tts
                        cursor.execute("PRAGMA table_info(seccion_tts)")
                        tts_columns = [col[1] for col in cursor.fetchall()]
                        has_nombre_column = 'nombre' in tts_columns
                        
                        # Construir la consulta dinámicamente según las columnas disponibles
                        columns = [
                            'seccion_id', 
                            'texto', 
                            'voz', 
                            'idioma', 
                            column_name, 
                            'duracion_seg'
                        ]
                        placeholders = ['?'] * len(columns)
                        values = [
                            seccion_id, 
                            text, 
                            voice, 
                            language, 
                            relative_audio_path, 
                            duration_float
                        ]
                        
                        # Agregar el nombre si la columna existe
                        if has_nombre_column:
                            columns.append('nombre')
                            placeholders.append('?')
                            values.append(name)  # Usar el nombre de la sección
                        
                        # Construir y ejecutar la consulta
                        query = f"""
                            INSERT INTO seccion_tts (
                                {', '.join(columns)}
                            ) VALUES ({', '.join(placeholders)})
                        """
                        
                        print(f"[DEBUG] Ejecutando consulta: {query}")
                        print(f"[DEBUG] Valores: {values}")
                        
                        cursor.execute(query, values)
                    except sqlite3.Error as e:
                        print(f"[ERROR] Error in INSERT INTO seccion_tts: {str(e)}")
                        # Print the table structure for debugging
                        cursor.execute("PRAGMA table_info(seccion_tts)")
                        columns = cursor.fetchall()
                        print("\n=== seccion_tts table structure ===")
                        for col in columns:
                            print(f"- {col[1]} ({col[2]}){' PK' if col[5] else ''}")
                        print("=================================\n")
                        raise
                    
                    # Get the ID of the newly created TTS section
                    tts_id = cursor.lastrowid
                    print(f"[DEBUG] Nueva entrada en seccion_tts con ID: {tts_id}")
                    
                    # Commit the transaction
                    conn.commit()
                    
                    print(f"[SUCCESS] TTS section saved successfully with ID: {tts_id}")
                    return True, tts_id
                    
                except sqlite3.Error as e:
                    error_msg = f"Error de base de datos al guardar la sección TTS: {str(e)}"
                    print(f"[ERROR] {error_msg}")
                    if conn:
                        conn.rollback()
                    return False, error_msg
                
            except sqlite3.OperationalError as e:
                print(f"[ATTEMPT {attempt + 1}/{max_retries}] Database error: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    print("[ERROR] Max retries reached, giving up")
                    raise
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
    except sqlite3.Error as e:
        error_msg = f"Error de base de datos al guardar la sección TTS: {str(e)}"
        print(f"[ERROR] {error_msg}")
        if conn:
            try:
                conn.rollback()
                print("[DEBUG] Transacción revertida")
            except Exception as rollback_error:
                print(f"[WARNING] Error al revertir la transacción: {rollback_error}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado al guardar la sección TTS: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                print("[DEBUG] Transacción revertida por error inesperado")
            except Exception as rollback_error:
                print(f"[WARNING] Error al revertir la transacción: {rollback_error}")
        return False, error_msg
        
    finally:
        if conn:
            try:
                conn.close()
                print("[DEBUG] Conexión a la base de datos cerrada")
            except:
                pass
