import pyttsx3


def tts(text,output_file,velocidad):
    # Inicializa el motor TTS
    engine = pyttsx3.init()

    # Configura la velocidad del habla (opcional)
    engine.setProperty('rate', velocidad)

    # Guarda el texto convertido a voz en un archivo MP3
    engine.save_to_file(text, output_file)

    # Ejecuta el motor y espera a que termine
    engine.runAndWait()

#tts("hola","test.mp3",100)