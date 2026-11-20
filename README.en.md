<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/logo-completo-oscuro.svg">
    <img src="docs/logo/logo-completo.svg" width="420" alt="HAMNA — HAM Net Automation">
  </picture>
</p>

<p align="center"><a href="README.md">Español</a> · <b>English</b></p>

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

**Contents:** [Screenshots](#screenshots) · [What it does](#what-it-does) · [Requirements](#requirements) · [Installation](#installation) · [Updating](#updating) · [First steps](#first-steps) · [The page](#the-page) · [Scheduling and time zones](#scheduling-and-time-zones) · [Sections and audio](#sections-and-audio) · [How it goes on the air](#how-it-goes-on-the-air) · [Automatic pauses](#automatic-pauses) · [Connections](#connections) · [Live listening](#live-listening) · [Recordings](#recordings) · [Syncing events between nodes](#syncing-events-between-nodes) · [Nodes panel](#nodes-panel) · [Telegram alerts](#telegram-alerts) · [Telegram bot](#telegram-bot) · [Backups](#backups) · [Equipment health and diagnostics](#equipment-health-and-diagnostics) · [Users and security](#users-and-security) · [Cron](#cron) · [Files](#files) · [Common problems](#common-problems) · [Development](#development)

### Screenshots

Taken from the Radio Club Guadiana hub **299081** (the page is shown in Spanish; each user can switch it to English).

<p align="center"><img src="docs/img/pc-programacion.png?v=1.32.0" width="900" alt="Schedule: events with the node time, the source time and their broadcast number"></p>

| Events and their sections | Sections grouped by event |
|---|---|
| <img src="docs/img/pc-eventos.png?v=1.32.0" alt="Event detail with its sections in order"> | <img src="docs/img/pc-secciones.png?v=1.32.0" alt="Sections by event, including the ones renewed every broadcast"> |

| Connections | Nodes panel (hub) |
|---|---|
| <img src="docs/img/pc-conexiones.png?v=1.32.0" alt="Connections: nodes linked right now"> | <img src="docs/img/pc-nodos.png?v=1.32.0" alt="Cards for the nodes reporting to the hub"> |

<p align="center"><img src="docs/img/pc-respaldo.png?v=1.32.0" width="900" alt="Automatic backup to another node and to the cloud"></p>

**On a phone** — schedule, menu and nodes panel:

<p align="center"><img src="docs/img/celular.png?v=1.32.0" width="900" alt="HAMNA Web on a phone"></p>

### What it does

- **Events built from sections**: audio files (MP3, WAV, OGG, FLAC…), text read with synthetic voice (Azure, Google Cloud, ElevenLabs, Piper or eSpeak, with automatic fallback between engines) and sounds, in any order you want.
- **Scheduling**: once, daily, weekly or Monday to Friday, **in the program's time zone** (it follows that zone's daylight saving changes by itself), with **automatic numbering** of the broadcasts.
- **Automatic transmission** through AllStarLink or IRLP, with an even audio level (-18 LUFS) and automatic pauses for the repeaters.
- **Automatic connections** before and after each event, and a **Connections** tab to see and control the node's links live.
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

### Connections

**Connections tab**: the nodes linked right now, with callsign and city (from the AllStar directory), mode, direction, time connected, IP and who is talking; a summary with the nodes reachable across the whole network; and buttons to **connect** (transceive, monitor or local monitor) and **disconnect**. If Asterisk has several nodes, you choose which one to view. It refreshes every 4 s, only while the tab is open.

**On IRLP** the tab shows which node or reflector it's connected to (from `$LOCAL/active`), with the IP, port and audio format; the radio state (COS and PTT) and whether HAMNA is transmitting, read every 1.5 s; and the **other nodes on the same reflector**, according to status.irlp.net (that page updates every few minutes, so a connection of a few seconds may not show up).

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
- **🔗 Conexiones** (in Nodes): the node's links with their mode and time connected; connect as transceive, monitor or local monitor, choosing from the **AllScan favorites** or typing the number; change the mode, disconnect one or all. On IRLP: connect to a node or reflector and disconnect.
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
| `sessions.py` | Connections tab (`rpt xnode`; IRLP with status.irlp.net) |
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
