import json
import os
from pathlib import Path

def get_tts_config():
    """Obtiene la configuración del motor TTS desde el archivo de configuración"""
    config_path = os.path.join(Path.home(), '.hamna', 'config', 'tts_config.json')
    default_config = {
        'engine': 'azure',  # Valor por defecto
        'voices': {}
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error al leer la configuración TTS: {e}")
    
    return default_config

def get_available_voices(engine=None):
    """Obtiene las voces disponibles para el motor especificado"""
    if engine is None:
        config = get_tts_config()
        engine = config.get('engine', 'azure')
    
    # Importar el módulo correspondiente según el motor
    try:
        if engine.lower() == 'azure':
            from .azure_tts import load_voices_from_cache
            return load_voices_from_cache()
        elif engine.lower() == 'edge':
            from .edge_tts import list_voices
            return list_voices()
        else:
            print(f"Motor de TTS no soportado: {engine}")
            return []
    except ImportError as e:
        print(f"Error al importar el módulo de {engine}: {str(e)}")
        return []

def get_filtered_voices(engine=None, filters=None):
    """
    Obtiene las voces filtradas según los idiomas habilitados
    
    Args:
        engine: Motor TTS a usar (azure, edge, etc.)
        filters: Diccionario con los filtros de idioma (ej: {'en': True, 'es': False})
    
    Returns:
        Lista de voces formateadas y filtradas
    """
    if engine is None:
        config = get_tts_config()
        engine = config.get('engine', 'azure')
    
    if filters is None:
        config = get_tts_config()
        filters = {
            'en': config.get('filter_en', True),
            'es': config.get('filter_es', True),
            'pt': config.get('filter_pt', False),
            'fr': config.get('filter_fr', False),
            'de': config.get('filter_de', False),
            'it': config.get('filter_it', False),
            'ja': config.get('filter_ja', False),
            'ko': config.get('filter_ko', False),
            'ru': config.get('filter_ru', False),
            'zh': config.get('filter_zh', False)
        }
    
    # Obtener voces disponibles
    all_voices = get_available_voices(engine)
    
    # Filtrar voces según los idiomas habilitados
    enabled_languages = [lang for lang, enabled in filters.items() if enabled]
    
    voices = []
    for voice in all_voices:
        voice_lang = voice.get('locale', voice.get('ShortName', '')).split('-')[0].lower()
        
        # Si no hay filtros o la voz coincide con algún idioma habilitado
        if not enabled_languages or any(lang.startswith(voice_lang) for lang in enabled_languages):
            # Formatear el nombre para mostrar según el motor
            if engine == 'azure':
                display_name = f"{voice.get('display_name')} ({voice.get('locale')})"
            else:  # edge
                display_name = f"{voice.get('FriendlyName')} ({voice.get('ShortName')})"
            
            voices.append({
                'id': voice.get('name') or voice.get('ShortName'),
                'display_name': display_name,
                'locale': voice.get('locale') or voice.get('ShortName', '').split('-')[0]
            })
    
    # Ordenar por nombre
    return sorted(voices, key=lambda x: x['display_name'].lower())
