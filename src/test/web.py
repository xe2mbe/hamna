import streamlit as st
from streamlit_player import st_player

# Título de la aplicación
st.title("Reproductor de Video Interactivo")

# Campo para ingresar la URL del video
video_url = st.text_input("Ingresa la URL del video:")

# Mensajes de entrada y salida
entry_message = st.text_input("Mensaje de entrada:")
exit_message = st.text_input("Mensaje de salida:")

# Tiempos de inicio y fin
start_time = st.number_input("Tiempo de inicio (en segundos):", min_value=0, value=0)
end_time = st.number_input("Tiempo de fin (en segundos):", min_value=0, value=10)

# Botón para iniciar la reproducción
if st.button("Iniciar Video"):
    if video_url:
        st.write(entry_message)  # Mostrar mensaje de entrada
        st_player(video_url, start_time=start_time, playing=True, muted=True)  # Reproducir video
        st.write(exit_message)  # Mostrar mensaje de salida
    else:
        st.error("Por favor, ingresa una URL de video válida.")