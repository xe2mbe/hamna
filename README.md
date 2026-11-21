<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/logo-completo-oscuro.svg">
    <img src="docs/logo/logo-completo.svg" width="420" alt="HAMNA — HAM Net Automation">
  </picture>
</p>

<p align="center"><a href="#english"><b>🇺🇸 English</b></a> · <a href="#espanol"><b>🇲🇽 Español</b></a></p>

<a name="english"></a>

# HAMNA — HAM Net Automation

> Amateur radio has always stood out for the creativity and innovation of its operators.
> In that spirit HAMNA (HAM Net Automation) was born: a project to make broadcasts from amateur
> radio stations easier and more modern, especially bulletins and other recurring content that
> is recorded or prepared in advance.

## What does HAMNA mean?

**HAM** (amateur radio) + **N**et + **A**utomation. A *net* is an on-air gathering of hams at a set time, run by a net control station. HAMNA takes care of the part that can be prepared ahead of time —bulletins, announcements, recorded programs— so it goes on the air by itself, on time, and respecting the repeaters.

## How it started

HAMNA was born in December 2024 at the **Radio Club Guadiana A.C.** (Durango, Mexico) to broadcast the **Sunday Bulletin of the Federación Mexicana de Radio Experimentadores (FMRE)**. Every Sunday an operator had to stay live at the station to air content that, most of the time, had been prepared in advance. When work or personal commitments got in the way, the bulletin simply didn't go out: it was hard for other operators to step in, either because they didn't have the material or because they lacked experience running the broadcast and timing the pauses for the repeaters to drop. HAMNA automated that part: the material goes on the air by itself, on time, and the operator is free. All that's left is taking check-ins, which any operator can do.

- **The first version (December 2024)** was a Python script. The opening and closing messages, transmit and pause times, the pre-pause alert and the rewind on resume were set in the code or in a YAML file. PTT was physical: a GPIO pin (17) on the AllStar node's Raspberry Pi.
- **HAMNA Desktop (2026)** turned it into an application with a user interface: events built from sections, synthetic voice (Azure), audio leveling, automatic pauses and a weekly schedule. It lives at [xe2mbe/hamna_desktop](https://github.com/xe2mbe/hamna_desktop).
- **HAMNA Web (November 2026)** —this repository— moves all of that **into the node itself**, with no PC running: it's managed from the browser, transmits directly through AllStarLink or IRLP, and can be shared with the club members, each with their own user.

The same words it was born with still go on the air: *«Les recordamos que esta es una transmisión automatizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A.C.»* ("We remind you that this is an automated broadcast made with HAMNA, developed by Radio Club Guadiana A.C.")

---

## HAMNA Web

HAMNA Web runs **inside the node** (AllStarLink 3, HamVOIP, ASL2 or IRLP) and automates bulletins, nets and programs: from the browser you upload audio or type text, build events, schedule them, and the node transmits them by itself, with automatic pauses to respect the repeaters' timeout timers. No PC needs to be on.

**Contents:** [Screenshots](#screenshots) · [What it does](#what-it-does) · [Requirements](#requirements) · [Installation](#installation) · [Updating](#updating) · [First steps](#first-steps) · [The page](#the-page) · [Scheduling and time zones](#scheduling-and-time-zones) · [Sections and audio](#sections-and-audio) · [How it goes on the air](#how-it-goes-on-the-air) · [Automatic pauses](#automatic-pauses) · [Node dashboard](#node-dashboard) · [Live listening](#live-listening) · [Recordings](#recordings) · [Syncing events between nodes](#syncing-events-between-nodes) · [Nodes panel](#nodes-panel) · [Telegram alerts](#telegram-alerts) · [Telegram bot](#telegram-bot) · [Backups](#backups) · [Equipment health and diagnostics](#equipment-health-and-diagnostics) · [Users and security](#users-and-security) · [Cron](#cron) · [Files](#files) · [Common problems](#common-problems) · [Development](#development)

### Screenshots

Taken from the Radio Club Guadiana hub **299081** (the page is shown in Spanish; each user can switch it to English).

<p align="center"><img src="docs/img/pc-programacion.png?v=1.32.0" width="900" alt="Schedule: events with the node time, the source time and their broadcast number"></p>

| Events and their sections | Sections grouped by event |
|---|---|
| <img src="docs/img/pc-eventos.png?v=1.32.0" alt="Event detail with its sections in order"> | <img src="docs/img/pc-secciones.png?v=1.32.0" alt="Sections by event, including the ones renewed every broadcast"> |

| Dashboard | Nodes panel (hub) |
|---|---|
| <img src="docs/img/pc-conexiones.png?v=1.32.0" alt="Connections: nodes linked right now"> | <img src="docs/img/pc-nodos.png?v=1.32.0" alt="Cards for the nodes reporting to the hub"> |

<p align="center"><img src="docs/img/pc-respaldo.png?v=1.32.0" width="900" alt="Automatic backup to another node and to the cloud"></p>

**On a phone** — schedule, menu and nodes panel:

<p align="center"><img src="docs/img/celular.png?v=1.32.0" width="900" alt="HAMNA Web on a phone"></p>

### What it does

- **Events built from sections**: audio files (MP3, WAV, OGG, FLAC…), text read with synthetic voice (Azure, Google Cloud, ElevenLabs, Piper or eSpeak, with automatic fallback between engines) and sounds, in any order you want.
- **Scheduling**: once, daily, weekly or Monday to Friday, **in the program's time zone** (it follows that zone's daylight saving changes by itself), with **automatic numbering** of the broadcasts.
- **Automatic transmission** through AllStarLink or IRLP, with an even audio level (-18 LUFS) and automatic pauses for the repeaters.
- **Automatic connections** before and after each event, and a **Dashboard** tab to see and control the node live with your HAMNA user: on ASL its links, favorites and a node search, on IRLP it replaces IRLPvCON (favorites, enable/disable, DTMF, AUX and log).
- **Listen to the node live** from the page (computer or phone), no plugins, on ASL and IRLP, and **record** what you hear (e.g. the check-ins) to MP3.
- **Sync between nodes**: another HAMNA (for example, one rebroadcasting in another city) pulls the sections and audio of an event by itself, every week.
- **Nodes panel** on the hub: one card for each of the club's HAMNA nodes with its status, health and last backup.
- **Telegram**: alerts and a **bot** to check status, transmit, record and let contributors send their audio.
- **Backups**: downloadable and automatic (to another node, to Google Drive / OneDrive or via Telegram), and restore from the page.
- **Users with roles** (including **Contributor**, who only uploads the audio of their own sections), profile with photo, per-user language (English or Spanish), light or dark theme and station logo.
- **Equipment monitor and health** (CPU, RAM, disk, temperature, SD card, undervoltage), **Check this node** and **update notices** from GitHub.
- Lightweight: no Python packages, designed for a Raspberry Pi.

### Requirements

| | ASL3 (Debian 12/13) | HamVOIP | IRLP |
|---|---|---|---|
| Python | 3.5 or newer (comes with the system) | 3.5 (comes with the system) | 3.5 or newer |
| Audio | `ffmpeg` (the installer installs it) | `sox` and `mpg123` (already there; pacman is not touched) | `ffmpeg` and `alsa-utils` |
| Voice | Azure, Google, ElevenLabs, Piper (`asl3-tts`) or eSpeak | Azure, Google or ElevenLabs | Azure, Google, ElevenLabs or eSpeak |
| Page at `/hamna/` | Apache (Allmon3 / AllScan) | httpd (Supermon / Allmon2) | — (port 8090) |

### Installation

On the node, as root (or with `sudo`):

```bash
curl -sL https://raw.githubusercontent.com/xe2mbe/hamna/main/update.sh | sudo bash
```

(On HamVOIP, without `sudo`.) It installs the **latest published release**. If you'd rather review the files first, download the release package from the GitHub *Releases/Tags* page, unpack it and run `sudo bash install.sh`.

The installer:

1. Detects whether the node is **AllStarLink 3**, **HamVOIP**, ASL2 or **IRLP**, and the node number.
2. On Debian/Raspbian it installs `ffmpeg` and `espeak-ng` with apt (if the node has `asl3-tts`, it doesn't install `espeak-ng`: they conflict). On HamVOIP it **doesn't touch pacman**.
3. Copies the program to `/opt/hamna-web`. Data goes to `/var/lib/hamna`.
4. Creates the `admin` user and asks for its password (with no terminal, it generates one and shows it).
5. If the node has Apache, it publishes the page at **`https://NODE-IP/hamna/`** (HamVOIP: `http://`), on the same port as Allmon/AllScan/Supermon: no extra port needs to be opened.
6. Creates the `hamna-web` service. With Apache, the service listens **only inside the node** (127.0.0.1:8090) and port 8090 is closed in the firewall: everything goes through `/hamna/`, with the password encrypted. Without Apache (e.g. IRLP), it's at `http://NODE-IP:8090` and that port is opened in the firewall.
7. Creates the `sudo` rules so the page can view/edit cron (see [Cron](#cron)).

`install.sh` options:

| Option | What for |
|---|---|
| `--type asl\|irlp` | Force the node type (normally detected) |
| `--node 12345` | ASL node number or IRLP stationid |
| `--port 8090` | Internal port of the page |
| `--password PASS` | Password for the `admin` user, without asking |
| `--no-packages` | Don't install anything with apt |
| `--no-cron` | Don't give the page permission over cron |
| `--no-apache` | Don't publish `/hamna/` in Apache |
| `--listen-all` | Keep 8090 open to the network even with Apache |
| `--force` | Install even if something is on the air or being prepared |

The older Spanish options (`--tipo`, `--nodo`, `--puerto`, `--sin-paquetes`, `--sin-cron`) still work.

### Updating

```bash
sudo /opt/hamna-web/update.sh
```

On HamVOIP, without `sudo` (you're already root). On nodes with a version older than 1.6.5, use the [Installation](#installation) command.

The updater installs the **latest published release** (the newest `vX.Y.Z` tag in the repository), not whatever was last pushed to `main`: changes under test don't reach the nodes until a release is published. Options: `--version v1.7.0` to install a specific version (also to go back to an older one) and `--branch main` to try the latest unpublished code. It then runs that version's `install.sh`, which:

- **refuses to install if something is on the air or preparing audio** (so it never cuts a broadcast);
- first backs up the data and the program to `/var/backups/hamna/` (keeps the last 5);
- keeps events, audio, users, settings and schedule.

On the page, the version tag next to "HAMNA Web" turns **green** when you're up to date and **amber** when there's a new version; **Settings → System → Updates** shows the changes and the command to install it. GitHub is only queried for administrators, and the answer is cached for 6 hours.

| Task | Command |
|---|---|
| Change a user's password | `sudo hamna-web-passwd USER` (asks for it without showing it and signs out their sessions) |
| Recover access | `sudo hamna-web-passwd admin` (if `admin` doesn't exist, it's created as administrator) |
| Create another administrator from the terminal | `sudo hamna-web-passwd --create USER` |
| View the log | `journalctl -u hamna-web -f` (or `/var/lib/hamna/hamna.log`) |
| Restart | `sudo systemctl restart hamna-web` |
| Uninstall | `sudo /opt/hamna-web/uninstall.sh` (add `--delete-data` to delete the data too) |

### First steps

1. Open `https://NODE-IP/hamna/` and sign in as `admin`.
2. **Settings → Node**: check the node number and the playback mode (see [How it goes on the air](#how-it-goes-on-the-air)), and upload your station logo. Try a test transmission.
3. **Settings → Voice**: choose the voice engine (Azure needs a key and region; Google and ElevenLabs, their API key).
4. **Settings → Users**: create a user for each club member with their role.
5. **Sections**: upload audio or type text.
6. **Events**: create an event, add sections and put them in order.
7. **Schedule**: schedule the event with its time and time zone.

### The page

- **Sidebar** with the tabs, the equipment monitor, your user and the node's clock. It hides with the ‹ arrow (and comes back with ☰); on a phone it's a menu that slides in from the left. Next to the name, color tags show the node number and the detected type: ASL3/ASL (blue), HamVOIP (orange) and IRLP (purple).
- **My profile** (click your photo or name): photo, name, language, password and open sessions. The photo is shrunk in the browser before uploading.
- **Per-user language**: English (default) or Spanish, in **My profile**; the sign-in screen has its own selector. What goes on the air (voices, dates) stays in Spanish.
- **Light or dark theme** (moon button), remembered by each browser.
- **Station logo** (Settings → Node): shown in the sidebar, on the sign-in screen and in the browser tab. The browser shrinks it before uploading.
- **On-air bar**: status, current section, **time remaining / duration** of the section and the event, and controls (pause, skip wait, next, stop, log).
- **Equipment monitor**: CPU, RAM, disk, temperature (not available on HamVOIP), load, network and uptime. With the menu hidden, the top bar shows CPU and temperature.
- **Resource use**: the page polls the status every 1 s only while something is on the air, every 5 s when idle, and not at all when the tab is hidden. The monitor comes in that same request (reading it takes ~4 ms on a Pi 3).

### Scheduling and time zones

- Each scheduled event has its own **time zone**: the time and day are taken in that zone and HAMNA converts them to the node's time **for each date**. If the program comes from San Antonio (America/Chicago) or Tijuana, the event shifts by itself when that zone changes to or from daylight saving time. Without a zone, the node's time is used.
- In the zone list each zone shows its UTC offset (e.g. *US Central (UTC−6, summer UTC−5)*), and the UTC time is shown next to the time field.
- The card shows the **node time** in large type with its zone (*19:00 · CDMX/Monterrey*), the source time below it (*Broadcast from: 17:00 Tijuana*), and warns about the next daylight saving change (*"From 17 Mar 2027 it will be at 18:00 (Daylight Time)"*).
- The **Next event** strip with the countdown sits above the card of the upcoming event.
- Each card's **timeline** shows the event's connections and the users' cron jobs (root, asterisk, IRLP) that fall nearby; the system ones (`/etc/cron.d`) are only shown in the Cron tab.
- An event's audio is prepared (converted and leveled) **as soon as** you add sections or save the schedule, and again 20 minutes before air time.
- Variables for voice texts: `{fecha}`, `{fecha_larga}`, `{hora}`, `{dia}`, `{saludo}` (buenos días / buenas tardes / buenas noches), `{despedida}` (buen día / buena tarde / buena noche), `{evento}`, `{numero}`, `{emision}`, `{emision_anio}`, `{anio}`, `{num_secciones}`, `{duracion_total}`, `{dur_contabilizable}`, `{titulo}`, `{descripcion}`, `{pausa_cada}`, `{pausa_duracion}`, `{pausa_alerta}`, `{nodo}`. Voice sections with "Regenerate before transmitting" are generated again right before going on the air.
- **Automatic numbering** (event detail): `{emision_anio}` counts the event's scheduled dates in the year (the 46th Sunday is #46) and restarts every January 1; `{emision}` is the global number based on "the broadcast on day R is #N". Numbers come from the calendar, not from a counter: a test, a restart or restoring a backup doesn't move them. The number advances when the day's broadcast ends (time + duration + 30 min), so a Saturday test already says Sunday's number. It's shown on the Schedule cards.

> On HamVOIP the system's time zone database is from 2016: US zones work fine, but central Mexico zones still think there's daylight saving time. Use "Node time" there for Mexican programs.

### Sections and audio

- **"By event" view**: sections grouped by event in the order they go on the air; those not used by any event are kept, collapsed, under "Unused".
- **"Renewed every broadcast" 🔁**: for sections that change every week (editorial, DXpeditions, statistics…). The pre-broadcast check warns if any of them still has the previous broadcast's audio.
- **Previous version**: when you replace an audio file, the old one is kept (`audios/anteriores/`, not included in backups) and you can go back to it. It's controlled by the option "When replacing a section's audio, keep the previous one".
- **Download ⬇** a section's audio: the file as is if it's a common format; otherwise, converted to WAV.
- **Export** an event's sections to a single file (MP3 or WAV): you pick and order the sections, the silence between them and the LUFS level; it's built in the background and downloaded when done (44.1 kHz if the originals exist, 8 kHz if only the on-air version exists).
- If you upload audio the node can't read (e.g. MP3 on a node without mpg123), the page converts it to WAV in the browser before uploading. Uploads are rejected before copying if there's not enough space.

**Voices** (Settings → Voice): Azure, **Google Cloud** (Neural2 / Chirp HD, with an API key), **ElevenLabs** (API key; the quota is shown), Piper and eSpeak. Long texts are split by sentence. With **automatic fallback** enabled, if the chosen engine fails the other configured ones are used (Azure → Google → ElevenLabs → Piper → eSpeak) and a single Telegram alert is sent.

### How it goes on the air

| Node | How it transmits | Service user |
|---|---|---|
| ASL3 / HamVOIP | `asterisk -rx "rpt localplay\|playback <node> <file>"`; app_rpt keys and unkeys the PTT. Stop/Pause/Next cut it with `rpt cmd <node> cop 24 0`. | `asterisk` on ASL3, `root` on HamVOIP |
| IRLP | `$BIN/key` → `aplay` → `$BIN/unkey`, with the environment from `/home/irlp/custom/environment`. In **Radio + network** mode (default) the same audio also goes to the connected reflector or node. | `repeater` |

**ASL playback mode** (Settings → Node):

- `localplay`: only this node's transmitter.
- `playback`: this node **and all linked nodes**.

**IRLP playback mode** (Settings → Node):

- **Radio + network** (default): this node **and the connected reflector or node**, like `playback` on ASL.
- **Radio only**: only this node's transmitter.

IRLP only sends to the network what comes in through the receiver with COS, so `aplay` alone doesn't reach the reflector. HAMNA uses IRLP's own `imike` in file mode, with the node's identity (`SPEAKFREE_CNAME` and `SPEAKFREE_ID`), and an internal relay that forwards it to the reflector from a single port and drops the RTCP goodbye (with it, the reflector forgets the sender). imike compresses in the channel's format (UNCOMP, ADPCM or GSM). The IP, port and format come from `local/calledip`, `local/udp_port` and `local/codec`, which IRLP writes when connecting; on an incoming call from another IRLP node it doesn't save the IP and the audio only goes out over the radio. If anything in the network part fails, the radio keeps transmitting and it's noted in the log. While HAMNA plays, the PTT is re-keyed every 0.3 s, because IRLP drops it when someone stops talking on the reflector. Tested with echo reflector 9990.

> **Important (ASL3):** app_rpt only sends `playback` to the links if the node has `duplex` greater than 0 **or** `linktolink = yes`. On a hub with `duplex = 0`, add `linktolink = yes` to its stanza in `rpt.conf` and restart Asterisk with `sudo systemctl restart asterisk` (never `rpt restart`). Without it, the audio plays on the hub but the linked nodes don't hear it.

Everything is converted to 8 kHz, 16-bit, mono WAV and leveled to **-18 LUFS** measured in mono, with a limiter at -2 dB. With ffmpeg, loudness is measured with the `ebur128` filter (17 min of audio: ~1 min on a Pi 3); with sox (HamVOIP) it's approximated with K-weighting. Conversion runs at low priority so Asterisk never waits for the CPU.

In **Settings → Audio level** you can turn off "Keep the original audio" to save space: only the on-air version is kept.

Formats: with ffmpeg, MP3, WAV, M4A, OGG, FLAC, AAC, OPUS; with sox + mpg123 (HamVOIP), MP3, WAV, OGG, FLAC.

### Automatic pauses

Each section longer than the "time before pausing" is cut into segments; each segment is a single file, so the PTT is never released halfway:

```
[PTT silence] + [We continue] + audio + [Going to pause]
                         alert ↑ mixed in N s before the cut
```

Between segments the PTT is released for the pause, and the next segment can start a few seconds before the cut point (rewind).

### Node dashboard

**Dashboard tab** (it used to be called Connections): one place to control the node with your HAMNA user, without the AllScan or IRLPvCON passwords. On ASL: the nodes linked right now, with callsign and city (from the AllStar directory), mode, direction, time connected, IP and who is talking; a summary with the nodes reachable across the whole network; buttons to **connect** (transceive, monitor or local monitor) and **disconnect** one or **all** of them; and your **favorites** as mini cards, with the node number on the left and its description below (they connect in the mode chosen next to the Connect button). The first time, the favorites are imported from AllScan; after that the administrator edits them in HAMNA (✏️ Edit), because AllScan's file belongs to www-data. The bot uses the same list. A **node search** looks up the AllStar directory by callsign or node number (by how they start: `XE` lists every XE… node, `XE2MBE` your nodes) or, with 3 letters or more, by description or location, and connects any result in the chosen mode. Search results and favorites show whether each node is online: **● Online** (registered with AllStar and answering), **● Not answering** (on and registered, but it doesn't accept incoming connections, usually because UDP port 4569 isn't forwarded on its router; it can still connect to you) or **○ Offline** (not registered). HAMNA checks it with AllStar's DNS and an IAX POKE, and remembers it for a couple of minutes. If Asterisk has several nodes, you choose which one to view. It refreshes every 4 s, only while the tab is open.

**On IRLP** the tab shows which node or reflector it's connected to (from `$LOCAL/active`), with the IP, port and audio format; the radio state (COS and PTT) and whether HAMNA is transmitting, read every 1.5 s; and the **other nodes on the same reflector**, according to status.irlp.net (that page updates every few minutes, so a connection of a few seconds may not show up).

**IRLP node control** (Dashboard tab; replaces IRLPvCON): connect to a node or reflector by number or with one click on a **favorite**, and disconnect; **enable or disable** the node; turn the **inactivity disconnect** on or off (`$LOCAL/timeout`); switch the **AUX1–3** outputs; run a **DTMF code** as if it came in over the radio; and read the **IRLP log** (`/home/irlp/log/messages`). Operators and administrators use the controls, read-only users only see them, and only administrators edit the favorites. The first time, the IRLPvCON favorites are imported. Everything goes through `bin/hamna-irlp` as the `repeater` user, which only accepts those commands with validated values.

**Turning IRLPvCON off** (**Settings → System → IRLPvCON**, administrator, IRLP only): one button turns the old console off or back on. HAMNA replaces its `.htaccess` (in `/var/www/html/irlpvcon/` and `/usr/lib/cgi-bin/irlpvcon/`) with `Require all denied` and keeps the original as `.htaccess.hamna-antes`; turning it on restores it exactly. It doesn't need root or an Apache restart.

**Automatic connections for an event** (Events → detail → bottom): connect or disconnect links before starting and when finished.

| System | Connect | Disconnect |
|---|---|---|
| ASL / HamVOIP | `rpt cmd <node> ilink 3` (transceive), `2` (monitor), `8` (local monitor) or `13` (permanent) | `ilink 1 <node>` or `ilink 6` (all); if a permanent link is still up, `ilink 11 <node>` |
| IRLP | `$SCRIPT/decode <node or reflector>` | `$SCRIPT/end` |

"N min before" only runs early when the event is scheduled; if you start it by hand, it runs at the start. The "when finished" ones also run if you stop the event.

### Live listening

With the **🔊** speaker on the bottom card (next to the counter) you can listen to the node from the page, on a computer or phone: what HAMNA transmits, the members' check-ins and the linked nodes. It arrives with a 1 to 2 second delay, in radio quality (8 kHz), using about 64 kbps per listener. Up to 8 people can listen at once; any user, even read-only.

To enable it, add this line to your node's stanza in `/etc/asterisk/rpt.conf` (ASL3 and HamVOIP) and restart Asterisk **when nothing is on the air** (`sudo systemctl restart asterisk`; on ASL3 never use `rpt restart`):

```
outstreamcmd = /opt/hamna-web/bin/hamna-live
```

app_rpt hands the node's audio to that small program, which forwards it to HAMNA Web on the same machine (127.0.0.1:8091). If HAMNA Web is off, the audio is simply discarded: it never blocks Asterisk. HAMNA converts it to µ-law only while someone is listening (≈1% CPU on a Raspberry Pi 4) and the browser plays it with no plugins. **Settings → System** shows whether audio is arriving and who is listening.

**On IRLP** it's turned on from the page: **Settings → System → Live audio** (administrator). HAMNA adds a marked block to `/home/irlp/.asoundrc` that taps what IRLP plays into `bin/hamna-live-irlp`, and reads the receiver with `arecord` (dsnoop), without taking the sound card away from IRLP. When turning it on it tests the output and the receiver and, if anything fails, leaves everything as it was. It's off by default; it can also be managed with `/opt/hamna-web/bin/hamna-irlp-envivo on|off|status`, and the uninstaller removes the block.

### Recordings

Records what is heard on the node (what it receives and what it transmits), for example the **check-ins** after the bulletin. It uses the same audio as [Live listening](#live-listening), so it needs `outstreamcmd` (ASL) or live audio turned on (IRLP).

- It starts by hand, from the bot (`/grabar`), or by itself when an event ends or starts (Settings). While recording, the bottom bar shows **REC**.
- Long silences aren't recorded (pauses of up to 1 s are kept), so the recording flows. It stops by itself after N minutes with no activity (5 by default) or when it reaches the limit (180 min), and the end is trimmed.
- It's saved as MP3 if the node can (otherwise WAV) with a title like «Boletín Dominical 46 · Toma de reportes», in the **Recordings** tab. Recordings are deleted after 30 days (adjustable).
- Optional: Telegram alerts when it starts and ends, and the audio sent to the alerts group.

### Syncing events between nodes

Lets another node rebroadcast an event without anyone sending it the audio. Example: the Tijuana node rebroadcasts the Sunday Bulletin that is put together on the hub.

**On the sharing node** (event → **Share with other nodes**): an administrator creates an **access code** and gives it to the other node along with the address of its HAMNA. The code is **read-only**, works **only for that event** (it can't be used to sign in to the page) and can be revoked; the same place shows when and from which IP it was used.

**On the receiving node** (its event, e.g. "Rebroadcast" → **Sync from another node**):

1. The address of the source HAMNA (e.g. `https://299081.nodes.allstarlink.org/hamna/`) and the code. **Test connection** shows the event, how many sections it has and its size.
2. **When to sync**: days and time, and/or "N hours before each scheduled run of this event". There's always a **Sync now** button.

When syncing:

- the order of the sections, their names, texts and the edition number (`{numero}`) are copied;
- **only audio that changed is downloaded** (compared by its sha256 fingerprint);
- voice sections (opening, closing) are copied once and stay as **📌 local**: this node can use its own text and the sync leaves them alone. Any section can be marked or unmarked as local;
- sections removed at the source are removed here;
- if the source doesn't answer or the code was revoked, **what was there last time is kept**;
- with HTTPS and a self-signed certificate (the ASL3 default), the certificate fingerprint is saved the first time and checked on every connection after that.

The receiving node needs to reach port 443 (or 80) of the sharing node.

### Nodes panel

Each HAMNA can report to a **hub** (the club's central node) every 60 s; the hub's **Nodes** tab shows one card per node with:

- station, number, type (ASL3/ASL/HamVOIP/IRLP) and version (green if up to date, orange if it needs updating);
- what's on the air or the next event, whether it's recording, equipment health, CPU/RAM/disk/temperature and the last backup received;
- **Edit** (administrator): the address of the node's dashboard on the local network and on the internet. Clicking the name opens it: the local one if you reached the hub from the local network, the internet one otherwise. Only addresses saved on the hub are used, never ones sent by the node.

To report, on the node: **Settings → Node → Nodes panel**, check "Report this node's status to a hub" and enter the hub's address and code (if left empty, the ones for backing up to another node are used). Each node's own tab shows only its card and those of the nodes reporting to it; the full panel is on the hub. If a node stops reporting for more than 10 min (adjustable), the hub sends a Telegram alert, and another when it comes back. "🗑 Remove from panel" deletes the card.

### Telegram alerts

In **Settings → Alerts** (administrators) HAMNA can send you a Telegram message when something goes wrong:

- ❌ an event couldn't start or ended with an error;
- ⚠ the **check 30 minutes before** each scheduled event found a problem: sections without audio, the node isn't responding, the Azure key is missing for voices that are regenerated, low disk space, or the last sync failed;
- ❌ an automatic sync from another node or an automatic backup failed;
- ⚠ equipment health got worse (see [Equipment health](#equipment-health-and-diagnostics)), a node on the panel stopped reporting, or a voice engine failed;
- optional: N minutes before each scheduled event (one or several alerts), a summary at start and end, each section as it starts, recordings, and when a contributor uploads their audio.

**Test alerts** sends a simple message or a sample of each type with data from a real event.

To set it up: create a bot with **@BotFather** (`/newbot`), paste its token, send something to the bot (or add it to a group) and use **Find my chat**; save and try **Send a test**. To have alerts arrive with the HAMNA logo, use `/setuserpic` in @BotFather and send it [`hamna/static/icon-512.png`](hamna/static/icon-512.png). Each message says which station and node it comes from; the same alert isn't repeated within 15 minutes, and messages are sent in the background (they never hold up a transmission).

### Telegram bot

With **"The bot answers commands"** turned on (Settings → Alerts) (on only one node per bot), the same bot also answers. Each user **links** it from My profile with a 6-digit code, and the bot offers what their role allows. The bot speaks Spanish; the button and command names below are the ones it shows.

- **Button menu** (📋 Menú, `/menu`): status, next event, health, history, nodes, transmit an event and record, with confirmation before acting.
- Commands: `/estado` (status), `/proximo` (next), `/salud` (health), `/historial` (history), `/nodos` (nodes, on the hub), `/grabar [title]` (record), `/ayuda` (help).
- Buttons on alerts: "next section" and "details" when starting; "transmit now" and "skip this time" on the next-event alert.
- **Contributors**: send their audio or voice note (up to 20 MB) and choose the section; they get a reminder days before if they haven't uploaded it, and a message when their section went on the air. Administrators can replace any section this way.
- **🤝 Colaboración** (in the menu): the events, soonest first, and in each one its sections in order, with duration and whether they were updated. Tapping a section lets you send new audio, change the text of a text-to-speech section (or generate the voice again), listen to it or go back to the previous version. Contributors see the events they appear in and edit only their own sections. Operators and administrators edit any section, can **add a new section** at the end of the event (audio or text-to-speech), **move it** (↕ up, down, to the start or to the end) and **delete it** (remove it from that event only, or delete it completely with its audio).
- **🔗 Conexiones** (in Nodes): the node's links with their mode and time connected; connect as transceive, monitor or local monitor, choosing from your **favorites** or typing the number; change the mode, disconnect one or all. On IRLP: connect to a node or reflector (with your IRLP favorites), disconnect, and enable or disable the node.
- Telegram's ☰ menu only lists `/menu` and `/start`; everything else is in the menu buttons (the commands still work if typed).
- **Backup via Telegram**: the automatic backup (without audio, up to 49 MB) is sent privately to linked administrators.

### Users and security

| Role | Can |
|---|---|
| Administrator | Everything: Settings, Cron, logo, users, backups, sharing and setting up syncs |
| Operator | Transmit, schedule, edit events and sections, connect and disconnect nodes, sync by hand, record, view cron |
| Read only | View status, schedule, events, sections and connections; listen live |
| Contributor | Only their **My sections** page: upload the audio of the sections assigned to them (from the page or via Telegram), see the cards and details of the events they appear in, and listen to the section or the whole event |

- The server checks the role on every action; the page also hides what the role can't use.
- The log and the broadcast history record who did what and from which IP (behind Apache, the visitor's real IP is used).
- 5 wrong passwords for a user from one IP, 20 from one IP, or 30 for a user from any IP lock it for 15 minutes. An administrator can unlock in Settings → Users; restarting the service also clears the locks. In the bot, 5 wrong linking codes lock that Telegram account for 15 minutes.
- Sessions last 30 days from last use (90 at most), and over https the cookie is marked `Secure`. Open sessions are listed in **My profile** (your own) and **Settings → Users** (all) and can be closed. Changing a user's password or deactivating them signs them out immediately. Only a fingerprint of each session's code is stored.
- The last active administrator can't be deleted, deactivated or have their role removed.
- The page can't be embedded in an iframe on another site, and it accepts no files without a session.
- With Apache, the page only opens through `https://…/hamna/` (the password travels encrypted) and 8090 only listens inside the node. To reach 8090 from outside the node (not recommended), install with `--listen-all`, or use an SSH tunnel: `ssh -L 8090:127.0.0.1:8090 user@node`.

### Cron

The **Cron** tab shows and edits the node's scheduled tasks: the crontab of asterisk (and of other users who have one), and on IRLP `custom/custom.crons` (repeater's crontab is rebuilt by itself every day at 3:00 from `irlp.crons` + `custom.crons`). **root**'s crontab, `/etc/crontab` and `/etc/cron.d` are shown read-only: root's is edited on the node with `crontab -e`.

Each change is validated, rejected if the table changed while you were editing it, and the previous version is saved first to `/var/backups/hamna-cron/`. For this the installer creates `/etc/sudoers.d/hamna-web`, limited to the helpers `/opt/hamna-web/bin/hamna-cron` and `hamna-irlp`. A page administrator can schedule commands as those users (e.g. asterisk): give that role only to the right people and use strong passwords. Operators can see cron but not edit it. To not grant this permission, install with `--no-cron`.

### Backups

**Settings → Backup** (administrators), in three tabs:

- **Download and restore**: a `.tar.gz` with events, sections, schedule, users, settings (including the keys), logo, photos and pause sounds; section audio is optional. It's built while downloading, without using space on the SD card. **Restore** validates the file and the database, moves the current data to `/var/lib/hamna/antes-de-restaurar-<date>/` (keeps the last 2), can **keep the node's own data** (number, type, logo, Asterisk/IRLP connection) and restarts the service by itself.
- **Automatic**: every day at the chosen time (it waits if something is on the air), **to another HAMNA node**, **to the cloud** (Google Drive or OneDrive, with rclone; you paste the token from `rclone authorize`) and/or **via Telegram**. Section audio is only sent when it changed since the last backup with audio. **Back up now**, status of the last backup, and an alert if it fails.
- **Receive from other nodes**: the storing node creates an access code for each node that backs up to it. It keeps several backups without audio and 2 with audio per node (in `/var/lib/hamna/respaldos/<node>/`) and offers them for download. The connection checks the certificate fingerprint.

### Equipment health and diagnostics

- **Equipment health** (every minute, without root): SD card errors (dmesg and ext4), read-only disk, a write test every 10 min, **undervoltage**, temperature, disk and memory. If something gets worse a Telegram alert arrives with what to do, a reminder every 12 h and another when it's back to normal; the sidebar shows a **Check** badge. An unclean shutdown (power cut) is only noted.
- **Check this node** (Settings → System): node, live audio (`outstreamcmd`, with commands to copy), pause and section audio readable, voices (if the Azure key returns 401 it looks for the right region and offers to change it; ElevenLabs key, voice and quota), Telegram, automatic backup, health, time and version, each with how to fix it.

### Files

| Path | What's there |
|---|---|
| `/opt/hamna-web/` | The program, `install.sh`, `update.sh` and `uninstall.sh` |
| `/var/lib/hamna/hamna.db` | Database: sections, events, schedule, users, syncs |
| `/var/lib/hamna/settings.json` | Settings (including the Azure key) |
| `/var/lib/hamna/audios/` | Section audio (`anteriores/`: previous versions); `sonidos/` the pause sounds; `cache/` the on-air versions |
| `/var/lib/hamna/grabaciones/` | Recordings |
| `/var/lib/hamna/respaldos/` | Backups received from other nodes |
| `/var/lib/hamna/fotos/` | Profile photos |
| `/var/lib/hamna/hamna.log` | Log |
| `/var/backups/hamna/` | Backups made by the installer before each update (the last 5) |
| `/var/backups/hamna-cron/` | Previous versions of the cron tables |
| `/etc/apache2/conf-available/hamna-web.conf` | Publishing at `/hamna/` (HamVOIP: `/etc/httpd/conf/extra/hamna-web.conf`) |
| `/etc/sudoers.d/hamna-web` | Limited permissions for cron and IRLP |

### Common problems

| Symptom | What to check |
|---|---|
| `playback` plays on the hub but not on the linked nodes | `duplex = 0` without `linktolink = yes` in `rpt.conf` (see [How it goes on the air](#how-it-goes-on-the-air)) |
| "PREPARANDO" (preparing) for several minutes | Long audio that hadn't been prepared is being leveled; since 1.6 it's prepared when added, so this only happens the first time |
| Forgot your password | `sudo hamna-web-passwd YOUR_USER` on the node's terminal |
| "Too many attempts" when signing in | Wait 15 min, ask an administrator to unlock it, or `sudo systemctl restart hamna-web` |
| `hamna-web-passwd admin` said "at least 6 characters" | Versions before 1.6.8 took that word as the password; update |
| The updater says "is on air" or "preparing audio" | Wait for it to finish; it won't install mid-broadcast (or use `--force`) |
| Apache shows `AH00558: Could not reliably determine the server's fully qualified domain name` | It's only a warning; it goes away with `ServerName my-node` in the Apache configuration |
| The sync says the certificate changed | The source node renewed its certificate: in the sync settings, run "Test connection" again and save |

### Differences from HAMNA Desktop

- Same database schema and the same voice variables, plus `{fecha_larga}`, `{saludo}`, `{despedida}`, `{numero}`, `{emision}`, `{emision_anio}`, `{anio}` and `{nodo}`.
- Voices: Azure (same as Desktop), Google Cloud, ElevenLabs, Piper (`asl3-tts`, a local neural voice on ASL3) and eSpeak NG. There's no SAPI5. HamVOIP has no local voices.
- The gap between sections is a separate setting (in Desktop it was the same as the pause duration).
- Two events can't be scheduled in the same minute: the second one stops the first.

### Development

No dependencies: the web server is built on the standard library (`hamna/web.py`) and the code is compatible with Python 3.5 to 3.14. The page is HTML, CSS and JavaScript with no external libraries; the texts are in Spanish in the code and `hamna/static/i18n.js` translates them to English in the browser (if you add texts, add them to its dictionary too).

```bash
set HAMNA_DATA=%TEMP%\hamna
python -m hamna --init backend=simulado
python -m hamna --set-password prueba123 --user admin
python -m hamna --port 8090
```

`simulado` (simulated) mode doesn't transmit anything; it only keeps the timing.

**Publishing a release** (what the nodes see as an update):

```bash
# 1. bump VERSION in hamna/__init__.py and the ?v= in hamna/static/index.html
git commit -am "Release v1.8.0"
git tag v1.8.0
git push origin main v1.8.0
```

What's pushed to `main` without a tag isn't offered to the nodes. Converting audio needs `ffmpeg` in the PATH; time zones on Windows need the Python `tzdata` package.

| Module | What it does |
|---|---|
| `app.py` | API routes |
| `web.py` | HTTP server, sessions and roles |
| `engine.py` | Scheduler and transmission |
| `backends.py` | ASL / IRLP / simulated |
| `irlpnet.py` | IRLP: audio also to the connected reflector or node (imike + relay) |
| `audio.py` | Conversion and leveling |
| `tts.py` | Voices |
| `auth.py` | Users, sessions and locks |
| `tz.py` | Time zones |
| `sessions.py` | Dashboard tab (`rpt xnode`; IRLP with status.irlp.net) |
| `links.py` | Automatic connections |
| `share.py` / `sync.py` | Sharing and syncing events between nodes |
| `numeracion.py` | Automatic broadcast numbering |
| `export.py` | Exporting sections to a file |
| `sysmon.py` / `health.py` | Equipment monitor and health |
| `diagnose.py` | Check this node |
| `updates.py` | Update notices |
| `notify.py` / `bot.py` | Telegram alerts and bot |
| `live.py` | Live audio (receives from `bin/hamna-live` and `bin/hamna-live-irlp`) |
| `grabar.py` | Recordings |
| `hub.py` | Nodes panel (heartbeats) |
| `backup.py` / `autobackup.py` | Backup, restore and automatic backup |
| `cron.py` | Cron tab |

---

<a name="espanol"></a>

<p align="right"><a href="#english">↑ English</a></p>

# HAMNA — HAM Net Automation (Español)

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

**Contenido:** [Capturas](#capturas) · [Qué hace](#qué-hace) · [Requisitos](#requisitos) · [Instalación](#instalación) · [Actualizar](#actualizar) · [Primeros pasos](#primeros-pasos) · [La página](#la-página) · [Programación y zonas horarias](#programación-y-zonas-horarias) · [Secciones y audios](#secciones-y-audios) · [Cómo sale al aire](#cómo-sale-al-aire) · [Pausas automáticas](#pausas-automáticas) · [Dashboard del nodo](#dashboard-del-nodo) · [Escuchar en vivo](#escuchar-en-vivo) · [Grabaciones](#grabaciones) · [Sincronizar eventos entre nodos](#sincronizar-eventos-entre-nodos) · [Panel de nodos](#panel-de-nodos) · [Avisos por Telegram](#avisos-por-telegram) · [Bot de Telegram](#bot-de-telegram) · [Respaldos](#respaldos) · [Salud del equipo y diagnóstico](#salud-del-equipo-y-diagnóstico) · [Usuarios y seguridad](#usuarios-y-seguridad) · [Cron](#cron-1) · [Archivos](#archivos) · [Problemas comunes](#problemas-comunes) · [Desarrollo](#desarrollo)

### Capturas

Tomadas del hub **299081** del Radio Club Guadiana.

<p align="center"><img src="docs/img/pc-programacion.png?v=1.32.0" width="900" alt="Programación: eventos con la hora del nodo, la de origen y su número de emisión"></p>

| Eventos y sus secciones | Secciones agrupadas por evento |
|---|---|
| <img src="docs/img/pc-eventos.png?v=1.32.0" alt="Detalle de un evento con sus secciones en orden"> | <img src="docs/img/pc-secciones.png?v=1.32.0" alt="Secciones por evento, con las que se renuevan en cada emisión"> |

| Dashboard | Panel de nodos (hub) |
|---|---|
| <img src="docs/img/pc-conexiones.png?v=1.32.0" alt="Conexiones: nodos enlazados en este momento"> | <img src="docs/img/pc-nodos.png?v=1.32.0" alt="Tarjetas de los nodos que reportan al hub"> |

<p align="center"><img src="docs/img/pc-respaldo.png?v=1.32.0" width="900" alt="Respaldo automático a otro nodo y a la nube"></p>

**En el celular** — programación, menú y panel de nodos:

<p align="center"><img src="docs/img/celular.png?v=1.32.0" width="900" alt="HAMNA Web en el celular"></p>

### Qué hace

- **Eventos armados con secciones**: audios (MP3, WAV, OGG, FLAC…), textos que se leen con voz sintética (Azure, Google Cloud, ElevenLabs, Piper o eSpeak, con respaldo automático entre motores) y sonidos, en el orden que quieras.
- **Programación** única, diaria, semanal o de lunes a viernes, **en la zona horaria del programa** (se ajusta sola al horario de verano de esa zona), con **numeración automática** de las emisiones.
- **Transmisión automática** por AllStarLink o IRLP, con nivel de audio parejo (-18 LUFS) y pausas automáticas para los repetidores.
- **Conexiones automáticas** antes y después de cada evento, y una pestaña **Dashboard** para ver y controlar el nodo en vivo con tu usuario de HAMNA: en ASL sus enlaces, favoritos y un buscador de nodos, en IRLP reemplaza a IRLPvCON (favoritos, habilitar/deshabilitar, DTMF, AUX y bitácora).
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
7. Crea las reglas de `sudo` para que la página pueda ver/editar el cron (ver [Cron](#cron-1)).

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

### Dashboard del nodo

**Pestaña Dashboard** (antes se llamaba Conexiones): un solo lugar para controlar el nodo con tu usuario de HAMNA, sin las claves de AllScan ni de IRLPvCON. En ASL: los nodos enlazados en este momento, con indicativo y ciudad (del directorio de AllStar), modo, dirección, tiempo conectado, IP y quién está hablando; un resumen con los nodos alcanzables en toda la red; botones para **conectar** (transceptor, monitor o monitor local) y **desconectar** uno o **todos**; y tus **favoritos** como mini tarjetas, con el número de nodo a la izquierda y su descripción abajo (conectan en el modo elegido junto al botón Conectar). La primera vez se importan de AllScan; después el administrador los edita en HAMNA (✏️ Editar), porque el archivo de AllScan es de www-data. El bot usa la misma lista. Un **buscador de nodos** consulta el directorio de AllStar por indicativo o número de nodo (por cómo empiezan: `XE` trae todos los nodos XE…, `XE2MBE` tus nodos) o, con 3 letras o más, por descripción o lugar, y conecta cualquier resultado en el modo elegido. Los resultados y los favoritos dicen si cada nodo está en línea: **● En línea** (registrado en AllStar y responde), **● No responde** (prendido y registrado, pero no acepta conexiones de fuera, casi siempre porque falta reenviar el puerto UDP 4569 en su router; él sí puede conectarse a ti) o **○ Fuera de línea** (no está registrado). HAMNA lo revisa con el DNS de AllStar y un POKE de IAX, y lo recuerda un par de minutos. Si el Asterisk tiene varios nodos, se elige cuál ver. Se actualiza cada 4 s solo con la pestaña abierta.

**En IRLP** la pestaña muestra a qué nodo o reflector está conectado (de `$LOCAL/active`), con la IP, el puerto y el formato de audio; el estado del radio (COS y PTT) y si HAMNA está transmitiendo, leídos cada 1.5 s; y los **otros nodos del mismo reflector**, según status.irlp.net (esa página se actualiza cada pocos minutos, así que una conexión de unos segundos no alcanza a aparecer).

**Control del nodo IRLP** (pestaña Dashboard; reemplaza a IRLPvCON): conectar a un nodo o reflector escribiendo el número o con un clic en un **favorito**, y desconectar; **habilitar o deshabilitar** el nodo; activar o desactivar la **desconexión por inactividad** (`$LOCAL/timeout`); encender o apagar las salidas **AUX1–3**; ejecutar un **código DTMF** como si llegara por el radio; y ver la **bitácora de IRLP** (`/home/irlp/log/messages`). Los controles son para operador y administrador, solo lectura únicamente los ve, y los favoritos los edita el administrador. La primera vez se importan los favoritos de IRLPvCON. Todo pasa por `bin/hamna-irlp` como el usuario `repeater`, que solo acepta esos comandos con valores validados.

**Apagar IRLPvCON** (**Ajustes → Sistema → IRLPvCON**, administrador, solo en IRLP): un botón apaga la consola vieja o la vuelve a encender. HAMNA cambia su `.htaccess` (en `/var/www/html/irlpvcon/` y `/usr/lib/cgi-bin/irlpvcon/`) por `Require all denied` y guarda el original como `.htaccess.hamna-antes`; al encender lo restaura exacto. No necesita root ni reiniciar Apache.

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
- **🔗 Conexiones** (en Nodos): los enlaces del nodo con su modo y tiempo conectado; conectar como transceptor, monitor o monitor local eligiendo de tus **favoritos** o escribiendo el número; cambiar el modo, desconectar uno o todos. En IRLP: conectar a un nodo o reflector (con tus favoritos de IRLP), desconectar, y habilitar o deshabilitar el nodo.
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
| `sessions.py` | Pestaña Dashboard (`rpt xnode`; IRLP con status.irlp.net) |
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
