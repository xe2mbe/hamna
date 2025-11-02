## HAMNA — Copilot instructions for code contributors

This file contains concise, actionable guidance for AI coding agents working in the HAMNA repo. Focus on small, safe, reviewable changes that respect audio/IO concerns and device-specific PTT integration.

### Big picture (what this project does)
- HAMNA automates scheduled audio transmissions for amateur radio (TTS + prerecorded audio + controlled pauses).
- Core responsibilities: generate TTS files (`src/func/tts.py`), slice/inspect audio (`src/func/functions.py`), play/manage audio with pauses and PTT control (`main.py`), and expose a tiny PTT HTTP API (`src/app.py`).

### Key files to read first
- `main.py` — primary playback runner. Shows use of pygame mixer, signals, Mutagen for duration, and uses utilities in `src/func`.
- `src/func/functions.py` — utilities: time conversion, progress bar, `ptt(action)` implementation (HTTP client), `file_duration`, `convert_to_valid_mp3`, and YAML config loading.
- `src/func/tts.py` — pyttsx3-based TTS that saves audio files.
- `cfg.yml` — canonical configuration: `general`, `secciones` (list with `archivo`, `inicio`, `fin`), `duraciones`, `mensajes`, and `ami` credentials.
- `src/app.py` — small FastAPI app implementing `/ptt_on` and `/ptt_off` to drive GPIO (used on Raspberry Pi).

### Project-specific conventions & patterns
- Config is YAML-driven. `cfg.yml` lists `secciones` with playback slices (hh:mm:ss). Helpers exist to read and summarise (`load_config`, `resume`, `resume_menu`).
- PTT control is implemented as an HTTP API: the player calls `ptt('on')` / `ptt('off')` which issues GET requests to `BASE_URL` (see `src/func/functions.py`). Update `BASE_URL` to point to the device running `src/app.py` or a hardware gateway.
- Audio duration uses `mutagen` (MP3). Playback is performed with `pygame.mixer` and controlled with pause/unpause logic in `main.py`.
- FFmpeg is used for file conversion (`convert_to_valid_mp3`) and the repository sets a Windows PATH override in `functions.py` pointing to `C:\ffmpeg\bin` — on other platforms prefer relying on the environment PATH instead of hard-coded values.
- TTS uses `pyttsx3.save_to_file(...)`. Generated files are saved under `./src/media/` by default (see `cfg.yml: general.media_path`).

### Integration points & external dependencies
- Devices: Raspberry Pi GPIO (FastAPI app in `src/app.py`) or any HTTP endpoint that accepts `/ptt_on` and `/ptt_off`.
- External tools: `ffmpeg` is required for `convert_to_valid_mp3`.
- Python packages: See `requirements.txt` (pygame, mutagen, pyttsx3, requests, fastapi/uvicorn if running the API).

### How to run locally (developer workflows)
1. Install dependencies:
   - pip install -r requirements.txt
   - Ensure `ffmpeg` is installed and on PATH (or update the hard-coded path in `src/func/functions.py`).
2. Generate or update TTS audio: run `python main.py` — it will call `tts()` and produce `audio_entrada.mp3`/`audio_salida.mp3` in `src/media/` and then run playback logic.
3. PTT device server (Raspberry Pi): start the server that toggles GPIO with `python src/app.py` (or run uvicorn: `uvicorn src.app:app --host 0.0.0.0 --port 8000`).
4. To test PTT from the player, ensure `BASE_URL` in `src/func/functions.py` points to the PTT server IP (e.g., `http://192.168.1.37`) and that `/ptt_on` and `/ptt_off` are reachable.

### Concrete examples to copy/paste
- Toggle PTT from code: `from src.func.functions import ptt ; ptt('on')` → sends GET to `{BASE_URL}/ptt_on`.
- Convert an audio file via ffmpeg wrapper: use `convert_to_valid_mp3(raw_file, 'out.mp3', './src/media')` in `src/func/functions.py`.
- Read duration: `from src.func.functions import file_duration ; file_duration('src/media/boletin.mp3')`.

### Safety notes & assumptions (do not change without review)
- Avoid automatic changes to GPIO control or PTT logic without hardware tests — these affect real radios and legal transmissions.
- The code assumes `es_ES` locale in `main.py`; this may not be available in every environment (Windows builds may differ). Prefer safe changes and test locale effects.

### What a helpful AI change looks like
- Small, localized edits: fix a bug in time conversion, add unit tests for `convert_hhmmss_to_seconds`, make `BASE_URL` configurable via env var, or improve error handling in `file_duration`.
- Avoid large refactors that change runtime behavior of audio/PTT flows without explicit human testing.

---
If any of these sections need more detail (run commands for Windows PowerShell, additional file examples, or clarifications about hardware wiring), tell me what to expand and I will update this file.
