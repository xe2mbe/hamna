# HAMNA - _Amateur Radio Net Automatization_
> La radioafición siempre ha destacado por la creatividad y la innovación de sus operadores. 
> En este espíritu, nace HAMNA (HAM Net Automation), un proyecto diseñado para facilitar y 
> modernizar las transmisiones en estaciones de radioaficionados, especialmente para aplicaciones 
> como boletines dominicales y otros contenidos recurrentes.

¿Qué es HAMNA? HAMNA es un software de código abierto que automatiza la transmisión de contenido pregrabado en estaciones de radio. Su principal objetivo es reducir la carga operativa del radioaficionado o estacion control responsable de la transmision del boletín, programa o net al permitir programar y transmitir contenido sin la necesidad de estar presente físicamente frente a la estación.

## Principales características:
 - Automatización de transmisiones: Con HAMNA, el operador puede cargar y programar boletines, anuncios o cualquier contenido de audio con anticipación.
 - Integración flexible: Compatible con diversas configuraciones de radio y sistemas operativos, HAMNA es adaptable a las necesidades de cualquier estación.
 - Código abierto: El proyecto, disponible en GitHub, permite a los operadores modificar y personalizar el software según sus requerimientos específicos.
 - Facilidad de uso: Una interfaz intuitiva facilita la programación y el monitoreo de las transmisiones.

## Descripción técnica del código: 
El código de HAMNA está diseñado en Python, aprovechando su flexibilidad y facilidad de implementación en múltiples plataformas. Entre sus componentes principales destacan:
 - Sistema de manejo de tareas programadas: Utiliza bibliotecas como schedule o crontab para programar y gestionar transmisiones en intervalos específicos.
 - Reproducción de audio: Hace uso de bibliotecas como pydub o playsound para garantizar una reproducción de alta calidad y compatible con varios formatos de audio, como MP3 y WAV.
 - Interfaz de configuración: Una interfaz basada en archivos de texto o configuración YAML permite personalizar horarios, rutas de audio y parámetros específicos de la transmisión.

## Configuración:
La version actual (primitiva) ofrece una version donde el operador debe tener conocimientos basicos de Python, ya que los parámetros de operación deben ser actualizados desde el script principal (main.py), estos parametros son:
1.- Mensajes:
```sh
mensaje_entrada = """Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Gracias por sintonizarnos, en un instante iniciamos. 
Esta es una transmisión automátizada mediante la aplicación HAMNA"""
```
```sh
mensaje_salida = (f"""Gracias por sintonizar el boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Hemos terminado con nuestra emisión de este día {fecha}. 
Les recordamos que esta es una transmisión automátizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A C.
Agradecemos por escuchar este medio de difusión de la máxima autoridad de radio afición en nuestro país, 
ahora damos paso a la estación control para que inicie la toma de reportes, hasta la próxima edición, 73 y feliz día.""")
```
2.- Parámetros de tiempo:
**play_duration:** Tiempo de transmision antes de una pausa.
**pause_duration:** Tiempo en pausa.
**alert_time:** Tiempo antes de la pausa para enviar el sonido de alerta de pausa.
**rewind_time** Tiempo en segudos para retroceder el audio déspues de la pausa.
```sh
# Configuración de parámetros (en segundos)
play_duration = 90
pause_duration = 8
alert_time = 7
rewind_time = 3
```
3.- Parámetros de reproducción:
En ocasiones el audio a transmitir no se desea que se reproduzca desde el inicio o hasta el final, para esto se utilizan las variables **star_time** y **end_time**.
```sh
# Configurar tiempos de inicio y fin (en formato hh:mm:ss)
start_time_str = "00:05:40"
end_time_str = "00:21:45"
```
## Control de PTT:
En esta versión de HAMNA aun no se tiene un control via software del PTT, por lo anterior, es necesario realizar un PTT físico, utilizando un pin del GPIO de la raspberry donde se tiene instalado el Nodo All Star. En nuestro caso el PIN por default es el GPIO 17.
### Instalación control de PTT
Se necesita cargar el archivo app.py que se encuentra dentro de hamna>src en la raspberry. Una vez descargado 

