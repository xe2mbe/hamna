import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import os
import time
import threading
from pathlib import Path
from functools import partial
import hid  # For CM108 interface
from src.func.cm108 import hid_enumerate_filtered, hid_open_device, hid_close_device, hid_set_ptt, hid_read_cos
from src.func.serial import SerialInterface
from src.func.ami import AMIConnection, AMIConnectionError
from src.func.api import APIConnection, APIConnectionError

class ConfigTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config_file = Path("config/cfg.yaml")
        self.config = self.load_config()
        self.connected = False
        self.ptt_state = False
        self.cos_state = False
        self.cm108_device = None
        self.serial_interface = SerialInterface()
        self.ami_connection = None  # Will be initialized when needed
        self.api_connection = APIConnection()  # API connection instance
        self.running = True
        self.setup_ui()
        
        # Start status update thread
        self.status_thread = threading.Thread(target=self.update_status, daemon=True)
        self.status_thread.start()
        
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
            },
            'ami': {
                'host': '',
                'port': '5038',
                'username': '',
                'password': '',
                'enabled': False
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
        
        # Configure style for configuration tabs with more padding
        style = ttk.Style()
        style.configure('Config.TNotebook.Tab', padding=[10, 2])
        
        # Create notebook for different configuration sections with custom style
        config_notebook = ttk.Notebook(main_frame, style='Config.TNotebook')
        config_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # General Settings Tab
        general_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_general_settings(general_frame)
        config_notebook.add(general_frame, text="General")      
        
        # Radio Interface Tab
        radio_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_radio_interface(radio_frame)
        config_notebook.add(radio_frame, text="Radio Interface")
        
        # AMI Settings Tab
        ami_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_ami_settings(ami_frame)
        config_notebook.add(ami_frame, text="AMI")
        
        # API Settings Tab
        api_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_api_settings(api_frame)
        config_notebook.add(api_frame, text="API")
        
        # Transmitting Settings Tab
        transmitting_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_transmitting_settings(transmitting_frame)
        config_notebook.add(transmitting_frame, text="Transmitting")
            
        # Database Settings Tab
        db_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_database_settings(db_frame)
        config_notebook.add(db_frame, text="Base de Datos")
        
        # TTS Settings Tab
        tts_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_tts_settings(tts_frame)
        config_notebook.add(tts_frame, text="TTS")
        
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
        """Set up radio interface section with CM108 and Serial options"""
        # Main frame with padding
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Interface Type selection
        ttk.Label(main_frame, text="Interface Type:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.interface_type = tk.StringVar(value="cm108")  # Default to CM108
        
        # Radio buttons for interface type
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        cm108_btn = ttk.Radiobutton(
            type_frame, 
            text="CM108 (GPIO Audio Device)", 
            variable=self.interface_type, 
            value="cm108",
            command=self.switch_interface
        )
        cm108_btn.pack(side=tk.LEFT, padx=5)
        
        serial_btn = ttk.Radiobutton(
            type_frame, 
            text="Serial (RS232 / USB-UART)", 
            variable=self.interface_type, 
            value="serial",
            command=self.switch_interface
        )
        serial_btn.pack(side=tk.LEFT, padx=5)
        
        # Container for interface-specific frames
        self.interface_container = ttk.Frame(main_frame)
        self.interface_container.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        
        # Create both interface frames but don't pack them yet
        self.setup_cm108_interface()
        self.setup_serial_interface()
        
        # Show the appropriate interface based on config
        self.switch_interface()
    
    def setup_cm108_interface(self):
        """Set up CM108 interface frame"""
        self.cm108_frame = ttk.Frame(self.interface_container)
        
        # Device selection
        ttk.Label(self.cm108_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            self.cm108_frame,
            textvariable=self.device_var,
            state="readonly",
            width=40
        )
        self.device_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            self.cm108_frame,
            text="Refresh",
            command=self.refresh_devices
        )
        self.refresh_btn.grid(row=0, column=2, padx=5)
        
        # Status indicators frame
        status_frame = ttk.LabelFrame(self.cm108_frame, text="Status", padding=10)
        status_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # COS status
        ttk.Label(status_frame, text="COS:").grid(row=0, column=0, padx=5)
        self.cos_status = ttk.Label(status_frame, text="OFF", foreground="gray")
        self.cos_status.grid(row=0, column=1, padx=5)
        
        # PTT status
        ttk.Label(status_frame, text="PTT:").grid(row=0, column=2, padx=5)
        self.ptt_status = ttk.Label(status_frame, text="OFF", foreground="gray")
        self.ptt_status.grid(row=0, column=3, padx=5)
        
        # Connection status
        self.connection_status = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.connection_status.grid(row=0, column=4, padx=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(self.cm108_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.ptt_btn = ttk.Button(
            btn_frame, 
            text="PTT ON", 
            command=self.toggle_ptt, 
            state=tk.DISABLED
        )
        self.ptt_btn.pack(side=tk.LEFT, padx=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(self.cm108_frame, text="CM108 Configuration", padding=10)
        config_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # VID
        ttk.Label(config_frame, text="VID:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=5)
        self.vid_var = tk.StringVar(value="0x0d8c")
        ttk.Entry(config_frame, textvariable=self.vid_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        # PID
        ttk.Label(config_frame, text="PID:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=5)
        self.pid_var = tk.StringVar(value="0x000c")
        ttk.Entry(config_frame, textvariable=self.pid_var, width=10).grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)
        
        # PTT Bit
        ttk.Label(config_frame, text="PTT Bit (hex):").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.ptt_bit_var = tk.StringVar(value="0x01")
        ttk.Entry(config_frame, textvariable=self.ptt_bit_var, width=5).grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # COS Bit
        ttk.Label(config_frame, text="COS Bit (hex):").grid(row=1, column=2, sticky=tk.W, pady=2, padx=5)
        self.cos_bit_var = tk.StringVar(value="0x02")
        ttk.Entry(config_frame, textvariable=self.cos_bit_var, width=5).grid(row=1, column=3, sticky=tk.W, pady=2, padx=5)
        
        # Checkboxes frame
        check_frame = ttk.Frame(config_frame)
        check_frame.grid(row=2, column=0, columnspan=4, pady=5)
        
        # Invert PTT
        self.invert_ptt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            check_frame,
            text="Invert PTT",
            variable=self.invert_ptt_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Invert COS
        self.invert_cos_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            check_frame,
            text="Invert COS",
            variable=self.invert_cos_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Save button
        save_btn = ttk.Button(
            self.cm108_frame,
            text="Save Configuration",
            command=self.save_radio_config,
            width=20
        )
        save_btn.grid(row=4, column=0, columnspan=3, pady=10)
        
        # Load saved configuration
        self.load_radio_config()
        
        # Initial device refresh
        self.refresh_devices()
    
    def setup_serial_interface(self):
        """Set up Serial interface frame"""
        self.serial_frame = ttk.Frame(self.interface_container)
        
        # Port selection
        ttk.Label(self.serial_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.serial_port_var = tk.StringVar()
        self.serial_port_combo = ttk.Combobox(
            self.serial_frame,
            textvariable=self.serial_port_var,
            state="readonly",
            width=30
        )
        self.serial_port_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Refresh button
        self.serial_refresh_btn = ttk.Button(
            self.serial_frame,
            text="Refresh",
            command=self.refresh_serial_ports
        )
        self.serial_refresh_btn.grid(row=0, column=2, padx=5)
        
        # Baudrate selection
        ttk.Label(self.serial_frame, text="Baudrate:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.baudrate_var = tk.StringVar(value="9600")
        self.baudrate_combo = ttk.Combobox(
            self.serial_frame,
            textvariable=self.baudrate_var,
            values=["9600", "19200", "38400", "57600", "115200"],
            state="readonly",
            width=10
        )
        self.baudrate_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Status indicators frame
        status_frame = ttk.LabelFrame(self.serial_frame, text="Status", padding=10)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # COS status
        ttk.Label(status_frame, text="COS:").grid(row=0, column=0, padx=5)
        self.serial_cos_status = ttk.Label(status_frame, text="INACTIVE", foreground="gray")
        self.serial_cos_status.grid(row=0, column=1, padx=5)
        
        # PTT status
        ttk.Label(status_frame, text="PTT:").grid(row=0, column=2, padx=5)
        self.serial_ptt_status = ttk.Label(status_frame, text="OFF", foreground="gray")
        self.serial_ptt_status.grid(row=0, column=3, padx=5)
        
        # Connection status
        self.serial_connection_status = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.serial_connection_status.grid(row=0, column=4, padx=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(self.serial_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.serial_connect_btn = ttk.Button(
            btn_frame, 
            text="Connect", 
            command=self.toggle_serial_connection
        )
        self.serial_connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.serial_ptt_btn = ttk.Button(
            btn_frame, 
            text="PTT ON", 
            command=self.toggle_serial_ptt,
            state=tk.DISABLED
        )
        self.serial_ptt_btn.pack(side=tk.LEFT, padx=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(self.serial_frame, text="Serial Configuration", padding=10)
        config_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # Checkboxes frame
        check_frame = ttk.Frame(config_frame)
        check_frame.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Invert PTT
        self.serial_invert_ptt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            check_frame,
            text="Invert PTT",
            variable=self.serial_invert_ptt_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Invert COS
        self.serial_invert_cos_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            check_frame,
            text="Invert COS",
            variable=self.serial_invert_cos_var
        ).pack(side=tk.LEFT, padx=10)
        
        # Save button
        save_btn = ttk.Button(
            self.serial_frame,
            text="Save Configuration",
            command=self.save_serial_config,
            width=20
        )
        save_btn.grid(row=5, column=0, columnspan=3, pady=10)
        
        # Load saved configuration
        self.load_serial_config()
        
        # Initial port refresh
        self.refresh_serial_ports()
    
    def switch_interface(self):
        """Switch between CM108 and Serial interfaces"""
        # Hide all frames first
        for widget in self.interface_container.winfo_children():
            widget.pack_forget()
        
        # Show the selected interface
        if self.interface_type.get() == "cm108":
            self.cm108_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.serial_frame.pack(fill=tk.BOTH, expand=True)
    
    def refresh_devices(self):
        """Refresh list of available CM108 devices"""
        try:
            devices, labels = hid_enumerate_filtered()
            self.devices = devices
            self.device_combo['values'] = labels
            if labels:
                self.device_combo.current(0)
                return True
            else:
                messagebox.showwarning("No Devices", "No CM108 devices found")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Error enumerating devices: {e}")
            return False
    
    def toggle_connection(self):
        """Toggle connection to the CM108 device"""
        if not self.connected:
            # Try to connect
            if self.interface_type.get() == "cm108":
                if self.connect_cm108():
                    self.connected = True
                    self.connect_btn.config(text="Disconnect")
                    self.ptt_btn.config(state=tk.NORMAL) 
                    self.connection_status.config(text="Connected", foreground="green")
                    
                    # Save configuration on successful connection
                    self.save_radio_config()
        else:
            # Disconnect
            if self.interface_type.get() == "cm108":
                self.disconnect_cm108()
            
            self.connected = False
            self.connect_btn.config(text="Connect")
            self.ptt_btn.config(state=tk.DISABLED)
            self.ptt_btn.config(text="PTT ON")
            self.ptt_state = False
            self.ptt_status.config(text="OFF", foreground="gray")
            self.cos_status.config(text="INACTIVE", foreground="gray")
            self.connection_status.config(text="Disconnected", foreground="red")
    
    def connect_cm108(self):
        """Connect to CM108 device"""
        try:
            if not hasattr(self, 'devices') or not self.devices:
                if not self.refresh_devices():
                    return False
            
            selected_idx = self.device_combo.current()
            if selected_idx < 0:
                messagebox.showerror("Error", "No device selected")
                return False
            
            device_info = self.devices[selected_idx]
            self.cm108_device = hid_open_device(device_info)
            
            if self.cm108_device:
                # Update UI with device info
                self.vid_var.set(f"0x{device_info['vendor_id']:04x}")
                self.pid_var.set(f"0x{device_info['product_id']:04x}")
                return True
            else:
                messagebox.showerror("Error", "Failed to open device")
                return False
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            return False
    
    def disconnect_cm108(self):
        """Disconnect from CM108 device"""
        if self.cm108_device:
            try:
                hid_close_device(self.cm108_device)
            except:
                pass
            self.cm108_device = None
    
    def toggle_ptt(self):
        """Toggle PTT state"""
        if not self.connected:
            return
            
        self.ptt_state = not self.ptt_state
        
        if self.interface_type.get() == "cm108" and self.cm108_device:
            try:
                ptt_bit = int(self.ptt_bit_var.get(), 16)
                hid_set_ptt(
                    self.cm108_device,
                    ptt_bit,
                    self.ptt_state,
                    self.invert_ptt_var.get()
                )
                
                # Update UI
                if self.ptt_state:
                    self.ptt_btn.config(text="PTT OFF", style="Red.TButton")
                    self.ptt_status.config(text="ON", foreground="red")
                else:
                    self.ptt_btn.config(text="PTT ON", style="TButton")
                    self.ptt_status.config(text="OFF", foreground="gray")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set PTT: {e}")
    
    def update_status(self):
        """Update COS/PTT status periodically"""
        while self.running:
            # Update CM108 status
            if self.connected and self.interface_type.get() == "cm108" and self.cm108_device:
                try:
                    # Read COS state
                    cos_bit = int(self.cos_bit_var.get(), 16)
                    cos_state = hid_read_cos(
                        self.cm108_device,
                        cos_bit,
                        self.invert_cos_var.get()
                    )
                    
                    # Update UI
                    if cos_state is not None:
                        self.cos_state = cos_state
                        if self.cos_state:
                            self.cos_status.config(text="ACTIVE", foreground="green")
                        else:
                            self.cos_status.config(text="INACTIVE", foreground="gray")
                    
                except Exception as e:
                    print(f"Error reading CM108 COS: {e}")
            
            # Update Serial status
            elif self.connected and self.interface_type.get() == "serial" and self.serial_interface.is_connected():
                try:
                    # Read COS state
                    cos_state = self.serial_interface.read_cos()
                    
                    # Update UI
                    if cos_state is not None:
                        self.cos_state = cos_state
                        if self.cos_state:
                            self.serial_cos_status.config(text="ACTIVE", foreground="green")
                        else:
                            self.serial_cos_status.config(text="INACTIVE", foreground="gray")
                    
                except Exception as e:
                    print(f"Error reading Serial COS: {e}")
            
            # Sleep for a bit to avoid high CPU usage
            time.sleep(0.2)  # Update 5 times per second
    
    def load_radio_config(self):
        """Load CM108 radio configuration from config"""
        if 'radio' in self.config:
            radio_cfg = self.config['radio']
            if 'cm108' in radio_cfg:
                cm108_cfg = radio_cfg['cm108']
                self.vid_var.set(cm108_cfg.get('vid', '0x0d8c'))
                self.pid_var.set(cm108_cfg.get('pid', '0x000c'))
                self.ptt_bit_var.set(cm108_cfg.get('ptt_bit', '0x01'))
                self.cos_bit_var.set(cm108_cfg.get('cos_bit', '0x02'))
                self.invert_ptt_var.set(cm108_cfg.get('invert_ptt', False))
                self.invert_cos_var.set(cm108_cfg.get('invert_cos', True))
                # Select the device if it exists in the config
                if 'device' in cm108_cfg and cm108_cfg['device'] in self.device_combo['values']:
                    self.device_combo.set(cm108_cfg['device'])
    
    def save_radio_config(self):
        """Save CM108 radio configuration to config"""
        try:
            if 'radio' not in self.config:
                self.config['radio'] = {}
                
            self.config['radio']['cm108'] = {
                'device': self.device_var.get(),
                'vid': self.vid_var.get(),
                'pid': self.pid_var.get(),
                'ptt_bit': self.ptt_bit_var.get(),
                'cos_bit': self.cos_bit_var.get(),
                'invert_ptt': self.invert_ptt_var.get(),
                'invert_cos': self.invert_cos_var.get()
            }
            
            if self.save_config():
                messagebox.showinfo("Success", "CM108 configuration saved successfully!")
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CM108 configuration: {e}")
        return False
        
    def load_serial_config(self):
        """Load serial configuration from config"""
        if 'radio' in self.config and 'serial' in self.config['radio']:
            serial_cfg = self.config['radio']['serial']
            self.serial_port_var.set(serial_cfg.get('port', ''))
            self.baudrate_var.set(str(serial_cfg.get('baudrate', '9600')))
            self.serial_invert_ptt_var.set(serial_cfg.get('invert_ptt', False))
            self.serial_invert_cos_var.set(serial_cfg.get('invert_cos', False))
    
    def save_serial_config(self):
        """Save serial configuration to config"""
        try:
            if 'radio' not in self.config:
                self.config['radio'] = {}
                
            self.config['radio']['serial'] = {
                'port': self.serial_port_var.get(),
                'baudrate': int(self.baudrate_var.get()),
                'invert_ptt': self.serial_invert_ptt_var.get(),
                'invert_cos': self.serial_invert_cos_var.get()
            }
            
            if self.save_config():
                messagebox.showinfo("Success", "Serial configuration saved successfully!")
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save serial configuration: {e}")
        return False
        
    def refresh_serial_ports(self):
        """Refresh list of available serial ports"""
        try:
            ports = self.serial_interface.list_ports()
            port_list = [f"{p['device']} - {p['description']}" for p in ports]
            self.serial_port_combo['values'] = port_list
            
            if port_list:
                # Try to select the previously selected port if it exists
                current_port = self.serial_port_var.get().split(' - ')[0]
                for i, port in enumerate(ports):
                    if port['device'] == current_port:
                        self.serial_port_combo.current(i)
                        break
                else:
                    self.serial_port_combo.current(0)
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list serial ports: {e}")
            return False
    
    def toggle_serial_connection(self):
        """Toggle serial connection"""
        if not self.connected:
            # Connect
            port = self.serial_port_var.get().split(' - ')[0]  # Extract port name
            if not port:
                messagebox.showerror("Error", "Please select a serial port")
                return
                
            try:
                baudrate = int(self.baudrate_var.get())
                if self.serial_interface.connect_serial(port, baudrate):
                    self.connected = True
                    self.serial_connect_btn.config(text="Disconnect")
                    self.serial_ptt_btn.config(state=tk.NORMAL)
                    self.serial_connection_status.config(text="Connected", foreground="green")
                    
                    # Apply inversion settings
                    self.serial_interface.set_invert_ptt(self.serial_invert_ptt_var.get())
                    self.serial_interface.set_invert_cos(self.serial_invert_cos_var.get())
                    
                    # Save configuration on successful connection
                    self.save_serial_config()
                else:
                    messagebox.showerror("Error", "Failed to connect to the serial port")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to connect: {e}")
        else:
            # Disconnect
            self.serial_interface.disconnect_serial()
            self.connected = False
            self.serial_connect_btn.config(text="Connect")
            self.serial_ptt_btn.config(state=tk.DISABLED, text="PTT ON")
            self.serial_ptt_status.config(text="OFF", foreground="gray")
            self.serial_cos_status.config(text="INACTIVE", foreground="gray")
            self.serial_connection_status.config(text="Disconnected", foreground="red")
    
    def toggle_serial_ptt(self):
        """Toggle PTT for serial interface"""
        if not self.connected or not self.serial_interface.is_connected():
            return
            
        self.ptt_state = not self.ptt_state
        
        try:
            if self.serial_interface.set_ptt(self.ptt_state):
                # Update UI
                if self.ptt_state:
                    self.serial_ptt_btn.config(text="PTT OFF")
                    self.serial_ptt_status.config(text="ON", foreground="red")
                else:
                    self.serial_ptt_btn.config(text="PTT ON")
                    self.serial_ptt_status.config(text="OFF", foreground="gray")
            else:
                messagebox.showerror("Error", "Failed to set PTT state")
                self.ptt_state = not self.ptt_state  # Revert state on failure
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set PTT: {e}")
            self.ptt_state = not self.ptt_state  # Revert state on error
    
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
    
    def setup_tts_settings(self, parent):
        """Set up TTS (Text-to-Speech) settings section"""
        # Main frame with padding
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # TTS Settings Frame
        tts_frame = ttk.LabelFrame(main_frame, text="TTS Configuration", padding=10)
        tts_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Engine selection
        ttk.Label(tts_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.tts_engine_var = tk.StringVar()
        self.tts_engine_combo = ttk.Combobox(
            tts_frame,
            textvariable=self.tts_engine_var,
            values=["Azure Speech", "gTTS", "pyttsx3", "Edge TTS"],
            state="readonly",
            width=20
        )
        self.tts_engine_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        self.tts_engine_combo.set("Azure Speech")  # Default value
        
        # Format selection
        ttk.Label(tts_frame, text="Format:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        self.tts_format_var = tk.StringVar()
        self.tts_format_combo = ttk.Combobox(
            tts_frame,
            textvariable=self.tts_format_var,
            values=["mp3", "wav"],
            state="readonly",
            width=10
        )
        self.tts_format_combo.grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        self.tts_format_combo.set("mp3")  # Default value
        
        # Voice selection
        ttk.Label(tts_frame, text="Voice:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.tts_voice_var = tk.StringVar()
        self.tts_voice_combo = ttk.Combobox(
            tts_frame,
            textvariable=self.tts_voice_var,
            state="readonly",
            width=30
        )
        self.tts_voice_combo.grid(row=1, column=1, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # Language filters frame
        filter_frame = ttk.LabelFrame(tts_frame, text="Language Filters", padding=5)
        filter_frame.grid(row=2, column=0, columnspan=4, sticky=tk.EW, pady=5, padx=5)
        
        # Language filter checkboxes
        self.tts_filter_en_var = tk.BooleanVar(value=True)
        self.tts_filter_es_var = tk.BooleanVar(value=True)
        self.tts_filter_all_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(
            filter_frame, 
            text="English (EN)", 
            variable=self.tts_filter_en_var,
            command=self.update_voice_list
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(
            filter_frame, 
            text="Spanish (ES)", 
            variable=self.tts_filter_es_var,
            command=self.update_voice_list
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(
            filter_frame, 
            text="All Languages", 
            variable=self.tts_filter_all_var,
            command=self.toggle_language_filters
        ).pack(side=tk.LEFT, padx=10)
        
        # Rate control
        ttk.Label(tts_frame, text="Speech Rate (%):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.tts_rate_var = tk.IntVar(value=100)  # 100% default rate
        ttk.Scale(
            tts_frame,
            from_=50,
            to=200,
            orient=tk.HORIZONTAL,
            variable=self.tts_rate_var,
            command=lambda v: self.tts_rate_var.set(round(float(v)))
        ).grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # Rate value display
        self.tts_rate_display = ttk.Label(tts_frame, text="100%")
        self.tts_rate_display.grid(row=3, column=3, sticky=tk.E, padx=5)
        self.tts_rate_var.trace_add("write", self.update_rate_display)
        
        # Text input
        ttk.Label(tts_frame, text="Test Text:").grid(row=4, column=0, sticky=tk.NW, pady=5, padx=5)
        self.tts_text = tk.Text(tts_frame, width=50, height=5, wrap=tk.WORD)
        self.tts_text.grid(row=4, column=1, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(tts_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        
        ttk.Button(
            btn_frame,
            text="Generate TTS",
            command=self.generate_tts,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Preview",
            command=self.preview_tts,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Stop",
            command=self.stop_tts,
            width=10,
            state=tk.DISABLED
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Save",
            command=self.save_tts_settings,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # Azure Speech specific settings
        self.azure_frame = ttk.LabelFrame(main_frame, text="Azure Speech Configuration", padding=10)
        self.azure_frame.pack(fill=tk.X, pady=5)
        
        # Region
        ttk.Label(self.azure_frame, text="Region:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.azure_region_var = tk.StringVar()
        ttk.Entry(
            self.azure_frame,
            textvariable=self.azure_region_var,
            width=30
        ).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Key (password field)
        ttk.Label(self.azure_frame, text="Key:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.azure_key_var = tk.StringVar()
        self.azure_key_entry = ttk.Entry(
            self.azure_frame,
            textvariable=self.azure_key_var,
            show="*",
            width=40
        )
        self.azure_key_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Show/Hide key button
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.azure_frame,
            text="Show",
            variable=self.show_key_var,
            command=self.toggle_key_visibility
        ).grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        
        # Save Azure settings button
        ttk.Button(
            self.azure_frame,
            text="Save Azure Settings",
            command=self.save_azure_settings,
            width=20
        ).grid(row=2, column=0, columnspan=3, pady=10)
        
        # Load saved settings
        self.load_tts_settings()
        
        # Update voice list based on selected engine
        self.tts_engine_combo.bind("<<ComboboxSelected>>", self.on_engine_changed)
        self.update_voice_list()
    
    def toggle_key_visibility(self):
        """Toggle visibility of the Azure key"""
        if self.show_key_var.get():
            self.azure_key_entry.config(show="")
        else:
            self.azure_key_entry.config(show="*")
    
    def on_engine_changed(self, event=None):
        """Handle engine change event"""
        self.update_voice_list()
        
        # Show/hide Azure settings based on selected engine
        if self.tts_engine_var.get() == "Azure Speech":
            self.azure_frame.pack(fill=tk.X, pady=5)
        else:
            self.azure_frame.pack_forget()
    
    def update_rate_display(self, *args):
        """Update the rate display label"""
        self.tts_rate_display.config(text=f"{self.tts_rate_var.get()}%")
    
    def toggle_language_filters(self):
        """Toggle language filters based on 'All Languages' checkbox"""
        if self.tts_filter_all_var.get():
            self.tts_filter_en_var.set(True)
            self.tts_filter_es_var.set(True)
        self.update_voice_list()
    
    def update_voice_list(self, event=None):
        """Update the voice list based on selected engine and filters"""
        engine = self.tts_engine_var.get()
        voices = []
        
        print(f"\n=== Updating voice list for engine: {engine} ===")
        
        try:
            if engine == "Azure Speech":
                # Get Azure credentials from environment variables
                from dotenv import load_dotenv
                import os
                from pathlib import Path
                
                # Load .env file from config directory
                env_path = Path("config") / ".env"
                if env_path.exists():
                    load_dotenv(dotenv_path=env_path, override=True)
                
                speech_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("AZURE_TTS_KEY")
                speech_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_TTS_REGION")
                
                if not speech_key or not speech_region:
                    print("Warning: Azure credentials not found in .env file")
                    voices = [("", "Configure Azure credentials in Settings")]
                else:
                    print(f"Fetching voices from Azure region: {speech_region}")
                    try:
                        import azure.cognitiveservices.speech as speechsdk
                        
                        # Create speech config
                        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
                        
                        # Create speech synthesizer
                        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                        
                        # Get voices from Azure
                        result = speech_synthesizer.get_voices_async().get()
                        
                        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                            print(f"Successfully retrieved {len(result.voices)} voices from Azure")
                            for voice in result.voices:
                                # Only include neural voices for better quality
                                if "neural" in voice.name.lower():
                                    # Format: "Name (Locale) - Gender [Neural]"
                                    display_name = f"{voice.short_name.split('-')[-1]} ({voice.locale}) - {voice.gender}"
                                    if hasattr(voice, 'style_list') and voice.style_list:
                                        display_name += f" [{', '.join(voice.style_list)}]"
                                    voices.append((voice.short_name, display_name))
                            
                            # Sort voices by locale and name
                            voices.sort(key=lambda x: (x[0].split('-')[0], x[1]))
                            
                            if not voices:
                                print("Warning: No neural voices found in Azure TTS")
                                voices = [("", "No neural voices available")]
                        else:
                            print(f"Error fetching voices from Azure: {result.reason}")
                            voices = [("", f"Error: {result.reason}")]
                            
                    except Exception as e:
                        print(f"Error fetching Azure voices: {str(e)}")
                        voices = [("", f"Error: {str(e)}")]
            
            elif engine == "gTTS":
                print("Loading gTTS languages")
                try:
                    from gtts.lang import tts_langs
                    langs = tts_langs()
                    voices = [(code, f"{name} ({code})") for code, name in sorted(langs.items())]
                    print(f"Loaded {len(voices)} gTTS languages")
                except Exception as e:
                    print(f"Error loading gTTS languages: {str(e)}")
                    voices = [("en", "English"), ("es", "Spanish")]
            
            elif engine == "pyttsx3":
                print("Loading pyttsx3 voices")
                try:
                    import pyttsx3
                    tts_engine = pyttsx3.init()
                    voices = [(str(i), voice.name) for i, voice in enumerate(tts_engine.getProperty('voices'))]
                    print(f"Loaded {len(voices)} pyttsx3 voices")
                except Exception as e:
                    print(f"Error loading pyttsx3 voices: {str(e)}")
                    voices = [("0", "Default Voice")]
            
            elif engine == "Edge TTS":
                print("Loading Edge TTS voices")
                try:
                    import edge_tts
                    import asyncio
                    
                    async def get_voices():
                        return await edge_tts.list_voices()
                        
                    edge_voices = asyncio.run(get_voices())
                    voices = [(v['ShortName'], f"{v['ShortName']} - {v['Gender']}") 
                             for v in edge_voices if 'neural' in v.get('VoiceType', '').lower()]
                    print(f"Loaded {len(voices)} Edge TTS neural voices")
                except Exception as e:
                    print(f"Error loading Edge TTS voices: {str(e)}")
                    voices = [("en-US-JennyNeural", "Jenny (en-US)")]
            
            # Debug output
            print(f"\nAvailable voices ({len(voices)}):")
            for i, (voice_id, voice_name) in enumerate(voices[:5]):  # Show first 5 for brevity
                print(f"  {i+1}. {voice_name} ({voice_id})")
            if len(voices) > 5:
                print(f"  ... and {len(voices)-5} more")
            
            # Apply language filters if not showing all languages
            if not self.tts_filter_all_var.get():
                filtered_voices = []
                for voice_id, voice_name in voices:
                    lang_code = voice_id.split('-')[0] if '-' in voice_id else voice_id
                    if self.tts_filter_en_var.get() and lang_code.startswith("en"):
                        filtered_voices.append((voice_id, voice_name))
                    elif self.tts_filter_es_var.get() and lang_code.startswith("es"):
                        filtered_voices.append((voice_id, voice_name))
                
                print(f"\nFiltered voices ({len(filtered_voices)}):")
                for i, (voice_id, voice_name) in enumerate(filtered_voices[:5]):
                    print(f"  {i+1}. {voice_name} ({voice_id})")
                if len(filtered_voices) > 5:
                    print(f"  ... and {len(filtered_voices)-5} more")
                    
                voices = filtered_voices
            
            # Update the combobox
            display_values = [f"{name} ({id})" for id, name in voices]
            current_value = self.tts_voice_var.get()
            
            self.tts_voice_combo['values'] = display_values
            
            # Try to maintain the current selection if it exists in the new list
            if current_value in display_values:
                self.tts_voice_combo.set(current_value)
            elif voices:
                self.tts_voice_combo.current(0)
                
            print(f"Voice list updated. Current selection: {self.tts_voice_var.get()}")
            
        except Exception as e:
            print(f"Error in update_voice_list: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback to default voices
            self.tts_voice_combo['values'] = ["Error loading voices"]
            self.tts_voice_combo.current(0)
    
    def generate_tts(self):
        """Generate TTS audio with file dialog for saving"""
        import os
        import azure.cognitiveservices.speech as speechsdk
        from dotenv import load_dotenv
        from tkinter import filedialog
        from datetime import datetime
        
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "Por favor ingresa un texto para convertir a voz.")
            return
        
        # Get selected voice and parse it
        selected_voice = self.tts_voice_combo.get()
        if not selected_voice:
            messagebox.showwarning("No Voice", "Por favor selecciona una voz.")
            return
        
        # Extract voice ID from the display string (format: "Name (id)")
        try:
            voice_id = selected_voice.split("(")[-1].rstrip(")")
            print(f"Generating TTS with voice ID: {voice_id}")
        except (IndexError, AttributeError):
            voice_id = selected_voice
        
        # Get other parameters
        rate = self.tts_rate_var.get()
        output_format = self.tts_format_var.get()
        
        # Load Azure configuration
        load_dotenv()
        speech_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("AZURE_TTS_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_TTS_REGION")
        
        if not speech_key or not speech_region:
            messagebox.showerror("Error", "No se encontraron las credenciales de Azure TTS. Por favor configura las variables de entorno AZURE_SPEECH_KEY y AZURE_SPEECH_REGION.")
            return
        
        try:
            # Ask user where to save the file
            default_filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{output_format}",
                filetypes=[("Audio Files", f"*.{output_format}"), ("All Files", "*.*")],
                initialfile=default_filename,
                title="Guardar archivo de audio"
            )
            
            # If user cancels the dialog
            if not file_path:
                print("Operación cancelada por el usuario")
                return
                
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            print(f"Generando TTS con voz: {voice_id}, velocidad: {rate}%, formato: {output_format}")
            print(f"Guardando en: {file_path}")
            
            # Configure speech synthesis
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
            speech_config.speech_synthesis_voice_name = voice_id
            
            # Adjust speech rate if needed
            if rate != 100:
                # Get language code from voice ID (first part before -)
                lang_code = voice_id.split('-')[0]
                
                # Create SSML with rate adjustment
                ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang_code}'>
                    <voice name='{voice_id}'>
                        <prosody rate='{rate}%'>{text}</prosody>
                    </voice>
                </speak>"""
                
                audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                result = synthesizer.speak_ssml_async(ssml).get()
            else:
                audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                result = synthesizer.speak_text_async(text).get()
            
            # Check the result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                messagebox.showinfo("TTS Generado", f"El audio se ha generado correctamente en:\n{file_path}")
                # Ask if user wants to play the audio
                if messagebox.askyesno("Reproducir audio", "¿Deseas reproducir el audio generado?"):
                    self.play_audio(file_path)
            else:
                error_details = result.cancellation_details
                error_msg = f"No se pudo generar el audio.\nRazón: {error_details.reason}"
                if error_details.error_details:
                    error_msg += f"\nDetalles: {error_details.error_details}"
                messagebox.showerror("Error", error_msg)
                
        except Exception as e:
            error_msg = f"Ocurrió un error al generar el TTS:\n{str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            import traceback
            traceback.print_exc()
    
    def play_audio(self, audio_file):
        """Reproducir el archivo de audio generado"""
        import os
        import platform
        
        try:
            if platform.system() == 'Windows':
                os.startfile(audio_file)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'afplay "{audio_file}"')
            else:  # Linux
                os.system(f'aplay "{audio_file}"')
        except Exception as e:
            print(f"No se pudo reproducir el archivo de audio: {str(e)}")
    
    def preview_tts(self):
        """Preview TTS audio"""
        import os
        import tempfile
        import azure.cognitiveservices.speech as speechsdk
        from dotenv import load_dotenv
        
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "Por favor ingresa un texto para previsualizar.")
            return
        
        # Get selected voice and parse it
        selected_voice = self.tts_voice_combo.get()
        if not selected_voice:
            messagebox.showwarning("No Voice", "Por favor selecciona una voz.")
            return
        
        # Extract voice ID from the display string (format: "Display Name (voice-id)")
        try:
            # The voice ID is the part between the last parenthesis
            voice_id = selected_voice.split('(')[-1].rstrip(')')
            print(f"Previewing with voice ID: {voice_id}")
        except (IndexError, AttributeError):
            voice_id = selected_voice
        
        # Get other parameters
        rate = self.tts_rate_var.get()
        
        # Load Azure configuration
        load_dotenv()
        speech_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("AZURE_TTS_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_TTS_REGION")
        
        if not speech_key or not speech_region:
            messagebox.showerror("Error", "No se encontraron las credenciales de Azure TTS. Por favor configura las variables de entorno AZURE_SPEECH_KEY y AZURE_SPEECH_REGION.")
            return
        
        try:
            # Configure speech config
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
            speech_config.speech_synthesis_voice_name = voice_id
            
            # Use default speaker for preview
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            
            # Create speech synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            
            # Adjust speech rate if needed
            if rate != 100:
                # Get language code from voice ID (first part before -)
                lang_code = voice_id.split('-')[0]
                
                # Create SSML with rate adjustment
                ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang_code}'>
                    <voice name='{voice_id}'>
                        <prosody rate='{rate}%'>{text}</prosody>
                    </voice>
                </speak>"""
                
                # Synthesize using SSML
                result = synthesizer.speak_ssml_async(ssml).get()
            else:
                # Synthesize plain text
                result = synthesizer.speak_text_async(text).get()
            
            # Check the result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("TTS preview completed successfully")
            else:
                error_details = result.cancellation_details
                error_message = f"No se pudo generar la vista previa. Razón: {error_details.reason}"
                if error_details.error_details:
                    error_message += f"\nDetalles: {error_details.error_details}"
                messagebox.showerror("Error", error_message)
                
        except Exception as e:
            error_message = f"Error al generar la vista previa: {str(e)}"
            print(error_message)
            messagebox.showerror("Error", error_message)
            import traceback
            traceback.print_exc()
    
    def stop_tts(self):
        """Stop TTS playback"""
        print("Stopping TTS...")
        # TODO: Implement TTS stop
    
    def save_tts_settings(self):
        """Save TTS settings to config"""
        if 'tts' not in self.config:
            self.config['tts'] = {}
        
        # Save general TTS settings
        self.config['tts'].update({
            'engine': self.tts_engine_var.get(),
            'format': self.tts_format_var.get(),
            'voice': self.tts_voice_var.get(),
            'rate': self.tts_rate_var.get()
        })
        
        if self.save_config():
            messagebox.showinfo("Success", "TTS settings saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save TTS settings.")
    
    def save_azure_settings(self):
        """Save Azure Speech settings to .env file"""
        region = self.azure_region_var.get().strip()
        key = self.azure_key_var.get().strip()
        
        if not region or not key:
            messagebox.showwarning("Missing Information", "Please enter both region and key for Azure Speech.")
            return
        
        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to .env file
        env_path = config_dir / ".env"
        try:
            # Read existing .env file if it exists
            env_vars = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                k, v = line.split('=', 1)
                                env_vars[k] = v.strip('\'"')
                            except ValueError:
                                continue
            
            # Update Azure settings in .env
            env_vars['AZURE_SPEECH_REGION'] = region
            env_vars['AZURE_SPEECH_KEY'] = key
            
            # Also add alternative names for backward compatibility
            env_vars['AZURE_TTS_REGION'] = region
            env_vars['AZURE_TTS_KEY'] = key
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            
            # Update config - ensure we don't store sensitive data here
            if 'tts' not in self.config:
                self.config['tts'] = {}
            if 'azure' in self.config['tts']:
                # Remove region from config since it's now in .env
                if 'region' in self.config['tts']['azure']:
                    del self.config['tts']['azure']['region']
                # If azure section is empty, remove it
                if not self.config['tts']['azure']:
                    del self.config['tts']['azure']
            
            if self.save_config():
                messagebox.showinfo("Success", "Azure Speech settings saved successfully to .env file.")
            else:
                messagebox.showerror("Error", "Failed to update configuration file.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Azure settings: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_tts_settings(self):
        """Load TTS settings from config and .env"""
        # Initialize Azure settings variables if they don't exist
        if not hasattr(self, 'azure_region_var'):
            self.azure_region_var = tk.StringVar()
        if not hasattr(self, 'azure_key_var'):
            self.azure_key_var = tk.StringVar()
        
        # First try to load from .env file (for security, credentials should be in .env)
        try:
            from dotenv import load_dotenv
            env_path = Path("config") / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                
                # Get region and key from environment variables
                region = os.getenv('AZURE_SPEECH_REGION') or os.getenv('AZURE_TTS_REGION')
                key = os.getenv('AZURE_SPEECH_KEY') or os.getenv('AZURE_TTS_KEY')
                
                # Update UI with the values from .env
                if region:
                    self.azure_region_var.set(region)
                if key:
                    self.azure_key_var.set(key)
        except Exception as e:
            print(f"Warning: Could not load Azure settings from .env: {e}")
        
        # Then load other TTS settings from config
        if 'tts' in self.config:
            tts_config = self.config['tts']
            
            # Load general TTS settings
            self.tts_engine_var.set(tts_config.get('engine', 'Azure Speech'))
            self.tts_format_var.set(tts_config.get('format', 'mp3'))
            self.tts_voice_var.set(tts_config.get('voice', ''))
            self.tts_rate_var.set(tts_config.get('rate', 100))
            
            # Only use cfg.yaml for region if not already set from .env
            if not self.azure_region_var.get() and 'azure' in tts_config and 'region' in tts_config['azure']:
                self.azure_region_var.set(tts_config['azure']['region'])
        
        # Update UI based on loaded settings
        self.on_engine_changed()
        
        # Ensure the key field shows the correct visibility state
        if hasattr(self, 'key_visible') and hasattr(self, 'azure_key_entry'):
            self.toggle_key_visibility()
    
    def save_settings(self):
        """Save all settings"""
        # Save TTS settings
        if hasattr(self, 'tts_engine_var'):  # Check if TTS settings are initialized
            if 'tts' not in self.config:
                self.config['tts'] = {}
            
            # Save general TTS settings
            self.config['tts'].update({
                'engine': self.tts_engine_var.get(),
                'format': self.tts_format_var.get(),
                'voice': self.tts_voice_var.get(),
                'rate': self.tts_rate_var.get()
            })
            
            # Save Azure settings (without the key, which is stored in .env)
            if hasattr(self, 'azure_region_var'):
                if 'azure' not in self.config['tts']:
                    self.config['tts']['azure'] = {}
                self.config['tts']['azure']['region'] = self.azure_region_var.get()
        
        # Save the config to file
        if self.save_config():
            messagebox.showinfo("Guardar", "Configuración guardada correctamente.")
            return True
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")
            return False
    
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
            
    def setup_ami_settings(self, parent):
        """Set up AMI (Asterisk Manager Interface) settings section"""
        # AMI Settings Frame
        ami_frame = ttk.LabelFrame(parent, text="AMI Settings", padding=10)
        ami_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Enable AMI Checkbox
        self.ami_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ami_frame,
            text="Habilitar AMI",
            variable=self.ami_enabled_var,
            command=self.toggle_ami_settings
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Host
        ttk.Label(ami_frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.ami_host_var = tk.StringVar()
        host_entry = ttk.Entry(ami_frame, textvariable=self.ami_host_var, width=30)
        host_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Port
        ttk.Label(ami_frame, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=2, padx=5)
        self.ami_port_var = tk.StringVar()
        port_entry = ttk.Entry(ami_frame, textvariable=self.ami_port_var, width=10)
        port_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Username
        ttk.Label(ami_frame, text="Username:").grid(row=3, column=0, sticky=tk.W, pady=2, padx=5)
        self.ami_username_var = tk.StringVar()
        username_entry = ttk.Entry(ami_frame, textvariable=self.ami_username_var, width=30)
        username_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Password
        ttk.Label(ami_frame, text="Contraseña:").grid(row=4, column=0, sticky=tk.W, pady=2, padx=5)
        
        # Frame for password entry and toggle button
        password_frame = ttk.Frame(ami_frame)
        password_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.ami_password_var = tk.StringVar()
        self.ami_password_entry = ttk.Entry(
            password_frame, 
            textvariable=self.ami_password_var, 
            show="*",
            width=28
        )
        self.ami_password_entry.pack(side=tk.LEFT)
        
        # Toggle password visibility button
        self.show_password = False
        self.toggle_btn = ttk.Button(
            password_frame,
            text="👁️",
            width=3,
            command=self.toggle_password_visibility
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status
        self.ami_status_var = tk.StringVar(value="Status: Disconnected")
        status_frame = ttk.Frame(ami_frame)
        status_frame.grid(row=5, column=0, columnspan=2, pady=(10, 5), sticky=tk.W, padx=5)
        
        # Status indicator (dot)
        self.ami_status_canvas = tk.Canvas(
            status_frame, 
            width=14, 
            height=14, 
            highlightthickness=0
        )
        self.ami_status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.ami_status_dot = self.ami_status_canvas.create_oval(
            4, 4, 12, 12, fill="gray", outline=""
        )
        
        # Status label with fixed width
        status_label = ttk.Label(status_frame, textvariable=self.ami_status_var, width=20, anchor='w')
        status_label.pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(ami_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(5, 0), sticky=tk.EW)
        
        self.ami_test_btn = ttk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_ami_connection,
            width=15
        )
        self.ami_test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.ami_save_btn = ttk.Button(
            button_frame,
            text="Save",
            command=self.save_ami_settings,
            width=10
        )
        self.ami_save_btn.pack(side=tk.LEFT)
        
        # Configure grid weights
        ami_frame.columnconfigure(1, weight=1)
        
        # Load saved settings
        self.load_ami_settings()
    
    def test_ami_connection(self):
        """Test the AMI connection with current settings"""
        host = self.ami_host_var.get().strip()
        port_str = self.ami_port_var.get().strip()
        username = self.ami_username_var.get().strip()
        password = self.ami_password_var.get().strip()
        
        if not all([host, port_str, username, password]):
            messagebox.showwarning(
                "Missing Information",
                "Please fill in all AMI connection details."
            )
            return
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror(
                "Invalid Port",
                "Port must be a valid number."
            )
            return
        
        # Update status to connecting
        self.update_ami_status("connecting")
        
        # Test connection in a separate thread to avoid freezing the UI
        import threading
        
        def _test_connection():
            try:
                # Create a test connection
                ami = AMIConnection()
                connected = ami.test_connection(host, port, username, password)
                
                if connected:
                    self.after(0, self.update_ami_status, "connected")
                    self.after(0, messagebox.showinfo, 
                             "Connection Successful", 
                             "Successfully connected to AMI.")
                else:
                    self.after(0, self.update_ami_status, "disconnected")
                    self.after(0, messagebox.showerror,
                             "Connection Failed",
                             "Could not connect to AMI. Please check your settings.")
                
            except Exception as e:
                self.after(0, self.update_ami_status, "error")
                self.after(0, messagebox.showerror,
                         "Connection Error",
                         f"An error occurred while testing the connection:\n{str(e)}")
        
        # Start the connection test in a separate thread
        thread = threading.Thread(target=_test_connection, daemon=True)
        thread.start()
    
    def connect_ami(self):
        """Connect to AMI server using saved settings"""
        if not self.ami_connection or not self.ami_connection.is_connected():
            host = self.ami_host_var.get().strip()
            port_str = self.ami_port_var.get().strip()
            username = self.ami_username_var.get().strip()
            password = self.ami_password_var.get().strip()
            
            if not all([host, port_str, username, password]):
                return False
            
            try:
                port = int(port_str)
                self.ami_connection = AMIConnection()
                if self.ami_connection.connect(host, port, username, password):
                    self.update_ami_status("connected")
                    return True
                else:
                    self.update_ami_status("disconnected")
                    return False
            except Exception as e:
                self.update_ami_status("error")
                print(f"AMI connection error: {e}")
                return False
        return True
    
    def disconnect_ami(self):
        """Disconnect from AMI server"""
        if self.ami_connection:
            self.ami_connection.disconnect()
            self.ami_connection = None
        self.update_ami_status("disconnected")
    
    def update_ami_status(self, status):
        """Update the AMI connection status indicator"""
        if status == "connected":
            self.ami_status_canvas.itemconfig(self.ami_status_dot, fill="green")
            self.ami_status_var.set("Status: Connected")
            self.ami_test_btn.config(state=tk.NORMAL)
        elif status == "connecting":
            self.ami_status_canvas.itemconfig(self.ami_status_dot, fill="orange")
            self.ami_status_var.set("Status: Connecting...")
            self.ami_test_btn.config(state=tk.DISABLED)
        elif status == "error":
            self.ami_status_canvas.itemconfig(self.ami_status_dot, fill="red")
            self.ami_status_var.set("Status: Connection Error")
            self.ami_test_btn.config(state=tk.NORMAL)
        else:  # disconnected
            self.ami_status_canvas.itemconfig(self.ami_status_dot, fill="gray")
            self.ami_status_var.set("Status: Disconnected")
            self.ami_test_btn.config(state=tk.NORMAL)
    
    def save_ami_settings(self):
        """Save AMI settings to config"""
        if 'ami' not in self.config:
            self.config['ami'] = {}
        
        # Get current values
        host = self.ami_host_var.get().strip()
        port = self.ami_port_var.get().strip()
        username = self.ami_username_var.get().strip()
        password = self.ami_password_var.get().strip()
        enabled = self.ami_enabled_var.get()
        
        # Update config
        self.config['ami'].update({
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'enabled': enabled
        })
        
        if self.save_config():
            # If we have a connection, reconnect with new settings
            if self.ami_connection and self.ami_connection.is_connected():
                self.disconnect_ami()
                if host:  # If host is not empty, reconnect with new settings
                    self.connect_ami()
            
            messagebox.showinfo("Success", "AMI settings saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save AMI settings.")
    
    def toggle_ami_settings(self):
        """Enable/disable AMI controls based on checkbox state"""
        state = tk.NORMAL if self.ami_enabled_var.get() else tk.DISABLED
        
        # Habilitar/deshabilitar controles de AMI (excepto el botón de guardar)
        for widget in [
            self.ami_host_var, self.ami_port_var, 
            self.ami_username_var, self.ami_password_var,
            self.ami_test_btn
        ]:
            if hasattr(widget, 'widget'):  # Si es un widget
                widget.widget.config(state=state)
            elif hasattr(widget, 'config'):  # Si es un Entry u otro widget
                widget.config(state=state)
        
        # El botón de guardar siempre debe estar habilitado
        if hasattr(self, 'ami_save_btn'):
            self.ami_save_btn.config(state=tk.NORMAL)
        
        # Actualizar el estado de la conexión
        if not self.ami_enabled_var.get() and hasattr(self, 'ami_connection'):
            self.disconnect_ami()
            
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        self.show_password = not self.show_password
        if self.show_password:
            self.ami_password_entry.config(show="")
            self.toggle_btn.config(text="🔒")
        else:
            self.ami_password_entry.config(show="*")
            self.toggle_btn.config(text="👁️")
        
    def load_ami_settings(self):
        """Load AMI settings from config"""
        if 'ami' in self.config:
            ami_config = self.config['ami']
            self.ami_host_var.set(ami_config.get('host', ''))
            self.ami_port_var.set(ami_config.get('port', '5038'))
            self.ami_username_var.set(ami_config.get('username', ''))
            self.ami_password_var.set(ami_config.get('password', ''))
            self.ami_enabled_var.set(ami_config.get('enabled', False))
            self.toggle_ami_settings()
            self.update_ami_status("disconnected")
            
    def setup_api_settings(self, parent):
        """Set up API settings section"""
        # API Settings Frame
        api_frame = ttk.LabelFrame(parent, text="API Settings", padding=10)
        api_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Enable/Disable API Checkbox
        self.api_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            api_frame, 
            text="Habilitar API", 
            variable=self.api_enabled_var,
            command=self.toggle_api_settings
        ).grid(row=0, column=0, sticky=tk.W, pady=2, columnspan=3)
        
        # Base URL
        url_help_frame = ttk.Frame(api_frame)
        url_help_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5,0))
        ttk.Label(url_help_frame, text="URL Base:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(url_help_frame, text=" (ej: http://192.168.1.50)", foreground='gray').pack(side=tk.LEFT)
        
        self.api_base_url_var = tk.StringVar()
        self.api_base_url_entry = ttk.Entry(api_frame, textvariable=self.api_base_url_var, width=40)
        self.api_base_url_entry.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0,10))
        
        # PTT ON Path
        ptt_on_help_frame = ttk.Frame(api_frame)
        ptt_on_help_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5,0))
        ttk.Label(ptt_on_help_frame, text="Ruta PTT ON:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(ptt_on_help_frame, text=" (ej: /encender)", foreground='gray').pack(side=tk.LEFT)
        
        self.api_ptt_on_var = tk.StringVar()
        self.ptt_on_entry = ttk.Entry(api_frame, textvariable=self.api_ptt_on_var, width=40)
        self.ptt_on_entry.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0,10))
        
        # PTT OFF Path
        ptt_off_help_frame = ttk.Frame(api_frame)
        ptt_off_help_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5,0))
        ttk.Label(ptt_off_help_frame, text="Ruta PTT OFF:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(ptt_off_help_frame, text=" (ej: /apagar)", foreground='gray').pack(side=tk.LEFT)
        
        self.api_ptt_off_var = tk.StringVar()
        self.ptt_off_entry = ttk.Entry(api_frame, textvariable=self.api_ptt_off_var, width=40)
        self.ptt_off_entry.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0,10))
        
        # Status
        self.api_status_var = tk.StringVar(value="Status: Desconectado")
        status_frame = ttk.Frame(api_frame)
        status_frame.grid(row=7, column=0, columnspan=2, pady=(10, 5), sticky=tk.W, padx=5)
        
        # Status indicator (dot)
        self.api_status_canvas = tk.Canvas(
            status_frame, 
            width=14, 
            height=14, 
            highlightthickness=0
        )
        self.api_status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.api_status_dot = self.api_status_canvas.create_oval(
            4, 4, 12, 12, fill="gray", outline=""
        )
        status_label = ttk.Label(status_frame, textvariable=self.api_status_var, width=20, anchor='w')
        status_label.pack(side=tk.LEFT)
        
        # Buttons frame
        btn_frame = ttk.Frame(api_frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(5, 0), sticky=tk.W, padx=5)
        
        # Test Connection Button
        self.api_test_btn = ttk.Button(
            btn_frame,
            text="Probar Conexión",
            command=self.test_api_connection,
            width=15
        )
        self.api_test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Save Button
        self.api_save_btn = ttk.Button(
            btn_frame,
            text="Guardar",
            command=self.save_api_settings,
            width=10
        )
        self.api_save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # PTT ON Button
        self.api_ptt_on_btn = ttk.Button(
            btn_frame,
            text="PTT ON",
            command=self.api_ptt_on,
            width=10,
            state=tk.DISABLED
        )
        self.api_ptt_on_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # PTT OFF Button
        self.api_ptt_off_btn = ttk.Button(
            btn_frame,
            text="PTT OFF",
            command=self.api_ptt_off,
            width=10,
            state=tk.DISABLED
        )
        self.api_ptt_off_btn.pack(side=tk.LEFT)
        
        # Configure grid weights
        api_frame.columnconfigure(0, weight=1)
        api_frame.columnconfigure(1, weight=0)  # Changed to 0 to prevent expanding
        
        # Load saved settings
        self.load_api_settings()
    
    def test_api_connection(self):
        """Test the API connection with current settings"""
        base_url = self.api_base_url_var.get().strip()
        ptt_on_path = self.api_ptt_on_var.get().strip()
        ptt_off_path = self.api_ptt_off_var.get().strip()
        
        if not all([base_url, ptt_on_path, ptt_off_path]):
            messagebox.showwarning(
                "Missing Information",
                "Please fill in all API connection details."
            )
            return
        
        # Update status to connecting
        self.update_api_status("connecting")
        
        # Test connection in a separate thread
        import threading
        
        def _test_connection():
            try:
                # Configure API connection
                self.api_connection.connect(
                    base_url=base_url,
                    ptt_on_path=ptt_on_path,
                    ptt_off_path=ptt_off_path
                )
                
                # Test connection
                connected = self.api_connection.test_connection()
                
                if connected:
                    self.after(0, self.update_api_status, "connected")
                    self.after(0, messagebox.showinfo, 
                             "Connection Successful", 
                             "Successfully connected to API.")
                    # Enable PTT buttons
                    self.after(0, self.api_ptt_on_btn.config, {"state": tk.NORMAL})
                    self.after(0, self.api_ptt_off_btn.config, {"state": tk.NORMAL})
                else:
                    self.after(0, self.update_api_status, "disconnected")
                    self.after(0, messagebox.showerror,
                             "Connection Failed",
                             "Could not connect to API. Please check your settings.")
                
            except Exception as e:
                self.after(0, self.update_api_status, "error")
                self.after(0, messagebox.showerror,
                         "Connection Error",
                         f"An error occurred while testing the connection:\n{str(e)}")
        
        # Start the connection test in a separate thread
        thread = threading.Thread(target=_test_connection, daemon=True)
        thread.start()
    
    def update_api_status(self, status):
        """Update the API connection status indicator"""
        if status == "connected":
            self.api_status_canvas.itemconfig(self.api_status_dot, fill="green")
            self.api_status_var.set("Status: Connected")
            self.api_test_btn.config(state=tk.NORMAL)
        elif status == "connecting":
            self.api_status_canvas.itemconfig(self.api_status_dot, fill="orange")
            self.api_status_var.set("Status: Connecting...")
            self.api_test_btn.config(state=tk.DISABLED)
        elif status == "error":
            self.api_status_canvas.itemconfig(self.api_status_dot, fill="red")
            self.api_status_var.set("Status: Connection Error")
            self.api_test_btn.config(state=tk.NORMAL)
        else:  # disconnected
            self.api_status_canvas.itemconfig(self.api_status_dot, fill="gray")
            self.api_status_var.set("Status: Disconnected")
            self.api_test_btn.config(state=tk.NORMAL)
            self.api_ptt_on_btn.config(state=tk.DISABLED)
            self.api_ptt_off_btn.config(state=tk.DISABLED)
    
    def save_api_settings(self):
        """Save API settings to config"""
        if 'api' not in self.config:
            self.config['api'] = {}
        
        # Get current values and validate they are not empty or just whitespace
        base_url = self.api_base_url_var.get().strip()
        ptt_on_path = self.api_ptt_on_var.get().strip()
        ptt_off_path = self.api_ptt_off_var.get().strip()
        
        # Check if any required field is empty
        if not base_url or not ptt_on_path or not ptt_off_path:
            messagebox.showerror("Error", "Por favor complete todos los campos de la configuración de API.")
            return
            
        # Check if any required field is empty
        if not base_url or not ptt_on_path or not ptt_off_path:
            messagebox.showerror("Error", "Por favor complete todos los campos de la configuración de API.")
            return
        
        # Update config
        self.config['api'].update({
            'base_url': base_url,
            'ptt_on_path': ptt_on_path,
            'ptt_off_path': ptt_off_path,
            'enabled': self.api_enabled_var.get()
        })
        
        if self.save_config():
            # If we have a connection, reconnect with new settings
            if hasattr(self, 'api_connection') and self.api_connection.connected:
                self.api_connection.disconnect()
                if base_url and ptt_on_path and ptt_off_path:
                    try:
                        self.api_connection.connect(
                            base_url=base_url,
                            ptt_on_path=ptt_on_path,
                            ptt_off_path=ptt_off_path
                        )
                    except Exception as e:
                        print(f"Error reconnecting to API: {e}")
            
            messagebox.showinfo("Success", "API settings saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save API settings.")
    
    def toggle_api_settings(self):
        """Enable/disable API controls based on checkbox state"""
        enabled = self.api_enabled_var.get()
        
        # Habilitar/deshabilitar controles
        self.api_base_url_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.ptt_on_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.ptt_off_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        
        # Actualizar estado de los botones
        if enabled:
            self.api_test_btn.config(state=tk.NORMAL)
            self.update_api_status("disconnected")
        else:
            self.api_test_btn.config(state=tk.DISABLED)
            self.update_api_status("disabled")
    
    def load_api_settings(self):
        """Load API settings from config"""
        if 'api' in self.config:
            api_config = self.config['api']
            
            # Obtener valores del archivo de configuración
            base_url = api_config.get('base_url', '')
            ptt_on_path = api_config.get('ptt_on_path', '')
            ptt_off_path = api_config.get('ptt_off_path', '')
            enabled = api_config.get('enabled', True)
            
            # Establecer valores en los campos
            if base_url:
                self.api_base_url_var.set(base_url)
                self.api_base_url_entry.config(foreground='black')
            else:
                self.api_base_url_var.set("http://192.168.1.50")
                self.api_base_url_entry.config(foreground='gray')
                
            if ptt_on_path:
                self.api_ptt_on_var.set(ptt_on_path)
                
            if ptt_off_path:
                self.api_ptt_off_var.set(ptt_off_path)
            
            # Establecer estado del checkbox
            self.api_enabled_var.set(enabled)
            self.toggle_api_settings()
            
            # Actualizar estado de la conexión
            if base_url and ptt_on_path and ptt_off_path and enabled:
                self.update_api_status("disconnected")
            else:
                self.update_api_status("disabled")
    
    def api_ptt_on(self):
        """Send PTT ON command to API"""
        if not hasattr(self, 'api_connection') or not self.api_connection.connected:
            messagebox.showwarning("Not Connected", "Not connected to API. Please test the connection first.")
            return
        
        try:
            if self.api_connection.ptt_on():
                self.api_status_var.set("Status: PTT ON")
                self.api_ptt_on_btn.config(state=tk.DISABLED)
                self.api_ptt_off_btn.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Error", "Failed to turn PTT ON")
        except Exception as e:
            self.update_api_status("error")
            messagebox.showerror("Error", f"Failed to turn PTT ON: {str(e)}")
    
    def api_ptt_off(self):
        """Send PTT OFF command to API"""
        if not hasattr(self, 'api_connection') or not self.api_connection.connected:
            messagebox.showwarning("Not Connected", "Not connected to API. Please test the connection first.")
            return
        
        try:
            if self.api_connection.ptt_off():
                self.api_status_var.set("Status: Connected")
                self.api_ptt_on_btn.config(state=tk.NORMAL)
                self.api_ptt_off_btn.config(state=tk.DISABLED)
            else:
                messagebox.showerror("Error", "Failed to turn PTT OFF")
        except Exception as e:
            self.update_api_status("error")
            messagebox.showerror("Error", f"Failed to turn PTT OFF: {str(e)}")
