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
    "🎛 Permitir que el hub controle este nodo desde su bot de Telegram (conexiones, anuncios, salud…). Quién puede hacerlo lo decide el administrador del hub, nodo por nodo.": "🎛 Let the hub control this node from its Telegram bot (connections, announcements, health…). Who can do it is decided by the hub's administrator, node by node.",
    // Programación → Eventos | Anuncios
    "📅 Eventos": "📅 Events", "📢 Anuncios": "📢 Announcements", "📚 Biblioteca": "📚 Library", "Buscar por nombre, notas o texto": "Search by name, notes or text", "Más recientes": "Most recent", "Por nombre": "By name", "＋ Agregar": "＋ Add", "📄 Cargar varios .txt": "📄 Load several .txt", "Una entrada por archivo, con el nombre del archivo": "One entry per file, named after the file", "Ordenar": "Sort", "＋ Nuevo anuncio": "＋ New announcement",
    "Bitácora de anuncios": "Announcement log", "Anuncios cortos que el nodo transmite solo": "Short announcements the node transmits on its own",
    // Bot de Telegram apagado (perfil, sin ser administrador)
    "El bot de Telegram no está activo en este nodo. Pídele al administrador que lo active.":
      "The Telegram bot isn't active on this node. Ask the administrator to turn it on.",
    // Ajustes → Avisos: cómo crear el bot (texto partido por <b>/<code>)
    "En Telegram, abre": "In Telegram, open", "y envíale": "and send it",
    ". Ponle un nombre (p. ej. «HAMNA Hub RCG»).": ". Give it a name (e.g. «HAMNA Hub RCG»).",
    "BotFather te da un": "BotFather gives you a", "(algo como": "(something like", "): pégalo abajo.": "): paste it below.",
    "Escríbele cualquier cosa a tu bot (o agrégalo a un grupo y escribe ahí) y presiona":
      "Write anything to your bot (or add it to a group and write there) and press",
    "Guarda los ajustes y presiona": "Save the settings and press",
    "El bot de Telegram no está activo en este nodo. Actívalo en Ajustes → Avisos («Responder comandos y botones»).":
      "The Telegram bot isn't active on this node. Turn it on in Settings → Alerts («Answer commands and buttons»).",
    "Cada día te llega el respaldo": "Every day you get the backup",
    "(pesa poco) en tu chat privado con el bot. Nunca va al grupo de avisos: lleva claves y contraseñas cifradas.":
      "(it's small) in your private chat with the bot. It never goes to the alerts group: it carries encrypted keys and passwords.",
    // Colaborador
    "Colaborador": "Contributor", "Mis secciones": "My sections", "🔑 Contraseña": "🔑 Password", "Salir": "Sign out",
    "Aquí subes el audio de las secciones que te asignaron. El audio nuevo sale al aire en la próxima transmisión.":
      "Here you upload the audio for the sections assigned to you. The new audio goes on air in the next broadcast.",
    "⬆ Subir audio nuevo": "⬆ Upload new audio", "Texto que lee la voz": "Text read by the voice", "Guardar texto": "Save text",
    "Generando voz…": "Generating voice…", "Texto guardado ✓": "Text saved ✓", "Audio actualizado ✓": "Audio updated ✓",
    "Sí, reemplazar": "Yes, replace", "⚠ Sin audio": "⚠ No audio",
    "Cambiar": "Change", "Contraseña cambiada": "Password changed",
    "Todavía no tienes secciones asignadas. Pídele al administrador que te asigne una.":
      "You don't have any sections assigned yet. Ask the administrator to assign you one.",
    "Secciones que puede actualizar": "Sections they can update", "Sin secciones asignadas": "No sections assigned",
    "Todavía no hay secciones.": "There are no sections yet.",
    "Todo, incluidos usuarios, ajustes y respaldos.": "Everything, including users, settings and backups.",
    "Programa, transmite y edita eventos y secciones.": "Schedules, broadcasts and edits events and sections.",
    "Solo ve; no puede cambiar nada.": "Can only view; can't change anything.",
    "Solo entra a «Mis secciones» y sube el audio de las secciones que le asignes. Te llega un aviso por Telegram cada vez.":
      "Only sees «My sections» and uploads the audio for the sections you assign. You get a Telegram alert each time.",
    "📤 Cuando un colaborador sube el audio de una sección": "📤 When a contributor uploads a section's audio",
    "Elige el archivo de audio": "Choose the audio file", "Escribe el texto": "Write the text",
    "↩ Regresar a la anterior": "↩ Go back to the previous one",
    "📡 Dónde sale tu colaboración": "📡 Where your contribution airs",
    "📷 Cambiar foto": "📷 Change photo", "Quitar foto": "Remove photo", "Foto guardada": "Photo saved", "Foto quitada": "Photo removed",
    "Elige una imagen": "Choose an image", "La foto debe ser JPEG": "The photo must be JPEG", "La foto es muy grande": "The photo is too large",
    "No pude leer la imagen": "Couldn't read the image",
    "▶ Escuchar todo el evento": "▶ Listen to the whole event", "⏹ Detener": "⏹ Stop",
    "Escuchar esta sección": "Listen to this section", "No se pudo reproducir esta sección": "Couldn't play this section",
    "Puedes escuchar el evento, pero no cambiarlo: las demás secciones las maneja el administrador.":
      "You can listen to the event, but not change it: the administrator manages the other sections.",
    "Cerrar la sesión en ese equipo": "Sign out that device",
    "Cada equipo o navegador donde entras es una sesión. Se cierra sola si no la usas en 30 días (y a los 90 días como máximo). Si no reconoces una, ciérrala con su botón.":
      "Each device or browser you sign in from is a session. It closes by itself if you don't use it for 30 days (and after 90 days at most). If you don't recognize one, close it with its button.",
    "Comandos y botones": "Commands and buttons",
    "Título de la grabación automática": "Title of the automatic recording",
    "Variables: {evento} · {numero} (#47 · 2026 #47) · {emision} · {emision_anio} · {anio} · {fecha} · {hora}. Así se llama también al descargarla o recibirla por Telegram.":
      "Variables: {evento} · {numero} (#47 · 2026 #47) · {emision} · {emision_anio} · {anio} · {fecha} · {hora}. That is also the file name when downloading it or receiving it on Telegram.",
    "El título de la grabación es muy largo (máximo 120 caracteres)": "The recording title is too long (120 characters max)",
    "Por evento": "By event", "Todas": "All", "Cómo ver las secciones": "How to view the sections",
    "Actualizada": "Updated", "Sin usar en ningún evento": "Not used in any event", "Sin programar": "Not scheduled",
    "Marca las secciones que cambian en cada emisión": "Mark the sections that change every broadcast",
    "Marca en cada sección si se renueva en cada emisión": "Mark in each section whether it's renewed every broadcast",
    "Este evento no tiene secciones.": "This event has no sections.",
    "Cambiada después de la última emisión": "Changed after the last broadcast", "Sigue la de la emisión anterior": "Still the one from the previous broadcast",
    "Se renueva en cada emisión": "Renewed every broadcast",
    "🔁 Se renueva en cada emisión (por ejemplo, el editorial o las noticias de la semana). Te aviso si sigue la de la emisión anterior.":
      "🔁 Renewed every broadcast (for example the editorial or the week's news). I'll warn you if it's still the previous one.",
    "⏺ Cuando empieza y termina una grabación (con botón para detenerla)": "⏺ When a recording starts and ends (with a button to stop it)",
    "Grabaciones": "Recordings", "Grabación": "Recording", "⏺ Grabar ahora": "⏺ Record now", "⏹ Detener": "⏹ Stop",
    "Lo que se escucha en el nodo: la toma de reportes, las redes…": "What is heard on the node: check-ins, nets…",
    "Grabar ahora": "Record now", "Título": "Title", "⏺ Grabar": "⏺ Record", "Grabando": "Recording",
    "Grabación detenida": "Recording stopped", "Borrada": "Deleted", "⬇ Descargar": "⬇ Download", "🗑 Borrar": "🗑 Delete",
    "Todavía no hay grabaciones.": "There are no recordings yet.", "Se escucha actividad.": "Activity is being heard.",
    "¿Detener la grabación? Se guarda lo que lleva.": "Stop the recording? What it has so far is saved.",
    "¿Borrar esta grabación? No se puede deshacer.": "Delete this recording? It can't be undone.",
    "Ver las grabaciones": "See the recordings", "Grabar solo": "Record automatically",
    "Al terminar cada evento (la toma de reportes)": "When each event ends (the check-ins)",
    "Desde que empieza cada evento (la emisión completa y lo que sigue)": "From the start of each event (the whole broadcast and what follows)",
    "No, solo a mano": "No, only by hand", "Terminar tras (minutos sin actividad)": "Stop after (minutes without activity)",
    "Duración máxima (minutos)": "Maximum length (minutes)", "Borrar las grabaciones de más de (días)": "Delete recordings older than (days)",
    "0 = no borrar. Si el disco se llena, se borran las más viejas.": "0 = don't delete. If the disk fills up, the oldest are deleted.",
    "📲 Mandar cada grabación al grupo de avisos de Telegram (hasta 50 MB, unas 3 h en MP3)":
      "📲 Send each recording to the Telegram alerts group (up to 50 MB, about 3 h in MP3)",
    "Graba lo que se escucha en el nodo (lo que recibe de la red y de radio, y lo que transmite) con el mismo audio del botón 🔊 En vivo. Los silencios largos no se graban, así que no queda aire muerto.":
      "Records what is heard on the node (what it receives from the network and radio, and what it transmits) with the same audio as the 🔊 Live button. Long silences aren't recorded, so there's no dead air.",
    " · terminó sin actividad": " · ended with no activity", " · llegó al tope de duración": " · reached the maximum length", " · detenida a mano": " · stopped by hand",
    "Ya se está grabando": "Already recording", "No se está grabando": "Not recording",
    "Opción de grabación inválida": "Invalid recording option",
    "Nodos": "Nodes", "este hub": "this hub", "Número de nodo": "Node number", "Tipo de nodo detectado": "Detected node type", "Al día": "Up to date", "Estado de los nodos que reportan a este hub": "Status of the nodes that report to this hub",
    "Panel de nodos": "Nodes panel", "Quitar del panel": "Remove from panel", "Quitado del panel": "Removed from panel",
    "🗺 Reportar el estado de este nodo a un hub cada minuto (al aire, próximo evento, salud, versión, respaldo)":
      "🗺 Report this node's status to a hub every minute (on air, next event, health, version, backup)",
    "Dirección del hub": "Hub address", "Vacío = la del respaldo a otro nodo": "Empty = the one used for backups to another node",
    "Vacío = el del respaldo": "Empty = the backup one",
    "El código se crea en el hub: Ajustes → Respaldo → Recibir de otros nodos (el mismo código sirve para el respaldo y para el panel).":
      "The code is created on the hub: Settings → Backup → Receive from other nodes (the same code works for backups and the panel).",
    "Si este nodo es el hub: avisar si un nodo deja de reportar por (minutos)": "If this node is the hub: alert when a node stops reporting for (minutes)",
    "0 = no avisar. El aviso llega por Telegram (Ajustes → Avisos).": "0 = no alert. The alert arrives on Telegram (Settings → Alerts).",
    "🗺 Un nodo dejó de reportar al panel de nodos (y cuando vuelve)": "🗺 A node stopped reporting to the nodes panel (and when it comes back)",
    "Sin eventos programados": "No scheduled events", "Se actualiza solo cada 30 s. Cada nodo manda su estado cada minuto.":
      "Refreshes by itself every 30 s. Each node sends its status every minute.",
    "Minutos para avisar de un nodo: de 0 a 1440": "Minutes to alert about a node: 0 to 1440",
    "Falta la dirección o el código de acceso del hub": "The hub address or access code is missing",
    "📲 Por Telegram a los administradores": "📲 By Telegram to the administrators",
    "⚠ Primero configura el bot de Telegram en Ajustes → Avisos.": "⚠ First set up the Telegram bot in Settings → Alerts.",
    "⚠ Ningún administrador tiene su Telegram vinculado. Vincúlalo en Mi perfil (clic en tu foto o nombre).":
      "⚠ No administrator has linked their Telegram. Link it in My profile (click your photo or name).",
    "(uno o varios)": "(one or more)",
    "No hay destinos configurados (otro nodo, nube o Telegram)": "No destinations set up (another node, cloud or Telegram)",
    "📩 Mensajes privados al colaborador: le recuerdo subir su audio si no lo ha cambiado desde la última emisión, y le aviso cuando su sección sale al aire. También puede mandarme su audio por Telegram.":
      "📩 Private messages to contributors: I remind them to upload their audio if they haven't changed it since the last broadcast, and tell them when their section airs. They can also send me their audio on Telegram.",
    "Recordarle con (días de anticipación)": "Remind them (days in advance)",
    "0 = no recordar. Los recordatorios se mandan de 9 a 21 h.": "0 = no reminder. Reminders are sent from 9 am to 9 pm.",
    "Días para el recordatorio: de 0 a 14": "Reminder days: from 0 to 14",
    "🤖 El bot responde comandos (/estado, /proximo, /salud, /historial) y pone botones en los avisos para detener, pasar a la siguiente sección, transmitir ya o saltar una emisión.":
      "🤖 The bot answers commands (/estado, /proximo, /salud, /historial) and puts buttons on alerts to stop, skip to the next section, broadcast now or skip a broadcast.",
    "Cada usuario vincula su Telegram en Mi perfil (clic en su foto o nombre). Los botones solo los pueden usar operadores y el administrador. Si varios nodos usan el mismo bot, actívalo solo en uno.":
      "Each user links their Telegram in My profile (click their photo or name). Only operators and the administrator can use the buttons. If several nodes use the same bot, turn it on in only one.",
    "Telegram desvinculado": "Telegram unlinked", "Desvincular": "Unlink", "🔗 Vincular Telegram": "🔗 Link Telegram",
    "Tu código": "Your code", "Abrir Telegram": "Open Telegram", "Telegram vinculado ✓": "Telegram linked ✓",
    "Escríbele al bot /estado, /proximo o /ayuda.": "Send the bot /estado, /proximo or /ayuda.",
    "¿Desvincular tu Telegram? El bot ya no te reconocerá hasta que lo vuelvas a vincular.": "Unlink your Telegram? The bot won't recognize you until you link it again.",
    "El bot de Telegram no está escuchando en este nodo (el administrador lo activa en Ajustes → Avisos)":
      "The Telegram bot isn't listening on this node (the administrator turns it on in Settings → Alerts)",
    "El bot no está escuchando (activa Telegram y esta casilla, y guarda).": "The bot isn't listening (turn on Telegram and this box, and save).",
    "Mi nombre": "My name", "Guardar nombre": "Save name", "Nombre guardado": "Name saved", "👤 Mi perfil": "👤 My profile",
    "Mi perfil": "My profile", "Perfil guardado": "Profile saved", "Déjalo vacío si no quieres cambiarla.": "Leave it empty if you don't want to change it.",
    "Así te ven los demás usuarios y así apareces en los avisos. Para entrar sigues usando tu usuario.":
      "This is how other users see you and how you appear in alerts. You still sign in with your username.", "📋 Detalles": "📋 Details",
    "Secciones del evento": "Event sections", "Tu sección": "Your section", "Cerrar": "Close",
    "Solo puedes ver el orden y la duración; las demás secciones las maneja el administrador.":
      "You can only see the order and length; the administrator manages the other sections.", "Sí, regresar": "Yes, go back",
    "Versión anterior restaurada": "Previous version restored",
    "↩ Al reemplazar el audio de una sección, guardar el anterior para poder regresarlo":
      "↩ When a section's audio is replaced, keep the previous one so it can be restored",
    "Esta sección no tiene versión anterior": "This section has no previous version",
    "No encontré el archivo de la versión anterior": "Couldn't find the previous version's file",
    "No se pudo cambiar el audio (¿se está usando en este momento?). Intenta de nuevo en un momento.":
      "Couldn't switch the audio (is it in use right now?). Try again in a moment.",
    // Numeración de emisiones
    "Emisión global · emisión del año": "Overall broadcast · broadcast of the year",
    "🔢 Numerar las emisiones automáticamente": "🔢 Number broadcasts automatically",
    "Emisión global #": "Overall broadcast #", "…es la del día": "…is the one on",
    "Lo pone la numeración automática.": "Set by automatic numbering.",
    "Opcional. Se lee con {numero}.": "Optional. Read with {numero}.",
    "Numeración automática: falta programar el evento": "Automatic numbering: the event isn't scheduled yet",
    "⚠ Este evento todavía no tiene programación: sin fechas no hay qué contar. Prográmalo primero en Programación.":
      "⚠ This event has no schedule yet: without dates there's nothing to count. Schedule it first in Schedule.",
    "🔢 Después de guardarlo y programarlo podrás numerar sus emisiones automáticamente.":
      "🔢 Once it's saved and scheduled you can number its broadcasts automatically.",
    "Se lee con {emision} (global), {emision_anio} y {anio}. Las secciones que los usen deben tener 🔄 «Regenerar justo antes de transmitir».":
      "Read with {emision} (overall), {emision_anio} and {anio}. Sections that use them must have 🔄 «Regenerate right before broadcasting».",
    "🔄 Activé «Regenerar justo antes de transmitir»: el número de emisión cambia cada vez.":
      "🔄 I turned on «Regenerate right before broadcasting»: the broadcast number changes every time.",
    "Para numerar solo, indica qué número global tiene la emisión de qué fecha":
      "For automatic numbering, say which overall number the broadcast of which date has",
    "Fecha de referencia inválida": "Invalid reference date",
    "El número de emisión global debe ser un número entero": "The overall broadcast number must be a whole number",
    "Número de emisión global (numeración automática)": "Overall broadcast number (automatic numbering)",
    "Número de emisión del año: se reinicia cada 1 de enero": "Broadcast number of the year: restarts every January 1",
    "Año de la emisión": "Year of the broadcast",
    "Cuenta las fechas de la programación de este evento. La emisión del año vuelve a #1 cada 1 de enero (el domingo 46 del año es la #46); la global sigue sumando de un año a otro.":
      "Counts the dates in this event's schedule. The broadcast of the year goes back to #1 every January 1 (the 46th Sunday of the year is #46); the overall number keeps adding up from one year to the next.",
    "Número de edición del evento (la emisión global si es automática)": "Event edition number (the overall broadcast if automatic)",
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
    "El nodo y sus conexiones en este momento": "The node and its connections right now", "⛔ Desconectar todos": "⛔ Disconnect all",
    "Desconectar todos": "Disconnect all", "Favoritos de AllScan": "AllScan favorites", "Desconectando todos": "Disconnecting all",
    "Encendido": "On", "Apagado": "Off", "Apagar IRLPvCON": "Turn off IRLPvCON", "Encender IRLPvCON": "Turn on IRLPvCON",
    "IRLPvCON encendido": "IRLPvCON turned on", "IRLPvCON apagado": "IRLPvCON turned off",
    "La consola web vieja de IRLP (/irlpvcon/). Su contraseña viaja sin cifrar y no tiene límite de intentos; el Dashboard de HAMNA hace lo mismo con tus usuarios. Al apagarla, Apache deja de servirla; al encenderla vuelve exactamente como estaba.":
      "IRLP's old web console (/irlpvcon/). Its password travels unencrypted and has no attempt limit; the HAMNA Dashboard does the same with your users. When turned off, Apache stops serving it; when turned on, it comes back exactly as it was.",
    "¿Apagar IRLPvCON? Nadie podrá abrir /irlpvcon/ hasta que lo vuelvas a encender aquí.": "Turn off IRLPvCON? Nobody will be able to open /irlpvcon/ until you turn it back on here.",
    "IRLPvCON no está instalado en este nodo": "IRLPvCON is not installed on this node",
    "↻ Actualizar": "↻ Refresh", "↻ Recargar": "↻ Reload", "Enlaces directos": "Direct links", "Historial de conexiones": "Connection history", "Duración máxima de un anuncio (s)": "Maximum announcement length (s)", "Anuncios desde una dirección (opcional)": "Announcements from an address (optional)", "Solo estos dominios": "Only these domains", "Separados por comas; también valen sus subdominios. Vacío = cualquier dirección pública por https.": "Comma-separated; their subdomains count too. Empty = any public https address.", "Archivo de certificados": "Certificate file", "Solo si el equipo es viejo y no reconoce el certificado del servidor. Vacío = el del sistema.": "Only if the device is old and doesn't recognize the server's certificate. Empty = the system's.", "Caracteres máximos del texto": "Maximum text characters", "De 30 a 170 s. Por omisión 60.": "From 30 to 170 s. Default 60.", "De 200 a 4000. Por omisión 2000.": "From 200 to 4000. Default 2000.", "Todo": "All", "Últimas 24 horas": "Last 24 hours", "Últimos 7 días": "Last 7 days", "Últimos 30 días": "Last 30 days", "Solo intentos fallidos": "Failed attempts only", "Solo entrantes": "Incoming only", "Solo salientes": "Outgoing only", "Periodo": "Period", "Mostrar": "Show", "Nodo": "Node",
    "Transceptor": "Transceive", "Solo monitor": "Monitor only", "Monitor local": "Local monitor", "monitor local": "local monitor", "Conectar": "Connect", "Cargando…": "Loading…",
    "Red completa": "Full network", "Nodos alcanzables a través de los enlaces": "Nodes reachable through the links",
    // Control del nodo IRLP
    "Control del nodo IRLP": "IRLP node control", "Nodo o reflector": "Node or reflector", "✖ Desconectar": "✖ Disconnect",
    "Buscar nodos": "Search nodes",
    "Indicativo, nodo o lugar (p. ej. XE2MBE, XE, 59624)": "Callsign, node or place (e.g. XE2MBE, XE, 59624)",
    "Busca en el directorio de AllStar: el indicativo o el número de nodo por cómo empiezan; con 3 letras o más también por descripción o lugar.":
      "Searches the AllStar directory: callsign or node number by how they start; with 3 letters or more also by description or location.",
    "Favoritos": "Favorites", "Todavía no hay favoritos.": "No favorites yet.", "✏️ Editar": "✏️ Edit",
    "Todavía no hay favoritos. Agrégalos con ✏️ Editar.": "No favorites yet. Add them with ✏️ Edit.", "Sin descripción": "No description",
    "● Conectado": "● Connected", "Favoritos de ASL": "ASL favorites",
    "Uno por línea: el número de nodo (3 a 7 dígitos; EchoLink 3xxxxxx) y su descripción. La primera vez se importaron de AllScan; los cambios se guardan en HAMNA. Aparecen en el Dashboard y en el bot de Telegram.":
      "One per line: the node number (3 to 7 digits; EchoLink 3xxxxxx) and its description. The first time they were imported from AllScan; changes are saved in HAMNA. They show up in the Dashboard and in the Telegram bot.",
    "Uno por línea: el nodo o reflector (4 a 6 dígitos) y su descripción. Aparecen en el Dashboard y en el bot de Telegram.":
      "One per line: the node or reflector (4 to 6 digits) and its description. They show up in the Dashboard and in the Telegram bot.",
    "✅ Habilitado": "✅ Enabled", "⛔ Deshabilitado": "⛔ Disabled", "Habilitar": "Enable", "Deshabilitar": "Disable",
    "Desconexión por inactividad": "Inactivity disconnect", "Activada": "On",
    "IRLP se desconecta solo tras un rato sin actividad": "IRLP disconnects by itself after a while without activity",
    "Encender": "Turn on", "Código DTMF": "DTMF code", "Enviar código": "Send code",
    "Se ejecuta como si llegara por el radio (p. ej. 73 desconecta).": "It runs as if it came in over the radio (e.g. 73 disconnects).",
    "Bitácora de IRLP": "IRLP log", "Las últimas 100 líneas, la más nueva arriba": "The last 100 lines, newest first", "(vacía)": "(empty)",
    "Favoritos de IRLP": "IRLP favorites", "Favoritos guardados": "Favorites saved",
    "Uno por línea: el nodo o reflector (4 a 6 dígitos) y su nombre. Aparecen aquí y en el bot de Telegram.":
      "One per line: the node or reflector (4 to 6 digits) and its name. They show up here and in the Telegram bot.",
    "Nodo habilitado": "Node enabled", "Nodo deshabilitado": "Node disabled", "Desconectando": "Disconnecting", "Conectado": "Connected",
    "Desconexión por inactividad activada": "Inactivity disconnect turned on", "Desconexión por inactividad desactivada": "Inactivity disconnect turned off",
    "¿Deshabilitar el nodo? IRLP deja de aceptar conexiones y códigos DTMF del radio hasta que lo habilites.":
      "Disable the node? IRLP stops accepting connections and DTMF codes from the radio until you enable it.",
    "Este nodo no es IRLP": "This node is not IRLP", "Código DTMF inválido: usa 0-9, A-D, * o # (hasta 16)": "Invalid DTMF code: use 0-9, A-D, * or # (up to 16)",
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
    "Descargar el audio": "Download the audio",
    "Probar voz": "Try the voice", "▶ Escuchar": "▶ Listen", "Pega aquí tu clave": "Paste your key here",
    "Google Cloud — voces neuronales (requiere internet y clave)": "Google Cloud — neural voices (needs internet and a key)",
    "ElevenLabs — voces muy naturales (requiere internet y clave)": "ElevenLabs — very natural voices (needs internet and a key)",
    "Respaldo automático: si este motor falla, usar otro": "Automatic fallback: if this engine fails, use another one",
    "Apagado: si el motor falla, la sección no se genera (se avisa por Telegram).": "Off: if the engine fails, the section is not generated (a Telegram alert is sent).",
    "⚠ No hay otro motor configurado: pon la clave de otro (Azure, Google o ElevenLabs).": "⚠ No other engine is set up: add the key of another one (Azure, Google or ElevenLabs).",
    "Clave de API de Google": "Google API key", "Clave de API de ElevenLabs": "ElevenLabs API key",
    "Google Cloud → APIs y servicios → Credenciales → Crear clave de API (con «Cloud Text-to-Speech API» habilitada).": "Google Cloud → APIs & Services → Credentials → Create API key (with “Cloud Text-to-Speech API” enabled).",
    "elevenlabs.io → Developers → API Keys (con permiso de Text to Speech y de Voices).": "elevenlabs.io → Developers → API Keys (with Text to Speech and Voices permissions).",
    "Las Chirp3-HD y Neural2 son las más naturales; las es-US tienen acento latino.": "Chirp3-HD and Neural2 sound the most natural; es-US voices have a Latin American accent.",
    "Tono (semitonos)": "Pitch (semitones)", "Las voces Chirp HD no lo usan.": "Chirp HD voices ignore it.",
    "— Carga las voces de tu cuenta —": "— Load the voices of your account —", "— Elige una voz —": "— Choose a voice —",
    "Salen las voces de tu cuenta («Mis voces» y las que agregaste de la biblioteca).": "Shows the voices in your account (“My voices” and those you added from the library).",
    "Modelo": "Model", "Multilingual v2 — la mejor calidad": "Multilingual v2 — best quality",
    "Flash v2.5 — más rápido, cuesta la mitad": "Flash v2.5 — faster, half the cost", "Turbo v2.5 — rápido, buena calidad": "Turbo v2.5 — fast, good quality",
    "Estabilidad (%)": "Stability (%)", "Parecido a la voz (%)": "Similarity (%)",
    "Más alto = más parejo; más bajo = más expresivo.": "Higher = steadier; lower = more expressive.",
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
    ": solo sube el audio de las secciones que le asignes (por ejemplo, el editorial).": ": only uploads the audio for the sections you assign (for example, the editorial).",
    "+ Nuevo usuario": "+ New user", "Sesiones abiertas": "Open sessions", "Idioma": "Language",
    "Nuevo usuario": "New user", "Editar usuario": "Edit user", "Nombre": "Name", "Rol": "Role",
    "Para entrar. Letras, números, punto o guion.": "Used to sign in. Letters, numbers, dot or dash.",
    "Déjala vacía para no cambiarla": "Leave empty to keep it", "Al menos 8 caracteres.": "At least 8 characters.",
    "Si la cambias, se cierran sus sesiones.": "Changing it signs out their sessions.",
    "Activo (si lo desactivas, sale de inmediato y no puede entrar)": "Active (if you deactivate it, they are signed out at once and cannot sign in)",
    "Crear usuario": "Create user", "Usuario creado": "User created", "Usuario guardado": "User saved", "Usuario borrado": "User deleted",
    "Tú": "You", "Desactivado": "Deactivated", "Esta sesión": "This session", "Cerrar": "Close", "Sesión cerrada": "Session closed",
    "No hay sesiones abiertas.": "No open sessions.", "nunca ha entrado": "never signed in", "IP desconocida": "unknown IP",
    "Sin Telegram": "No Telegram", "vinculado, sin usar": "linked, not used yet", "Desvincular Telegram": "Unlink Telegram",
    "📲 Telegram:": "📲 Telegram:", "vinculado": "linked",
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
    "Escuchar este nodo IRLP desde la página (reflector, estaciones locales y HAMNA al aire) y grabar los reportes. Está apagado. Al encenderlo, HAMNA agrega un bloque en": "Listen to this IRLP node from the page (reflector, local stations and HAMNA on air) and record the reports. It is off. When you turn it on, HAMNA adds a block to",
    "y lo prueba; si algo falla, lo deja como estaba.": "and tests it; if anything fails, it leaves everything as it was.",
    "🔊 Encender escuchar en vivo": "🔊 Turn on listen live", "Apagar escuchar en vivo": "Turn off listen live",
    "Probando…": "Testing…", "Apagando…": "Turning off…", "Listo: escuchar en vivo encendido": "Done: listen live is on",
    "Escuchar en vivo apagado": "Listen live is off", "Apagar": "Turn off",
    "Ya no se podrá escuchar ni grabar este nodo desde la página. ¿Apagar?": "You will no longer be able to listen to or record this node from the page. Turn off?",
    "⚠ Para grabar, este nodo IRLP necesita «escuchar en vivo». Enciéndelo en Ajustes → Sistema → Audio en vivo.": "⚠ To record, this IRLP node needs “listen live”. Turn it on in Settings → System → Live audio.",
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
    "Hablando": "Talking", "Grupo": "Group", "Monitor": "Monitor", "↘ Entrante": "↘ Incoming", "↗ Saliente": "↗ Outgoing",
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
    // Diagnóstico
    "Revisar este nodo": "Check this node", "🔍 Revisar este nodo": "🔍 Check this node",
    "Revisa el nodo, el audio en vivo, los audios, la voz de Azure, Telegram, el respaldo, la salud del equipo y la hora, y dice cómo arreglar lo que falte.":
      "Checks the node, live audio, audio files, the Azure voice, Telegram, the backup, the device health and the clock, and tells you how to fix what's missing.",
    "Revisando… puede tardar unos segundos.": "Checking… this may take a few seconds.",
    "❌ Hay problemas que arreglar": "❌ There are problems to fix", "⚠️ Hay cosas por revisar": "⚠️ Some things need checking",
    "✅ Todo está bien": "✅ Everything is fine", "Copiar comando": "Copy command", "Comando copiado": "Command copied",
    "Ajuste guardado": "Setting saved",
    "Equipo": "Device",
    "El nodo responde": "The node responds", "Audio en vivo": "Live audio", "Formatos que puede leer": "Formats it can read",
    "Alerta de pausa": "Pause alert", "Anuncio de pausa": "Pause announcement", "Continuamos": "Resume",
    "Pausas": "Pauses", "Audios de las secciones": "Section audios", "Secciones sin archivo": "Sections without a file",
    "Secciones en formato no soportado": "Sections in an unsupported format", "Motor de voz": "Voice engine",
    "Salud del equipo": "Device health", "Versión de HAMNA": "HAMNA version",
    "Las pausas automáticas están apagadas": "Automatic pauses are off",
    "Los avisos por Telegram están apagados: no te enterarás si algo falla": "Telegram alerts are off: you won't find out if something fails",
    "Configúralos en Ajustes → Avisos.": "Set them up in Settings → Alerts.",
    "No hay respaldo automático: si la tarjeta SD se daña, se pierde todo lo de HAMNA": "There's no automatic backup: if the SD card fails, everything in HAMNA is lost",
    "Actívalo en Ajustes → Respaldo (a otro nodo o a Google Drive / OneDrive).": "Turn it on in Settings → Backup (to another node or to Google Drive / OneDrive).",
    "Tarjeta SD, alimentación, temperatura, disco y memoria bien": "SD card, power, temperature, disk and memory OK",
    "Todavía no se revisa (empieza un minuto después de arrancar)": "Not checked yet (starts a minute after startup)",
    "No se pudo saber si la hora está sincronizada": "Couldn't tell whether the clock is synchronized",
    "Reinicia Asterisk cuando no haya nada al aire (no uses «rpt restart»).": "Restart Asterisk when nothing is on air (don't use «rpt restart»).",
    "Escuchar en vivo todavía no funciona en nodos IRLP": "Live listening doesn't work on IRLP nodes yet",
    "Configurado (sin audio en los últimos segundos, normal si el nodo está en silencio)": "Configured (no audio in the last seconds, normal if the node is quiet)",
    "Asterisk está mandando el audio del nodo; el botón 🔊 En vivo está disponible": "Asterisk is sending the node's audio; the 🔊 Live button is available",
    "La clave de Azure solo sirve en la región donde se creó.": "An Azure key only works in the region where it was created.",
    "El nodo está en modo SIMULADO: nada sale por el radio": "The node is in SIMULATED mode: nothing goes out over the radio",
    "Elige AllStarLink o IRLP en Ajustes → Nodo.": "Choose AllStarLink or IRLP in Settings → Node.",
    "Falta la clave de Azure: no se pueden generar secciones de voz": "The Azure key is missing: voice sections can't be generated",
    "Pégala en Ajustes → Voz.": "Paste it in Settings → Voice.",
    "Todavía no se ha hecho ningún respaldo": "No backup has been made yet",
    "Usa «Respaldar ahora» en Ajustes → Respaldo para comprobar que funciona.": "Use «Back up now» in Settings → Backup to check that it works.",
    "Las pausas están activadas pero no hay audio de «Alerta de pausa»": "Pauses are on but there's no «Pause alert» audio",
    "Súbelo en Ajustes → Tiempos y pausas.": "Upload it in Settings → Timing and pauses.",
    "Vuelve a subirlo desde Ajustes → Tiempos y pausas: la página lo convertirá a WAV.": "Upload it again from Settings → Timing and pauses: the page will convert it to WAV.",
    "Vuelve a subir esos audios: la página los convertirá a WAV.": "Upload those audios again: the page will convert them to WAV.",
    "Actualiza cuando no haya nada al aire.": "Update when nothing is on air.",
    // Salud del equipo
    "❌ El equipo necesita atención": "❌ The node needs attention", "⚠️ Hay algo que revisar en el equipo": "⚠️ Something on the node needs checking",
    "✅ El equipo está bien": "✅ The node is healthy", "Revisando el equipo…": "Checking the node…", "↻ Revisar ahora": "↻ Check now",
    "Revisando…": "Checking…", "Tarjeta SD": "SD card", "Escritura en la SD": "SD card writes", "Alimentación": "Power supply",
    "Temperatura": "Temperature", "Memoria": "Memory",
    "🩺 Salud del nodo: errores de la tarjeta SD, escritura lenta, bajo voltaje, temperatura alta, poco disco (y cuando se normaliza)":
      "🩺 Node health: SD card errors, slow writes, under-voltage, high temperature, low disk (and when it recovers)",
    "Bajo voltaje en este momento": "Under-voltage right now", "Sin bajo voltaje desde el arranque": "No under-voltage since boot",
    "Sin errores de la tarjeta desde el arranque": "No card errors since boot", "Este equipo no informa la temperatura": "This device doesn't report temperature",
    "Este equipo no informa el voltaje": "This device doesn't report voltage",
    "No se puede leer el registro del kernel (dmesg) con los permisos de HAMNA; sin errores de ext4": "Can't read the kernel log (dmesg) with HAMNA's permissions; no ext4 errors", "Aún no se mide": "Not measured yet", "Sin datos": "No data",
    "La tarjeta SD puede estar fallando. Descarga un respaldo cuanto antes (Ajustes → Respaldo) y cámbiala por una nueva, de preferencia «High Endurance». Revisa también la fuente de alimentación.":
      "The SD card may be failing. Download a backup as soon as possible (Settings → Backup) and replace it, preferably with a «High Endurance» card. Check the power supply too.",
    "La tarjeta SD tarda mucho en guardar o no responde: es la señal típica de una SD que se está muriendo. Saca un respaldo ya y prepara una SD nueva.":
      "The SD card is very slow to save or doesn't respond: the typical sign of a dying card. Make a backup now and prepare a new SD card.",
    "La fuente no da suficiente voltaje. Usa una fuente de 5.1 V y al menos 2.5 A (Pi 3) con un cable corto y grueso; el bajo voltaje también daña las tarjetas SD.":
      "The power supply doesn't give enough voltage. Use a 5.1 V supply of at least 2.5 A (Pi 3) with a short, thick cable; under-voltage also damages SD cards.",
    "La Raspberry está muy caliente y puede frenarse. Mejora la ventilación, agrega disipador o ventilador y revisa que no esté encerrada.":
      "The Raspberry Pi is very hot and may slow down. Improve ventilation, add a heatsink or fan and make sure it isn't enclosed.",
    "Queda poco espacio. Borra audios que ya no uses, compacta las secciones (Ajustes → Nivel de audio) o revisa la bitácora del sistema.":
      "Space is running low. Delete audios you no longer use, compact the sections (Settings → Audio level) or check the system log.",
    "Queda muy poca memoria libre. Revisa qué programas están corriendo en el nodo.": "Very little free memory left. Check which programs are running on the node.",
    // Respaldo (sub-pestañas)
    "⏰ Automático": "⏰ Automatic", "💾 Descargar y restaurar": "💾 Download and restore", "📥 Recibir de otros nodos": "📥 Receive from other nodes",
    "Cada día HAMNA arma un respaldo y lo manda fuera de este nodo, para que no se pierda nada si se daña la tarjeta SD. Los audios de las secciones solo se incluyen cuando cambiaron.":
      "Every day HAMNA makes a backup and sends it off this node, so nothing is lost if the SD card fails. Section audios are only included when they changed.",
    "Último respaldo": "Last backup", "1. Cuándo": "1. When", "2. Adónde se manda": "2. Where it goes", "(uno o los dos)": "(one or both)",
    "Si a esa hora hay algo al aire, espera a que termine.": "If something is on air at that time, it waits until it ends.",
    "🖥️ A otro nodo HAMNA": "🖥️ To another HAMNA node", "☁️ A Google Drive u OneDrive": "☁️ To Google Drive or OneDrive",
    "Por ejemplo el hub. En ese nodo: Respaldo → Recibir de otros nodos → Nuevo código.": "For example the hub. On that node: Backup → Receive from other nodes → New code.",
    "⬆ Restaurar desde un respaldo": "⬆ Restore from a backup",
    // Respaldo automático
    "Respaldo automático": "Automatic backup",
    "Cada día, a la hora elegida, HAMNA arma un respaldo y lo manda fuera de este nodo, para que no se pierda nada si se daña la tarjeta SD. Los audios de las secciones solo se incluyen cuando cambiaron desde el último respaldo con audios. Si a esa hora hay algo al aire, espera a que termine.":
      "Every day at the chosen time HAMNA makes a backup and sends it off this node, so nothing is lost if the SD card fails. Section audios are only included when they changed since the last backup with audios. If something is on air at that time, it waits until it ends.",
    "Hacer un respaldo automático cada día": "Make an automatic backup every day", "Hora del respaldo": "Backup time",
    "A otro nodo HAMNA": "To another HAMNA node",
    "Mandar el respaldo a otro nodo HAMNA (por ejemplo el hub)": "Send the backup to another HAMNA node (for example the hub)",
    "Dirección del nodo destino": "Destination node address",
    "En ese nodo: Ajustes → Respaldo → Recibir respaldos de otros nodos → Nuevo código.": "On that node: Settings → Backup → Receive backups from other nodes → New code.",
    "A Google Drive u OneDrive": "To Google Drive or OneDrive", "Mandar el respaldo a la nube": "Send the backup to the cloud",
    "Carpeta en la nube": "Cloud folder", "Dentro de ella se crea una carpeta con el número de este nodo.": "A folder named after this node's number is created inside it.",
    "Respaldos sin audios a conservar en la nube": "Backups without audios to keep in the cloud",
    "De los que traen audios se conservan los 2 últimos.": "Of those with audios, the last 2 are kept.",
    "Audios solo si cambiaron": "Audios only if they changed", "Con audios": "With audios", "Sin audios": "Without audios",
    "Respaldar ahora": "Back up now", "Guarda los ajustes antes de usar «Respaldar ahora».": "Save the settings before using «Back up now».",
    "Respaldo iniciado": "Backup started", "⏳ Haciendo un respaldo…": "⏳ Making a backup…",
    "Todavía no se ha hecho ningún respaldo automático.": "No automatic backup has been made yet.",
    "Los audios cambiaron desde el último respaldo con audios: el próximo los incluirá.": "The audios changed since the last backup with audios: the next one will include them.",
    "Los audios no han cambiado desde el último respaldo con audios.": "The audios haven't changed since the last backup with audios.",
    "otro nodo": "other node", "nube": "cloud", "con audios": "with audios", "sin audios": "without audios",
    "automático": "automatic", "Los respaldos van a": "Backups go to",
    "Falta rclone en este nodo": "rclone is missing on this node",
    "rclone es el programa que sube los respaldos a Google Drive u OneDrive. Para instalarlo, en la terminal del nodo:":
      "rclone is the program that uploads backups to Google Drive or OneDrive. To install it, in the node's terminal:",
    "Si apt no lo encuentra (por ejemplo en HamVOIP):": "If apt can't find it (for example on HamVOIP):",
    "Conectar con la nube": "Connect to the cloud", "Servicio": "Service", "Texto que te dio rclone": "Text rclone gave you",
    "Nube conectada": "Cloud connected",
    "Nube desconectada": "Cloud disconnected",
    "¿Desconectar la nube? Los respaldos que ya están ahí no se borran.": "Disconnect the cloud? Backups already there are not deleted.",
    "En tu computadora instala rclone (": "On your computer install rclone (",
    "En una terminal de tu computadora corre el comando de abajo. Se abre el navegador para que autorices con tu cuenta.":
      "In a terminal on your computer run the command below. A browser opens so you can authorize with your account.",
    "Copia todo el texto que aparece entre": "Copy all the text that appears between", "y pégalo aquí.": "and paste it here.",
    "Recibir respaldos de otros nodos": "Receive backups from other nodes",
    "Este nodo puede guardar los respaldos automáticos de tus otros nodos. Crea un código para cada nodo y pégalo en su sección «Respaldo automático», junto con la dirección de este nodo.":
      "This node can store the automatic backups of your other nodes. Create a code for each node and paste it into its «Automatic backup» section, together with this node's address.",
    "Respaldos sin audios a conservar por nodo": "Backups without audios to keep per node",
    "Códigos de acceso": "Access codes", "Respaldos guardados": "Stored backups", "+ Nuevo código": "+ New code",
    "No hay códigos. Crea uno para cada nodo que mandará respaldos aquí.": "No codes. Create one for each node that will send backups here.",
    "Todavía no ha llegado ningún respaldo.": "No backup has arrived yet.", "(sin nombre)": "(no name)",
    "Nombre (p. ej. nodo 58788)": "Name (e.g. node 58788)", "Código quitado": "Code removed",
    "¿Quitar este código? El nodo que lo usa ya no podrá mandar respaldos aquí. Los respaldos guardados no se borran.":
      "Remove this code? The node using it won't be able to send backups here. Stored backups are not deleted.",
    "Código para recibir respaldos": "Code to receive backups",
    "En el nodo que mandará los respaldos, ve a Ajustes → Respaldo → Respaldo automático → «A otro nodo HAMNA» y pega:":
      "On the node that will send the backups, go to Settings → Backup → Automatic backup → «To another HAMNA node» and paste:",
    "Copia el código ahora: por seguridad no se vuelve a mostrar.": "Copy the code now: for security it is not shown again.",
    "Copiar código": "Copy code", "Código copiado": "Code copied",
    "💾 Si falla el respaldo automático": "💾 If the automatic backup fails",
    "Primero configura y guarda al menos un destino (otro nodo o nube)": "First set up and save at least one destination (another node or the cloud)",
    "Ya se está haciendo un respaldo": "A backup is already running",
    "Falta el código de acceso del nodo destino": "The destination node's access code is missing",
    "El nodo destino rechazó el código de acceso": "The destination node rejected the access code",
    "Hora del respaldo inválida (HH:MM)": "Invalid backup time (HH:MM)", "Copias a conservar: de 1 a 60": "Copies to keep: 1 to 60",
    "Elige Google Drive u OneDrive": "Choose Google Drive or OneDrive",
    "No encontré el token. Pega todo el texto que aparece entre ---> y <--- en tu PC": "Token not found. Paste all the text between ---> and <--- on your PC",
    "rclone no está instalado en este nodo": "rclone is not installed on this node",
    // Respaldo
    "Respaldo": "Backup", "Descargar respaldo": "Download backup", "⬇ Descargar respaldo": "⬇ Download backup",
    "Guarda en tu computadora eventos, secciones, programación, usuarios, ajustes (incluidas las claves de Azure y Telegram), el logo y los audios de pausa. Sirve para cambiar la tarjeta SD o pasar todo a otro nodo.":
      "Saves events, sections, schedule, users, settings (including the Azure and Telegram keys), the logo and the pause audios to your computer. Use it to replace the SD card or move everything to another node.",
    "Incluir los audios de las secciones": "Include the section audios",
    "⚠️ El archivo contiene contraseñas (cifradas) y claves; guárdalo en un lugar seguro y no lo compartas.":
      "⚠️ The file contains passwords (hashed) and keys; keep it somewhere safe and don't share it.",
    "Restaurar desde un respaldo": "Restore from a backup",
    "Reemplaza los datos de este nodo con los del respaldo. Lo que hay ahora no se borra: se mueve a":
      "Replaces this node's data with the backup's. What is here now is not deleted: it is moved to",
    "(se guardan las 2 más recientes). Los usuarios y contraseñas pasan a ser los del respaldo. Si el respaldo no trae audios de secciones, se quedan los de este nodo.":
      "(the 2 most recent are kept). Users and passwords become the backup's. If the backup has no section audios, this node's are kept.",
    "Archivo de respaldo": "Backup file",
    "Conservar los datos de este nodo (tipo, número, comandos IRLP/ASL, nombre de la estación y logo)":
      "Keep this node's own data (type, number, IRLP/ASL commands, station name and logo)",
    "Desmárcalo solo si restauras el mismo nodo (por ejemplo, después de cambiar la tarjeta SD).":
      "Uncheck it only when restoring the same node (for example, after replacing the SD card).",
    "Restaurar": "Restore", "Restaurando…": "Restoring…", "Sí, restaurar": "Yes, restore",
    "Preparando el respaldo; la descarga empieza en unos segundos…": "Preparing the backup; the download starts in a few seconds…",
    "Elige el archivo de respaldo": "Choose the backup file", "Elige el archivo de respaldo (.tar.gz)": "Choose the backup file (.tar.gz)",
    "Revisando y restaurando…": "Checking and restoring…", "Se cortó la conexión al subir el respaldo": "The connection dropped while uploading the backup",
    "Hay una transmisión en curso; detenla antes de restaurar": "A broadcast is in progress; stop it before restoring",
    "El archivo no es un respaldo de HAMNA (.tar.gz)": "The file is not a HAMNA backup (.tar.gz)",
    "El archivo no es un respaldo de HAMNA Web": "The file is not a HAMNA Web backup",
    "El respaldo no trae la base de datos": "The backup has no database",
    "La base de datos del respaldo está dañada": "The backup's database is damaged",
    "Los ajustes del respaldo están dañados": "The backup's settings are damaged",
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
    M(/^se detiene en (\S+)$/, (m, f) => "stops in " + f),
    M(/^Conectar a (\d{3,7})$/, (m, n) => "Connect to " + n),
    M(/^Conectando a (\d{4,6})$/, (m, n) => "Connecting to " + n),
    M(/^Ya está conectado a (\d{4,6})$/, (m, n) => "Already connected to " + n),
    M(/^¿Conectar a (\d{4,6})\?$/, (m, n) => `Connect to ${n}?`),
    M(/^El nodo está conectado a (.+)\. ¿Conectar a (\d{4,6})\?$/, (m, a, n) => `The node is connected to ${a}. Connect to ${n}?`),
    M(/^¿Desconectar de (.+)\?$/, (m, a) => `Disconnect from ${a}?`),
    M(/^¿Ejecutar el código DTMF (\S+)\? IRLP lo toma como si llegara por el radio\.$/, (m, c) => `Run DTMF code ${c}? IRLP takes it as if it came in over the radio.`),
    M(/^Código (\S+) enviado$/, (m, c) => `Code ${c} sent`),
    M(/^AUX(\d) encendida$/, (m, n) => `AUX${n} on`), M(/^AUX(\d) apagada$/, (m, n) => `AUX${n} off`),
    M(/^Líneas sin número de nodo: (.+)$/, (m, l) => "Lines without a node number: " + l),
    M(/^✅ Lista: (\d+) de (\d+) actualizadas$/, (m, a, b) => `✅ Ready: ${a} of ${b} updated`),
    M(/^⚠ Faltan (\d+): (\d+) de (\d+) actualizadas$/, (m, f, a, b) => `⚠ ${f} missing: ${a} of ${b} updated`),
    M(/^(\d+) secciones en la biblioteca$/, (m, n) => `${n} sections in the library`),
    M(/^(\d+) secciones · (\d+) eventos?( · (\d+) sin usar)?$/, (m, n, e, x, s) => `${n} sections · ${e} event${e === "1" ? "" : "s"}` + (x ? ` · ${s} unused` : "")),
    M(/^Sale (.+?)( · última emisión (.+))?$/, (m, a, x, b) => "Airs " + a + (x ? " · last broadcast " + b : "")),
    M(/^También en: (.+)$/, (m, a) => "Also in: " + a),
    M(/^ℹ Esta sección se usa en (\d+) eventos: (.+)\. Lo que cambies aquí cambia en todos\.$/, (m, n, e) => `ℹ This section is used in ${n} events: ${e}. What you change here changes in all of them.`),
    M(/^Quedaría: (.+)$/, (m, t) => "It would be: " + t),
    M(/^Así apareces para el administrador y en los avisos\. Para entrar sigues usando «(.+)»\.$/,
      (m, u) => `This is how the administrator and alerts see you. You still sign in with «${u}».`),
    M(/^¿Reemplazar el audio de (.+) con «(.+)»\?$/, (m, a, b) => `Replace the audio of ${a} with «${b}»?`),
    M(/^¿Regresar (.+) a la versión anterior\? La actual queda como anterior, por si cambias de opinión\.$/,
      (m, a) => `Go back to the previous version of ${a}? The current one becomes the previous one, in case you change your mind.`),
    M(/^↩ Versión anterior: (\S+)( · reemplazada (\S+) (\S+) (\S+))?$/,
      (m, d, x, dia, f, h) => `↩ Previous version: ${d}` + (x ? ` · replaced ${DIA[dia] || dia} ${f} ${h}` : "")),
    M(/^(.+) · actualizado (\S+) (\S+) (\S+)$/, (m, d, dia, f, h) => `${d} · updated ${DIA[dia] || dia} ${f} ${h}`),
    M(/^📡 (.+) · sale (\S+) (\S+) (\S+)$/, (m, e, dia, f, h) => `📡 ${e} · airs ${DIA[dia] || dia} ${f} ${h}`),
    M(/^(🔢 )?Próxima emisión: (\S+) (\S+) · global #(-?\d+) · (\d+) #(\d+)$/,
      (m, i, d, f, g, y, n) => `${i || ""}Next broadcast: ${DIA[d] || d} ${f} · overall #${g} · ${y} #${n}`),
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
    M(/^Nodo (\w+) — el nodo y sus conexiones en este momento$/, (m, n) => `Node ${n} — the node and its connections right now`),
    M(/^Nodo (\w+) · (.+) — el nodo y sus conexiones en este momento$/, (m, n, c) => `Node ${n} · ${c} — the node and its connections right now`),
    M(/^El nodo (\d+) ya está conectado\. ¿Cambiarlo a (.+)\?$/, (m, n, x) => `Node ${n} is already connected. Change it to ${x}?`),
    M(/^¿Conectar el nodo (\d+) como (.+)\?$/, (m, n, x) => `Connect node ${n} as ${x}?`),
    M(/^¿Desconectar los (\d+) enlaces del nodo (\d+)\? También se sueltan los permanentes\.$/, (m, k, n) => `Disconnect the ${k} links of node ${n}? Permanent ones are released too.`),
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
    M(/^usó el bot ahora$/, () => "used the bot just now"),
    M(/^usó el bot hace (\d+) (min|h|d)$/, (m, n, u) => `used the bot ${n} ${u} ago`),
    M(/^vinculado el (.+)$/, (m, d) => "linked on " + d),
    M(/^👥 (\d+) de (\d+) usuarios tienen el bot vinculado$/, (m, a, b) => `👥 ${a} of ${b} users have the bot linked`),
    M(/^Sin vincular: (.+)$/, (m, x) => "Not linked: " + x),
    M(/^¿Desvincular el Telegram de «(.+)»\? El bot deja de reconocerlo hasta que lo vuelva a vincular desde Mi perfil\.$/,
      (m, u) => `Unlink «${u}»'s Telegram? The bot will stop recognizing them until they link it again from My profile.`),
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
    M(/^✅ Conectado con (.+?)( · nodo \w+)? \(v(.+), (\d+) MB libres\)\. Guarda los ajustes\.$/,
      (m, e, n, v, l) => `✅ Connected to ${e === "el nodo" ? "the node" : e}${n ? n.replace("nodo", "node") : ""} (v${v}, ${l} MB free). Save the settings.`),
    M(/^(✅|❌) Último respaldo: (.+)$/, (m, i, f) => `${i} Last backup: ${f}`),
    M(/^✅ Conectado a (.+)$/, (m, a) => "✅ Connected to " + a),
    M(/^(✅|❌) (otro nodo|nube)$/, (m, i, d) => `${i} ${d === "nube" ? "cloud" : "other node"}`),
    M(/^Creado (.+?) · (?:último respaldo (.+) del nodo (\w+) \((.*)\)|sin usar)$/, (m, c, u, n, ip) =>
      `Created ${c} · ` + (u ? `last backup ${u} from node ${n} (${ip})` : "unused")),
    M(/^Último: (.+) desde (.+) · HAMNA v(.+)$/, (m, a, b, c) => `Last: ${a} from ${b} · HAMNA v${c}`),
    M(/^Nodo (\w+)$/, (m, a) => "Node " + a),
    M(/^sin audios por falta de espacio en el nodo \((\d+) MB libres\)$/, (m, a) => `without audios: not enough space on the node (${a} MB free)`),
    M(/^(\d+) por atender$/, (m, n) => `${n} to attend`),
    M(/^(\d+) por atender · (.+) · ([\d.]+) s$/, (m, n, f, t) => `${n} to attend · ${f} · ${t} s`),
    M(/^Usar la región (\w+)$/, (m, r) => "Use region " + r),
    M(/^La clave funciona en la región (\w+)$/, (m, r) => `The key works in region ${r}`),
    M(/^Azure rechaza la clave en la región «(\w+)» \(HTTP (\d+)\), pero la clave sí funciona en «(\w+)»$/,
      (m, a, c, b) => `Azure rejects the key in region «${a}» (HTTP ${c}), but the key does work in «${b}»`),
    M(/^La clave de Azure solo sirve en la región donde se creó\. Cambia la región a «(\w+)»\.$/,
      (m, r) => `An Azure key only works in the region where it was created. Change the region to «${r}».`),
    M(/^(\d+) secciones, todas con audio legible$/, (m, n) => `${n} sections, all with readable audio`),
    M(/^v([\d.]+) \(al día\)$/, (m, v) => `v${v} (up to date)`),
    M(/^Sincronizada por internet \((.+)\)$/, (m, a) => `Synchronized over the internet (${a})`),
    M(/^Último respaldo bueno: (.+)$/, (m, a) => "Last good backup: " + a),
    M(/^El bot @(\w+) responde$/, (m, a) => `Bot @${a} responds`),
    M(/^Asterisk responde y el nodo (\w+) está activo$/, (m, a) => `Asterisk responds and node ${a} is active`),
    M(/^Este nodo no lee (\w+): convirtiendo a WAV en tu navegador…$/, (m, a) => `This node can't read ${a}: converting to WAV in your browser…`),
    M(/^Salud del equipo( · revisado (.+))? · se revisa cada minuto$/, (m, x, f) => `Node health${f ? " · checked " + f : ""} · checked every minute`),
    M(/^Guardar 64 KB tardó ([\d.]+) s( \(lo normal es menos de 1 s\))?$/, (m, s, n) => `Saving 64 KB took ${s} s${n ? " (normally under 1 s)" : ""}`),
    M(/^(\d+) MB libres de (\d+) MB$/, (m, a, b) => `${a} MB free of ${b} MB`),
    M(/^Hubo bajo voltaje (\d+) (?:vez|veces) desde el arranque$/, (m, n) => `Under-voltage ${n} time(s) since boot`),
    M(/^Sin errores de la tarjeta desde el arranque\. Nota: el último arranque fue después de un apagado sin cerrar \(corte de luz o desconexión\)$/,
      () => "No card errors since boot. Note: the last boot came after an unclean shutdown (power cut or unplug)"),
    M(/^\((\d+) archivos?, (.+)\)$/, (m, n, t) => `(${n} file${n === "1" ? "" : "s"}, ${t})`),
    M(/^Tamaño aproximado: (.+)$/, (m, a) => "Approximate size: " + a),
    M(/^Subiendo… (\d+) %$/, (m, a) => `Uploading… ${a} %`),
    M(/^¿Restaurar «(.+)»\? Se reemplazan eventos, secciones, programación, usuarios y ajustes de este nodo; HAMNA se reiniciará y tendrás que entrar de nuevo\.$/,
      (m, a) => `Restore «${a}»? This node's events, sections, schedule, users and settings will be replaced; HAMNA will restart and you will need to sign in again.`),
    M(/^✅ Restaurado \(nodo (.+), (.+), (.+)\)\. Reiniciando HAMNA…$/, (m, n, f, a) =>
      `✅ Restored (node ${n}, ${f}, ${a.replace("audios de secciones sin cambio", "section audios unchanged")}). Restarting HAMNA…`),
    M(/^No hay espacio (?:suficiente )?en el nodo para (?:restaurar|recibir el archivo) \((\d+) MB libres\)$/, (m, a) => `Not enough space on the node (${a} MB free)`),
    M(/^El respaldo es de una versión más nueva de HAMNA \(v(.+)\); actualiza este nodo primero$/, (m, a) => `The backup is from a newer HAMNA (v${a}); update this node first`),
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
