<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/logo-completo-oscuro.svg">
    <img src="docs/logo/logo-completo.svg" width="420" alt="HAMNA — HAM Net Automation">
  </picture>
</p>

<p align="center"><b>Español</b> · <a href="README.en.md">English</a></p>

# HAMNA — HAM Net Automation

> La radioafición siempre ha destacado por la creatividad y la innovación de sus operadores.
> En este espíritu nace HAMNA (HAM Net Automation), un proyecto diseñado para facilitar y
> modernizar las transmisiones en estaciones de radioaficionados, especialmente para boletines
> y otros contenidos recurrentes que se graban o preparan con anticipación.

## ¿Qué significa HAMNA?

**HAM** (radioaficionado) + **N**et + **A**utomation: automatización de redes de radioaficionados. Una *net* es la reunión al aire de colegas a una hora fija, guiada por una estación control; HAMNA se encarga de la parte que se puede preparar con tiempo —boletines, anuncios, programas grabados— para que salga al aire sola, a su hora y respetando los repetidores.

## Cómo nació

HAMNA nació en diciembre de 2024 en el **Radio Club Guadiana A.C.** (Durango, México) para transmitir el **Boletín Dominical de la Federación Mexicana de Radio Experimentadores (FMRE)**. Cada domingo, un operador debía permanecer en vivo frente a la estación para difundir un contenido que, en la mayoría de los casos, había sido preparado con antelación. Cuando sus actividades o compromisos personales se lo impedían, el boletín simplemente no se emitía: para otros operadores resultaba difícil relevarlo, ya fuera porque no contaban con el material o porque les faltaba experiencia en la conducción de la emisión y en el control de los tiempos para la caída de los repetidores. HAMNA vino a automatizar esa parte: el material sale al aire solo, a su hora, y el operador queda libre para sus actividades. Lo único que queda pendiente es la toma de reportes, que puede hacerla cualquier operador.

- **La versión primitiva (diciembre de 2024)** era un script en Python. Los mensajes de entrada y salida, los tiempos de transmisión y de pausa, la alerta antes de la pausa y el retroceso al reanudar se ajustaban en el código o en un archivo YAML. El PTT era físico: un pin GPIO (el 17) de la Raspberry Pi del nodo AllStar.
- **HAMNA Desktop (2026)** lo convirtió en una aplicación con interfaz: eventos armados con secciones, voz sintética (Azure), nivelación del audio, pausas automáticas y programación semanal. Vive en [xe2mbe/hamna_desktop](https://github.com/xe2mbe/hamna_desktop).
- **HAMNA Web (noviembre de 2026)** —este repositorio— lleva todo eso **dentro del propio nodo**, sin una PC encendida: se administra desde el navegador, transmite directamente por AllStarLink o IRLP y se puede compartir con los colegas del club, cada uno con su usuario.

Las mismas palabras con las que nació siguen saliendo al aire: *«Les recordamos que esta es una transmisión automatizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A.C.»*

---

## HAMNA Web

HAMNA Web corre **dentro del nodo** (AllStarLink 3, HamVOIP, ASL2 o IRLP) y automatiza boletines, nets y programas: desde el navegador se suben los audios o se escriben los textos, se arman los eventos, se programan, y el nodo los transmite solo, con pausas automáticas para respetar el temporizador de los repetidores. No necesita una PC encendida.

**Contenido:** [Capturas](#capturas) · [Qué hace](#qué-hace) · [Requisitos](#requisitos) · [Instalación](#instalación) · [Actualizar](#actualizar) · [Primeros pasos](#primeros-pasos) · [La página](#la-página) · [Programación y zonas horarias](#programación-y-zonas-horarias) · [Secciones y audios](#secciones-y-audios) · [Cómo sale al aire](#cómo-sale-al-aire) · [Pausas automáticas](#pausas-automáticas) · [Conexiones](#conexiones) · [Escuchar en vivo](#escuchar-en-vivo) · [Grabaciones](#grabaciones) · [Sincronizar eventos entre nodos](#sincronizar-eventos-entre-nodos) · [Panel de nodos](#panel-de-nodos) · [Avisos por Telegram](#avisos-por-telegram) · [Bot de Telegram](#bot-de-telegram) · [Respaldos](#respaldos) · [Salud del equipo y diagnóstico](#salud-del-equipo-y-diagnóstico) · [Usuarios y seguridad](#usuarios-y-seguridad) · [Cron](#cron) · [Archivos](#archivos) · [Problemas comunes](#problemas-comunes) · [Desarrollo](#desarrollo)

### Capturas

Tomadas del hub **299081** del Radio Club Guadiana.

<p align="center"><img src="docs/img/pc-programacion.png?v=1.32.0" width="900" alt="Programación: eventos con la hora del nodo, la de origen y su número de emisión"></p>

| Eventos y sus secciones | Secciones agrupadas por evento |
|---|---|
| <img src="docs/img/pc-eventos.png?v=1.32.0" alt="Detalle de un evento con sus secciones en orden"> | <img src="docs/img/pc-secciones.png?v=1.32.0" alt="Secciones por evento, con las que se renuevan en cada emisión"> |

| Conexiones | Panel de nodos (hub) |
|---|---|
| <img src="docs/img/pc-conexiones.png?v=1.32.0" alt="Conexiones: nodos enlazados en este momento"> | <img src="docs/img/pc-nodos.png?v=1.32.0" alt="Tarjetas de los nodos que reportan al hub"> |

<p align="center"><img src="docs/img/pc-respaldo.png?v=1.32.0" width="900" alt="Respaldo automático a otro nodo y a la nube"></p>

**En el celular** — programación, menú y panel de nodos:

<p align="center"><img src="docs/img/celular.png?v=1.32.0" width="900" alt="HAMNA Web en el celular"></p>

### Qué hace

- **Eventos armados con secciones**: audios (MP3, WAV, OGG, FLAC…), textos que se leen con voz sintética (Azure, Google Cloud, ElevenLabs, Piper o eSpeak, con respaldo automático entre motores) y sonidos, en el orden que quieras.
- **Programación** única, diaria, semanal o de lunes a viernes, **en la zona horaria del programa** (se ajusta sola al horario de verano de esa zona), con **numeración automática** de las emisiones.
- **Transmisión automática** por AllStarLink o IRLP, con nivel de audio parejo (-18 LUFS) y pausas automáticas para los repetidores.
- **Conexiones automáticas** antes y después de cada evento, y una pestaña **Conexiones** para ver y controlar los enlaces del nodo en vivo.
- **Escuchar el nodo en vivo** desde la página (computadora o celular), sin complementos, en ASL e IRLP, y **grabar** lo que se escucha (p. ej. la toma de reportes) en MP3.
- **Sincronización entre nodos**: otro HAMNA (por ejemplo, el que retransmite en otra ciudad) se trae solo las secciones y audios de un evento, cada semana.
- **Panel de nodos** en el hub: una tarjeta por cada HAMNA del club con su estado, salud y último respaldo.
- **Telegram**: avisos y un **bot** para consultar, transmitir, grabar y que los colaboradores manden su audio.
- **Respaldos** descargables y automáticos (a otro nodo, a Google Drive / OneDrive o por Telegram), y restauración desde la página.
- **Usuarios con roles** (incluido **Colaborador**, que solo sube el audio de sus secciones), perfil con foto, idioma por usuario (inglés o español), tema claro u oscuro y logo de la estación.
- **Monitor y salud del equipo** (CPU, RAM, disco, temperatura, tarjeta SD, bajo voltaje), **Revisar este nodo** y **aviso de actualizaciones** desde GitHub.
- Ligero: sin paquetes de Python, pensado para una Raspberry Pi.

### Requisitos

| | ASL3 (Debian 12/13) | HamVOIP | IRLP |
|---|---|---|---|
| Python | 3.5 o más nuevo (viene con el sistema) | 3.5 (viene con el sistema) | 3.5 o más nuevo |
| Audio | `ffmpeg` (lo instala el instalador) | `sox` y `mpg123` (ya vienen; no se toca pacman) | `ffmpeg` y `alsa-utils` |
| Voz | Azure, Google, ElevenLabs, Piper (`asl3-tts`) o eSpeak | Azure, Google o ElevenLabs | Azure, Google, ElevenLabs o eSpeak |
| Página en `/hamna/` | Apache (Allmon3 / AllScan) | httpd (Supermon / Allmon2) | — (puerto 8090) |

### Instalación

En el nodo, como root (o con `sudo`):

```bash
curl -sL https://raw.githubusercontent.com/xe2mbe/hamna/main/update.sh | sudo bash
```

(En HamVOIP, sin `sudo`.) Instala la **última versión publicada**. Si prefieres revisar antes los archivos, baja el paquete de la versión desde la página de *Releases/Tags* de GitHub, descomprímelo y corre `sudo bash install.sh`.

El instalador (sus mensajes y opciones están en inglés):

1. Detecta si el nodo es **AllStarLink 3**, **HamVOIP**, ASL2 o **IRLP**, y el número de nodo.
2. En Debian/Raspbian instala `ffmpeg` y `espeak-ng` con apt (si el nodo tiene `asl3-tts`, no instala `espeak-ng`: chocan). En HamVOIP **no toca pacman**.
3. Copia el programa a `/opt/hamna-web`. Los datos van a `/var/lib/hamna`.
4. Crea el usuario `admin` y pide su contraseña (si no hay terminal, genera una y la muestra).
5. Si el nodo tiene Apache, publica la página en **`https://IP-DEL-NODO/hamna/`** (HamVOIP: `http://`), en el mismo puerto que Allmon/AllScan/Supermon: no hay que abrir otro puerto.
6. Crea el servicio `hamna-web`. Con Apache, el servicio escucha **solo dentro del nodo** (127.0.0.1:8090) y el puerto 8090 se cierra en el firewall: todo pasa por `/hamna/`, con la contraseña cifrada. Sin Apache (p. ej. IRLP), queda en `http://IP-DEL-NODO:8090` y abre ese puerto en el firewall.
7. Crea las reglas de `sudo` para que la página pueda ver/editar el cron (ver [Cron](#cron)).

Opciones de `install.sh`:

| Opción | Para qué |
|---|---|
| `--type asl\|irlp` | Forzar el tipo de nodo (normalmente se detecta) |
| `--node 12345` | Número de nodo ASL o stationid de IRLP |
| `--port 8090` | Puerto interno de la página |
| `--password CLAVE` | Contraseña del usuario `admin` sin preguntar |
| `--no-packages` | No instalar nada con apt |
| `--no-cron` | No dar a la página permiso sobre el cron |
| `--no-apache` | No publicar `/hamna/` en Apache |
| `--listen-all` | Dejar el 8090 abierto a la red aunque haya Apache |
| `--force` | Instalar aunque haya algo al aire o preparándose |

Las opciones anteriores en español (`--tipo`, `--nodo`, `--puerto`, `--sin-paquetes`, `--sin-cron`) siguen funcionando.

### Actualizar

```bash
sudo /opt/hamna-web/update.sh
```

En HamVOIP, sin `sudo` (ya se entra como root). En nodos con una versión anterior a la 1.6.5, usa el comando de [Instalación](#instalación).

El actualizador instala la **última versión publicada** (la etiqueta `vX.Y.Z` más nueva del repositorio), no lo último que se haya subido a `main`: los cambios en prueba no les llegan a los nodos hasta que se publica una versión. Opciones: `--version v1.7.0` para instalar una versión concreta (también sirve para regresar a una anterior) y `--branch main` para probar lo último sin publicar. Después corre el `install.sh` de esa versión, que:

- **se niega a instalar si hay algo al aire o preparando audio** (para no cortar una transmisión);
- respalda antes los datos y el programa en `/var/backups/hamna/` (guarda los últimos 5);
- conserva eventos, audios, usuarios, ajustes y programación.

En la página, la etiqueta de versión junto a "HAMNA Web" se pone **verde** si estás al día y **ámbar** si hay versión nueva; en **Ajustes → Sistema → Actualizaciones** se ven los cambios y el comando para instalarla. La consulta a GitHub se hace solo para administradores y se guarda 6 horas.

| Tarea | Comando |
|---|---|
| Cambiar la contraseña de un usuario | `sudo hamna-web-passwd USUARIO` (la pide sin mostrarla y cierra sus sesiones) |
| Recuperar el acceso | `sudo hamna-web-passwd admin` (si `admin` no existe, se crea como administrador) |
| Crear otro administrador desde la terminal | `sudo hamna-web-passwd --create USUARIO` |
| Ver la bitácora | `journalctl -u hamna-web -f` (o `/var/lib/hamna/hamna.log`) |
| Reiniciar | `sudo systemctl restart hamna-web` |
| Desinstalar | `sudo /opt/hamna-web/uninstall.sh` (agrega `--delete-data` para borrar también los datos) |

### Primeros pasos

1. Entra a `https://IP-DEL-NODO/hamna/` con el usuario `admin`.
2. **Ajustes → Nodo**: revisa el número de nodo, el modo de reproducción (ver [Cómo sale al aire](#cómo-sale-al-aire)) y sube el logo de tu estación. Prueba con **"Transmitir prueba"**.
3. **Ajustes → Voz**: elige el motor de voz (Azure necesita clave y región; Google y ElevenLabs, su clave de API).
4. **Ajustes → Usuarios**: crea un usuario para cada colega con su rol.
5. **Secciones**: sube audios o escribe textos.
6. **Eventos**: crea un evento, agrégale secciones y ordénalas.
7. **Programación**: programa el evento con su hora y zona horaria.

### La página

- **Barra lateral** con las secciones, el monitor del equipo, tu usuario y el reloj del nodo. Se esconde con la flecha ‹ (y vuelve con ☰); en el celular es un menú que sale de la izquierda. Junto al nombre, etiquetas de color con el número de nodo y el tipo detectado: ASL3/ASL (azul), HamVOIP (naranja) e IRLP (morado).
- **Mi perfil** (clic en tu foto o nombre): foto, nombre, idioma, contraseña y sesiones abiertas. La foto se reduce en el navegador antes de subirla.
- **Idioma por usuario**: inglés (predeterminado) o español, en **Mi perfil**; la pantalla de entrada tiene su propio selector. Lo que sale al aire (voces, fechas) sigue en español.
- **Tema claro u oscuro** (botón de luna), recordado en cada navegador.
- **Logo de la estación** (Ajustes → Nodo): aparece en la barra, en la entrada y en la pestaña del navegador. El navegador lo reduce antes de subirlo.
- **Barra "Al aire"**: estado, sección actual, **tiempo restante / duración** de la sección y del evento, y controles (pausa, saltar espera, siguiente, detener, bitácora).
- **Monitor del equipo**: CPU, RAM, disco, temperatura (en HamVOIP no está disponible), carga, red y tiempo encendido. Con el menú escondido, la barra superior muestra CPU y temperatura.
- **Consumo**: la página pregunta el estado cada 1 s solo mientras hay algo al aire, cada 5 s en reposo y nada con la pestaña oculta. El monitor viene en esa misma consulta (leerlo toma ~4 ms en una Pi 3).

### Programación y zonas horarias

- Cada evento programado tiene su **zona horaria**: la hora y el día se toman en esa zona y HAMNA los convierte a la hora del nodo **para cada fecha**. Si el programa es de San Antonio (America/Chicago) o Tijuana, el evento se recorre solo cuando esa zona cambia de horario. Sin zona, se usa la hora del nodo.
- En la lista de zonas cada una dice su diferencia con UTC (p. ej. *EE. UU. centro (UTC−6, verano UTC−5)*), y junto al campo de hora se ve la hora en UTC.
- La tarjeta muestra en grande la **hora del nodo** con su zona (*19:00 · CDMX/Monterrey*), debajo la hora de origen (*Se emite desde: 17:00 Tijuana*) y avisa del próximo cambio de horario (*"A partir del 17 Mar 2027 será a las 18:00 (Horario de Verano)"*).
- La franja **Próximo evento** con la cuenta regresiva va encima de la tarjeta del evento que sigue.
- La **línea de tiempo** de cada tarjeta muestra las conexiones del evento y las tareas del cron de los usuarios (root, asterisk, IRLP) que caen cerca; las del sistema (`/etc/cron.d`) solo se ven en la pestaña Cron.
- Los audios de un evento se preparan (convierten y nivelan) **en cuanto** agregas secciones o guardas la programación, y otra vez 20 minutos antes de la hora.
- Variables para los textos de voz: `{fecha}`, `{fecha_larga}`, `{hora}`, `{dia}`, `{saludo}` (buenos días / buenas tardes / buenas noches), `{despedida}` (buen día / buena tarde / buena noche), `{evento}`, `{numero}`, `{emision}`, `{emision_anio}`, `{anio}`, `{num_secciones}`, `{duracion_total}`, `{dur_contabilizable}`, `{titulo}`, `{descripcion}`, `{pausa_cada}`, `{pausa_duracion}`, `{pausa_alerta}`, `{nodo}`. Las secciones de voz con "Regenerar antes de transmitir" se vuelven a generar justo antes de salir al aire.
- **Numeración automática** (detalle del evento): `{emision_anio}` cuenta las fechas programadas del evento en el año (el domingo 46 es la #46) y se reinicia cada 1 de enero; `{emision}` es el número global a partir de "la emisión del día R es la #N". Los números salen del calendario, no de un contador: una prueba, un reinicio o restaurar un respaldo no los mueven. El número avanza cuando termina la emisión del día (hora + duración + 30 min), así una prueba del sábado ya dice el número del domingo. Se ve en las tarjetas de Programación.

> En HamVOIP la base de zonas horarias del sistema es de 2016: las zonas de EE. UU. funcionan bien, pero las del centro de México todavía creen que hay horario de verano. Ahí usa "Hora del nodo" para los programas de México.

### Secciones y audios

- **Vista «Por evento»**: las secciones agrupadas por evento en el orden en que salen al aire; las que no usa ningún evento quedan en «Sin usar», plegadas.
- **«Se renueva en cada emisión» 🔁**: para secciones que cambian cada semana (editorial, DXpeditions, estadísticas…). La revisión previa avisa si alguna sigue con el audio de la emisión anterior.
- **Versión anterior**: al reemplazar un audio se guarda el anterior (`audios/anteriores/`, no va en los respaldos) y se puede regresar a él. Se controla con la opción "Al reemplazar el audio de una sección, guardar el anterior".
- **Descargar ⬇** el audio de una sección: el archivo tal cual si es un formato común; si no, convertido a WAV.
- **Exportar** secciones de un evento a un solo archivo (MP3 o WAV): eliges y ordenas las secciones, el silencio entre ellas y el nivel en LUFS; se arma en segundo plano y se descarga al terminar (44.1 kHz si hay originales, 8 kHz si solo existe la versión del aire).
- Si subes un audio que el nodo no puede leer (p. ej. MP3 en un nodo sin mpg123), la página lo convierte a WAV en el navegador antes de subirlo. Las subidas se rechazan antes de copiarse si no hay espacio.

**Voces** (Ajustes → Voz): Azure, **Google Cloud** (Neural2 / Chirp HD, con clave de API), **ElevenLabs** (clave de API; se ve la cuota), Piper y eSpeak. Los textos largos se parten por frases. Con **respaldo automático** activado, si el motor elegido falla se usan los demás que estén configurados (Azure → Google → ElevenLabs → Piper → eSpeak) y llega un solo aviso por Telegram.

### Cómo sale al aire

| Nodo | Cómo transmite | Usuario del servicio |
|---|---|---|
| ASL3 / HamVOIP | `asterisk -rx "rpt localplay\|playback <nodo> <archivo>"`; app_rpt activa y suelta el PTT. Detener/Pausa/Siguiente cortan con `rpt cmd <nodo> cop 24 0`. | `asterisk` en ASL3, `root` en HamVOIP |
| IRLP | `$BIN/key` → `aplay` → `$BIN/unkey`, con el entorno de `/home/irlp/custom/environment`. En modo **Radio + red** (predeterminado) el mismo audio va además al reflector o nodo conectado. | `repeater` |

**Modo de reproducción en ASL** (Ajustes → Nodo):

- `localplay`: solo el transmisor de este nodo.
- `playback`: este nodo **y todos los nodos enlazados**.

**Modo de reproducción en IRLP** (Ajustes → Nodo):

- **Radio + red** (predeterminado): este nodo **y el reflector o nodo conectado**, como `playback` en ASL.
- **Solo el radio**: solo el transmisor de este nodo.

IRLP solo manda a la red lo que entra por el receptor con COS, así que `aplay` por sí solo no llega al reflector. HAMNA usa el mismo `imike` de IRLP en modo archivo, con la identidad del nodo (`SPEAKFREE_CNAME` y `SPEAKFREE_ID`), y un relevo interno que lo reenvía al reflector desde un solo puerto y descarta la despedida RTCP (con ella el reflector olvida al emisor). imike comprime en el formato del canal (UNCOMP, ADPCM o GSM). La IP, el puerto y el formato salen de `local/calledip`, `local/udp_port` y `local/codec`, que IRLP escribe al conectar; en una llamada entrante de otro nodo IRLP no guarda la IP y el audio sale solo por el radio. Si algo de la parte de red falla, el radio sigue transmitiendo y queda anotado en la bitácora. Mientras HAMNA suena, el PTT se reactiva cada 0.3 s, porque IRLP lo suelta cuando alguien termina de hablar en el reflector. Probado con el reflector de eco 9990.

> **Importante (ASL3):** app_rpt solo manda el `playback` a los enlaces si el nodo tiene `duplex` mayor a 0 **o** `linktolink = yes`. En un hub con `duplex = 0`, agrega `linktolink = yes` en su estrofa de `rpt.conf` y reinicia Asterisk con `sudo systemctl restart asterisk` (nunca `rpt restart`). Sin eso, el audio suena en el hub pero los enlazados no lo oyen.

Todo se convierte a WAV 8 kHz, 16 bits, mono y se nivela a **-18 LUFS** medidos en mono, con limitador a -2 dB. Con ffmpeg la sonoridad se mide con el filtro `ebur128` (17 min de audio: ~1 min en una Pi 3); con sox (HamVOIP) se aproxima con ponderación K. La conversión corre con prioridad baja para que Asterisk nunca espere por la CPU.

En **Ajustes → Nivel de audio** se puede desactivar "Guardar los audios originales" para ahorrar espacio: se guarda solo la versión para el aire.

Formatos: con ffmpeg, MP3, WAV, M4A, OGG, FLAC, AAC, OPUS; con sox + mpg123 (HamVOIP), MP3, WAV, OGG, FLAC.

### Pausas automáticas

Cada sección más larga que el "tiempo antes de pausar" se corta en tramos; cada tramo es un solo archivo, así el PTT no se suelta a la mitad:

```
[silencio PTT] + [Continuamos] + audio + [Vamos a pausa]
                           alerta ↑ mezclada N s antes del corte
```

Entre tramos el PTT se suelta durante la pausa, y el tramo siguiente puede empezar unos segundos antes del corte (retroceso).

### Conexiones

**Pestaña Conexiones**: los nodos enlazados en este momento, con indicativo y ciudad (del directorio de AllStar), modo, dirección, tiempo conectado, IP y quién está hablando; un resumen con los nodos alcanzables en toda la red; y botones para **conectar** (transceptor, monitor o monitor local) y **desconectar**. Si el Asterisk tiene varios nodos, se elige cuál ver. Se actualiza cada 4 s solo con la pestaña abierta.

**En IRLP** la pestaña muestra a qué nodo o reflector está conectado (de `$LOCAL/active`), con la IP, el puerto y el formato de audio; el estado del radio (COS y PTT) y si HAMNA está transmitiendo, leídos cada 1.5 s; y los **otros nodos del mismo reflector**, según status.irlp.net (esa página se actualiza cada pocos minutos, así que una conexión de unos segundos no alcanza a aparecer).

**Conexiones automáticas de un evento** (Eventos → detalle → abajo): conectar o desconectar enlaces antes de empezar y al terminar.

| Sistema | Conectar | Desconectar |
|---|---|---|
| ASL / HamVOIP | `rpt cmd <nodo> ilink 3` (transceptor), `2` (monitor), `8` (monitor local) o `13` (permanente) | `ilink 1 <nodo>` o `ilink 6` (todos); si un enlace permanente sigue conectado, `ilink 11 <nodo>` |
| IRLP | `$SCRIPT/decode <nodo o reflector>` | `$SCRIPT/end` |

"N min antes" se adelanta solo cuando el evento está programado; si lo lanzas a mano, se hace al iniciar. Las de "al terminar" corren también si detienes el evento.

### Escuchar en vivo

Con la bocina **🔊** de la tarjeta de abajo (junto al contador) se escucha el nodo desde la página, en la computadora o el celular: lo que transmite HAMNA, los reportes de los colegas y los nodos enlazados. Llega con 1 a 2 segundos de retraso, en calidad de radio (8 kHz) y gasta unos 64 kbps por persona. Pueden escuchar hasta 8 personas a la vez; cualquier usuario, incluso de solo lectura.

Para activarlo, agrega esta línea en la sección de tu nodo en `/etc/asterisk/rpt.conf` (ASL3 y HamVOIP) y reinicia Asterisk **cuando no haya emisión** (`sudo systemctl restart asterisk`; en ASL3 nunca uses `rpt restart`):

```
outstreamcmd = /opt/hamna-web/bin/hamna-live
```

app_rpt le pasa el audio del nodo a ese pequeño programa, que lo reenvía a HAMNA Web dentro del mismo equipo (127.0.0.1:8091). Si HAMNA Web está apagado, el audio simplemente se descarta: nunca detiene a Asterisk. HAMNA lo convierte a µ-law solo mientras alguien escucha (≈1 % de CPU en una Raspberry Pi 4) y el navegador lo reproduce sin complementos. En **Ajustes → Sistema** se ve si llega audio y quién está escuchando.

**En IRLP** se enciende desde la página: **Ajustes → Sistema → Audio en vivo** (administrador). HAMNA agrega un bloque marcado en `/home/irlp/.asoundrc` que deriva lo que IRLP reproduce hacia `bin/hamna-live-irlp` y lee el receptor con `arecord` (dsnoop), sin quitarle la tarjeta de sonido a IRLP. Al encender prueba la salida y el receptor y, si algo falla, deja todo como estaba. Viene apagado; también se maneja con `/opt/hamna-web/bin/hamna-irlp-envivo on|off|status`, y el desinstalador quita el bloque.

### Grabaciones

Graba lo que se escucha en el nodo (lo que recibe y lo que transmite), por ejemplo la **toma de reportes** después del boletín. Usa el mismo audio de [Escuchar en vivo](#escuchar-en-vivo), así que necesita `outstreamcmd` (ASL) o el audio en vivo encendido (IRLP).

- Se inicia a mano, desde el bot (`/grabar`) o sola al terminar o al iniciar un evento (Ajustes). Mientras graba, la barra de abajo muestra **REC**.
- Los silencios largos no se graban (se dejan pausas de hasta 1 s), así la grabación queda corrida. Termina sola tras N minutos sin actividad (5 por omisión) o al llegar al tope (180 min), y se recorta el final.
- Se guarda en MP3 si el nodo puede (si no, WAV) con un título como «Boletín Dominical 46 · Toma de reportes», en la pestaña **Grabaciones**. Se borran solas después de 30 días (ajustable).
- Opcional: avisos de Telegram al empezar y terminar, y el audio mandado al grupo de avisos.

### Sincronizar eventos entre nodos

Sirve para que otro nodo retransmita un evento sin que nadie le pase los audios. Ejemplo: el nodo de Tijuana retransmite el Boletín Dominical que se arma en el hub.

**En el nodo que comparte** (evento → **Compartir con otros nodos**): un administrador crea un **código de acceso** y se lo pasa al otro nodo junto con la dirección de su HAMNA. El código es de **solo lectura**, sirve **solo para ese evento** (no permite entrar a la página) y se puede revocar; ahí mismo se ve cuándo y desde qué IP se usó.

**En el nodo que recibe** (su evento, por ejemplo "Retransmisión" → **Sincronización desde otro nodo**):

1. Dirección del HAMNA de origen (p. ej. `https://299081.nodes.allstarlink.org/hamna/`) y el código. **Probar conexión** muestra el evento, cuántas secciones tiene y su tamaño.
2. **Cuándo sincronizar**: días y hora, y/o "N horas antes de cada programación de este evento". Siempre está el botón **Sincronizar ahora**.

Al sincronizar:

- se copia el orden de las secciones, sus nombres, textos y el número de edición (`{numero}`);
- **solo se descargan los audios que cambiaron** (se comparan por su huella sha256);
- las secciones de voz (Entrada, Salida) se copian una vez y quedan como **📌 locales**: este nodo puede poner su propio texto y la sincronización no las toca. Cualquier sección se puede marcar o desmarcar como local;
- las secciones que se quitan en el origen se quitan aquí;
- si el origen no responde o el código fue revocado, **se conserva lo de la vez anterior**;
- con HTTPS y certificado propio (el de fábrica de ASL3), la primera vez se guarda la huella del certificado y después se comprueba en cada conexión.

El nodo que recibe necesita llegar al puerto 443 (o 80) del nodo que comparte.

### Panel de nodos

Cada HAMNA puede reportarse a un **hub** (el nodo central del club) cada 60 s; en la pestaña **Nodos** del hub aparece una tarjeta por nodo con:

- estación, número, tipo (ASL3/ASL/HamVOIP/IRLP) y versión (verde si está al día, naranja si hay que actualizar);
- qué está al aire o el próximo evento, si está grabando, la salud del equipo, CPU/RAM/disco/temperatura y el último respaldo recibido;
- **Editar** (administrador): la dirección del dashboard del nodo en la red local y en internet. Clic en el nombre lo abre: la local si entraste al hub desde la red local, la de internet si no. Solo se usan las direcciones guardadas en el hub, nunca las que mande el nodo.

Para reportar, en el nodo: **Ajustes → Nodo → Panel de nodos**, marcar "Reportar el estado de este nodo a un hub" y poner la dirección y el código del hub (si se dejan vacíos, se usan los del respaldo a otro nodo). Cada nodo ve en su propia pestaña solo su tarjeta y las de quienes le reportan; el panel completo está en el hub. Si un nodo deja de reportar más de 10 min (ajustable), el hub manda aviso por Telegram y otro cuando vuelve. "🗑 Quitar del panel" borra la tarjeta.

### Avisos por Telegram

En **Ajustes → Avisos** (administradores) HAMNA puede mandarte un mensaje de Telegram cuando algo falla:

- ❌ un evento no pudo iniciar o terminó con error;
- ⚠ la **revisión 30 minutos antes** de cada evento programado encontró un problema: secciones sin audio, el nodo no responde, falta la clave de Azure para las voces que se regeneran, poco disco, o la última sincronización falló;
- ❌ falló una sincronización automática desde otro nodo o un respaldo automático;
- ⚠ la salud del equipo empeoró (ver [Salud del equipo](#salud-del-equipo-y-diagnóstico)), un nodo del panel dejó de reportar, o un motor de voz falló;
- opcional: N minutos antes de cada evento programado (uno o varios avisos), resumen al iniciar y al terminar, cada sección que empieza, grabaciones, y cuando un colaborador sube su audio.

**Probar avisos** manda un mensaje simple o un ejemplo de cada tipo con datos de un evento real.

Para configurarlo: crea un bot con **@BotFather** (`/newbot`), pega su token, escríbele algo al bot (o agrégalo a un grupo) y usa **Buscar mi chat**; guarda y prueba con **Enviar prueba**. Para que los avisos lleguen con el logo de HAMNA, en @BotFather usa `/setuserpic` y mándale [`hamna/static/icon-512.png`](hamna/static/icon-512.png). Cada mensaje dice de qué estación y nodo viene; el mismo aviso no se repite en 15 minutos, y los envíos van en segundo plano (nunca detienen una transmisión).

### Bot de Telegram

Con **"El bot responde comandos"** activado (Ajustes → Avisos) (solo en un nodo por bot), el mismo bot también responde. Cada usuario lo **vincula** desde Mi perfil con un código de 6 dígitos, y el bot le ofrece lo que su rol permite:

- **Menú con botones** (📋 Menú, `/menu`): estado, próximo evento, salud, historial, nodos, transmitir un evento y grabar, con confirmación antes de actuar.
- Comandos: `/estado`, `/proximo`, `/salud`, `/historial`, `/nodos` (en el hub), `/grabar [título]`, `/ayuda`.
- Botones en los avisos: "siguiente sección" y "detalles" al iniciar; "transmitir ya" y "saltar esta vez" en el aviso del próximo evento.
- **Colaboradores**: mandan su audio o nota de voz (hasta 20 MB) y eligen la sección; reciben recordatorio días antes si no lo han subido y un mensaje cuando su sección salió al aire. Los administradores pueden cambiar así cualquier sección.
- **🤝 Colaboración** (en el menú): los eventos, primero los que salen pronto, y en cada uno sus secciones en orden, con duración y si ya se actualizaron. Al tocar una sección se puede mandar el audio nuevo, cambiar el texto de una de texto a voz (o generar la voz otra vez), escucharla o regresar a la versión anterior. El colaborador ve los eventos donde sale y edita solo sus secciones. El operador y el administrador editan cualquiera, pueden **agregar una sección nueva** al final del evento (de audio o de texto a voz), **cambiarla de lugar** (↕ Mover de lugar: subir, bajar, al inicio o al final) y **borrarla** (quitarla solo de ese evento o borrarla por completo con su audio).
- El menú ☰ de Telegram solo trae `/menu` y `/start`; todo lo demás está en los botones del menú (los comandos siguen funcionando si se escriben).
- **🔗 Conexiones** (en Nodos): los enlaces del nodo con su modo y tiempo conectado; conectar como transceptor, monitor o monitor local eligiendo de los **favoritos de AllScan** o escribiendo el número; cambiar el modo, desconectar uno o todos. En IRLP: conectar a un nodo o reflector y desconectar.
- **Respaldo por Telegram**: el respaldo automático (sin audios, hasta 49 MB) les llega en privado a los administradores vinculados.

### Usuarios y seguridad

| Rol | Puede |
|---|---|
| Administrador | Todo: Ajustes, Cron, logo, usuarios, respaldos, compartir y configurar sincronizaciones |
| Operador | Transmitir, programar, editar eventos y secciones, conectar y desconectar nodos, sincronizar a mano, grabar, ver el cron |
| Solo lectura | Ver estado, programación, eventos, secciones y conexiones; escuchar en vivo |
| Colaborador | Solo su página **Mis secciones**: subir el audio de las secciones que le asignan (desde la página o por Telegram), ver las tarjetas y detalles de los eventos donde salen, y escuchar la sección o el evento completo |

- El servidor revisa el rol en cada acción; la página además esconde lo que el rol no puede usar.
- La bitácora y el historial de transmisiones registran quién hizo cada cosa y desde qué IP (detrás de Apache se usa la IP real del visitante).
- 5 contraseñas malas para un usuario desde una IP, 20 desde una IP, o 30 para un usuario desde cualquier IP, bloquean 15 minutos. En el bot, 5 códigos de vinculación equivocados bloquean esa cuenta de Telegram 15 minutos. Un administrador puede desbloquear en Ajustes → Usuarios; reiniciar el servicio también limpia los bloqueos.
- Las sesiones duran 30 días desde el último uso (tope 90) y con https la cookie va marcada como `Secure`. Las abiertas se ven en **Mi perfil** (las propias) y **Ajustes → Usuarios** (todas) y se pueden cerrar. Cambiar la contraseña o desactivar a un usuario lo saca al instante. De cada sesión solo se guarda la huella de su código.
- No se puede borrar, desactivar ni quitar el rol al último administrador activo.
- La página no se deja meter en un iframe de otro sitio, y sin sesión no acepta archivos.
- Con Apache, la página solo se abre por `https://…/hamna/` (la contraseña viaja cifrada) y el 8090 escucha solo dentro del nodo. Para entrar al 8090 desde fuera del nodo (no recomendado), instala con `--listen-all`, o usa un túnel SSH: `ssh -L 8090:127.0.0.1:8090 usuario@nodo`.

### Cron

La pestaña **Cron** muestra y edita las tareas programadas del nodo: el crontab de asterisk (y de otros usuarios que tengan uno), y en IRLP `custom/custom.crons` (el crontab de repeater se vuelve a armar solo cada día a las 3:00 con `irlp.crons` + `custom.crons`). El crontab de **root**, `/etc/crontab` y `/etc/cron.d` se muestran en solo lectura: el de root se edita en el nodo con `crontab -e`.

Cada cambio se valida, se rechaza si la tabla cambió mientras la editabas y guarda antes la versión anterior en `/var/backups/hamna-cron/`. Para esto el instalador crea `/etc/sudoers.d/hamna-web`, limitado a los ayudantes `/opt/hamna-web/bin/hamna-cron` y `hamna-irlp`. Un administrador de la página puede programar comandos como esos usuarios (p. ej. asterisk): dale ese rol solo a quien corresponda y usa contraseñas fuertes. Los operadores ven el cron pero no lo editan. Para no dar ese permiso, instala con `--no-cron`.

### Respaldos

**Ajustes → Respaldo** (administradores), en tres pestañas:

- **Descargar y restaurar**: un `.tar.gz` con eventos, secciones, programación, usuarios, ajustes (con las claves), logo, fotos y audios de pausa; los audios de las secciones son opcionales. Se arma mientras se descarga, sin ocupar espacio en la SD. **Restaurar** valida el archivo y la base de datos, mueve lo actual a `/var/lib/hamna/antes-de-restaurar-<fecha>/` (guarda los 2 últimos), puede **conservar los datos propios del nodo** (número, tipo, logo, conexión con Asterisk/IRLP) y reinicia el servicio solo.
- **Automático**: cada día a la hora elegida (espera si hay algo al aire), **a otro nodo HAMNA**, **a la nube** (Google Drive u OneDrive, con rclone; se pega el token de `rclone authorize`) y/o **por Telegram**. Los audios de las secciones solo se mandan cuando cambiaron desde el último respaldo con audios. **Respaldar ahora**, estado del último respaldo y aviso si falla.
- **Recibir de otros nodos**: el nodo que guarda crea un código de acceso para cada nodo que le respalda. Conserva varios respaldos sin audios y 2 con audios por nodo (en `/var/lib/hamna/respaldos/<nodo>/`) y los ofrece para descargar. La conexión comprueba la huella del certificado.

### Salud del equipo y diagnóstico

- **Salud del equipo** (cada minuto, sin root): errores de la tarjeta SD (dmesg y ext4), disco en solo lectura, una prueba de escritura cada 10 min, **bajo voltaje**, temperatura, disco y memoria. Si algo empeora llega un aviso por Telegram con qué hacer, un recordatorio cada 12 h y otro cuando se normaliza; la barra lateral muestra la insignia **Revisar**. Un apagado sin cerrar (corte de luz) queda solo como nota.
- **Revisar este nodo** (Ajustes → Sistema): nodo, audio en vivo (`outstreamcmd`, con los comandos para copiar), audios de pausa y de secciones legibles, voces (si la clave de Azure da 401 busca la región correcta y ofrece cambiarla; clave, voz y cuota de ElevenLabs), Telegram, respaldo automático, salud, hora y versión, cada cosa con cómo arreglarla.

### Archivos

| Ruta | Qué hay |
|---|---|
| `/opt/hamna-web/` | El programa, `install.sh`, `update.sh` y `uninstall.sh` |
| `/var/lib/hamna/hamna.db` | Base de datos: secciones, eventos, programación, usuarios, sincronizaciones |
| `/var/lib/hamna/settings.json` | Ajustes (incluida la clave de Azure) |
| `/var/lib/hamna/audios/` | Audios de las secciones (`anteriores/`: versiones anteriores); `sonidos/` los de la pausa; `cache/` las versiones para el aire |
| `/var/lib/hamna/grabaciones/` | Grabaciones |
| `/var/lib/hamna/respaldos/` | Respaldos recibidos de otros nodos |
| `/var/lib/hamna/fotos/` | Fotos de perfil |
| `/var/lib/hamna/hamna.log` | Bitácora |
| `/var/backups/hamna/` | Respaldos que hace el instalador antes de cada actualización (los últimos 5) |
| `/var/backups/hamna-cron/` | Versiones anteriores de las tablas del cron |
| `/etc/apache2/conf-available/hamna-web.conf` | Publicación en `/hamna/` (HamVOIP: `/etc/httpd/conf/extra/hamna-web.conf`) |
| `/etc/sudoers.d/hamna-web` | Permisos limitados para cron e IRLP |

### Problemas comunes

| Síntoma | Qué revisar |
|---|---|
| El `playback` suena en el hub pero no en los nodos enlazados | `duplex = 0` sin `linktolink = yes` en `rpt.conf` (ver [Cómo sale al aire](#cómo-sale-al-aire)) |
| "PREPARANDO" por varios minutos | Se están nivelando audios largos que no se habían preparado; desde la 1.6 se preparan al agregarlos, así que pasa solo la primera vez |
| Olvidaste la contraseña | `sudo hamna-web-passwd TU_USUARIO` en la terminal del nodo |
| "Demasiados intentos" al entrar | Espera 15 min, pide a un administrador que desbloquee, o `sudo systemctl restart hamna-web` |
| `hamna-web-passwd admin` decía "al menos 6 caracteres" | Versiones anteriores a la 1.6.8 tomaban esa palabra como contraseña; actualiza |
| El actualizador dice "is on air" o "preparing audio" | Espera a que termine; no se instala a media transmisión (o usa `--force`) |
| Apache muestra `AH00558: Could not reliably determine the server's fully qualified domain name` | Es solo un aviso; se quita con `ServerName mi-nodo` en la configuración de Apache |
| La sincronización dice que el certificado cambió | El nodo de origen renovó su certificado: en la configuración de la sincronización vuelve a "Probar conexión" y guarda |

### Diferencias con HAMNA Desktop

- Mismo esquema de base de datos y mismas variables de voz, más `{fecha_larga}`, `{saludo}`, `{despedida}`, `{numero}`, `{emision}`, `{emision_anio}`, `{anio}` y `{nodo}`.
- Voces: Azure (igual que Desktop), Google Cloud, ElevenLabs, Piper (`asl3-tts`, voz neuronal local en ASL3) y eSpeak NG. No hay SAPI5. En HamVOIP no hay voces locales.
- El intervalo entre secciones es un ajuste aparte (en Desktop era la misma duración que la pausa).
- No se pueden programar dos eventos a la vez en el mismo minuto: el segundo detiene al primero.

### Desarrollo

Sin dependencias: el servidor web está hecho con la librería estándar (`hamna/web.py`) y el código es compatible con Python 3.5 a 3.14. La página es HTML, CSS y JavaScript sin bibliotecas externas; los textos están en español en el código y `hamna/static/i18n.js` los traduce al inglés en el navegador (si agregas textos, agrégalos también a su diccionario).

```bash
set HAMNA_DATA=%TEMP%\hamna
python -m hamna --init backend=simulado
python -m hamna --set-password prueba123 --user admin
python -m hamna --port 8090
```

El modo `simulado` no transmite nada, solo respeta los tiempos.

**Publicar una versión** (lo que ven los nodos como actualización):

```bash
# 1. subir VERSION en hamna/__init__.py y los ?v= de hamna/static/index.html
git commit -am "Release v1.8.0"
git tag v1.8.0
git push origin main v1.8.0
```

Lo que se sube a `main` sin etiqueta no se ofrece a los nodos. Para convertir audio necesita `ffmpeg` en el PATH; para las zonas horarias en Windows, el paquete `tzdata` de Python.

| Módulo | Qué hace |
|---|---|
| `app.py` | Rutas de la API |
| `web.py` | Servidor HTTP, sesiones y roles |
| `engine.py` | Programador y transmisión |
| `backends.py` | ASL / IRLP / simulado |
| `irlpnet.py` | IRLP: el audio también al reflector o nodo conectado (imike + relevo) |
| `audio.py` | Conversión y nivelación |
| `tts.py` | Voces |
| `auth.py` | Usuarios, sesiones y bloqueos |
| `tz.py` | Zonas horarias |
| `sessions.py` | Pestaña Conexiones (`rpt xnode`; IRLP con status.irlp.net) |
| `links.py` | Conexiones automáticas |
| `share.py` / `sync.py` | Compartir y sincronizar eventos entre nodos |
| `numeracion.py` | Numeración automática de emisiones |
| `export.py` | Exportar secciones a un archivo |
| `sysmon.py` / `health.py` | Monitor y salud del equipo |
| `diagnose.py` | Revisar este nodo |
| `updates.py` | Aviso de actualizaciones |
| `notify.py` / `bot.py` | Avisos y bot de Telegram |
| `live.py` | Audio en vivo (recibe de `bin/hamna-live` y `bin/hamna-live-irlp`) |
| `grabar.py` | Grabaciones |
| `hub.py` | Panel de nodos (latidos) |
| `backup.py` / `autobackup.py` | Respaldo, restauración y respaldo automático |
| `cron.py` | Pestaña Cron |
