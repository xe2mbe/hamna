import os
import sys
import time
from pathlib import Path
import yaml
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import using absolute path
from func.tts_config import get_tts_config, get_filtered_voices

def get_tts_engine_config():
    """Obtiene la configuración del motor TTS desde cfg.yaml"""
    # Look for cfg.yaml in the project root directory
    project_root = Path(__file__).parent.parent.parent  # Go up to the project root
    config_path = project_root / 'config' / 'cfg.yaml'
    
    # Fallback to root directory if not found in config folder
    if not config_path.exists():
        config_path = project_root / 'cfg.yaml'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('tts', {}).get('engine', 'azure')
    except Exception as e:
        print(f"Error al leer la configuración: {e}")
        return 'azure'  # Valor por defecto

def save_speech_to_file(audio_data, filename=None, output_dir=None):
    """
    Guarda el audio en un archivo MP3.
    
    Args:
        audio_data: Datos de audio a guardar (bytes o ruta de archivo)
        filename (str, opcional): Nombre del archivo de salida. Si no se especifica, se genera uno automáticamente.
        output_dir (str, opcional): Directorio de salida. Por defecto es 'media/audios/tts/'.
        
    Returns:
        str: Ruta completa al archivo guardado
    """
    # Configurar directorio de salida
    if output_dir is None:
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / 'media' / 'audios' / 'tts'
    else:
        output_dir = Path(output_dir)
    
    # Asegurar que el directorio exista
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo si no se proporciona
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tts_output_{timestamp}.mp3"
    elif not filename.lower().endswith('.mp3'):
        filename += '.mp3'
    
    # Construir ruta completa
    output_path = output_dir / filename
    
    try:
        # Si audio_data es una ruta de archivo, copiar el archivo
        if isinstance(audio_data, (str, Path)) and os.path.exists(audio_data):
            import shutil
            shutil.copy2(audio_data, output_path)
        # Si son bytes, escribir directamente
        elif isinstance(audio_data, bytes):
            with open(output_path, 'wb') as f:
                f.write(audio_data)
        # Si es un objeto de audio de Azure (por ejemplo)
        elif hasattr(audio_data, 'audio_data'):
            with open(output_path, 'wb') as f:
                f.write(audio_data.audio_data)
        else:
            raise ValueError("Formato de audio no soportado")
            
        print(f"Audio guardado en: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"Error al guardar el archivo de audio: {e}")
        raise

def speech(text, engine=None, save_to_file=False, filename=None, output_dir=None):
    """
    Sintetiza el texto a voz usando el motor TTS configurado.
    
    Args:
        text (str): Texto a sintetizar
        engine (str, opcional): Motor TTS a usar. Si no se especifica, se usará el de la configuración.
        save_to_file (bool): Si es True, guarda el audio en un archivo MP3.
        filename (str, opcional): Nombre del archivo de salida. Si no se especifica, se genera uno automáticamente.
        output_dir (str, opcional): Directorio de salida. Por defecto es 'media/audios/tts/'.
        
    Returns:
        str or audio_data: Si save_to_file es True, retorna la ruta al archivo guardado.
                         Si es False, retorna los datos de audio.
    """
    # Obtener el motor de la configuración si no se especifica
    if engine is None:
        engine = get_tts_engine_config()
    
    # Normalizar el nombre del motor (case-insensitive)
    engine = engine.lower().strip()
    if 'azure' in engine:  # Handle variations like 'Azure Speech'
        engine = 'azure'
    elif 'edge' in engine:
        engine = 'edge'
    
    print(f"Usando motor TTS: {engine}")  # Debug
    
    try:
        # Usar el motor TTS correspondiente
        if engine == 'azure':
            from func.azure_tts import synthesize_text, get_available_voices
            
            # Obtener la lista de voces disponibles
            voices = get_available_voices()
            print(f"Voces disponibles: {len(voices)}")
            
            # Usar la primera voz disponible o la especificada
            voice_id = voices[0]['name'] if voices else 'en-US-JennyNeural'
            print(f"Usando voz: {voice_id}")
            
            # Determinar si necesitamos los datos de audio para guardar
            need_audio = save_to_file
            
            # Sintetizar el texto
            success, result = synthesize_text(
                text, 
                voice_name=voice_id,
                return_audio=need_audio
            )
            
            if not success:
                print(f"Error al sintetizar voz: {result}")
                return None
                
            # Si no necesitamos guardar, la reproducción ya se manejó internamente
            if not save_to_file:
                print("Reproducción completada")
                return True
                
            # Si llegamos aquí, necesitamos guardar el audio
            audio_data = result  # En este caso, result contiene los datos de audio
            return save_speech_to_file(audio_data, filename, output_dir)
            
        elif engine == 'edge':
            try:
                from func.edge_tts import text_to_speech
                voices = get_filtered_voices(engine='edge')
                print(f"Voces disponibles: {len(voices)}")  # Debug
                voice_id = voices[0]['id'] if voices else 'es-ES-ElviraNeural'
                print(f"Usando voz: {voice_id}")  # Debug
                audio_data = text_to_speech(text, voice=voice_id)
                if save_to_file:
                    return save_speech_to_file(audio_data, filename, output_dir)
                return audio_data
            except ImportError as e:
                print(f"Error al importar edge_tts: {e}")
                raise
            
    except Exception as e:
        print(f"Error al sintetizar voz: {str(e)}")
        raise

# Ejemplo de uso
if __name__ == "__main__":
    # Example usage with debug info
    try:
        print("Iniciando prueba de síntesis de voz...")
        print("Buscando configuración en:", os.path.abspath('cfg.yaml'))
        engine = get_tts_engine_config()
        print(f"Motor TTS configurado: {engine}")
        print("Intentando sintetizar voz...")
        # Ejemplo guardando a archivo
        output_path = speech(
            "Hola, esto es una prueba de texto a voz guardada en archivo.",
            save_to_file=True,
            filename="prueba_tts"  # Opcional: se le agregará la extensión .mp3
        )
        
        # Ejemplo sin guardar a archivo (solo reproducción)
        speech("Hola, esto es una prueba de texto a voz sin guardar.")
        print("¡Texto sintetizado correctamente!")
    except Exception as e:
        import traceback
        print("\n--- ERROR DETALLADO ---")
        traceback.print_exc()
        print("----------------------\n")
        print(f"Error: {str(e)}")
