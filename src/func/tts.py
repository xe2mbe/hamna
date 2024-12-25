import pyttsx3

def tts(text, output_file, velocidad):
    # Inicializa el motor TTS
    engine = pyttsx3.init()

    # Configura la velocidad del habla
    engine.setProperty('rate', velocidad)

    # Busca y selecciona una voz en español
    voces = engine.getProperty('voices')
    for voz in voces:
        if "spanish" in voz.languages or "es" in voz.id.lower():
            engine.setProperty('voice', voz.id)
            break
    else:
        print("Advertencia: No se encontró una voz en español. Usando la predeterminada.")

    # Guarda el texto convertido a voz en un archivo MP3
    engine.save_to_file(text, output_file)

    # Ejecuta el motor y espera a que termine
    engine.runAndWait()

# Ejemplo de uso
texto = "Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A.C."
tts(texto, "test.mp3", 150)
