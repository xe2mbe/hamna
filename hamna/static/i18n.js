/* HAMNA Web — idiomas.
   Los textos de la página están en español en el código; si el idioma es
   inglés, este archivo los traduce en pantalla (al cargar y cada vez que la
   página dibuja algo). Lo que no esté en el diccionario se queda en español.
   No toca: valores de campos, nombres de eventos/secciones que no coincidan,
   comandos (code, textarea), la bitácora ni nada marcado translate="no".
   Las transmisiones (TTS, fechas al aire) siguen en español. */
"use strict";
(function () {
  const KEY = "hamna.lang";
  let lang = "en";
  try { lang = localStorage.getItem(KEY) || "en"; } catch {}
  if (lang !== "es" && lang !== "en") lang = "en";
  window.HAMNA_LANG = lang;
  document.documentElement.lang = lang;
  window.hamnaSetLang = (l, reload = true) => {
    let saved = false;
    try { localStorage.setItem(KEY, l); saved = localStorage.getItem(KEY) === l; } catch {}
    // Sin almacenamiento (modo privado estricto) no se recarga: evitaría un bucle
    if (reload && saved && l !== lang) location.reload();
  };
  if (lang === "es") return;

  const DIA = { domingo: "Sunday", lunes: "Monday", martes: "Tuesday", "miércoles": "Wednesday",
    jueves: "Thursday", viernes: "Friday", "sábado": "Saturday" };

  const D = {
    // Entrada y estructura
    "Automatización de redes para tu nodo": "Net automation for your node",
    "Usuario": "Username", "Contraseña": "Password", "Entrar": "Sign in", "Entrando…": "Signing in…",
    "Mostrar menú": "Show menu", "Esconder menú": "Hide menu",
    "Programación": "Schedule", "Eventos": "Events", "Secciones": "Sections", "Conexiones": "Connections",
    "Cron": "Cron", "Ajustes": "Settings", "Cerrar sesión": "Sign out",
    "Tema claro / oscuro": "Light / dark theme", "Cambiar tema": "Change theme",
    "Eventos disponibles para transmitir": "Events available to broadcast",
    "+ Programar evento": "+ Schedule event",
    "Eventos disponibles": "Available events",
    "+ Nuevo evento": "+ New event",
    "Elige un evento para ver y ordenar sus secciones.": "Pick an event to see and order its sections.",
    "Secciones disponibles": "Available sections",
    "Buscar…": "Search…", "Todas": "All", "TTS": "TTS", "Audio": "Audio", "Sonido": "Sound",
    "+ Nueva sección": "+ New section",
    "Nodos conectados en este momento": "Nodes connected right now", "Nodo local": "Local node",
    "↻ Actualizar": "↻ Refresh", "↻ Recargar": "↻ Reload", "Enlaces directos": "Direct links", "Nodo": "Node",
    "Transceptor": "Transceive", "Solo monitor": "Monitor only", "Conectar": "Connect", "Cargando…": "Loading…",
    "Red completa": "Full network", "Nodos alcanzables a través de los enlaces": "Nodes reachable through the links",
    "Tareas de cron": "Cron jobs", "Lo que el sistema del nodo corre a horas fijas": "What the node's system runs at set times",
    "Las tareas programadas del sistema del nodo (boletines, hora, conexiones). Cada cambio guarda antes un respaldo en":
      "The node's scheduled system jobs (bulletins, time, connections). Every change first saves a backup in",
    ". Cuidado: lo que pongas aquí corre con los permisos de ese usuario.": ". Careful: whatever you put here runs with that user's permissions.",
    "Nodo, voz, pausas y seguridad": "Node, voice, pauses and security",
    "Voz (TTS)": "Voice (TTS)", "Tiempos y pausas": "Timing and pauses", "Nivel de audio": "Audio level",
    "Usuarios": "Users", "Mi cuenta": "My account", "Sistema": "System",
    // Ajustes > Nodo
    "Tipo de nodo": "Node type", "Detectar automáticamente": "Detect automatically",
    "Simulado (sin radio, para pruebas)": "Simulated (no radio, for testing)", "Número de nodo": "Node number",
    "Nombre de la estación (opcional)": "Station name (optional)", "Sin logo": "No logo", "Logo de la estación": "Station logo",
    "PNG, JPG, WEBP o GIF. Se reduce en tu navegador antes de subirlo. Aparece arriba, en la pantalla de entrada y en la pestaña del navegador.":
      "PNG, JPG, WEBP or GIF. Your browser shrinks it before uploading. It shows at the top, on the sign-in screen and on the browser tab.",
    "Subir logo": "Upload logo", "Quitar": "Remove", "Comando para cortar el audio (opcional)": "Command to cut the audio (optional)",
    "Lo usan Detener, Pausa y Siguiente para soltar el PTT a media reproducción. Vacío = el tramo en curso termina solo.":
      "Used by Stop, Pause and Next to release PTT mid-playback. Empty = the current chunk finishes on its own.",
    "Modo de reproducción en ASL": "ASL playback mode",
    "localplay — solo el transmisor de este nodo": "localplay — this node's transmitter only",
    "playback — este nodo y todos los enlazados": "playback — this node and every linked node",
    "Modo de reproducción en IRLP": "IRLP playback mode",
    "Radio + red — este nodo y el reflector o nodo conectado": "Radio + network — this node and the connected reflector or node",
    "Solo el radio — el transmisor de este nodo": "Radio only — this node's transmitter",
    "Archivo de entorno IRLP": "IRLP environment file", "Comando PTT ON": "PTT ON command", "Comando PTT OFF": "PTT OFF command",
    "Reproductor": "Player", "Probar conexión": "Test connection", "Probando…": "Testing…",
    "Texto para la prueba al aire": "Text for the on-air test", "📡 Transmitir prueba": "📡 Transmit test",
    // Voz
    "Motor": "Engine", "Azure — voces neuronales (requiere internet y clave)": "Azure — neural voices (needs internet and a key)",
    "Piper — voz neuronal local (asl3-tts)": "Piper — local neural voice (asl3-tts)", "eSpeak NG — local, voz sintética": "eSpeak NG — local, synthetic voice",
    "Clave de Azure": "Azure key", "(sin cambios)": "(unchanged)", "Región": "Region", "Voz": "Voice", "Cargar": "Load",
    "Estilo": "Style", "Velocidad (%)": "Speed (%)", "Tono (Hz)": "Pitch (Hz)", "Velocidad (ppm)": "Speed (wpm)", "Tono (0-99)": "Pitch (0-99)",
    "Probar voz": "Try the voice", "▶ Escuchar": "▶ Listen", "Pega aquí tu clave": "Paste your key here",
    "•••••• (guardada; escribe para cambiarla)": "•••••• (saved; type to change it)",
    // Pausas y audio
    "Retardo PTT (s)": "PTT delay (s)", "Silencio al inicio de cada audio, para que el transmisor y los repetidores enganchen.":
      "Silence at the start of each audio so the transmitter and repeaters can key up.",
    "Intervalo entre secciones (s)": "Gap between sections (s)", "Tiempo con el PTT suelto entre una sección y la siguiente.":
      "Time with PTT released between one section and the next.",
    "Pausa automática (respetar el temporizador de los repetidores)": "Automatic pause (respect repeater time-out timers)",
    "Transmitir antes de pausar (s)": "Transmit before pausing (s)", "Duración de la pausa (s)": "Pause length (s)",
    "Alerta antes de pausar (s)": "Alert before pausing (s)", "Retroceder al reanudar": "Rewind when resuming",
    "Segundos de retroceso": "Rewind seconds", "Audios de la pausa": "Pause audio",
    "🔔 Alerta": "🔔 Alert", "Suena encima del audio, segundos antes de la pausa": "Plays over the audio, seconds before the pause",
    "⏸ Anuncio de pausa": "⏸ Pause announcement", "Al cortar, antes de soltar el PTT": "When cutting, before releasing PTT",
    "▶ Continuamos": "▶ We're back", "Al regresar de la pausa": "When returning from the pause", "Sin audio": "No audio", "Subir": "Upload",
    "Normalizar todos los audios al mismo nivel": "Normalize all audio to the same level", "Nivel objetivo (LUFS)": "Target level (LUFS)",
    "-18 es un buen punto para FM de banda angosta.": "-18 is a good point for narrowband FM.",
    "Volumen de los audios de pausa (%)": "Pause audio volume (%)",
    "Todo se convierte a 8 kHz mono, el formato que usan Asterisk e IRLP. El nivel se mide en mono, como sale al aire, con limitador de picos a -2 dB.":
      "Everything is converted to 8 kHz mono, the format Asterisk and IRLP use. Level is measured in mono, as it goes on air, with a -2 dB peak limiter.",
    "Espacio en disco": "Disk space", "Guardar los audios originales": "Keep the original audio files",
    "Si lo desactivas, al subir un audio se guarda solo la versión ya lista para el aire y se borra el original: ocupa casi la mitad, porque ya no se guardan dos copias de cada audio. A cambio, si después cambias el nivel objetivo, esos audios no se vuelven a nivelar, y lo que descargues desde la página será la versión de 8 kHz.":
      "If you turn this off, uploads keep only the on-air version and delete the original: it takes about half the space, because two copies are no longer kept. The trade-off: if you later change the target level, those files are not re-leveled, and downloads from the page will be the 8 kHz version.",
    "Convertir los ya subidos y borrar originales": "Convert existing uploads and delete originals",
    "Se van a convertir todas las secciones al formato del aire y se borrarán los audios originales. Esto no se puede deshacer.":
      "All sections will be converted to the on-air format and the original audio deleted. This cannot be undone.",
    "Sí, convertir y borrar": "Yes, convert and delete", "Convirtiendo…": "Converting…", "No había originales que convertir": "There were no originals to convert",
    "Guardar ajustes": "Save settings", "Ajustes guardados": "Settings saved", "Audio guardado": "Audio saved",
    // Cuenta y usuarios
    "Cambiar contraseña": "Change password", "Contraseña actual": "Current password", "Contraseña nueva": "New password",
    "Al menos 8 caracteres. Al cambiarla se cierran tus otras sesiones.": "At least 8 characters. Changing it signs out your other sessions.",
    "Mis sesiones abiertas": "My open sessions", "Cerrar las demás sesiones": "Sign out other sessions", "Cerrar esta sesión": "Sign out this session",
    "Administrador": "Administrator", "Operador": "Operator", "Solo lectura": "Read only",
    ": todo.": ": everything.", ": transmitir, programar, editar eventos y secciones, conectar nodos y ver el cron.":
      ": broadcast, schedule, edit events and sections, connect nodes and view cron.",
    ": ver estado, programación, eventos y conexiones.": ": view status, schedule, events and connections.",
    "+ Nuevo usuario": "+ New user", "Sesiones abiertas": "Open sessions", "Idioma": "Language",
    "Nuevo usuario": "New user", "Editar usuario": "Edit user", "Nombre": "Name", "Rol": "Role",
    "Para entrar. Letras, números, punto o guion.": "Used to sign in. Letters, numbers, dot or dash.",
    "Déjala vacía para no cambiarla": "Leave empty to keep it", "Al menos 8 caracteres.": "At least 8 characters.",
    "Si la cambias, se cierran sus sesiones.": "Changing it signs out their sessions.",
    "Activo (si lo desactivas, sale de inmediato y no puede entrar)": "Active (if you deactivate it, they are signed out at once and cannot sign in)",
    "Crear usuario": "Create user", "Usuario creado": "User created", "Usuario guardado": "User saved", "Usuario borrado": "User deleted",
    "Tú": "You", "Desactivado": "Deactivated", "Esta sesión": "This session", "Cerrar": "Close", "Sesión cerrada": "Session closed",
    "No hay sesiones abiertas.": "No open sessions.", "nunca ha entrado": "never signed in", "IP desconocida": "unknown IP",
    "Navegador": "Browser", "Programa": "Program", "Desbloquear": "Unlock", "Desbloqueado": "Unlocked",
    "¿Cerrar todas tus sesiones en otros equipos?": "Sign out all your sessions on other devices?",
    "Cerrar las demás": "Sign out the others", "Listo: solo queda esta sesión": "Done: only this session is left",
    "Contraseña cambiada; tus otras sesiones se cerraron": "Password changed; your other sessions were signed out",
    // Barra al aire
    "FUERA DEL AIRE": "OFF AIR", "AL AIRE": "ON AIR", "INTERVALO": "GAP", "PAUSA": "PAUSE", "EN PAUSA": "PAUSED", "PREPARANDO": "PREPARING",
    "Inicio de la sección / sección anterior": "Start of section / previous section",
    "Desde el inicio de la sección": "From the start of the section", "Regresando a la sección anterior": "Going back to the previous section",
    "Repitiendo la sección": "Repeating the section",
    "Nueva York": "New York", "Los Ángeles": "Los Angeles", "Belice": "Belize", "Canarias": "Canary Islands",
    "En vivo": "Live", "Escuchar en vivo": "Listen live", "Escuchar el nodo en vivo": "Listen to the node live", "🔊 Audio en vivo": "🔊 Live audio",
    "Para escuchar el nodo desde esta página, agrega esta línea en la sección de tu nodo en": "To listen to the node from this page, add this line to your node's section in",
    "y reinicia Asterisk cuando no haya emisión:": "and restart Asterisk when nothing is on air:",
    "Se cortó el audio en vivo": "The live audio stopped", "No se pudo conectar": "Could not connect",
    "El audio en vivo no está activo en este nodo": "Live audio is not active on this node",
    "Pausa": "Pause", "Reanudar": "Resume", "Saltar espera": "Skip wait", "Siguiente sección": "Next section", "Detener": "Stop", "Bitácora": "Log",
    "¿Detener la transmisión?": "Stop the broadcast?", "Iniciando transmisión": "Starting broadcast",
    "📡 Transmitir": "📡 Transmit", "📡 Transmitir ahora": "📡 Transmit now", "Transmitiendo…": "Transmitting…", "Prueba al aire": "On-air test",
    "Se va a activar el transmisor del nodo con un mensaje de prueba. ¿Continuar?": "The node's transmitter will key up with a test message. Continue?",
    "Prueba de transmisión": "Test broadcast", "Generando…": "Generating…",
    // Comunes
    "Confirmar": "Confirm", "Sí, continuar": "Yes, continue", "Cancelar": "Cancel", "Guardar": "Save", "Guardado": "Saved",
    "Borrar": "Delete", "Editar": "Edit", "Agregar": "Add", "Agregadas": "Added", "Sí": "Yes", "No": "No", "Error": "Error",
    "Procesando…": "Processing…", "Subiendo…": "Uploading…", "Conectando…": "Connecting…", "Hecho": "Done",
    "Inicia sesión": "Please sign in", "Se perdió la conexión con el nodo": "Lost connection to the node",
    "Activa": "Active", "Desactivada": "Inactive", "Desactivar": "Deactivate", "Activar": "Activate",
    "Hoy": "Today", "HOY": "TODAY", "Mañana": "Tomorrow", "Total": "Total",
    // Programación
    "Próximo evento": "Next event", "No hay nada programado.": "Nothing is scheduled.",
    "Crea primero un evento con sus secciones y luego prográmalo aquí.": "First create an event with its sections, then schedule it here.",
    "Sin próximas fechas": "No upcoming dates", "Primero crea un evento en la pestaña Eventos": "First create an event in the Events tab",
    "Editar programación": "Edit schedule", "Programar evento": "Schedule event", "Evento": "Event",
    "Fecha (o primera fecha)": "Date (or first date)", "Hora del nodo": "Node time", "Se repite": "Repeats",
    "Una sola vez": "Just once", "Todos los días": "Every day", "Cada semana": "Every week", "Lunes a viernes": "Monday to Friday",
    "Línea de tiempo": "Timeline", "sin desconexión programada": "no disconnect scheduled",
    "lo que va después de # no se ejecuta": "anything after # does not run",
    // Eventos
    "Aún no hay eventos.": "No events yet.", "Este evento no tiene secciones.": "This event has no sections.",
    "+ Agregar secciones": "+ Add sections", "Agregar secciones": "Add sections", "Quitar del evento": "Remove from event",
    "Mover arriba": "Move up", "Mover abajo": "Move down", "SIMULADO": "SIMULATED", "Duración total": "Total length", "Contabilizables": "Counted",
    "Editar evento": "Edit event", "Nuevo evento": "New event", "Tipo": "Type", "Número de edición": "Edition number",
    "Opcional. Se lee con {numero}.": "Optional. Read with {numero}.", "Evento borrado": "Event deleted",
    "Todas las secciones de la biblioteca ya están en este evento. Crea más en la pestaña Secciones.":
      "Every library section is already in this event. Create more in the Sections tab.",
    "Transmisión en Vivo": "Live broadcast", "Grabación": "Recording", "Programa Diferido": "Delayed program", "Boletín": "Bulletin", "Especial": "Special",
    "Conexiones automáticas": "Automatic connections",
    "Se ejecutan al lanzar el evento (a mano o programado) y al terminar, aunque lo detengas.":
      "They run when the event starts (manually or scheduled) and when it ends, even if you stop it.",
    "«N min antes» solo se adelanta cuando el evento está programado; a mano se hace al iniciar.":
      "“N min before” only runs early when the event is scheduled; when started by hand it runs at the start.",
    "⚠ No detecté ASL ni IRLP en este equipo: las acciones no podrán ejecutarse.": "⚠ No ASL or IRLP detected on this device: actions cannot run.",
    "Este evento no conecta ni desconecta nada.": "This event does not connect or disconnect anything.",
    "+ Agregar conexión o desconexión": "+ Add connect or disconnect", "Conexión o desconexión": "Connect or disconnect",
    "Ejecutar ahora": "Run now", "Ejecutar": "Run", "Acción": "Action", "Cuándo": "When", "Minutos": "Minutes", "Modo": "Mode",
    "Antes de iniciar": "Before starting", "Al terminar": "When finished", "Al iniciar": "At start", "Justo al iniciar": "Right at the start",
    "En cuanto termina": "As soon as it ends", "Desconectar todo": "Disconnect all", "Desconectar (end)": "Disconnect (end)",
    "Desconectar todos los enlaces": "Disconnect all links", "Desconectar": "Disconnect", "Conectar a": "Connect to",
    "· del evento": "· from event", "¿Quitar esta acción del evento?": "Remove this action from the event?",
    "Escribe un número de nodo válido": "Enter a valid node number",
    "Nodo (4 dígitos) o reflector, p. ej. 9050": "Node (4 digits) or reflector, e.g. 9050",
    "Nodo AllStar, o EchoLink (3xxxxxx)": "AllStar node, or EchoLink (3xxxxxx)",
    "transceptor": "transceive", "monitor": "monitor", "permanente": "permanent",
    // Secciones
    "Duración": "Length", "Nada coincide con la búsqueda.": "Nothing matches the search.",
    "La biblioteca está vacía. Crea una sección TTS o sube un audio.": "The library is empty. Create a TTS section or upload audio.",
    "Escuchar aquí": "Listen here", "Transmitir por el nodo": "Transmit through the node",
    "Nueva sección": "New section", "Editar sección": "Edit section", "Sección creada": "Section created", "Sección guardada": "Section saved",
    "🗣 Texto a voz": "🗣 Text to speech", "🎵 Audio": "🎵 Audio", "🔔 Sonido": "🔔 Sound", "Título": "Title", "Descripción": "Description",
    "Texto": "Text", "Archivo de audio": "Audio file", "▶ Escuchar prueba": "▶ Listen to a test", "Se leerá:": "Will be read:",
    "Bienvenida": "Welcome", "Boletín dominical": "Sunday bulletin",
    // Conexiones
    "En reposo": "Idle", "Recibiendo": "Receiving", "Transmitiendo": "Transmitting", "Estado del nodo": "Node status",
    "Nadie transmitiendo": "Nobody transmitting", "Sin transmitir": "Not broadcasting",
    "Preparando audio": "Preparing audio", "Según status.irlp.net (se actualiza cada pocos minutos).": "From status.irlp.net (updated every few minutes).", "En pausa": "Paused", "Entre secciones": "Between sections", "Nodos en la red": "Nodes in the network",
    "alcanzables a través de los enlaces": "reachable through the links", "No hay nodos conectados.": "No nodes connected.",
    "Hablando": "Talking", "Monitor": "Monitor", "↘ Entrante": "↘ Incoming", "↗ Saliente": "↗ Outgoing",
    "En modo simulado no hay enlaces que mostrar.": "In simulated mode there are no links to show.", "Sin conexión": "Not connected",
    // Cron
    "+ Agregar tarea": "+ Add job", "Editar como texto": "Edit as text", "Editar tarea": "Edit job", "Nueva tarea de cron": "New cron job",
    "Tarea agregada": "Job added", "Tarea borrada": "Job deleted", "Tarea guardada": "Job saved", "Tarea activada": "Job enabled",
    "Tarea desactivada": "Job disabled", "Sin tareas.": "No jobs.", "Hora y días": "Time and days", "Avanzado": "Advanced",
    "Comando": "Command", "Hora": "Time", "Días": "Days", "Día": "Day",
    "Programación (minuto hora día-del-mes mes día-de-semana)": "Schedule (minute hour day-of-month month day-of-week)",
    "Formato no válido": "Invalid format", "Elige al menos un día": "Pick at least one day", "Escribe el comando": "Enter the command",
    "La programación no es válida": "The schedule is not valid",
    "Texto completo de la tabla. Se valida antes de guardar y se respalda la versión anterior.":
      "Full text of the table. It is checked before saving and the previous version is backed up.",
    "Al arrancar el equipo": "At system boot", "Cada hora": "Every hour", "Cada día a medianoche": "Every day at midnight",
    "Cada domingo a medianoche": "Every Sunday at midnight", "El día 1 de cada mes": "On the 1st of every month", "Cada 1 de enero": "Every January 1st",
    "Desconecta todos los enlaces": "Disconnects all links", "Anuncia la hora": "Announces the time", "Reproduce audio": "Plays audio",
    "Conectar al boletín dominical": "Connect to the Sunday bulletin",
    "Este equipo no tiene el ayudante de cron. Vuelve a ejecutar": "This device lacks the cron helper. Run again", "en el nodo.": "on the node.",
    // Sistema
    "Versión": "Version", "Salida al aire": "On-air output", "Nodo responde": "Node responds", "Enlazado con": "Linked with",
    "sin herramientas": "no tools", "Formatos que acepta": "Accepted formats", "en curso": "in progress",
    "Todavía no hay transmisiones.": "No broadcasts yet.", "Últimas transmisiones": "Latest broadcasts", "Espacio libre": "Free space",
    "Zona horaria": "Time zone", "Herramientas de audio": "Audio tools", "Motores de voz": "Voice engines",
    "manual": "manual", "programado": "scheduled", "prueba": "test", "terminado": "finished", "detenido": "stopped",
    // Errores del servidor
    "Usuario o contraseña incorrectos": "Wrong username or password", "Este usuario está desactivado": "This user is deactivated",
    "Tu usuario no tiene permiso para esto": "Your user is not allowed to do this", "Petición rechazada": "Request rejected",
    "La contraseña actual no coincide": "The current password does not match",
    "La contraseña debe tener al menos 8 caracteres": "The password must be at least 8 characters",
    "Debe quedar al menos un administrador activo": "At least one active administrator must remain",
    "No puedes borrar tu propio usuario": "You cannot delete your own user",
    "No puedes quitarte el rol de administrador ni desactivarte a ti mismo": "You cannot remove your own administrator role or deactivate yourself",
    "Usuario inválido: de 2 a 32 letras, números, punto, guion o guion bajo": "Invalid username: 2 to 32 letters, numbers, dot, dash or underscore",
    "No existe ese usuario": "That user does not exist", "Rol inválido": "Invalid role", "Número de nodo inválido": "Invalid node number",
    "Elige un archivo": "Choose a file", "Elige una imagen": "Choose an image", "La imagen pesa más de 2 MB": "The image is larger than 2 MB",
    "Formato no soportado. Usa PNG, JPG, WEBP o GIF": "Unsupported format. Use PNG, JPG, WEBP or GIF",
    "El evento necesita un nombre": "The event needs a name", "La sección necesita un nombre": "The section needs a name",
    "El evento no tiene secciones": "The event has no sections", "El evento no existe": "The event does not exist",
    "La sección no tiene audio": "The section has no audio", "Espera a que termine la transmisión": "Wait for the broadcast to finish",
    "No se puede borrar un evento que está al aire": "You cannot delete an event that is on air",
    "Escribe algún texto": "Enter some text", "Escribe el texto a sintetizar": "Enter the text to synthesize",
    "Escribe la clave y la región de Azure": "Enter the Azure key and region", "Sube un archivo de audio": "Upload an audio file",
    "No pude leer el audio; ¿está dañado el archivo?": "Could not read the audio; is the file damaged?",
    "Falta la clave o la región de Azure (Ajustes → Voz)": "Missing Azure key or region (Settings → Voice)",
    "Falta el número de nodo (Ajustes → Nodo)": "Missing node number (Settings → Node)",
    "Falta el número de nodo ASL (Ajustes → Nodo)": "Missing ASL node number (Settings → Node)",
    "El nodo ASL debe ser un número de 3 a 7 dígitos": "The ASL node must be a 3 to 7 digit number",
    "El nodo o reflector IRLP debe ser un número de 4 a 6 dígitos": "The IRLP node or reflector must be a 4 to 6 digit number",
    "Fecha inválida (AAAA-MM-DD)": "Invalid date (YYYY-MM-DD)", "Hora inválida (HH:MM)": "Invalid time (HH:MM)",
    "Los minutos van de 0 a 120": "Minutes go from 0 to 120", "Máximo 20 acciones por evento": "At most 20 actions per event",
    "No pude leer la imagen": "Could not read the image", "Datos inválidos": "Invalid data", "No encontrado": "Not found",
    "Método no permitido": "Method not allowed", "Subida incompleta": "Incomplete upload", "Petición demasiado grande": "Request too large",
    "eSpeak no está instalado en este nodo": "eSpeak is not installed on this node",
    "Este nodo no tiene ffmpeg ni sox para convertir audio": "This node has neither ffmpeg nor sox to convert audio",
    "Zona horaria del programa": "Program time zone", "Hora": "Time",
    "Hora del nodo (sin conversión)": "Node time (no conversion)",
    "Buscando actualizaciones…": "Checking for updates…", "↻ Buscar de nuevo": "↻ Check again",
    "HAMNA Web está al día": "HAMNA Web is up to date", "Para instalarla, en la terminal del nodo:": "To install it, in the node's terminal:",
    "Conserva los datos, usuarios y ajustes. Antes de correrlo, revisa que nada esté al aire.": "Keeps data, users and settings. Before running it, make sure nothing is on air.",
    "Sincronización desde otro nodo": "Sync from another node",
    "Trae las secciones y audios de un evento de otro HAMNA (por ejemplo, el Boletín Dominical del hub) y los mantiene al día solo.":
      "Brings the sections and audio of an event from another HAMNA (for example the hub's Sunday bulletin) and keeps them up to date on its own.",
    "⇅ Configurar sincronización": "⇅ Set up sync", "⇅ Sincronizar ahora": "⇅ Sync now", "Sincronizando…": "Syncing…",
    "Origen": "Source", "Última vez": "Last time", "Nunca": "Never", "Pausada": "Paused", "Solo a mano": "Manual only",
    "Secciones sincronizadas": "Synced sections", "📌 Local": "📌 Local",
    "📌 Local = propia de este nodo: la sincronización no la cambia (p. ej. una Entrada con el nombre de tu estación).":
      "📌 Local = this node's own: syncing never changes it (e.g. an intro with your station's name).",
    "Una sección local no se sobreescribe al sincronizar": "A local section is not overwritten when syncing",
    "¿Quitar la sincronización? Las secciones que ya se trajeron se quedan en el evento.": "Remove the sync? Sections already brought stay in the event.",
    "Sincronización quitada": "Sync removed", "Sincronización guardada": "Sync saved",
    "Dirección de HAMNA en el nodo de origen": "HAMNA address on the source node",
    "La misma dirección con la que se entra a su página.": "The same address used to open its page.",
    "Código de acceso": "Access code", "(guardado; pega uno nuevo para cambiarlo)": "(saved; paste a new one to change it)",
    "Lo genera un administrador del nodo de origen en su evento → «Compartir con otros nodos».": "An administrator of the source node creates it in their event → “Share with other nodes”.",
    "Cuándo sincronizar": "When to sync", "A las (hora del nodo)": "At (node time)",
    "Y además, horas antes de cada programación de este evento": "And also, hours before each schedule of this event", "0 = no.": "0 = no.",
    "Sincronización automática activa": "Automatic sync enabled",
    "Siempre puedes sincronizar a mano con «Sincronizar ahora». Si el origen no responde, se conserva lo de la vez anterior.":
      "You can always sync by hand with “Sync now”. If the source does not answer, the previous content is kept.",
    "Compartir con otros nodos": "Share with other nodes",
    "Un código de acceso deja que otro HAMNA traiga las secciones y audios de este evento (solo lectura, solo este evento).":
      "An access code lets another HAMNA bring this event's sections and audio (read only, this event only).",
    "+ Crear código de acceso": "+ Create access code", "Nuevo código de acceso": "New access code", "¿Para quién es?": "Who is it for?",
    "Crear": "Create", "Código de acceso creado": "Access code created", "Pásalo al otro nodo.": "Give it to the other node.",
    "Solo se muestra esta vez.": "It is shown only this time.", "Dirección de este HAMNA": "This HAMNA's address", "Listo": "Done",
    "En el otro nodo: evento → «Sincronización desde otro nodo» → pega los dos datos. Puedes revocarlo cuando quieras.":
      "On the other node: event → “Sync from another node” → paste both values. You can revoke it at any time.",
    "Revocar": "Revoke", "Código revocado": "Code revoked", "sin usar": "never used",
    "¿Revocar este código? El nodo que lo usa ya no podrá sincronizar.": "Revoke this code? The node using it will no longer be able to sync.",
    "Este evento no tiene sincronización configurada": "This event has no sync set up", "Ya se está sincronizando": "A sync is already running",
    "Falta el código de acceso": "The access code is missing", "Dirección inválida": "Invalid address",
    "El nodo de origen rechazó el código de acceso": "The source node rejected the access code", "Código de acceso inválido": "Invalid access code",
    "Avisos": "Alerts", "Avisos por Telegram": "Telegram alerts",
    "Te avisa en Telegram cuando algo falla, para que no te enteres hasta que alguien pregunte por qué no salió el boletín.":
      "Sends you a Telegram message when something fails, so you don't find out only when someone asks why the bulletin didn't air.",
    "Enviar avisos por Telegram": "Send alerts via Telegram", "Cómo crear el bot (2 minutos)": "How to create the bot (2 minutes)",
    "Token del bot": "Bot token", "Chat que recibe los avisos": "Chat that receives the alerts", "ID del chat o del grupo": "Chat or group ID",
    "Buscar mi chat": "Find my chat", "Buscando…": "Searching…", "Usar este": "Use this one", "Listo. Guarda los ajustes.": "Done. Save the settings.",
    "Qué avisar": "What to alert", "❌ Un evento no pudo iniciar o terminó con error": "❌ An event could not start or ended with an error",
    "⚠ Revisión 30 min antes de cada evento programado encontró un problema (secciones sin audio, nodo que no responde, falta la clave de Azure, poco disco, sincronización fallida)":
      "⚠ The check 30 min before each scheduled event found a problem (sections without audio, node not responding, missing Azure key, low disk, failed sync)",
    "❌ Falló una sincronización automática desde otro nodo": "❌ An automatic sync from another node failed",
    "▶ Cada transmisión que empieza": "▶ Every broadcast that starts", "✅ Cada transmisión que termina": "✅ Every broadcast that ends",
    "Enviar prueba": "Send a test", "Enviando…": "Sending…", "✅ Enviado: revisa Telegram": "✅ Sent: check Telegram",
    "•••••• (guardado; escribe para cambiarlo)": "•••••• (saved; type to change it)", "Falta el token del bot": "The bot token is missing",
    "Falta el token del bot o el chat": "The bot token or the chat is missing",
    // v1.14: avisos nuevos
    "Durante las transmisiones": "During broadcasts", "Probar": "Test",
    "⏰ Aviso antes de que empiece cada evento programado": "⏰ Alert before each scheduled event starts",
    "Minutos antes": "Minutes before",
    "Uno o varios, separados por coma. Ejemplo: «60, 15, 5» manda tres avisos.": "One or more, separated by commas. Example: «60, 15, 5» sends three alerts.",
    "▶ Resumen al empezar: el evento, la hora de término aproximada, sus secciones con duración y las conexiones":
      "▶ Summary at the start: the event, its approximate end time, its sections with their length and the connections",
    "🔹 Al empezar cada sección (cuál es, cuánto dura y cuál sigue)": "🔹 When each section starts (which one, how long it is and what comes next)",
    "✅ Resumen al terminar: cuánto duró y qué secciones salieron completas, interrumpidas o sin audio":
      "✅ Summary at the end: how long it took and which sections aired fully, were interrupted or had no audio",
    "Manda a Telegram un mensaje de prueba o un ejemplo de cada aviso armado con los datos de un evento. No se transmite nada. Usa el token y el chat escritos arriba, aunque no los hayas guardado.":
      "Sends Telegram a test message or a sample of each alert built from an event's data. Nothing is transmitted. It uses the token and chat typed above, even if you haven't saved them.",
    "Qué enviar": "What to send", "Mensaje de prueba": "Test message", "⏰ Aviso antes del evento": "⏰ Alert before the event",
    "▶ Resumen al empezar": "▶ Start summary", "🔹 Inicio de sección": "🔹 Section start", "✅ Resumen al terminar": "✅ End summary",
    "Evento para el ejemplo": "Event for the sample", "(no hay eventos)": "(no events)",
    "Elige un evento para el ejemplo": "Pick an event for the sample", "Ese evento no tiene secciones": "That event has no sections",
    "Minutos de aviso inválidos: usa números de 1 a 1440 separados por coma": "Invalid alert minutes: use numbers from 1 to 1440 separated by commas",
    // v1.14: exportar
    "⬇ Exportar": "⬇ Export",
    "Elige y ordena las secciones. Se unen en un solo archivo para descargar. El orden aquí no cambia el del evento.":
      "Pick and order the sections. They are joined into a single file to download. The order here doesn't change the event's.",
    "✓ Todas": "✓ All", "✗ Ninguna": "✗ None", "Silencio entre secciones (s)": "Silence between sections (s)", "Formato": "Format",
    "Este nodo no puede crear MP3 (no tiene ffmpeg ni lame).": "This node can't create MP3 files (it has neither ffmpeg nor lame).",
    "Nivelar el volumen de cada sección": "Level the volume of each section", "Nivel objetivo (LUFS)": "Target level (LUFS)",
    "-16 es común para escuchar en el teléfono; -23 es el estándar de radiodifusión.": "-16 is common for listening on a phone; -23 is the broadcast standard.",
    "Exportando…": "Exporting…", "Iniciando…": "Starting…", "Preparando…": "Preparing…",
    "Uniendo las secciones…": "Joining the sections…", "Creando el MP3…": "Creating the MP3…",
    "Selecciona al menos una sección": "Select at least one section",
    "Ninguna de las secciones elegidas tiene audio": "None of the selected sections has audio",
    "Ya hay una exportación en curso; espera a que termine": "An export is already running; wait for it to finish",
    "La exportación ya no existe": "The export no longer exists", "El archivo ya no existe; vuelve a exportar": "The file no longer exists; export again",
    "Una de las secciones ya no está en el evento; recarga la página": "One of the sections is no longer in the event; reload the page",
    "Bajada": "Download", "Subida": "Upload", "Datos del equipo del nodo · se actualizan con el estado": "Node system data · updated with the status",
    "Idioma no disponible": "Language not available", "Logo guardado": "Logo saved", "Logo quitado": "Logo removed", "¿Quitar el logo?": "Remove the logo?",
  };

  const M = (re, fn) => [re, fn];
  const P = [
    M(/^Exportar: (.+)$/, (m, a) => "Export: " + a),
    M(/^(\d+) de (\d+) · (\S+)$/, (m, a, b, d) => `${a} of ${b} · ${d}`),
    M(/^(\S+) · ⚠ sin audio, se omite$/, (m, d) => `${d} · ⚠ no audio, skipped`),
    M(/^\((\d+)\/(\d+)\) (.+?)( — nivelando…)?$/, (m, a, b, n, l) => `(${a}/${b}) ${n}${l ? " — leveling…" : ""}`),
    M(/^✅ Listo: (.+?)( · se omitieron sin audio: (.+?))? ·$/, (m, a, w, x) => `✅ Done: ${a}` + (w ? ` · skipped (no audio): ${x}` : "") + " ·"),
    M(/^Este nodo no puede crear archivos (\w+); elige WAV$/, (m, f) => `This node can't create ${f} files; choose WAV`),
    M(/^Nodo (\w+)$/, (m, n) => "Node " + n),
    M(/^nodo (\w+)$/, (m, n) => "node " + n),
    M(/^Cada (domingo|lunes|martes|miércoles|jueves|viernes|sábado)$/, (m, d) => "Every " + DIA[d]),
    M(/^Cada (domingo|lunes|martes|miércoles|jueves|viernes|sábado) a las (.+)$/, (m, d, h) => `Every ${DIA[d]} at ${h}`),
    M(/^Una vez$/, () => "Once"),
    M(/^Bot (\S+): elige el chat$/, (m, b) => `Bot ${b}: pick the chat`),
    M(/^Bot (\S+): todavía no hay mensajes\. Escríbele algo al bot y vuelve a buscar\.$/, (m, b) => `Bot ${b}: no messages yet. Write something to the bot and search again.`),
    M(/^No pude conectar con Telegram: (.+)$/, (m, e) => "Could not reach Telegram: " + e),
    M(/^Telegram respondió: (.+)$/, (m, e) => "Telegram answered: " + e),
    M(/^Sincronizado: (.+)$/, (m, a) => "Synced: " + a),
    M(/^La sincronización falló: (.*)$/, (m, a) => "Sync failed: " + a),
    M(/^(\d+(?:\.\d+)?) h antes de cada programación$/, (m, a) => `${a} h before each schedule`),
    M(/^creado (.+?) · (último uso (.+) desde (.+)|sin usar)$/, (m, a, b, c, d) => `created ${a} · ` + (c ? `last used ${c} from ${d}` : "never used")),
    M(/^Código #(\d+)$/, (m, a) => "Code #" + a),
    M(/^El nodo de origen respondió (.+)$/, (m, a) => "The source node answered " + a),
    M(/^Hay una versión nueva: v(.+)$/, (m, v) => "A new version is available: v" + v),
    M(/^Instalada: v(.+) · En GitHub: v(.+) · Consultado: (.+)$/, (m, a, b, c) => `Installed: v${a} · On GitHub: v${b} · Checked: ${c}`),
    M(/^No pude consultar GitHub: (.+)$/, (m, e) => "Could not reach GitHub: " + e),
    M(/^Aquí \(hora del nodo\):$/, () => "Here (node time):"),
    M(/^Se emite desde:$/, () => "Broadcast from:"),
    M(/^(Recibiendo audio del nodo|Sin audio del nodo en los últimos segundos) · (\d+) personas? escuchando$/, (m, a, n) =>
      (a.startsWith("Recibiendo") ? "Receiving audio from the node" : "No audio from the node in the last few seconds") + ` · ${n} listening`),
    M(/^Ya hay (\d+) personas escuchando; intenta más tarde$/, (m, n) => `${n} people are already listening; try again later`),
    M(/^A partir del (\d+) (\S+) (\d+) será a las (\S+) \((Horario de Verano|Horario de Invierno|cambio de horario)\)$/, (m, d, mes, y, h, k) =>
      `Starting ${({ Ene: "Jan", Abr: "Apr", Ago: "Aug", Dic: "Dec" })[mes] || mes} ${d}, ${y} it will be at ${h} (${
        ({ "Horario de Verano": "Daylight Saving Time", "Horario de Invierno": "Standard Time" })[k] || "clock change"})`),
    M(/^Zona horaria desconocida: (.+)$/, (m, z) => "Unknown time zone: " + z),
    M(/^La hora y el día se toman en esa zona y HAMNA los convierte a la hora del nodo para cada fecha: si esa zona cambia de horario, el evento se recorre solo\. Zona del nodo: (.+)\.$/,
      (m, z) => `Time and day are read in that zone and HAMNA converts them to node time for each date: if that zone changes its clocks, the event shifts on its own. Node zone: ${z}.`),
    M(/^Próxima: (.+?) · en$/, (m, d) => `Next: ${d} · in`),
    M(/^Próxima: (.+)$/, (m, d) => "Next: " + d),
    M(/^(\d+) secciones$/, (m, n) => n + (n === "1" ? " section" : " sections")),
    M(/^(\d+) secciones convertidas$/, (m, n) => n + " sections converted"),
    M(/^(\d+) MB liberados$/, (m, n) => n + " MB freed"),
    M(/^(\d+) voces en español$/, (m, n) => n + " Spanish voices"),
    M(/^(\d+) entrantes$/, (m, n) => n + " incoming"), M(/^(\d+) salientes$/, (m, n) => n + " outgoing"),
    M(/^Habla: (.+)$/, (m, w) => "Talking: " + w),
    M(/^Red completa · (\d+) nodos más$/, (m, n) => `Full network · ${n} more nodes`),
    M(/^En (.+) · (\d+) nodos? más$/, (m, r, n) => `On ${r} · ${n} more node${n === "1" ? "" : "s"}`),
    M(/^Nodo (\w+) — nodos conectados en este momento$/, (m, n) => `Node ${n} — nodes connected right now`),
    M(/^Nodo (\w+) · (.+) — nodos conectados en este momento$/, (m, n, c) => `Node ${n} · ${c} — nodes connected right now`),
    M(/^Conectado a (.+)$/, (m, n) => "Connected to " + n),
    M(/^Conectando (.+)$/, (m, n) => "Connecting " + n), M(/^Desconectando (.+)$/, (m, n) => "Disconnecting " + n),
    M(/^Desconectar (\d+)$/, (m, n) => "Disconnect " + n), M(/^Conectar (\d+)$/, (m, n) => "Connect " + n),
    M(/^¿Desconectar el nodo (\w+)\? Dejará de oír y de mandar audio por este enlace\.$/, (m, n) => `Disconnect node ${n}? It will stop hearing and sending audio over this link.`),
    M(/^(\d+) min (\d+) s$/, (m, a, b) => `${a} min ${b} s`),
    M(/^hace (\d+) (min|h|d)$/, (m, n, u) => `${n} ${u} ago`),
    M(/^activa ahora$/, () => "active now"), M(/^activa hace (\d+) (min|h|d)$/, (m, n, u) => `active ${n} ${u} ago`),
    M(/^entró ahora$/, () => "signed in just now"), M(/^entró hace (\d+) (min|h|d)$/, (m, n, u) => `signed in ${n} ${u} ago`),
    M(/^último acceso (.+)$/, (m, d) => "last sign-in " + d),
    M(/^(\d+) sesión(es)? abiertas?$/, (m, n) => n + (n === "1" ? " open session" : " open sessions")),
    M(/^(.+) en (Windows|Android|iPhone\/iPad|Mac|Linux)$/, (m, b, o) => `${D[b] || b} on ${o}`),
    M(/^Demasiados intentos\. Espera (\d+) min\.$/, (m, n) => `Too many attempts. Wait ${n} min.`),
    M(/^🔒 Bloqueados por intentos fallidos: (.+)$/, (m, x) => "🔒 Locked after failed attempts: " + x.replace(/ desde /g, " from ")),
    M(/^Ya existe el usuario «(.+)»$/, (m, u) => `User «${u}» already exists`),
    M(/^¿Borrar el usuario «(.+)»\? Se cierran sus sesiones\. Si solo quieres quitarle el acceso por un tiempo, mejor desactívalo\.$/,
      (m, u) => `Delete user «${u}»? Their sessions will be signed out. If you only want to remove access for a while, deactivate them instead.`),
    M(/^Hay una transmisión al aire \(«(.+)»\)\. Se detendrá para iniciar «(.+)»\. ¿Continuar\?$/, (m, a, b) => `A broadcast is on air («${a}»). It will stop to start «${b}». Continue?`),
    M(/^¿Transmitir «(.+)» ahora\?$/, (m, a) => `Transmit «${a}» now?`),
    M(/^¿Transmitir «(.+)» \((.+)\) por el nodo ahora\?$/, (m, a, d) => `Transmit «${a}» (${d}) through the node now?`),
    M(/^¿Borrar la programación de «(.+)» a las (.+)\?$/, (m, a, h) => `Delete the schedule for «${a}» at ${h}?`),
    M(/^¿Borrar el evento «(.+)» y su programación\? Las secciones se conservan en la biblioteca\.$/, (m, a) => `Delete event «${a}» and its schedule? The sections stay in the library.`),
    M(/^¿Borrar «(.+)»\?( Se quitará de (\d+) evento\(s\)\.)?$/, (m, a, w, n) => `Delete «${a}»?` + (w ? ` It will be removed from ${n} event(s).` : "")),
    M(/^¿Ejecutar ahora «(.+)»\? Esto cambia los enlaces reales del nodo\.$/, (m, a) => `Run «${a}» now? This changes the node's real links.`),
    M(/^¿Borrar esta tarea\?([\s\S]*)$/, (m, r) => "Delete this job?" + r),
    M(/^Sección (\d+)\/(\d+)$/, (m, a, b) => `Section ${a}/${b}`),
    M(/^Hecho: (.+)$/, (m, a) => "Done: " + a),
    M(/^No se pudieron convertir: (.+)$/, (m, a) => "Could not convert: " + a),
    M(/^Detectado en este equipo: (\w+)$/, (m, a) => "Detected on this device: " + a),
    M(/^Detectado en este nodo: (.+)\.$/, (m, a) => `Detected on this node: ${a}.`),
    M(/^Disponibles en este nodo: (.+)$/, (m, a) => "Available on this node: " + a),
    M(/^Cuenta para \{num_secciones\}$/, () => "Counts toward {num_secciones}"),
    M(/^(\d+) min antes$/, (m, n) => `${n} min before`), M(/^(\d+) min después$/, (m, n) => `${n} min after`),
    M(/^(\d+) min antes de la hora programada$/, (m, n) => `${n} min before the scheduled time`),
    M(/^(\d+) min después de terminar$/, (m, n) => `${n} min after it ends`),
    M(/^Inicia «(.+)»$/, (m, a) => `Starts «${a}»`), M(/^Termina · dura (.+) aprox\.$/, (m, a) => `Ends · lasts about ${a}`),
    M(/^📅 (.+) antes de «(.+)»$/, (m, t, a) => `📅 ${t} before «${a}»`), M(/^📅 (.+) después de «(.+)»$/, (m, t, a) => `📅 ${t} after «${a}»`),
    M(/^📅 al iniciar «(.+)»$/, (m, a) => `📅 at the start of «${a}»`), M(/^📅 durante «(.+)»$/, (m, a) => `📅 during «${a}»`),
    M(/^⚠ suena durante «(.+)»$/, (m, a) => `⚠ plays during «${a}»`),
    M(/^cada hora, al minuto (\d+)$/, (m, a) => `every hour, at minute ${a}`),
    M(/^a las (.+)$/, (m, a) => "at " + a.replace(/ y /g, " and ")), M(/^a los minutos (.+)$/, (m, a) => "at minutes " + a.replace(/\(horas /, "(hours ")),
    M(/^Día (\S+) de cada mes$/, (m, a) => `Day ${a} of every month`),
    M(/^Día (\S+), mes (\S+), semana (\S+)$/, (m, a, b, c) => `Day ${a}, month ${b}, weekday ${c}`),
    M(/^días (.+)$/, (m, a) => "days " + a), M(/^\(día anterior\)$/, () => "(previous day)"), M(/^\(día siguiente\)$/, () => "(next day)"),
    M(/^en (\d+.*)$/, (m, a) => "in " + a),
    M(/^(\d+) d (\d+) h$/, (m, a, b) => `${a} d ${b} h`),
    M(/^Total (.+) \/ (.+)$/, (m, a, b) => `Total ${a} / ${b}`),
    M(/^Sección: faltan (.+) \/ (.+)$/, (m, a, b) => `Section: ${a} left / ${b}`),
    M(/^Evento: faltan (.+) \/ (.+)$/, (m, a, b) => `Event: ${a} left / ${b}`),
    M(/^Asterisk rechazó «(.+)»: (.*)$/, (m, a, b) => `Asterisk rejected «${a}»: ${b}`),
    M(/^Asterisk no respondió para el nodo (\w+): (.*)$/, (m, a, b) => `Asterisk did not answer for node ${a}: ${b}`),
    M(/^El nodo (\w+) no está en rpt\.conf$/, (m, a) => `Node ${a} is not in rpt.conf`),
    M(/^Formato (.+) no soportado en este nodo\. Usa: (.+)$/, (m, a, b) => `Format ${a} is not supported on this node. Use: ${b}`),
    M(/^El archivo es demasiado grande \(máximo (\d+) MB\)$/, (m, a) => `The file is too large (max ${a} MB)`),
    M(/^No pude conectar con Azure: (.+)$/, (m, a) => "Could not reach Azure: " + a),
    M(/^Azure no respondió: (.+)$/, (m, a) => "Azure did not answer: " + a),
    M(/^Error interno: (.+)$/, (m, a) => "Internal error: " + a),
    M(/^Valor inválido en (.+)$/, (m, a) => "Invalid value in " + a),
    M(/^Error (\d+)$/, (m, a) => "Error " + a),
    M(/^Aún no hay usuarios\. En el nodo ejecuta: (.+)$/, (m, a) => "No users yet. On the node run: " + a),
  ];

  function tr1(s) {
    if (Object.prototype.hasOwnProperty.call(D, s)) return D[s];
    for (const [re, fn] of P) { const m = s.match(re); if (m) return fn(...m); }
    return null;
  }
  function tr(s) {
    const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/), core = m[2];
    if (!core || !/[A-Za-zÁÉÍÓÚáéíóúñ¿¡]/.test(core)) return s;
    let out = tr1(core);
    if (out == null && core.includes(" · ")) {
      const parts = core.split(" · "), tp = parts.map((p) => { const x = tr1(p); return x == null ? p : x; });
      if (tp.some((x, i) => x !== parts[i])) out = tp.join(" · ");
    }
    return out == null ? s : m[1] + out + m[3];
  }
  window.hamnaT = (s) => tr(String(s));

  const SKIP = '[translate="no"], code, textarea, pre, .log, .cron-raw';
  const ATTRS = ["title", "placeholder", "aria-label"];
  function fixText(n) {
    const p = n.parentElement;
    if (!p || p.closest(SKIP) || p.tagName === "SCRIPT" || p.tagName === "STYLE") return;
    const t = tr(n.data);
    if (t !== n.data) n.data = t;
  }
  function fixAttrs(el) {
    if (el.closest(SKIP)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v) { const t = tr(v); if (t !== v) el.setAttribute(a, t); }
    }
  }
  function walk(root) {
    if (root.nodeType === 3) return fixText(root);
    if (root.nodeType !== 1) return;
    fixAttrs(root);
    root.querySelectorAll("[title],[placeholder],[aria-label]").forEach(fixAttrs);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) fixText(n);
  }
  walk(document.body);
  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "childList") m.addedNodes.forEach(walk);
      else if (m.type === "characterData") fixText(m.target);
      else if (m.type === "attributes") fixAttrs(m.target);
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true,
    attributes: true, attributeFilter: ATTRS });
})();
