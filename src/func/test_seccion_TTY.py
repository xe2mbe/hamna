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

def speech(text, engine=None, voice_id=None, save_to_file=False, filename=None, output_dir=None):
    """
    Sintetiza el texto a voz usando el motor TTS configurado.
    
    Args:
        text (str): Texto a sintetizar
        engine (str, opcional): Motor TTS a usar. Si no se especifica, se usará el de la configuración.
        voice_id (str, opcional): ID de la voz a utilizar. Si no se especifica, se usará una por defecto.
        save_to_file (bool): Si es True, guarda el audio en un archivo MP3.
        filename (str, opcional): Nombre del archivo de salida. Si no se especifica, se genera uno automáticamente.
        output_dir (str, opcional): Directorio de salida. Por defecto es 'media/audios/tts/'.
        
    Returns:
        str or bool or None: 
            - Si save_to_file es True, retorna la ruta al archivo guardado.
            - Si es False, retorna True si la reproducción fue exitosa.
            - Retorna None en caso de error.
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
    
    print(f"\n=== Configuración TTS ===")
    print(f"Motor: {engine}")
    
    try:
        # Usar el motor TTS correspondiente
        if engine == 'azure':
            from func.azure_tts import synthesize_text, get_available_voices
            
            # Obtener la lista de voces disponibles
            voices = get_available_voices()
            print(f"Voces disponibles: {len(voices)}")
            
            # Si no se especificó una voz, mostrar menú para seleccionar
            if voice_id is None:
                print("\nSelecciona un idioma para la voz:")
                print("1. Español")
                print("2. Inglés")
                print("x. Usar voz predeterminada")
                
                lang_choice = input("\nSelecciona una opción: ").strip().lower()
                
                if lang_choice == '1':
                    voice_id = select_voice_by_language(engine, 'es')
                elif lang_choice == '2':
                    voice_id = select_voice_by_language(engine, 'en')
                elif lang_choice in ('x', 'salir', 'exit'):
                    print("Usando voz predeterminada.")
                
                if not voice_id:
                    print("No se seleccionó ninguna voz. Usando voz predeterminada.")
                    voice_id = 'es-MX-JorgeNeural'  # Voz predeterminada en español
            
            print(f"\n=== Sintetizando voz ===")
            print(f"Voz seleccionada: {voice_id}")
            print(f"Texto: {text[:100]}{'...' if len(text) > 100 else ''}")
            
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
                print("\n✅ Reproducción completada")
                return True
                
            # Si llegamos aquí, necesitamos guardar el audio
            audio_data = result  # En este caso, result contiene los datos de audio
            file_path = save_speech_to_file(audio_data, filename, output_dir)
            print(f"\n✅ Audio guardado en: {file_path}")
            return file_path
            
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

def select_language_menu(engine):
    """Menú para seleccionar el idioma de la voz"""
    print("\n=== Selecciona un idioma ===")
    print("1. Español")
    print("2. Inglés")
    print("3. Buscar otro idioma")
    print("x. Volver al menú principal")
    
    while True:
        option = input("\nSelecciona una opción: ").strip().lower()
        
        if option == '1':
            return select_voice_by_language(engine, 'es')
        elif option == '2':
            return select_voice_by_language(engine, 'en')
        elif option == '3':
            return search_voice(engine)
        elif option in ('x', 'salir', 'exit'):
            return None
        else:
            print("Opción no válida. Intenta de nuevo.")

def select_voice_by_language(engine, language_code):
    """Selecciona una voz por código de idioma"""
    try:
        if engine == 'azure':
            try:
                from func.azure_tts import get_available_voices
                voices = get_available_voices()
                
                # Filtrar voces por idioma
                lang_voices = [v for v in voices 
                            if v.get('locale', '').startswith(language_code)]
                
                if not lang_voices:
                    print(f"No se encontraron voces para el idioma seleccionado.")
                    return None
                    
                # Mostrar voces
                print(f"\n=== Voces disponibles ({'Español' if language_code == 'es' else 'Inglés'}) ===")
                for i, voice in enumerate(lang_voices, 1):
                    display_name = voice.get('display_name', voice.get('name', 'Desconocido'))
                    locale = voice.get('locale', '')
                    print(f"{i}. {display_name} ({locale})")
                
                # Seleccionar voz
                while True:
                    try:
                        selection = input("\nSelecciona una voz (número) o 'x' para volver: ").strip().lower()
                        
                        if selection in ('x', 'salir', 'exit'):
                            return None
                            
                        if selection.isdigit():
                            idx = int(selection) - 1
                            if 0 <= idx < len(lang_voices):
                                return lang_voices[idx].get('name')
                        
                        print("Opción no válida. Intenta de nuevo.")
                        
                    except (ValueError, IndexError):
                        print("Opción no válida. Intenta de nuevo.")
                        
            except Exception as e:
                print(f"Error al obtener las voces de Azure TTS: {str(e)}")
                return None
                
        else:  # Edge TTS
            try:
                from func.edge_tts import list_voices as get_edge_voices
                voices = get_edge_voices()
                
                # Filtrar voces por idioma
                lang_voices = [v for v in voices 
                            if v.get('ShortName', '').startswith(f"{language_code}-")]
                
                if not lang_voices:
                    print(f"No se encontraron voces para el idioma seleccionado.")
                    return None
                    
                # Mostrar voces
                print(f"\n=== Voces disponibles ({'Español' if language_code == 'es' else 'Inglés'}) ===")
                for i, voice in enumerate(lang_voices, 1):
                    name = voice.get('ShortName', 'Desconocido')
                    gender = voice.get('Gender', '').capitalize()
                    print(f"{i}. {name} ({gender})")
                
                # Seleccionar voz
                while True:
                    try:
                        selection = input("\nSelecciona una voz (número) o 'x' para volver: ").strip().lower()
                        
                        if selection in ('x', 'salir', 'exit'):
                            return None
                            
                        if selection.isdigit():
                            idx = int(selection) - 1
                            if 0 <= idx < len(lang_voices):
                                return lang_voices[idx].get('ShortName')
                        
                        print("Opción no válida. Intenta de nuevo.")
                        
                    except (ValueError, IndexError):
                        print("Opción no válida. Intenta de nuevo.")
                        
            except ImportError:
                print("\n⚠️  El motor Edge TTS no está disponible.")
                print("Por favor, instala el paquete edge-tts o cambia a Azure TTS.")
                print("Puedes instalarlo con: pip install edge-tts")
                input("\nPresiona Enter para continuar...")
                return None
                
    except Exception as e:
        print(f"Error al obtener las voces: {str(e)}")
        return None

def search_voice(engine):
    """Buscar voz por término"""
    term = input("\nIngresa un término de búsqueda (ej: 'mexico', 'spanish', 'french'): ").strip().lower()
    
    try:
        if engine == 'azure':
            from func.azure_tts import get_available_voices
            voices = get_available_voices()
            
            # Filtrar voces por término de búsqueda
            filtered = [v for v in voices 
                       if term in v.get('name', '').lower() 
                       or term in v.get('display_name', '').lower()
                       or term in v.get('locale', '').lower()
                       or term in v.get('locale_name', '').lower()]
            
            if not filtered:
                print("No se encontraron voces que coincidan con la búsqueda.")
                return None
                
            # Mostrar resultados
            print(f"\n=== Resultados de búsqueda ({len(filtered)}) ===")
            for i, voice in enumerate(filtered, 1):
                print(f"{i}. {voice.get('display_name', voice.get('name', 'Desconocido'))} ({voice.get('locale', '')})")
            
            # Seleccionar voz
            while True:
                try:
                    selection = input("\nSelecciona una voz (número) o 'x' para volver: ").strip().lower()
                    
                    if selection in ('x', 'salir', 'exit'):
                        return None
                        
                    if selection.isdigit():
                        idx = int(selection) - 1
                        if 0 <= idx < len(filtered):
                            return filtered[idx].get('name')
                    
                    print("Opción no válida. Intenta de nuevo.")
                    
                except (ValueError, IndexError):
                    print("Opción no válida. Intenta de nuevo.")
                    
        else:  # Edge TTS
            try:
                from func.edge_tts import list_voices as get_edge_voices
                voices = get_edge_voices()
                
                # Filtrar voces por término de búsqueda
                filtered = [v for v in voices 
                           if term in v.get('ShortName', '').lower() 
                           or term in v.get('Gender', '').lower()
                           or term in v.get('Name', '').lower()
                           or term in v.get('Locale', '').lower()]
                
                if not filtered:
                    print("No se encontraron voces que coincidan con la búsqueda.")
                    return None
                    
                # Mostrar resultados
                print(f"\n=== Resultados de búsqueda ({len(filtered)}) ===")
                for i, voice in enumerate(filtered, 1):
                    name = voice.get('ShortName', 'Desconocido')
                    gender = voice.get('Gender', '').capitalize()
                    print(f"{i}. {name} ({gender})")
                
                # Seleccionar voz
                while True:
                    try:
                        selection = input("\nSelecciona una voz (número) o 'x' para volver: ").strip().lower()
                        
                        if selection in ('x', 'salir', 'exit'):
                            return None
                            
                        if selection.isdigit():
                            idx = int(selection) - 1
                            if 0 <= idx < len(filtered):
                                return filtered[idx].get('ShortName')
                        
                        print("Opción no válida. Intenta de nuevo.")
                        
                    except (ValueError, IndexError):
                        print("Opción no válida. Intenta de nuevo.")
            except ImportError:
                print("\n⚠️  El motor Edge TTS no está disponible.")
                print("Por favor, instala el paquete edge-tts o cambia a Azure TTS.")
                print("Puedes instalarlo con: pip install edge-tts")
                input("\nPresiona Enter para continuar...")
                return None
                    
    except Exception as e:
        print(f"Error al buscar voces: {str(e)}")
        return None

def main_menu():
    """Menú principal simplificado de prueba TTS"""
    print("\n" + "="*50)
    print("  PRUEBA DE SÍNTESIS DE VOZ (TTS)".center(50))
    print("="*50)
    
    # Obtener configuración
    engine = get_tts_engine_config()
    
    # Configuración predeterminada
    voice_id = None
    
    while True:
        print("\n=== Menú Principal ===")
        print(f"1. Probar TTS (Motor: {engine})")
        print(f"2. Seleccionar voz")
        print("3. Cambiar motor TTS")
        print("4. Salir")
        
        option = input("\nSelecciona una opción: ").strip()
        
        if option == '1':
            # Usar la función speech directamente
            print("\n=== Prueba de TTS ===\n")
            print(f"Configuración actual:")
            print(f"- Motor: {engine}")
            print(f"- Voz: {voice_id if voice_id else 'No seleccionada (se usará la predeterminada)'}")
            
            print("\nOpciones:")
            print("1. Probar con un texto de ejemplo")
            print("2. Ingresar texto personalizado")
            print("x. Volver al menú principal")
            
            sub_option = input("\nSelecciona una opción: ").strip().lower()
            
            if sub_option == '1':
                test_text = f"Hola, esto es una prueba de síntesis de voz con {engine}."
                print(f"\nTexto de ejemplo: {test_text}")
                
                # Opciones de reproducción
                print("\n¿Qué deseas hacer?")
                print("1. Solo reproducir")
                print("2. Guardar en archivo")
                print("3. Ambas")
                print("x. Cancelar")
                
                action = input("\nSelecciona una opción: ").strip().lower()
                
                if action == '1':
                    print(f"\nReproduciendo con voz: {voice_id if voice_id else 'predeterminada'}")
                    speech(test_text, engine=engine, voice_id=voice_id, save_to_file=False)
                elif action == '2':
                    filename = f"tts_output_{int(time.time())}.mp3"
                    output_dir = os.path.join("media", "audios", "tts")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                    
                    print(f"\nGuardando en: {output_path}")
                    speech(test_text, engine=engine, voice_id=voice_id, save_to_file=True, filename=filename, output_dir=output_dir)
                    print("✓ Archivo guardado exitosamente")
                elif action == '3':
                    filename = f"tts_output_{int(time.time())}.mp3"
                    output_dir = os.path.join("media", "audios", "tts")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                    
                    print(f"\nReproduciendo y guardando en: {output_path}")
                    speech(test_text, engine=engine, voice_id=voice_id, save_to_file=True, filename=filename, output_dir=output_dir)
                    print("✓ Archivo guardado exitosamente")
                elif action in ('x', 'salir', 'exit', 'cancelar'):
                    continue
                else:
                    print("Opción no válida.")
                    
            elif sub_option == '2':
                text = input("\nIngresa el texto a sintetizar: ").strip()
                if not text:
                    print("No se ingresó ningún texto.")
                    continue
                    
                # Opciones de reproducción
                print("\n¿Qué deseas hacer?")
                print("1. Solo reproducir")
                print("2. Guardar en archivo")
                print("3. Ambas")
                print("x. Cancelar")
                
                action = input("\nSelecciona una opción: ").strip().lower()
                
                if action == '1':
                    print(f"\nReproduciendo con voz: {voice_id if voice_id else 'predeterminada'}")
                    speech(text, engine=engine, voice_id=voice_id, save_to_file=False)
                elif action == '2':
                    filename = f"tts_output_{int(time.time())}.mp3"
                    output_dir = os.path.join("media", "audios", "tts")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                    
                    print(f"\nGuardando en: {output_path}")
                    speech(text, engine=engine, voice_id=voice_id, save_to_file=True, filename=filename, output_dir=output_dir)
                    print("✓ Archivo guardado exitosamente")
                elif action == '3':
                    filename = f"tts_output_{int(time.time())}.mp3"
                    output_dir = os.path.join("media", "audios", "tts")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                    
                    print(f"\nReproduciendo y guardando en: {output_path}")
                    speech(text, engine=engine, voice_id=voice_id, save_to_file=True, filename=filename, output_dir=output_dir)
                    print("✓ Archivo guardado exitosamente")
                elif action in ('x', 'salir', 'exit', 'cancelar'):
                    continue
                else:
                    print("Opción no válida.")
            
            input("\nPresiona Enter para continuar...")
            
        elif option == '2':
            voice_id = select_language_menu(engine)
        elif option == '3':
            engine = change_engine()
            voice_id = None  # Resetear la voz al cambiar de motor
        elif option in ('4', 'salir', 'exit'):
            print("\n¡Hasta luego!")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

def change_engine():
    """Cambia el motor TTS"""
    print("\n=== Cambiar motor TTS ===")
    print("1. Azure TTS")
    print("2. Edge TTS")
    
    option = input("Selecciona un motor (1-2): ").strip()
    
    if option == '1':
        return 'azure'
    elif option == '2':
        return 'edge'
    else:
        print("Opción no válida. Usando Azure TTS por defecto.")
        return 'azure'

def list_available_voices(engine):
    """Muestra las voces disponibles"""
    print(f"\n=== Voces disponibles ({engine.upper()}) ===")
    
    try:
        if engine == 'azure':
            from func.azure_tts import get_available_voices
            voices = get_available_voices()
            
            # Agrupar por idioma
            voices_by_lang = {}
            for voice in voices:
                lang = voice.get('locale', 'Desconocido')
                if lang not in voices_by_lang:
                    voices_by_lang[lang] = []
                voices_by_lang[lang].append(voice)
            
            # Mostrar por idioma
            for lang, lang_voices in sorted(voices_by_lang.items()):
                print(f"\n{lang}:")
                for i, voice in enumerate(lang_voices[:5], 1):  # Mostrar solo 5 por idioma
                    name = voice.get('name', 'Desconocido')
                    display = voice.get('display_name', name)
                    print(f"  {i}. {display}")
                if len(lang_voices) > 5:
                    print(f"  ... y {len(lang_voices) - 5} más")
        
        elif engine == 'edge':
            from func.edge_tts import list_voices as get_edge_voices
            voices = get_edge_voices()
            
            # Agrupar por idioma
            voices_by_lang = {}
            for voice in voices:
                lang = voice.get('ShortName', 'Desconocido').split('-')[0]
                if lang not in voices_by_lang:
                    voices_by_lang[lang] = []
                voices_by_lang[lang].append(voice)
            
            # Mostrar por idioma
            for lang, lang_voices in sorted(voices_by_lang.items()):
                print(f"\n{lang}:")
                for i, voice in enumerate(lang_voices[:5], 1):  # Mostrar solo 5 por idioma
                    name = voice.get('ShortName', 'Desconocido')
                    gender = voice.get('Gender', '').capitalize()
                    print(f"  {i}. {name} ({gender})")
                if len(lang_voices) > 5:
                    print(f"  ... y {len(lang_voices) - 5} más")
    
    except Exception as e:
        print(f"Error al obtener las voces: {str(e)}")
    
    input("\nPresiona Enter para continuar...")
    return engine

# Punto de entrada principal
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n¡Hasta luego!")
    except Exception as e:
        print("\n¡Se produjo un error inesperado!")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para salir...")
