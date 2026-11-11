<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/logo-completo-oscuro.svg">
    <img src="docs/logo/logo-completo.svg" width="420" alt="HAMNA — HAM Net Automation">
  </picture>
</p>

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

**Contenido:** [Capturas](#capturas) · [Qué hace](#qué-hace) · [Requisitos](#requisitos) · [Instalación](#instalación) · [Actualizar](#actualizar) · [Primeros pasos](#primeros-pasos) · [La página](#la-página) · [Programación y zonas horarias](#programación-y-zonas-horarias) · [Cómo sale al aire](#cómo-sale-al-aire) · [Pausas automáticas](#pausas-automáticas) · [Conexiones](#conexiones) · [Escuchar en vivo](#escuchar-en-vivo) · [Sincronizar eventos entre nodos](#sincronizar-eventos-entre-nodos) · [Avisos por Telegram](#avisos-por-telegram) · [Usuarios y seguridad](#usuarios-y-seguridad) · [Cron](#cron) · [Archivos y respaldos](#archivos-y-respaldos) · [Problemas comunes](#problemas-comunes) · [Desarrollo](#desarrollo)

### Capturas

Tomadas del hub **299081** del Radio Club Guadiana.

<p align="center"><img src="docs/img/pc-programacion.png?v=1.12.2" width="900" alt="Programación: próximos eventos con la hora del nodo y la de origen"></p>

| Eventos y sus secciones | Biblioteca de secciones |
|---|---|
| <img src="docs/img/pc-eventos.png?v=1.12.2" alt="Detalle de un evento con sus secciones en orden"> | <img src="docs/img/pc-secciones.png?v=1.12.2" alt="Lista de secciones de audio y voz sintética"> |

<p align="center"><img src="docs/img/pc-conexiones.png?v=1.12.2" width="900" alt="Conexiones: nodos enlazados en este momento"></p>

**En el celular** — programación, menú y conexiones:

<p align="center"><img src="docs/img/celular.png?v=1.12.2" width="900" alt="HAMNA Web en el celular"></p>

### Qué hace

- **Eventos armados con secciones**: audios (MP3, WAV, OGG, FLAC…), textos que se leen con voz sintética (Azure, Piper o eSpeak) y sonidos, en el orden que quieras.
- **Programación** única, diaria, semanal o de lunes a viernes, **en la zona horaria del programa** (se ajusta sola al horario de verano de esa zona).
- **Transmisión automática** por AllStarLink o IRLP, con nivel de audio parejo (-18 LUFS) y pausas automáticas para los repetidores.
- **Conexiones automáticas** antes y después de cada evento, y una pestaña **Conexiones** para ver y controlar los enlaces del nodo en vivo.
- **Escuchar el nodo en vivo** desde la página (computadora o celular), sin complementos.
- **Sincronización entre nodos**: otro HAMNA (por ejemplo, el que retransmite en otra ciudad) se trae solo las secciones y audios de un evento, cada semana.
- **Usuarios con roles**, idioma por usuario (inglés o español), tema claro u oscuro y logo de la estación.
- **Monitor del equipo** (CPU, RAM, disco, temperatura, red) y **aviso de actualizaciones** desde GitHub.
- Ligero: sin paquetes de Python, pensado para una Raspberry Pi.

### Requisitos

| | ASL3 (Debian 12/13) | HamVOIP | IRLP |
|---|---|---|---|
| Python | 3.5 o más nuevo (viene con el sistema) | 3.5 (viene con el sistema) | 3.5 o más nuevo |
| Audio | `ffmpeg` (lo instala el instalador) | `sox` y `mpg123` (ya vienen; no se toca pacman) | `ffmpeg` y `alsa-utils` |
| Voz | Azure, Piper (`asl3-tts`) o eSpeak | Azure | Azure o eSpeak |
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
3. **Ajustes → Voz**: elige el motor de voz (Azure necesita clave y región).
4. **Ajustes → Usuarios**: crea un usuario para cada colega con su rol.
5. **Secciones**: sube audios o escribe textos.
6. **Eventos**: crea un evento, agrégale secciones y ordénalas.
7. **Programación**: programa el evento con su hora y zona horaria.

### La página

- **Barra lateral** con las secciones, el monitor del equipo, tu usuario y el reloj del nodo. Se esconde con la flecha ‹ (y vuelve con ☰); en el celular es un menú que sale de la izquierda.
- **Idioma por usuario**: inglés (predeterminado) o español, en **Ajustes → Mi cuenta**; la pantalla de entrada tiene su propio selector. Lo que sale al aire (voces, fechas) sigue en español.
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
- Variables para los textos de voz: `{fecha}`, `{fecha_larga}`, `{hora}`, `{dia}`, `{evento}`, `{numero}`, `{num_secciones}`, `{duracion_total}`, `{dur_contabilizable}`, `{titulo}`, `{descripcion}`, `{pausa_cada}`, `{pausa_duracion}`, `{pausa_alerta}`, `{nodo}`. Las secciones de voz con "Regenerar antes de transmitir" se vuelven a generar justo antes de salir al aire.

> En HamVOIP la base de zonas horarias del sistema es de 2016: las zonas de EE. UU. funcionan bien, pero las del centro de México todavía creen que hay horario de verano. Ahí usa "Hora del nodo" para los programas de México.

### Cómo sale al aire

| Nodo | Cómo transmite | Usuario del servicio |
|---|---|---|
| ASL3 / HamVOIP | `asterisk -rx "rpt localplay\|playback <nodo> <archivo>"`; app_rpt activa y suelta el PTT. Detener/Pausa/Siguiente cortan con `rpt cmd <nodo> cop 24 0`. | `asterisk` en ASL3, `root` en HamVOIP |
| IRLP | `$BIN/key` → `aplay` → `$BIN/unkey`, con el entorno de `/home/irlp/custom/environment`. Sale por el radio local, no por el reflector. | `repeater` |

**Modo de reproducción en ASL** (Ajustes → Nodo):

- `localplay`: solo el transmisor de este nodo.
- `playback`: este nodo **y todos los nodos enlazados**.

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

**Pestaña Conexiones**: los nodos enlazados en este momento, con indicativo y ciudad (del directorio de AllStar), modo, dirección, tiempo conectado, IP y quién está hablando; un resumen con los nodos alcanzables en toda la red; y botones para **conectar** (transceptor o solo monitor) y **desconectar**. Si el Asterisk tiene varios nodos, se elige cuál ver. Se actualiza cada 4 s solo con la pestaña abierta.

**Conexiones automáticas de un evento** (Eventos → detalle → abajo): conectar o desconectar enlaces antes de empezar y al terminar.

| Sistema | Conectar | Desconectar |
|---|---|---|
| ASL / HamVOIP | `rpt cmd <nodo> ilink 3` (transceptor), `2` (monitor) o `13` (permanente) | `ilink 1 <nodo>` o `ilink 6` (todos) |
| IRLP | `$SCRIPT/decode <nodo o reflector>` | `$SCRIPT/end` |

"N min antes" se adelanta solo cuando el evento está programado; si lo lanzas a mano, se hace al iniciar. Las de "al terminar" corren también si detienes el evento.

### Escuchar en vivo

Con la bocina **🔊** de la tarjeta de abajo (junto al contador) se escucha el nodo desde la página, en la computadora o el celular: lo que transmite HAMNA, los reportes de los colegas y los nodos enlazados. Llega con 1 a 2 segundos de retraso, en calidad de radio (8 kHz) y gasta unos 64 kbps por persona. Pueden escuchar hasta 8 personas a la vez; cualquier usuario, incluso de solo lectura.

Para activarlo, agrega esta línea en la sección de tu nodo en `/etc/asterisk/rpt.conf` (ASL3 y HamVOIP) y reinicia Asterisk **cuando no haya emisión** (`sudo systemctl restart asterisk`; en ASL3 nunca uses `rpt restart`):

```
outstreamcmd = /opt/hamna-web/bin/hamna-live
```

app_rpt le pasa el audio del nodo a ese pequeño programa, que lo reenvía a HAMNA Web dentro del mismo equipo (127.0.0.1:8091). Si HAMNA Web está apagado, el audio simplemente se descarta: nunca detiene a Asterisk. HAMNA lo convierte a µ-law solo mientras alguien escucha (≈1 % de CPU en una Raspberry Pi 4) y el navegador lo reproduce sin complementos. En **Ajustes → Sistema** se ve si llega audio y quién está escuchando.

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

### Avisos por Telegram

En **Ajustes → Avisos** (administradores) HAMNA puede mandarte un mensaje de Telegram cuando algo falla:

- ❌ un evento no pudo iniciar o terminó con error;
- ⚠ la **revisión 30 minutos antes** de cada evento programado encontró un problema: secciones sin audio, el nodo no responde, falta la clave de Azure para las voces que se regeneran, poco disco, o la última sincronización falló;
- ❌ falló una sincronización automática desde otro nodo;
- opcional: cada transmisión que empieza y termina.

Para configurarlo: crea un bot con **@BotFather** (`/newbot`), pega su token, escríbele algo al bot (o agrégalo a un grupo) y usa **Buscar mi chat**; guarda y prueba con **Enviar prueba**. Para que los avisos lleguen con el logo de HAMNA, en @BotFather usa `/setuserpic` y mándale [`hamna/static/icon-512.png`](hamna/static/icon-512.png). Cada mensaje dice de qué estación y nodo viene; el mismo aviso no se repite en 15 minutos, y los envíos van en segundo plano (nunca detienen una transmisión).

### Usuarios y seguridad

| Rol | Puede |
|---|---|
| Administrador | Todo: Ajustes, Cron, logo, usuarios, compartir y configurar sincronizaciones |
| Operador | Transmitir, programar, editar eventos y secciones, conectar y desconectar nodos, sincronizar a mano, ver el cron |
| Solo lectura | Ver estado, programación, eventos, secciones y conexiones |

- El servidor revisa el rol en cada acción; la página además esconde lo que el rol no puede usar.
- La bitácora y el historial de transmisiones registran quién hizo cada cosa y desde qué IP (detrás de Apache se usa la IP real del visitante).
- 5 contraseñas malas para un usuario desde una IP (o 20 desde una IP) la bloquean 15 minutos. Un administrador puede desbloquear en Ajustes → Usuarios; reiniciar el servicio también limpia los bloqueos.
- Las sesiones abiertas se ven en **Ajustes → Mi cuenta** (las propias) y **Ajustes → Usuarios** (todas) y se pueden cerrar. Cambiar la contraseña o desactivar a un usuario lo saca al instante. De cada sesión solo se guarda la huella de su código.
- No se puede borrar, desactivar ni quitar el rol al último administrador activo.
- Con Apache, la página solo se abre por `https://…/hamna/` (la contraseña viaja cifrada) y el 8090 escucha solo dentro del nodo. Para entrar al 8090 desde fuera del nodo (no recomendado), instala con `--listen-all`, o usa un túnel SSH: `ssh -L 8090:127.0.0.1:8090 usuario@nodo`.

### Cron

La pestaña **Cron** muestra y edita las tareas programadas del nodo: el crontab de root y de asterisk, y en IRLP `custom/custom.crons` (el crontab de repeater se vuelve a armar solo cada día a las 3:00 con `irlp.crons` + `custom.crons`). `/etc/crontab` y `/etc/cron.d` se muestran en solo lectura.

Cada cambio se valida, se rechaza si la tabla cambió mientras la editabas y guarda antes la versión anterior en `/var/backups/hamna-cron/`. Para esto el instalador crea `/etc/sudoers.d/hamna-web`, limitado a los ayudantes `/opt/hamna-web/bin/hamna-cron` y `hamna-irlp`. **Un administrador de la página puede programar comandos como root**: dale ese rol solo a quien corresponda y usa contraseñas fuertes. Los operadores ven el cron pero no lo editan. Para no dar ese permiso, instala con `--no-cron`.

### Archivos y respaldos

| Ruta | Qué hay |
|---|---|
| `/opt/hamna-web/` | El programa, `install.sh`, `update.sh` y `uninstall.sh` |
| `/var/lib/hamna/hamna.db` | Base de datos: secciones, eventos, programación, usuarios, sincronizaciones |
| `/var/lib/hamna/settings.json` | Ajustes (incluida la clave de Azure) |
| `/var/lib/hamna/audios/` | Audios de las secciones; `sonidos/` los de la pausa; `cache/` las versiones para el aire |
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

- Mismo esquema de base de datos y mismas variables de voz, más `{fecha_larga}`, `{numero}` y `{nodo}`.
- Voces: Azure (igual que Desktop), Piper (`asl3-tts`, voz neuronal local en ASL3) y eSpeak NG. No hay SAPI5. En HamVOIP solo Azure.
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
| `audio.py` | Conversión y nivelación |
| `tts.py` | Voces |
| `auth.py` | Usuarios, sesiones y bloqueos |
| `tz.py` | Zonas horarias |
| `sessions.py` | Pestaña Conexiones (`rpt xnode`) |
| `links.py` | Conexiones automáticas |
| `share.py` / `sync.py` | Compartir y sincronizar eventos entre nodos |
| `sysmon.py` | Monitor del equipo |
| `updates.py` | Aviso de actualizaciones |
| `notify.py` | Avisos por Telegram |
| `live.py` | Audio en vivo (recibe de `bin/hamna-live`) |
