# HAMNA Web

La versión web de HAMNA Desktop. Corre **dentro del nodo** (AllStarLink o IRLP) y automatiza redes y boletines: el operador sube los audios o escribe textos desde el navegador, arma eventos, los programa, y el nodo los transmite solo, con pausas automáticas para respetar el temporizador de los repetidores.

## Instalación

En el nodo, como usuario con sudo:

```bash
tar xzf hamna-web-1.0.0.tar.gz
cd hamna-web-1.0.0
sudo ./install.sh
```

El instalador:

1. Detecta si el nodo es **ASL** (ASL3, ASL2, HamVOIP) o **IRLP**, y el número de nodo.
2. Instala `python3-flask`, `python3-waitress`, `ffmpeg` y `espeak-ng`.
3. Copia el programa a `/opt/hamna-web`. Los datos van a `/var/lib/hamna`.
4. Pide la contraseña de la página.
5. Crea el servicio `hamna-web` y abre el puerto 8090 en el firewall si hay uno activo.

Después abre `http://IP-DEL-NODO:8090`.

Opciones: `--tipo asl|irlp`, `--nodo 12345`, `--puerto 8090`, `--password CLAVE`, `--sin-espeak`.
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
| ASL | `asterisk -rx "rpt localplay <nodo> <archivo>"`. app_rpt activa y suelta el PTT. Con el modo **playback** el audio también va a los nodos enlazados. | `asterisk` |
| IRLP | `$BIN/key` → `aplay` → `$BIN/unkey`, con el entorno de `/home/irlp/custom/environment`. El audio sale solo por el radio local, no por el reflector. | `repeater` |

Todo se convierte a WAV 8 kHz, 16 bits, mono (el formato de Asterisk) y se normaliza a -18 LUFS medidos en mono, con limitador a -2 dB.

## Pausas automáticas

Cada sección más larga que el "tiempo antes de pausar" se corta en tramos. Cada tramo es un solo archivo, así el PTT no se suelta a la mitad:

```
[silencio PTT] + [Continuamos] + audio + [Vamos a pausa]
                           alerta ↑ mezclada N s antes del corte
```

Entre tramos el PTT se suelta durante la pausa, y el tramo siguiente puede empezar unos segundos antes del corte (retroceso).

## Diferencias con HAMNA Desktop

- Mismo esquema de base de datos y mismas variables TTS, más `{fecha_larga}`, `{numero}` y `{nodo}`.
- Voces: Azure (igual que Desktop), Piper (`asl3-tts`, voz neuronal local en ASL3) y eSpeak NG. No hay SAPI5.
- El intervalo entre secciones es un ajuste aparte (en Desktop era la misma duración que la pausa).
- No se pueden programar dos eventos a la vez en el mismo minuto: el segundo detiene al primero, como en Desktop.

## Desarrollo en Windows

```bash
python -m venv .venv && .venv/Scripts/pip install flask waitress
set HAMNA_DATA=%TEMP%\hamna
.venv\Scripts\python -m hamna --init backend=simulado
.venv\Scripts\python -m hamna --set-password prueba123
.venv\Scripts\python -m hamna --port 8090
```

El modo `simulado` no transmite nada, solo respeta los tiempos. Necesita `ffmpeg` en el PATH.
