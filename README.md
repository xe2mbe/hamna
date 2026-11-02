# HAMNA Web

La versión web de HAMNA Desktop. Corre **dentro del nodo** (AllStarLink o IRLP) y automatiza redes y boletines: el operador sube los audios o escribe textos desde el navegador, arma eventos, los programa, y el nodo los transmite solo, con pausas automáticas para respetar el temporizador de los repetidores.

## Instalación

Copia `hamna-web-1.0.0.tar.gz` al nodo y, como root (o con `sudo`):

```bash
tar xzf hamna-web-1.0.0.tar.gz
cd hamna-web-1.0.0
./install.sh
```

El instalador:

1. Detecta si el nodo es **AllStarLink 3**, **HamVOIP**, ASL2 o **IRLP**, y el número de nodo.
2. No necesita paquetes de Python: solo Python 3.5 o más nuevo (HamVOIP trae 3.5).
3. En Debian/Raspbian (ASL3, IRLP) instala `ffmpeg` y `espeak-ng` con apt. En HamVOIP **no toca pacman**: usa `sox` y `mpg123`, que ya vienen.
4. Copia el programa a `/opt/hamna-web`. Los datos van a `/var/lib/hamna`.
5. Pide la contraseña de la página (si no hay terminal, genera una y la muestra).
6. Crea el servicio `hamna-web` y abre el puerto 8090 en el firewall si hay uno activo.

Después abre `http://IP-DEL-NODO:8090`.

Opciones: `--tipo asl|irlp`, `--nodo 12345`, `--puerto 8090`, `--password CLAVE`, `--sin-paquetes`.
Para actualizar, vuelve a ejecutar `install.sh` con la versión nueva. Tus eventos y audios se conservan.

| Tarea | Comando |
|---|---|
| Cambiar contraseña | `sudo hamna-web-passwd` |
| Ver bitácora | `journalctl -u hamna-web -f` |
| Reiniciar | `sudo systemctl restart hamna-web` |
| Desinstalar | `sudo /opt/hamna-web/uninstall.sh` (agrega `--borrar-datos` para borrar todo) |

## Cómo sale al aire

| Nodo | Cómo transmite | Usuario del servicio |
|---|---|---|
| ASL3 / HamVOIP | `asterisk -rx "rpt localplay <nodo> <archivo>"`. app_rpt activa y suelta el PTT. Con el modo **playback** el audio también va a los nodos enlazados. Detener/Pausa/Siguiente cortan con `rpt cmd <nodo> cop 24 0` (vaciar telemetría). | `asterisk` en ASL3, `root` en HamVOIP |
| IRLP | `$BIN/key` → `aplay` → `$BIN/unkey`, con el entorno de `/home/irlp/custom/environment`. El audio sale solo por el radio local, no por el reflector. | `repeater` |

Todo se convierte a WAV 8 kHz, 16 bits, mono (el formato de Asterisk) y se normaliza a -18 LUFS medidos en mono, con limitador a -2 dB. Con ffmpeg se mide LUFS real; con sox (HamVOIP) se aproxima con un filtro de ponderación K y una segunda pasada que compensa lo que se come el limitador.

Para ahorrar espacio, en **Ajustes → Nivel de audio** se puede desactivar "Guardar los audios originales": al subir un audio se guarda solo la versión para el aire (`.aire.wav`) y se borra el original. El botón "Convertir los ya subidos" hace lo mismo con lo que ya está en el nodo.

Formatos que acepta: con ffmpeg, MP3, WAV, M4A, OGG, FLAC, AAC, OPUS. Con sox + mpg123 (HamVOIP), MP3, WAV, OGG, FLAC (no M4A).

## Pausas automáticas

Cada sección más larga que el "tiempo antes de pausar" se corta en tramos. Cada tramo es un solo archivo, así el PTT no se suelta a la mitad:

```
[silencio PTT] + [Continuamos] + audio + [Vamos a pausa]
                           alerta ↑ mezclada N s antes del corte
```

Entre tramos el PTT se suelta durante la pausa, y el tramo siguiente puede empezar unos segundos antes del corte (retroceso).

## Diferencias con HAMNA Desktop

- Mismo esquema de base de datos y mismas variables TTS, más `{fecha_larga}`, `{numero}` y `{nodo}`.
- Voces: Azure (igual que Desktop), Piper (`asl3-tts`, voz neuronal local en ASL3) y eSpeak NG. No hay SAPI5. En HamVOIP solo Azure.
- El intervalo entre secciones es un ajuste aparte (en Desktop era la misma duración que la pausa).
- No se pueden programar dos eventos a la vez en el mismo minuto: el segundo detiene al primero, como en Desktop.

## Desarrollo en Windows

Sin dependencias: el servidor web está hecho con la librería estándar (`hamna/web.py`) y el código es compatible con Python 3.5 a 3.14 (verificado con `vermin`).

```bash
set HAMNA_DATA=%TEMP%\hamna
python -m hamna --init backend=simulado
python -m hamna --set-password prueba123
python -m hamna --port 8090
```

El modo `simulado` no transmite nada, solo respeta los tiempos. Necesita `ffmpeg` en el PATH.
