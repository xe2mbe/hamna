import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import os
from pathlib import Path

class ConfigTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config_file = Path("config/cfg.yaml")
        self.config = self.load_config()
        self.connected = False
        self.ptt_state = False
        self.cos_state = False
        self.setup_ui()
        
    def load_config(self):
        """Load configuration from YAML file"""
        default_config = {
            'transmitting': {
                'ptt_time': 0.5,
                'pre_roll_delay': 0.5,
                'pause': 1.0,
                'rewind': 0.5
            },
            'radio': {
                'device': '',
                'vid': '0x16c0',
                'pid': '0x05dc',
                'ptt_bit': '0',
                'cos_bit': '1',
                'invert_ptt': False,
                'invert_cos': False
            }
        }
        
        # Create config directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    # Merge with default config to ensure all keys exist
                    return {**default_config, **config}
            except Exception as e:
                messagebox.showerror("Error", f"Error loading config: {e}")
        
        # If file doesn't exist or error loading, return default config
        return default_config
        
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error saving config: {e}")
            return False
    
    def setup_ui(self):
        """Set up the configuration tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different configuration sections
        config_notebook = ttk.Notebook(main_frame)
        config_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Radio Interface Tab
        radio_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_radio_interface(radio_frame)
        config_notebook.add(radio_frame, text="Radio Interface")
        
        # Transmitting Settings Tab
        transmitting_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_transmitting_settings(transmitting_frame)
        config_notebook.add(transmitting_frame, text="Transmitting")
        
        # General Settings Tab
        general_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_general_settings(general_frame)
        config_notebook.add(general_frame, text="General")
        
        # Audio Settings Tab has been removed
        
        # Database Settings Tab
        db_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_database_settings(db_frame)
        config_notebook.add(db_frame, text="Base de Datos")
        
        # Save/Cancel Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Guardar", command=self.save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.cancel_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Aplicar", command=self.apply_changes).pack(side=tk.RIGHT, padx=5)
    
    def setup_transmitting_settings(self, parent):
        """Set up transmitting settings section"""
        # Create a frame for better organization
        frame = ttk.LabelFrame(parent, text="Transmitting Settings", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # PTT Time
        ttk.Label(frame, text="PTT Time (s):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.ptt_time_var = tk.DoubleVar(value=self.config['transmitting']['ptt_time'])
        ttk.Spinbox(
            frame,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.ptt_time_var,
            width=10
        ).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Pre Roll Delay
        ttk.Label(frame, text="Pre Roll Delay (s):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.pre_roll_delay_var = tk.DoubleVar(value=self.config['transmitting']['pre_roll_delay'])
        ttk.Spinbox(
            frame,
            from_=0.0,
            to=5.0,
            increment=0.1,
            textvariable=self.pre_roll_delay_var,
            width=10
        ).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Pause
        ttk.Label(frame, text="Pause (s):").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.pause_var = tk.DoubleVar(value=self.config['transmitting']['pause'])
        ttk.Spinbox(
            frame,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.pause_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Rewind
        ttk.Label(frame, text="Rewind (s):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.rewind_var = tk.DoubleVar(value=self.config['transmitting']['rewind'])
        ttk.Spinbox(
            frame,
            from_=0.0,
            to=5.0,
            increment=0.1,
            textvariable=self.rewind_var,
            width=10
        ).grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Save button
        save_btn = ttk.Button(
            frame,
            text="Save",
            command=self.save_transmitting_settings,
            width=15
        )
        save_btn.grid(row=4, column=0, columnspan=2, pady=15)
    
    def setup_radio_interface(self, parent):
        """Set up radio interface section"""
        # Main frame with padding
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Device selection
        ttk.Label(main_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            main_frame,
            textvariable=self.device_var,
            state="readonly",
            width=40
        )
        self.device_combo.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        # Status indicators frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # COS status
        ttk.Label(status_frame, text="COS:").grid(row=0, column=0, padx=5)
        self.cos_status = ttk.Label(status_frame, text="OFF", foreground="red")
        self.cos_status.grid(row=0, column=1, padx=5)
        
        # PTT status
        ttk.Label(status_frame, text="PTT:").grid(row=0, column=2, padx=5)
        self.ptt_status = ttk.Label(status_frame, text="OFF", foreground="red")
        self.ptt_status.grid(row=0, column=3, padx=5)
        
        # Connection status
        self.connection_status = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.connection_status.grid(row=0, column=4, padx=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.ptt_btn = ttk.Button(btn_frame, text="PTT ON", command=self.toggle_ptt, state=tk.DISABLED)
        self.ptt_btn.pack(side=tk.LEFT, padx=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Device Configuration", padding=10)
        config_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # VID
        ttk.Label(config_frame, text="VID:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=5)
        self.vid_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.vid_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        # PID
        ttk.Label(config_frame, text="PID:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=5)
        self.pid_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.pid_var, width=10).grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)
        
        # PTT Bit
        ttk.Label(config_frame, text="PTT Bit:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.ptt_bit_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.ptt_bit_var, width=5).grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # COS Bit
        ttk.Label(config_frame, text="COS Bit:").grid(row=1, column=2, sticky=tk.W, pady=2, padx=5)
        self.cos_bit_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.cos_bit_var, width=5).grid(row=1, column=3, sticky=tk.W, pady=2, padx=5)
        
        # Checkboxes frame
        check_frame = ttk.Frame(config_frame)
        check_frame.grid(row=2, column=0, columnspan=4, pady=5)
        
        # Invert PTT
        self.invert_ptt_var = tk.BooleanVar()
        ttk.Checkbutton(
            check_frame,
            text="Invert PTT",
            variable=self.invert_ptt_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Invert COS
        self.invert_cos_var = tk.BooleanVar()
        ttk.Checkbutton(
            check_frame,
            text="Invert COS",
            variable=self.invert_cos_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Save button
        save_btn = ttk.Button(
            main_frame,
            text="Save Configuration",
            command=self.save_radio_config,
            width=20
        )
        save_btn.grid(row=4, column=0, columnspan=3, pady=10)
        
        # Load saved configuration
        self.load_radio_config()
        
        # Simulate device detection (in a real app, this would scan for actual devices)
        self.device_combo['values'] = ["DigiRig", "CM108", "Other Device"]
        if self.device_combo['values']:
            self.device_combo.current(0)
    
    def toggle_connection(self):
        """Toggle connection to the radio device"""
        if not self.connected:
            # Try to connect
            if self.connect_radio():
                self.connected = True
                self.connect_btn.config(text="Disconnect")
                self.ptt_btn.config(state=tk.NORMAL)
                self.connection_status.config(text="Connected", foreground="green")
        else:
            # Disconnect
            self.disconnect_radio()
            self.connected = False
            self.connect_btn.config(text="Connect")
            self.ptt_btn.config(state=tk.DISABLED)
            self.ptt_btn.config(text="PTT ON")
            self.ptt_state = False
            self.ptt_status.config(text="OFF", foreground="red")
            self.connection_status.config(text="Disconnected", foreground="red")
    
    def toggle_ptt(self):
        """Toggle PTT state"""
        self.ptt_state = not self.ptt_state
        if self.ptt_state:
            self.ptt_btn.config(text="PTT OFF")
            self.ptt_status.config(text="ON", foreground="green")
            # Here you would send PTT ON command to the device
        else:
            self.ptt_btn.config(text="PTT ON")
            self.ptt_status.config(text="OFF", foreground="red")
            # Here you would send PTT OFF command to the device
    
    def connect_radio(self):
        """Connect to the radio device"""
        # In a real implementation, this would connect to the actual hardware
        # For now, we'll just simulate a successful connection
        return True
    
    def disconnect_radio(self):
        """Disconnect from the radio device"""
        # In a real implementation, this would properly close the connection
        pass
    
    def load_radio_config(self):
        """Load radio configuration from config"""
        if 'radio' in self.config:
            radio_cfg = self.config['radio']
            self.vid_var.set(radio_cfg.get('vid', ''))
            self.pid_var.set(radio_cfg.get('pid', ''))
            self.ptt_bit_var.set(radio_cfg.get('ptt_bit', ''))
            self.cos_bit_var.set(radio_cfg.get('cos_bit', ''))
            self.invert_ptt_var.set(radio_cfg.get('invert_ptt', False))
            self.invert_cos_var.set(radio_cfg.get('invert_cos', False))
            
            # Select the device if it exists in the config
            if 'device' in radio_cfg and radio_cfg['device'] in self.device_combo['values']:
                self.device_combo.set(radio_cfg['device'])
    
    def save_radio_config(self):
        """Save radio configuration to config"""
        try:
            self.config['radio'] = {
                'device': self.device_var.get(),
                'vid': self.vid_var.get(),
                'pid': self.pid_var.get(),
                'ptt_bit': self.ptt_bit_var.get(),
                'cos_bit': self.cos_bit_var.get(),
                'invert_ptt': self.invert_ptt_var.get(),
                'invert_cos': self.invert_cos_var.get()
            }
            
            if self.save_config():
                messagebox.showinfo("Success", "Radio configuration saved successfully!")
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save radio configuration: {e}")
        return False
    
    def save_transmitting_settings(self):
        """Save transmitting settings to config"""
        try:
            self.config['transmitting'] = {
                'ptt_time': self.ptt_time_var.get(),
                'pre_roll_delay': self.pre_roll_delay_var.get(),
                'pause': self.pause_var.get(),
                'rewind': self.rewind_var.get()
            }
            
            if self.save_config():
                messagebox.showinfo("Success", "Transmitting settings saved successfully!")
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
        return False
    
    def setup_general_settings(self, parent):
        """Set up general settings section"""
        # Language
        ttk.Label(parent, text="Idioma:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.language_var = tk.StringVar(value="es")
        ttk.Combobox(
            parent, 
            textvariable=self.language_var,
            values=["Español", "English"],
            state="readonly",
            width=20
        ).grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Theme
        ttk.Label(parent, text="Tema:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.theme_var = tk.StringVar(value="default")
        ttk.Combobox(
            parent,
            textvariable=self.theme_var,
            values=["Claro", "Oscuro", "Sistema"],
            state="readonly",
            width=20
        ).grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Auto-save
        self.autosave_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent,
            text="Guardado automático",
            variable=self.autosave_var
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
    
    # Audio settings have been removed
    
    def setup_database_settings(self, parent):
        """Set up database settings section"""
        # Database Path
        ttk.Label(parent, text="Ubicación de la base de datos:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.db_path_var = tk.StringVar(value="data/hamna.db")
        ttk.Entry(parent, textvariable=self.db_path_var, width=40).grid(
            row=0, column=1, sticky=tk.W, pady=2, padx=5, columnspan=2
        )
        ttk.Button(parent, text="Examinar...", command=self.browse_db_path).grid(
            row=0, column=3, sticky=tk.W, padx=5
        )
        
        # Backup Settings
        ttk.Label(parent, text="Copia de seguridad automática:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, 
            text="Hacer copia de seguridad al salir",
            variable=self.backup_var
        ).grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=2)
        
        # Database Tools
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=10
        )
        
        ttk.Button(
            parent, 
            text="Hacer copia de seguridad ahora",
            command=self.backup_database
        ).grid(row=3, column=0, columnspan=2, pady=5, padx=5, sticky=tk.W)
        
        ttk.Button(
            parent,
            text="Restaurar desde copia",
            command=self.restore_database
        ).grid(row=3, column=2, columnspan=2, pady=5, padx=5, sticky=tk.W)
    
    def browse_db_path(self):
        """Open file dialog to select database path"""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Seleccionar ubicación de la base de datos",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("Todos los archivos", "*.*")],
            initialfile="hamna.db"
        )
        if path:
            self.db_path_var.set(path)
    
    def save_settings(self):
        """Save all settings"""
        # TODO: Implement settings save logic
        messagebox.showinfo("Guardar", "Configuración guardada correctamente.")
    
    def apply_changes(self):
        """Apply changes without closing"""
        # TODO: Implement apply changes logic
        messagebox.showinfo("Aplicar", "Cambios aplicados correctamente.")
    
    def cancel_changes(self):
        """Cancel changes and reload settings"""
        # TODO: Implement cancel changes logic
        if messagebox.askyesno("Cancelar", "¿Desea descartar los cambios realizados?"):
            # Reload settings
            pass
    
    def backup_database(self):
        """Create a backup of the database"""
        # TODO: Implement database backup
        messagebox.showinfo("Copia de seguridad", "Copia de seguridad creada correctamente.")
    
    def restore_database(self):
        """Restore database from backup"""
        # TODO: Implement database restore
        if messagebox.askyesno("Restaurar", "¿Está seguro de que desea restaurar la base de datos desde una copia de seguridad?"):
            messagebox.showinfo("Restaurar", "Base de datos restaurada correctamente.")
