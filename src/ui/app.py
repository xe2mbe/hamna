import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
import sys
import tempfile
import subprocess
import winsound
import ctypes
from urllib.parse import urlparse
try:
    from src.func.functions import (
        parse_int,
        hid_enumerate_filtered,
        hid_open_device,
        hid_close_device,
        hid_set_ptt as backend_hid_set_ptt,
        hid_read_cos,
        api_join,
        api_get,
        read_cfg,
        save_cfg,
        ami_test_connection,
    )
    from src.func.tts import (
        list_voices as tts_list_voices,
        synthesize as tts_synthesize,
    )
except Exception:  # fallback when running as a script from src/ui
    _CURR_DIR = os.path.dirname(os.path.abspath(__file__))
    _SRC_DIR = os.path.abspath(os.path.join(_CURR_DIR, ".."))
    if _SRC_DIR not in sys.path:
        sys.path.insert(0, _SRC_DIR)
    from func.functions import (
        parse_int,
        hid_enumerate_filtered,
        hid_open_device,
        hid_close_device,
        hid_set_ptt as backend_hid_set_ptt,
        hid_read_cos,
        api_join,
        api_get,
        read_cfg,
        save_cfg,
        ami_test_connection,
    )
    from func.tts import (
        list_voices as tts_list_voices,
        synthesize as tts_synthesize,
    )


class HamnaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hamna")
        self.geometry("900x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.production_tab = ProductionTab(notebook)
        self.editing_tab = EditingTab(notebook)
        self.configuration_tab = ConfigurationTab(notebook)

        notebook.add(self.production_tab, text="Production")
        notebook.add(self.editing_tab, text="Editing")
        notebook.add(self.configuration_tab, text="Setting")


class ProductionTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Production").pack(pady=10)
        controls = ttk.Frame(self)
        controls.pack(pady=10)
        ttk.Button(controls, text="Play").grid(row=0, column=0, padx=5)
        ttk.Button(controls, text="Pause").grid(row=0, column=1, padx=5)
        ttk.Button(controls, text="Stop").grid(row=0, column=2, padx=5)


class EditingTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Editing").pack(pady=10)
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(frame, text="Audio file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse").grid(row=0, column=2)
        frame.columnconfigure(1, weight=1)


class ConfigurationTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Setting").pack(pady=10)
        container = ttk.Frame(self)
        container.pack(fill="both", padx=10, pady=10, expand=True)
        # Left/Right grouped sections (ordered left-to-right as requested)
        left = ttk.LabelFrame(container, text="Transmitions Setting")
        radio = ttk.LabelFrame(container, text="Radio Interface")
        right = ttk.LabelFrame(container, text="AMI")
        api = ttk.LabelFrame(container, text="API")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        radio.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        right.grid(row=0, column=2, sticky="nsew", padx=(0, 10))
        api.grid(row=0, column=3, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)
        container.rowconfigure(1, weight=1)

        self.tts_voice_id_var = tk.StringVar()
        self.tts_rate_var = tk.StringVar()
        self.tts_volume_var = tk.StringVar()
        self.tts_text_var = tk.StringVar()
        self.tts_provider_var = tk.StringVar()
        self.tts_format_var = tk.StringVar()
        self._tts_preview_files = None  # {'wav': path, 'mp3': path}
        self.azure_region_var = tk.StringVar()
        self.azure_key_var = tk.StringVar()
        # Voice language filters
        self.filter_es_var = tk.BooleanVar(value=True)
        self.filter_en_var = tk.BooleanVar(value=True)
        self.filter_all_var = tk.BooleanVar(value=True)

        tts = ttk.LabelFrame(container, text="TTS")
        tts.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

        # Provider / Format row
        ttk.Label(tts, text="Engine:").grid(row=0, column=0, sticky="w")
        self._tts_provider_options = [("windows", "Windows (offline)"), ("edge", "Microsoft Edge (online)"), ("gtts", "gTTS (online)"), ("azure", "Azure Speech (online)")]
        self.tts_provider_combo = ttk.Combobox(tts, state="readonly", values=[label for _code, label in self._tts_provider_options])
        self.tts_provider_combo.grid(row=0, column=1, sticky="ew", padx=5)
        self.tts_provider_combo.bind("<<ComboboxSelected>>", lambda _e=None: self.on_provider_change())

        ttk.Label(tts, text="Format:").grid(row=0, column=2, sticky="w")
        self.tts_format_combo = ttk.Combobox(tts, state="readonly", values=["wav", "mp3"])
        self.tts_format_combo.grid(row=0, column=3, sticky="ew", padx=5)

        # Voice row
        ttk.Label(tts, text="Voice:").grid(row=1, column=0, sticky="w")
        self.tts_voice_combo = ttk.Combobox(tts, state="readonly", values=[])
        self.tts_voice_combo.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(tts, text="Refresh", command=self.load_tts_voices, width=10).grid(row=1, column=2, padx=(5, 0))
        # Language filter checkboxes (ES / EN / ALL)
        langf = ttk.Frame(tts)
        langf.grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(langf, text="ES", variable=self.filter_es_var, command=self.on_lang_filter_change).pack(side="left", padx=(0,4))
        ttk.Checkbutton(langf, text="EN", variable=self.filter_en_var, command=self.on_lang_filter_change).pack(side="left", padx=(0,4))
        ttk.Checkbutton(langf, text="ALL", variable=self.filter_all_var, command=self.on_lang_filter_change).pack(side="left")

        # Rate/Volume row
        ttk.Label(tts, text="Rate:").grid(row=2, column=0, sticky="w")
        self.tts_rate_entry = tk.Entry(tts, textvariable=self.tts_rate_var)
        self.tts_rate_entry.grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Label(tts, text="Volume:").grid(row=2, column=2, sticky="w")
        self.tts_volume_entry = tk.Entry(tts, textvariable=self.tts_volume_var)
        self.tts_volume_entry.grid(row=2, column=3, sticky="ew", padx=5)

        # Text row
        ttk.Label(tts, text="Text:").grid(row=3, column=0, sticky="w")
        self.tts_text_entry = tk.Entry(tts, textvariable=self.tts_text_var)
        self.tts_text_entry.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=(0, 4))

        # Action
        ttk.Button(tts, text="Generate TTS", command=self.tts_generate, width=16).grid(row=4, column=0, pady=(4, 0))
        ttk.Button(tts, text="Preview", command=self.tts_preview, width=12).grid(row=4, column=1, pady=(4, 0))
        ttk.Button(tts, text="Stop", command=self.tts_stop, width=10).grid(row=4, column=2, pady=(4, 0))

        # Column expand for TTS
        tts.columnconfigure(1, weight=1)
        tts.columnconfigure(3, weight=1)

        # Azure config
        self.azure_frame = ttk.LabelFrame(tts, text="Azure Speech")
        # Inline within TTS, appears only when provider == 'azure'
        self.azure_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        
        # Region row
        ttk.Label(self.azure_frame, text="Region:").grid(row=0, column=0, sticky="w")
        self.azure_region_entry = tk.Entry(self.azure_frame, textvariable=self.azure_region_var)
        self.azure_region_entry.bind("<FocusOut>", lambda _e=None: self.on_azure_region_blur())
        self.azure_region_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # Key row with toggle button
        ttk.Label(self.azure_frame, text="Key:").grid(row=1, column=0, sticky="w")
        key_frame = ttk.Frame(self.azure_frame)
        key_frame.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)
        key_frame.columnconfigure(0, weight=1)
        
        self.azure_key_entry = tk.Entry(key_frame, textvariable=self.azure_key_var, show="*")
        self.azure_key_entry.grid(row=0, column=0, sticky="ew")
        
        # Toggle key visibility button
        self.show_key = False
        self.toggle_key_btn = ttk.Button(key_frame, text="", width=3, 
                                      command=self.toggle_key_visibility)
        self.toggle_key_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Load from .env if exists
        self.load_azure_from_env()
        
        self.azure_frame.columnconfigure(1, weight=1)
        ttk.Button(self.azure_frame, text="Save", command=self.save_settings, width=12).grid(row=2, column=0, columnspan=4, pady=(8, 0))

        self.ptt_var = tk.StringVar()
        self.pre_roll_var = tk.StringVar()
        self.pause_var = tk.StringVar()
        self.rewind_var = tk.StringVar()

        # Placeholder texts
        self.ptt_ph = "e.g. 240"
        self.pre_roll_ph = "e.g. 1"
        self.pause_ph = "e.g. 15"
        self.rewind_ph = "e.g. 4"

        ttk.Label(left, text="PTT Time (s):").grid(row=0, column=0, sticky="w")
        self.ptt_entry = tk.Entry(left, textvariable=self.ptt_var)
        self.ptt_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.add_placeholder(self.ptt_entry, self.ptt_var, self.ptt_ph)

        ttk.Label(left, text="Pre Roll Delay (s):").grid(row=1, column=0, sticky="w")
        self.pre_roll_entry = tk.Entry(left, textvariable=self.pre_roll_var)
        self.pre_roll_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.add_placeholder(self.pre_roll_entry, self.pre_roll_var, self.pre_roll_ph)

        ttk.Label(left, text="Pause (s):").grid(row=2, column=0, sticky="w")
        self.pause_entry = tk.Entry(left, textvariable=self.pause_var)
        self.pause_entry.grid(row=2, column=1, sticky="ew", padx=5)
        self.add_placeholder(self.pause_entry, self.pause_var, self.pause_ph)

        ttk.Label(left, text="Rewind Time (s):").grid(row=3, column=0, sticky="w")
        self.rewind_entry = tk.Entry(left, textvariable=self.rewind_var)
        self.rewind_entry.grid(row=3, column=1, sticky="ew", padx=5)
        self.add_placeholder(self.rewind_entry, self.rewind_var, self.rewind_ph)

        ttk.Button(left, text="Save", command=self.save_settings, width=12).grid(row=4, column=0, columnspan=3, pady=10)
        left.columnconfigure(1, weight=1)
        right.columnconfigure(1, weight=1)
        # Radio Interface UI (middle-left)
        radio.columnconfigure(1, weight=1)
        radio.columnconfigure(3, weight=1)

        # HID/CM108 state
        self.hid_devices = []
        self.hid_dev = None
        self.hid_ptt_state = False
        self._hid_poll_id = None
        # Radio config vars
        self.hid_vid_var = tk.StringVar()
        self.hid_pid_var = tk.StringVar()
        self.hid_ptt_bit_var = tk.StringVar()
        self.hid_cos_bit_var = tk.StringVar()
        self.hid_invert_cos_var = tk.BooleanVar(value=True)
        self.hid_invert_ptt_var = tk.BooleanVar(value=False)
        # API config vars
        self.api_base_url_var = tk.StringVar()
        self.api_ptt_on_path_var = tk.StringVar(value="/ptt_on")
        self.api_ptt_off_path_var = tk.StringVar(value="/ptt_off")

        ttk.Label(radio, text="Device:").grid(row=0, column=0, sticky="w")
        self.hid_device_combo = ttk.Combobox(radio, state="readonly", values=[])
        self.hid_device_combo.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(radio, text="Refresh", command=self.refresh_hid_devices, width=10).grid(row=0, column=2, padx=(5, 0))

        self.hid_cos_canvas = tk.Canvas(radio, width=14, height=14, highlightthickness=0, bd=0)
        self.hid_cos_canvas.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.hid_cos_dot = self.hid_cos_canvas.create_oval(2, 2, 12, 12, fill="#999999", outline="")
        self.hid_cos_var = tk.StringVar(value="COS: Unknown")
        self.hid_cos_label = ttk.Label(radio, textvariable=self.hid_cos_var)
        self.hid_cos_label.grid(row=1, column=1, sticky="w")

        # PTT status indicator just below COS
        self.hid_ptt_canvas = tk.Canvas(radio, width=14, height=14, highlightthickness=0, bd=0)
        self.hid_ptt_canvas.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.hid_ptt_dot = self.hid_ptt_canvas.create_oval(2, 2, 12, 12, fill="#999999", outline="")
        self.hid_ptt_var = tk.StringVar(value="PTT: OFF")
        self.hid_ptt_label = ttk.Label(radio, textvariable=self.hid_ptt_var)
        self.hid_ptt_label.grid(row=2, column=1, sticky="w")

        self.hid_connect_btn = ttk.Button(radio, text="Connect", command=self.toggle_hid_connection, width=12)
        self.hid_connect_btn.grid(row=3, column=0, pady=(6, 0))

        self.hid_ptt_btn = ttk.Button(radio, text="PTT OFF", command=self.hid_toggle_ptt, state="disabled", width=10)
        self.hid_ptt_btn.grid(row=3, column=1, pady=(6, 0))

        # Radio Interface config fields
        # Row 4: VID and PID on same line
        ttk.Label(radio, text="VID:").grid(row=4, column=0, sticky="w")
        self.hid_vid_entry = tk.Entry(radio, textvariable=self.hid_vid_var)
        self.hid_vid_entry.grid(row=4, column=1, sticky="ew", padx=5)
        ttk.Label(radio, text="PID:").grid(row=4, column=2, sticky="w")
        self.hid_pid_entry = tk.Entry(radio, textvariable=self.hid_pid_var)
        self.hid_pid_entry.grid(row=4, column=3, sticky="ew", padx=5)
        # Row 5: PTT Bit + Invert PTT
        ttk.Label(radio, text="PTT Bit:").grid(row=5, column=0, sticky="w")
        self.hid_ptt_bit_entry = tk.Entry(radio, textvariable=self.hid_ptt_bit_var)
        self.hid_ptt_bit_entry.grid(row=5, column=1, sticky="ew", padx=5)
        self.hid_invert_ptt_check = ttk.Checkbutton(radio, text="Invert PTT", variable=self.hid_invert_ptt_var)
        self.hid_invert_ptt_check.grid(row=5, column=2, columnspan=2, sticky="w")
        # Row 6: COS Bit + Invert COS
        ttk.Label(radio, text="COS Bit:").grid(row=6, column=0, sticky="w")
        self.hid_cos_bit_entry = tk.Entry(radio, textvariable=self.hid_cos_bit_var)
        self.hid_cos_bit_entry.grid(row=6, column=1, sticky="ew", padx=5)
        self.hid_invert_cos_check = ttk.Checkbutton(radio, text="Invert COS", variable=self.hid_invert_cos_var)
        self.hid_invert_cos_check.grid(row=6, column=2, columnspan=2, sticky="w")

        # Save button for Radio Interface
        self.radio_save_btn = ttk.Button(radio, text="Save", command=self.save_settings, width=12)
        self.radio_save_btn.grid(row=7, column=0, columnspan=4, pady=(8, 0))

        # AMI section (right)
        self.ami_host_var = tk.StringVar()
        self.ami_port_var = tk.StringVar()
        self.ami_user_var = tk.StringVar()
        self.ami_pass_var = tk.StringVar()

        ttk.Label(right, text="Host:").grid(row=0, column=0, sticky="w")
        self.ami_host_entry = tk.Entry(right, textvariable=self.ami_host_var)
        self.ami_host_entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(right, text="Port:").grid(row=1, column=0, sticky="w")
        self.ami_port_entry = tk.Entry(right, textvariable=self.ami_port_var)
        self.ami_port_entry.grid(row=1, column=1, sticky="ew", padx=5)

        ttk.Label(right, text="Username:").grid(row=2, column=0, sticky="w")
        self.ami_user_entry = tk.Entry(right, textvariable=self.ami_user_var)
        self.ami_user_entry.grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Label(right, text="Password:").grid(row=3, column=0, sticky="w")
        self.ami_pass_entry = tk.Entry(right, textvariable=self.ami_pass_var, show="*")
        self.ami_pass_entry.grid(row=3, column=1, sticky="ew", padx=5)
        # AMI status indicator (colored dot + text)
        self.ami_status_canvas = tk.Canvas(right, width=14, height=14, highlightthickness=0, bd=0)
        self.ami_status_canvas.grid(row=4, column=0, sticky="w")
        self.ami_status_dot = self.ami_status_canvas.create_oval(2, 2, 12, 12, fill="#999999", outline="")
        self.ami_status_var = tk.StringVar(value="Status: Unknown")
        self.ami_status_label = ttk.Label(right, textvariable=self.ami_status_var)
        self.ami_status_label.grid(row=4, column=1, sticky="w")

        # AMI buttons on same row below the status
        self.ami_test_btn = ttk.Button(right, text="Test Connection", command=self.test_ami_connection, width=16)
        self.ami_test_btn.grid(row=5, column=0, pady=(10, 4))
        self.ami_save_btn = ttk.Button(right, text="Save", command=self.save_settings, width=12)
        self.ami_save_btn.grid(row=5, column=1, pady=(10, 4))

        # API section (rightmost)
        api.columnconfigure(1, weight=1)
        ttk.Label(api, text="Base URL:").grid(row=0, column=0, sticky="w")
        self.api_base_url_entry = tk.Entry(api, textvariable=self.api_base_url_var)
        self.api_base_url_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(api, text="PTT ON Path:").grid(row=1, column=0, sticky="w")
        self.api_ptt_on_entry = tk.Entry(api, textvariable=self.api_ptt_on_path_var)
        self.api_ptt_on_entry.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(api, text="PTT OFF Path:").grid(row=2, column=0, sticky="w")
        self.api_ptt_off_entry = tk.Entry(api, textvariable=self.api_ptt_off_path_var)
        self.api_ptt_off_entry.grid(row=2, column=1, sticky="ew", padx=5)
        api_btns = ttk.Frame(api)
        api_btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        api_btns.columnconfigure(0, weight=1)
        api_btns.columnconfigure(1, weight=1)
        api_btns.columnconfigure(2, weight=1)
        ttk.Button(api_btns, text="Test API", command=self.test_api, width=16).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(api_btns, text="PTT ON", command=self.api_ptt_on, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(api_btns, text="PTT OFF", command=self.api_ptt_off, width=10).grid(row=0, column=2, padx=(4, 0))
        # Save button for API section
        self.api_save_btn = ttk.Button(api, text="Save", command=self.save_settings, width=12)
        self.api_save_btn.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        # Help label shown on focus/hover
        self.help_label = tk.Label(self, text="", fg="#666")
        self.help_label.pack(fill="x", padx=10, pady=(0, 10))

        # Attach contextual help
        self.attach_help(self.ptt_entry, "PTT Time: maximum continuous transmit time per cycle (seconds).")
        self.attach_help(self.pre_roll_entry, "Pre Roll Delay: wait after PTT ON before audio starts (seconds).")
        self.attach_help(self.pause_entry, "Pause: silence between play chunks while PTT is OFF (seconds).")
        self.attach_help(self.rewind_entry, "Rewind Time: audio rewind after each pause (seconds).")
        self.attach_help(self.ami_host_entry, "AMI host: Asterisk server address (IP or hostname).")
        self.attach_help(self.ami_port_entry, "AMI port: default 5038.")
        self.attach_help(self.ami_user_entry, "AMI username for Asterisk Manager Interface.")
        self.attach_help(self.ami_pass_entry, "AMI password for the username.")
        self.attach_help(self.hid_device_combo, "Select CM108-based USB audio adapter (C-Media).")
        self.attach_help(self.hid_ptt_btn, "Manual PTT: toggle GPIO output on CM108 (TX key).")
        self.attach_help(self.hid_cos_label, "COS/COR: carrier state read from CM108 GPIO input.")
        self.attach_help(self.hid_ptt_label, "Shows current PTT state (TX).")
        self.attach_help(self.hid_vid_entry, "VID: Vendor ID. Accepts decimal or hex like 0x0d8c.")
        self.attach_help(self.hid_pid_entry, "PID: Product ID. Accepts decimal or hex like 0x0012.")
        self.attach_help(self.hid_ptt_bit_entry, "PTT Bit: GPIO output bit mask (e.g., 0x01 or 0x08).")
        self.attach_help(self.hid_cos_bit_entry, "COS Bit: GPIO input bit mask (e.g., 0x02 or 0x04).")
        self.attach_help(self.hid_invert_cos_check, "Invert COS: if checked, inverts the logic of the COS bit.")
        self.attach_help(self.hid_invert_ptt_check, "Invert PTT: if checked, PTT ON drives a 0 and OFF drives a 1.")
        # API helps
        self.attach_help(self.api_base_url_entry, "API base URL, e.g. http://192.168.1.37")
        self.attach_help(self.api_ptt_on_entry, "Path for PTT ON endpoint, default /ptt_on")
        self.attach_help(self.api_ptt_off_entry, "Path for PTT OFF endpoint, default /ptt_off")
        self.attach_help(self.tts_provider_combo, "Choose TTS engine: Windows (offline) or Edge (online).")
        self.attach_help(self.tts_format_combo, "Audio format. Edge/Azure/gTTS use MP3, Windows uses WAV.")
        self.attach_help(self.tts_voice_combo, "Select TTS voice.")
        self.attach_help(self.tts_rate_entry, "TTS rate (e.g., 150).")
        self.attach_help(self.tts_volume_entry, "TTS volume 0.0 to 1.0.")
        self.attach_help(self.tts_text_entry, "Text to synthesize.")
        self.attach_help(self.azure_region_entry, "Azure Speech region, p.ej. southcentralus.")
        self.attach_help(self.azure_key_entry, "Azure Speech key (se guarda en cfg).")
        # TTS preview
        self.attach_help(tts, "Use Preview to listen without saving. Stop cancels playback.")

        self.load_settings()
        self.load_tts_voices()
        self.update_azure_visibility()
        # Initial HID enumeration
        self.refresh_hid_devices()

    def add_placeholder(self, entry: tk.Entry, var: tk.StringVar, placeholder: str):
        if not (var.get() or "").strip():
            var.set(placeholder)
            entry.config(fg="#888")

        def on_focus_in(event):
            if var.get() == placeholder:
                var.set("")
                entry.config(fg="#000")

        def on_focus_out(event):
            if not (var.get() or "").strip():
                var.set(placeholder)
                entry.config(fg="#888")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def attach_help(self, widget, text: str):
        def show(_evt=None):
            self.help_label.config(text=text)
        def clear(_evt=None):
            self.help_label.config(text="")
        widget.bind("<FocusIn>", show)
        widget.bind("<FocusOut>", clear)
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", clear)

    def normalize_azure_region(self, val: str) -> str:
        s = (val or "").strip()
        if not s:
            return s
        s = s.lower()
        host = s
        try:
            if "://" in s:
                host = urlparse(s).netloc or s
            # Strip any trailing slash
            if host.endswith("/"):
                host = host[:-1]
            if host.endswith('.api.cognitive.microsoft.com'):
                return host.split('.')[0]
            if host.endswith('.tts.speech.microsoft.com'):
                return host.split('.')[0]
        except Exception:
            pass
        return s

    def update_azure_visibility(self):
        try:
            prov = self.get_selected_provider()
            if prov == "azure":
                self.azure_frame.grid()
            else:
                self.azure_frame.grid_remove()
        except Exception:
            pass

    def on_azure_region_blur(self):
        try:
            reg = self.normalize_azure_region(self.azure_region_var.get())
            if reg and reg != (self.azure_region_var.get() or "").strip():
                self.azure_region_var.set(reg)
        except Exception:
            pass
            
    def toggle_key_visibility(self):
        """Toggle between showing and hiding the Azure key"""
        self.show_key = not self.show_key
        self.azure_key_entry.config(show="" if self.show_key else "*")
        self.toggle_key_btn.config(style="TButton" if self.show_key else "")
        
    def load_azure_from_env(self):
        """Load Azure credentials from .env file if they exist"""
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Forzar recarga del archivo .env
        
        # Solo cargar si los campos están vacíos o contienen valores por defecto
        current_region = (self.azure_region_var.get() or "").strip()
        current_key = (self.azure_key_var.get() or "").strip()
        
        # Cargar región si no hay una configurada o está marcada como (from .env)
        if not current_region or current_region == "(from .env)":
            region = os.getenv("AZURE_SPEECH_REGION")
            if region and region != "(from .env)":
                self.azure_region_var.set(region)
            
        # Cargar clave si no hay una configurada o está marcada como (from .env)
        if not current_key or current_key == "(from .env)":
            key = os.getenv("AZURE_SPEECH_KEY")
            if key and key != "(from .env)":
                # Guardar la clave real en la variable pero mostrar (from .env) en la interfaz
                self.azure_key_var.set(key)
                self.azure_key_entry.config(show="*")
                self.show_key = False
                # Guardar una referencia a la clave real
                self._azure_actual_key = key
                # Mostrar (from .env) en la interfaz
                self.after_idle(lambda: self.azure_key_var.set("(from .env)"))

    def set_ami_status(self, state: str, custom_text: str | None = None):
        colors = {
            "unknown": "#999999",
            "connecting": "#f39c12",
            "success": "#2ecc71",
            "failure": "#e74c3c",
        }
        texts = {
            "unknown": "Status: Unknown",
            "connecting": "Status: Connecting...",
            "success": "Status: Connected",
            "failure": "Status: Failed",
        }
        fill = colors.get(state, "#999999")
        self.ami_status_canvas.itemconfig(self.ami_status_dot, fill=fill)
        self.ami_status_var.set(custom_text or texts.get(state, "Status: Unknown"))

    # ---------------- Radio Interface (CM108) helpers ----------------

    def set_hid_cos_indicator(self, active: bool | None):
        if active is True:
            fill = "#2ecc71"; text = "COS: Active"
        elif active is False:
            fill = "#999999"; text = "COS: Inactive"
        else:
            fill = "#999999"; text = "COS: Unknown"
        self.hid_cos_canvas.itemconfig(self.hid_cos_dot, fill=fill)
        self.hid_cos_var.set(text)

    def set_hid_ptt_indicator(self, active: bool | None):
        if active is True:
            fill = "#e74c3c"; text = "PTT: ON"
        elif active is False:
            fill = "#999999"; text = "PTT: OFF"
        else:
            fill = "#999999"; text = "PTT: Unknown"
        self.hid_ptt_canvas.itemconfig(self.hid_ptt_dot, fill=fill)
        self.hid_ptt_var.set(text)

    def refresh_hid_devices(self):
        try:
            devices, labels = hid_enumerate_filtered()
            self.hid_devices = devices
            self.hid_device_combo["values"] = labels
            selected_idx = -1
            cfg_vid = parse_int(self.hid_vid_var.get(), None)
            cfg_pid = parse_int(self.hid_pid_var.get(), None)
            if cfg_vid is not None and cfg_pid is not None:
                for i, d in enumerate(devices):
                    if d.get("vendor_id") == cfg_vid and d.get("product_id") == cfg_pid:
                        selected_idx = i
                        break
            if labels:
                if selected_idx >= 0:
                    self.hid_device_combo.current(selected_idx)
                else:
                    self.hid_device_combo.current(0)
            else:
                self.hid_device_combo.set("")
        except Exception as e:
            messagebox.showerror("HID", f"Failed to enumerate HID devices: {e}")

    def toggle_hid_connection(self):
        if self.hid_dev:
            self.hid_disconnect()
        else:
            self.hid_connect_selected()

    def hid_connect_selected(self):
        if not self.hid_devices:
            self.refresh_hid_devices()
        idx = self.hid_device_combo.current()
        if idx is None or idx < 0 or idx >= len(self.hid_devices):
            messagebox.showerror("HID", "Select a CM108 device from the list.")
            return
        d = self.hid_devices[idx]
        try:
            dev = hid_open_device(d)
            self.hid_dev = dev
            self.hid_connect_btn.config(text="Disconnect")
            self.hid_ptt_btn.config(state="normal")
            self.set_hid_cos_indicator(None)
            self.set_hid_ptt_indicator(False)
            self.schedule_hid_poll()
        except Exception as e:
            self.hid_dev = None
            messagebox.showerror("HID", f"Failed to open device: {e}")

    def hid_disconnect(self):
        if self._hid_poll_id:
            try:
                self.after_cancel(self._hid_poll_id)
            except Exception:
                pass
            self._hid_poll_id = None
        if self.hid_dev:
            try:
                # Ensure PTT is released
                ptt_bit = parse_int(self.hid_ptt_bit_var.get(), 0x01)
                backend_hid_set_ptt(self.hid_dev, ptt_bit, False, bool(self.hid_invert_ptt_var.get()))
            except Exception:
                pass
            try:
                hid_close_device(self.hid_dev)
            except Exception:
                pass
            self.hid_dev = None
        self.hid_connect_btn.config(text="Connect")
        self.hid_ptt_btn.config(state="disabled", text="PTT OFF")
        self.hid_ptt_state = False
        self.set_hid_cos_indicator(None)
        self.set_hid_ptt_indicator(False)

    def hid_set_ptt(self, state: bool):
        if not self.hid_dev:
            return
        try:
            ptt_bit = parse_int(self.hid_ptt_bit_var.get(), 0x01)
            ok = backend_hid_set_ptt(self.hid_dev, ptt_bit, bool(state), bool(self.hid_invert_ptt_var.get()))
            if not ok:
                raise RuntimeError("Backend hid_set_ptt() returned False")
            self.hid_ptt_state = state
            self.hid_ptt_btn.config(text=f"PTT {'ON' if state else 'OFF'}")
            self.set_hid_ptt_indicator(state)
        except Exception as e:
            messagebox.showerror("HID", f"Failed to set PTT: {e}")

    # ---------------- API helpers ----------------
    def test_api(self):
        base = (self.api_base_url_var.get() or "").strip()
        if not base:
            messagebox.showerror("API", "Please set Base URL in the API section.")
            return
        url = api_join(base, "/openapi.json")
        try:
            code, _ = api_get(url, timeout=5.0)
            if 200 <= code < 300:
                messagebox.showinfo("API", f"OK: {url} responded with {code}")
            else:
                messagebox.showerror("API", f"Unexpected status {code} for {url}")
        except Exception as e:
            messagebox.showerror("API", f"Request failed: {e}")

    def api_ptt_on(self):
        base = (self.api_base_url_var.get() or "").strip()
        path = (self.api_ptt_on_path_var.get() or "/ptt_on").strip()
        if not base:
            messagebox.showerror("API", "Please set Base URL.")
            return
        try:
            code, _ = api_get(api_join(base, path), timeout=5.0)
            if 200 <= code < 300:
                messagebox.showinfo("API", "PTT ON sent.")
            else:
                messagebox.showerror("API", f"PTT ON failed with status {code}.")
        except Exception as e:
            messagebox.showerror("API", f"PTT ON error: {e}")

    def api_ptt_off(self):
        base = (self.api_base_url_var.get() or "").strip()
        path = (self.api_ptt_off_path_var.get() or "/ptt_off").strip()
        if not base:
            messagebox.showerror("API", "Please set Base URL.")
            return
        try:
            code, _ = api_get(api_join(base, path), timeout=5.0)
            if 200 <= code < 300:
                messagebox.showinfo("API", "PTT OFF sent.")
            else:
                messagebox.showerror("API", f"PTT OFF failed with status {code}.")
        except Exception as e:
            messagebox.showerror("API", f"PTT OFF error: {e}")

    def hid_toggle_ptt(self):
        self.hid_set_ptt(not self.hid_ptt_state)

    def schedule_hid_poll(self):
        if self._hid_poll_id:
            try:
                self.after_cancel(self._hid_poll_id)
            except Exception:
                pass
        self._hid_poll_id = self.after(200, self.hid_poll_once)

    def hid_poll_once(self):
        if not self.hid_dev:
            return
        cos_active = None
        try:
            cos_bit = parse_int(self.hid_cos_bit_var.get(), 0x02)
            cos_active = hid_read_cos(self.hid_dev, cos_bit, bool(self.hid_invert_cos_var.get()))
        except Exception:
            cos_active = None
        self.set_hid_cos_indicator(cos_active)
        self.schedule_hid_poll()

    def get_selected_provider(self) -> str:
        try:
            idx = self.tts_provider_combo.current()
            if idx is None or idx < 0:
                return "windows"
            return self._tts_provider_options[idx][0]
        except Exception:
            return "windows"

    def set_provider_combo_from_code(self, code: str):
        code = (code or "windows").lower()
        idx = 0
        for i, (c, _label) in enumerate(self._tts_provider_options):
            if c == code:
                idx = i
                break
        try:
            self.tts_provider_combo.current(idx)
        except Exception:
            pass

    def update_tts_format_for_provider(self):
        prov = self.get_selected_provider()
        if prov in ("edge", "gtts", "azure"):
            self.tts_format_var.set("mp3")
            try:
                self.tts_format_combo.set("mp3")
                self.tts_format_combo.config(state="disabled")
            except Exception:
                pass
        else:
            self.tts_format_var.set("wav")
            try:
                self.tts_format_combo.set("wav")
                self.tts_format_combo.config(state="disabled")
            except Exception:
                pass

    def on_provider_change(self):
        self.update_tts_format_for_provider()
        self.load_tts_voices()
        self.update_azure_visibility()

    def on_lang_filter_change(self):
        try:
            if self.filter_all_var.get():
                # When ALL is on, ES/EN are ignored
                pass
            self.load_tts_voices()
        except Exception:
            pass

    def load_tts_voices(self):
        try:
            provider = self.get_selected_provider()
            if provider == "azure":
                # set env for backend convenience (optional)
                try:
                    reg = self.normalize_azure_region(self.azure_region_var.get())
                    if reg:
                        self.azure_region_var.set(reg)
                        os.environ["AZURE_SPEECH_REGION"] = reg
                    if (self.azure_key_var.get() or "").strip():
                        os.environ["AZURE_SPEECH_KEY"] = (self.azure_key_var.get() or "").strip()
                except Exception:
                    pass
            voices = tts_list_voices(provider)
            # Apply language filters
            try:
                show_all = bool(self.filter_all_var.get())
                show_es = bool(self.filter_es_var.get())
                show_en = bool(self.filter_en_var.get())
                if not show_all and not show_es and not show_en:
                    show_all = True  # nothing selected => show all
                if not show_all:
                    filtered = []
                    for v in voices or []:
                        try:
                            vid = (v.get('id') or '').lower()
                            langs = [str(x).lower() for x in (v.get('languages') or [])]
                            is_es = ('spanish' in vid) or vid.startswith('es-') or any(x.startswith('es') for x in langs)
                            is_en = ('english' in vid) or vid.startswith('en-') or any(x.startswith('en') for x in langs)
                            if (show_es and is_es) or (show_en and is_en):
                                filtered.append(v)
                        except Exception:
                            continue
                    voices = filtered
            except Exception:
                pass
        except Exception:
            voices = []
        self._tts_voices = voices
        labels = []
        selected = -1
        want_id = (self.tts_voice_id_var.get() or "").strip()
        for i, v in enumerate(voices):
            label = f"{v.get('name','')} ({v.get('id','')})".strip()
            labels.append(label)
            if want_id and v.get('id', '') == want_id:
                selected = i
        self.tts_voice_combo["values"] = labels
        if labels:
            if selected >= 0:
                self.tts_voice_combo.current(selected)
            else:
                self.tts_voice_combo.current(0)
        else:
            self.tts_voice_combo.set("")

    def tts_generate(self):
        text = (self.tts_text_var.get() or "").strip()
        if not text:
            messagebox.showerror("TTS", "Enter text to synthesize.")
            return
        provider = self.get_selected_provider()
        if provider in ("edge", "gtts", "azure"):
            defext = ".mp3"; ftypes = [("MP3", "*.mp3"), ("All files", "*.*")]
        else:
            defext = ".wav"; ftypes = [("WAV", "*.wav"), ("All files", "*.*")]
        path = filedialog.asksaveasfilename(defaultextension=defext, filetypes=ftypes)
        if not path:
            return
        voice_id = None
        try:
            idx = self.tts_voice_combo.current()
            if hasattr(self, "_tts_voices") and self._tts_voices and idx is not None and idx >= 0 and idx < len(self._tts_voices):
                voice_id = self._tts_voices[idx].get("id", "") or None
        except Exception:
            voice_id = None
        rate = None
        volume = None
        r = (self.tts_rate_var.get() or "").strip()
        if r:
            try:
                rate = int(r)
            except Exception:
                rate = None
        v = (self.tts_volume_var.get() or "").strip()
        if v:
            try:
                volume = float(v)
            except Exception:
                volume = None
        try:
            try:
                tts_synthesize(text, path, voice_id=voice_id, rate=rate, volume=volume, provider=provider)
            except Exception as se:
                s = str(se) if se else ""
                if provider == "edge" and ("401" in s or "Unauthorized" in s or "WSServerHandshakeError" in s or "Edge synthesis failed" in s):
                    # Auto fallback to gTTS
                    gtts_voice = None
                    try:
                        if isinstance(voice_id, str) and voice_id.lower().startswith("es-"):
                            gtts_voice = "es-us" if "-us" in voice_id.lower() else "es"
                    except Exception:
                        gtts_voice = None
                    if not gtts_voice:
                        gtts_voice = "es"
                    tts_synthesize(text, path, voice_id=gtts_voice, rate=None, volume=None, provider="gtts")
                    messagebox.showwarning("TTS", "Edge TTS falló (401). Se usó gTTS para generar el archivo.")
                else:
                    raise se
            messagebox.showinfo("TTS", f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("TTS", f"Failed to synthesize: {e}")

    def _cleanup_preview_files(self):
        try:
            if isinstance(self._tts_preview_files, dict):
                for k in list(self._tts_preview_files.keys()):
                    p = self._tts_preview_files.get(k)
                    if p and os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
        finally:
            self._tts_preview_files = None

    def _mci_send(self, cmd: str):
        try:
            ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
        except Exception:
            pass

    def tts_stop(self):
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        # Stop/close any MCI playback
        try:
            self._mci_send('stop hamna_preview')
            self._mci_send('close hamna_preview')
        except Exception:
            pass
        # Keep files for replay, don't delete on stop

    def tts_preview(self):
        text = (self.tts_text_var.get() or "").strip()
        if not text:
            messagebox.showerror("TTS", "Enter text to synthesize.")
            return
        provider = self.get_selected_provider()
        # Build temp paths
        tmpdir = tempfile.gettempdir()
        wav_path = os.path.join(tmpdir, "hamna_tts_preview.wav")
        mp3_path = os.path.join(tmpdir, "hamna_tts_preview.mp3")
        # Remove previous files
        try:
            for p in (wav_path, mp3_path):
                if os.path.exists(p):
                    os.remove(p)
        except Exception:
            pass
        # Params
        voice_id = None
        try:
            idx = self.tts_voice_combo.current()
            if hasattr(self, "_tts_voices") and self._tts_voices and idx is not None and idx >= 0 and idx < len(self._tts_voices):
                voice_id = self._tts_voices[idx].get("id", "") or None
        except Exception:
            voice_id = None
        rate = None
        volume = None
        r = (self.tts_rate_var.get() or "").strip()
        if r:
            try:
                rate = int(r)
            except Exception:
                rate = None
        v = (self.tts_volume_var.get() or "").strip()
        if v:
            try:
                volume = float(v)
            except Exception:
                volume = None
        try:
            if provider in ("edge", "gtts", "azure"):
                ok = False
                try:
                    tts_synthesize(text, mp3_path, voice_id=voice_id, rate=rate, volume=volume, provider=provider)
                    ok = True
                except Exception as se:
                    s = str(se) if se else ""
                    if provider == "edge" and ("401" in s or "Unauthorized" in s or "WSServerHandshakeError" in s):
                        gtts_voice = None
                        try:
                            if isinstance(voice_id, str) and voice_id.lower().startswith("es-"):
                                gtts_voice = "es-us" if "-us" in voice_id.lower() else "es"
                        except Exception:
                            gtts_voice = None
                        if not gtts_voice:
                            gtts_voice = "es"
                        try:
                            tts_synthesize(text, mp3_path, voice_id=gtts_voice, rate=None, volume=None, provider="gtts")
                            messagebox.showwarning("TTS", "Edge TTS falló (401). Usando gTTS para la previsualización.")
                            ok = True
                            provider = "gtts"
                        except Exception as se2:
                            raise se2
                    else:
                        raise se
                if ok:
                    try:
                        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception as conv_e:
                        try:
                            self._mci_send('stop hamna_preview')
                            self._mci_send('close hamna_preview')
                            self._mci_send(f'open "{mp3_path}" type mpegvideo alias hamna_preview')
                            self._mci_send('play hamna_preview')
                            self._tts_preview_files = {"wav": None, "mp3": mp3_path}
                            return
                        except Exception:
                            messagebox.showerror("TTS", f"Failed to convert MP3 to WAV for preview (ffmpeg required) and direct MP3 playback failed: {conv_e}")
                            return
            else:
                tts_synthesize(text, wav_path, voice_id=voice_id, rate=rate, volume=volume, provider=provider)
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self._tts_preview_files = {"wav": wav_path, "mp3": (mp3_path if provider in ("edge", "gtts", "azure") else None)}
        except Exception as e:
            messagebox.showerror("TTS", f"Preview failed: {e}")

    def load_settings(self):
        # Primero cargar desde .env solo las credenciales de Azure
        self.load_azure_from_env()
        
        # Luego cargar desde cfg.yaml
        data, used_path = read_cfg()
        if not data:
            return
            
        if used_path and used_path.endswith("cfg.yml"):
            # Código existente para manejar cfg.yml
            dur = (data.get("duraciones") or {})
            self.pause_var.set(str(dur.get("pausa", "")))
            self.rewind_var.set(str(dur.get("retroceso", "")))
            self.ptt_var.set("")
            self.pre_roll_var.set("")
            ami = data.get("ami", {})
            self.ami_host_var.set(str(ami.get("host", "")))
            self.ami_port_var.set(str(ami.get("port", "")))
            self.ami_user_var.set(str(ami.get("username", "")))
            self.ami_pass_var.set(str(ami.get("password", "")))
            self.refresh_placeholder_visuals()
            return
            
        # Cargar ajustes generales
        settings = data.get("settings", {})
        self.ptt_var.set(str(settings.get("ptt_time", "")))
        self.pre_roll_var.set(str(settings.get("pre_roll_delay", "")))
        self.pause_var.set(str(settings.get("pause", "")))
        self.rewind_var.set(str(settings.get("rewind_time", "")))
        
        # Cargar configuración AMI
        ami = data.get("ami", {})
        self.ami_host_var.set(str(ami.get("host", "")))
        self.ami_port_var.set(str(ami.get("port", "")))
        self.ami_user_var.set(str(ami.get("username", "")))
        self.ami_pass_var.set(str(ami.get("password", "")))
        
        # Cargar configuración de radio
        radio = data.get("radio_interface") or data.get("radio") or {}
        def set_hex_or_str(var, value, width=4):
            if value is None or value == "":
                return
            try:
                iv = int(value) if isinstance(value, int) else int(str(value), 0)
                var.set(f"0x{iv:0{width}x}")
            except Exception:
                var.set(str(value))
                
        set_hex_or_str(self.hid_vid_var, radio.get("vid"), 4)
        set_hex_or_str(self.hid_pid_var, radio.get("pid"), 4)
        set_hex_or_str(self.hid_ptt_bit_var, radio.get("ptt_bit"), 2)
        set_hex_or_str(self.hid_cos_bit_var, radio.get("cos_bit"), 2)
        
        inv = radio.get("invert_cos")
        if isinstance(inv, bool):
            self.hid_invert_cos_var.set(inv)
        invp = radio.get("invert_ptt")
        if isinstance(invp, bool):
            self.hid_invert_ptt_var.set(invp)
            
        # Cargar configuración de API
        api_cfg = data.get("api", {})
        self.api_base_url_var.set(str(api_cfg.get("base_url", "")))
        self.api_ptt_on_path_var.set(str(api_cfg.get("ptt_on_path", "/ptt_on")))
        self.api_ptt_off_path_var.set(str(api_cfg.get("ptt_off_path", "/ptt_off")))
        
        # Cargar configuración de TTS
        tts_cfg = data.get("tts", {})
        self.tts_voice_id_var.set(str(tts_cfg.get("voice_id", "")))
        self.tts_rate_var.set(str(tts_cfg.get("rate", "")))
        self.tts_volume_var.set(str(tts_cfg.get("volume", "")))
        
        # Establecer el proveedor de TTS
        provider_code = str(tts_cfg.get("provider", "windows")).lower()
        self.set_provider_combo_from_code(provider_code)
        
        # Establecer el formato de salida
        fmt = str(tts_cfg.get("format", "mp3" if provider_code in ("edge", "gtts", "azure") else "wav"))
        try:
            self.tts_format_var.set(fmt)
            self.tts_format_combo.set(fmt)
        except Exception:
            pass
            
        self.update_tts_format_for_provider()
        
        # No cargar configuración de Azure desde cfg.yaml si ya se cargó desde .env
        current_region = (self.azure_region_var.get() or "").strip()
        current_key = (self.azure_key_var.get() or "").strip()
        
        # Solo cargar desde cfg.yaml si no hay valores de .env
        if not current_region or current_region == "(from .env)":
            azure_cfg = tts_cfg.get("azure", {}) or {}
            azure_region = tts_cfg.get("azure_region") or azure_cfg.get("region", "")
            if azure_region and azure_region != "(from .env)":
                self.azure_region_var.set(str(azure_region))
                
        if not current_key or current_key == "(from .env)":
            azure_cfg = tts_cfg.get("azure", {}) or {}
            azure_key = tts_cfg.get("azure_key") or azure_cfg.get("key", "")
            if azure_key and azure_key != "(from .env)":
                self.azure_key_var.set(str(azure_key))
        
        self.refresh_placeholder_visuals()

    def refresh_placeholder_visuals(self):
        fields = [
            (self.ptt_entry, self.ptt_var, self.ptt_ph),
            (self.pre_roll_entry, self.pre_roll_var, self.pre_roll_ph),
            (self.pause_entry, self.pause_var, self.pause_ph),
            (self.rewind_entry, self.rewind_var, self.rewind_ph),
        ]
        for entry, var, ph in fields:
            val = (var.get() or "").strip()
            if not val or val == ph:
                var.set(ph)
                entry.config(fg="#888")
            else:
                entry.config(fg="#000")

    def save_settings(self):
        try:
            ptt = int(self.ptt_var.get() or 0)
            pre = int(self.pre_roll_var.get() or 0)
            pause = int(self.pause_var.get() or 0)
            rewind = int(self.rewind_var.get() or 0)
            ami_port = int(self.ami_port_var.get() or 0) if (self.ami_port_var.get() or "").strip() else ""
            tts_rate = int(self.tts_rate_var.get() or 0) if (self.tts_rate_var.get() or "").strip() else ""
            tts_volume = float(self.tts_volume_var.get() or 0) if (self.tts_volume_var.get() or "").strip() else ""
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values.")
            return
        # Parse radio interface numbers (hex or decimal accepted)
        vid_val = parse_int(self.hid_vid_var.get(), None)
        pid_val = parse_int(self.hid_pid_var.get(), None)
        ptt_bit_val = parse_int(self.hid_ptt_bit_var.get(), None)
        cos_bit_val = parse_int(self.hid_cos_bit_var.get(), None)
        invert_val = bool(self.hid_invert_cos_var.get())
        try:
            provider_code = self.get_selected_provider()
            cfg_path = save_cfg(
                settings={
                    "ptt_time": ptt,
                    "pre_roll_delay": pre,
                    "pause": pause,
                    "rewind_time": rewind,
                },
                ami={
                    "host": (self.ami_host_var.get() or ""),
                    "port": ami_port,
                    "username": (self.ami_user_var.get() or ""),
                    "password": (self.ami_pass_var.get() or ""),
                },
                radio={
                    "vid": vid_val if vid_val is not None else "",
                    "pid": pid_val if pid_val is not None else "",
                    "ptt_bit": ptt_bit_val if ptt_bit_val is not None else "",
                    "cos_bit": cos_bit_val if cos_bit_val is not None else "",
                    "invert_cos": invert_val,
                    "invert_ptt": bool(self.hid_invert_ptt_var.get()),
                },
                api={
                    "base_url": (self.api_base_url_var.get() or ""),
                    "ptt_on_path": (self.api_ptt_on_path_var.get() or "/ptt_on"),
                    "ptt_off_path": (self.api_ptt_off_path_var.get() or "/ptt_off"),
                },
                tts={
                    "voice_id": (self._tts_voices[self.tts_voice_combo.current()].get("id", "") if hasattr(self, "_tts_voices") and self._tts_voices and isinstance(self.tts_voice_combo.current(), int) and 0 <= self.tts_voice_combo.current() < len(self._tts_voices) else ""),
                    "rate": tts_rate,
                    "volume": tts_volume,
                    "provider": provider_code,
                    "format": ("mp3" if provider_code in ("edge", "gtts", "azure") else "wav"),
                    # No guardar credenciales en cfg.yaml, solo en .env
                    "azure_region": "(from .env)",
                    "azure_key": "(from .env)",
                },
            )
            # Save Azure credentials to .env file
            try:
                if provider_code == "azure":
                    # Get the values from the UI
                    region = self.normalize_azure_region(self.azure_region_var.get())
                    # Si el campo muestra "(from .env)", usar la clave guardada, de lo contrario usar la del campo
                    key = getattr(self, '_azure_actual_key', '') if self.azure_key_var.get() == "(from .env)" else (self.azure_key_var.get() or "")
                    
                    # Read existing .env file if it exists
                    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
                    env_lines = []
                    region_exists = False
                    key_exists = False
                    
                    if os.path.exists(env_path):
                        with open(env_path, 'r') as f:
                            env_lines = f.readlines()
                    
                    # Update or add AZURE_SPEECH_REGION
                    new_lines = []
                    for line in env_lines:
                        if line.strip().startswith('AZURE_SPEECH_REGION='):
                            new_lines.append(f'AZURE_SPEECH_REGION={region}\n')
                            region_exists = True
                        elif line.strip().startswith('AZURE_SPEECH_KEY='):
                            new_lines.append(f'AZURE_SPEECH_KEY={key}\n')
                            key_exists = True
                        else:
                            new_lines.append(line)
                    
                    # Add missing entries - solo si hay valores para guardar
                    if not region_exists and region and region != "(from .env)":
                        new_lines.append(f'AZURE_SPEECH_REGION={region}\n')
                    if not key_exists and key and key != "(from .env)":
                        new_lines.append(f'AZURE_SPEECH_KEY={key}\n')
                    
                    # Write back to .env file
                    with open(env_path, 'w') as f:
                        f.writelines(new_lines)
                    
                    # Update environment variables for current session
                    if region and region != "(from .env)":
                        os.environ["AZURE_SPEECH_REGION"] = region
                    if key and key != "(from .env)":
                        os.environ["AZURE_SPEECH_KEY"] = key
                        
                    # Update the UI to show (from .env) if we just saved the key
                    if key and self.azure_key_var.get() != "(from .env)":
                        self._azure_actual_key = key
                        self.azure_key_var.set("(from .env)")
                        self.azure_key_entry.config(show="*")
                        self.show_key = False
                        
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save Azure credentials: {str(e)}")
            messagebox.showinfo("Saved", f"Settings saved to {os.path.basename(cfg_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def test_ami_connection(self):
        host = (self.ami_host_var.get() or "").strip()
        port_s = (self.ami_port_var.get() or "").strip()
        user = (self.ami_user_var.get() or "").strip()
        password = (self.ami_pass_var.get() or "").strip()
        self.set_ami_status("connecting")
        self.update_idletasks()
        if not host or not port_s or not user or not password:
            messagebox.showerror("Error", "Please fill host, port, username and password.")
            self.set_ami_status("failure", "Status: Missing fields")
            return
        try:
            port = int(port_s)
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            self.set_ami_status("failure", "Status: Invalid port")
            return
        ok, detail = ami_test_connection(host, port, user, password)
        if ok:
            self.set_ami_status("success")
            messagebox.showinfo("AMI", "Connection successful.")
        else:
            self.set_ami_status("failure")
            messagebox.showerror("AMI", f"Connection failed. Detail:\n{detail}")


if __name__ == "__main__":
    app = HamnaApp()
    app.mainloop()
