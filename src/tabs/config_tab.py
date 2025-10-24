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
        ttk.Label(api_frame, text="Base URL:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)
        self.api_base_url_var = tk.StringVar()
        self.api_base_url_entry = ttk.Entry(api_frame, textvariable=self.api_base_url_var, width=30)
        self.api_base_url_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.api_base_url_entry.insert(0, "http://192.168.1.50")
        self.api_base_url_entry.config(foreground='gray')
        
        def on_entry_click(event, entry_widget, default_text):
            current_text = entry_widget.get()
            if current_text == default_text and entry_widget.cget('foreground') == 'gray':
                entry_widget.delete(0, tk.END)
                entry_widget.config(foreground='black')
                
        def on_focus_out(event, entry_widget, default_text):
            current_text = entry_widget.get()
            if not current_text or current_text == default_text:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, default_text)
                entry_widget.config(foreground='gray')
            else:
                entry_widget.config(foreground='black')
        
        # Bind events for base URL
        self.api_base_url_entry.bind('<FocusIn>', 
                          lambda e: on_entry_click(e, self.api_base_url_entry, "http://192.168.1.50"))
        self.api_base_url_entry.bind('<FocusOut>', 
                          lambda e: on_focus_out(e, self.api_base_url_entry, "http://192.168.1.50"))
        
        # PTT ON Path
        ttk.Label(api_frame, text="PTT ON Path:").grid(row=2, column=0, sticky=tk.W, pady=2, padx=5)
        self.api_ptt_on_var = tk.StringVar()
        self.ptt_on_entry = ttk.Entry(api_frame, textvariable=self.api_ptt_on_var, width=30)
        self.ptt_on_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.ptt_on_entry.insert(0, "/ptt_on")
        self.ptt_on_entry.config(foreground='gray')
        
        # Bind events for PTT ON path
        self.ptt_on_entry.bind('<FocusIn>', 
                         lambda e: on_entry_click(e, self.ptt_on_entry, "/ptt_on"))
        self.ptt_on_entry.bind('<FocusOut>', 
                         lambda e: on_focus_out(e, self.ptt_on_entry, "/ptt_on"))
        
        # PTT OFF Path
        ttk.Label(api_frame, text="PTT OFF Path:").grid(row=3, column=0, sticky=tk.W, pady=2, padx=5)
        self.api_ptt_off_var = tk.StringVar()
        self.ptt_off_entry = ttk.Entry(api_frame, textvariable=self.api_ptt_off_var, width=30)
        self.ptt_off_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        self.ptt_off_entry.insert(0, "/ptt_off")
        self.ptt_off_entry.config(foreground='gray')
        
        # Bind events for PTT OFF path
        self.ptt_off_entry.bind('<FocusIn>', 
                          lambda e: on_entry_click(e, self.ptt_off_entry, "/ptt_off"))
        self.ptt_off_entry.bind('<FocusOut>', 
                          lambda e: on_focus_out(e, self.ptt_off_entry, "/ptt_off"))
        
        # Status
        self.api_status_var = tk.StringVar(value="Status: Desconectado")
        status_frame = ttk.Frame(api_frame)
        status_frame.grid(row=4, column=0, columnspan=2, pady=(10, 5), sticky=tk.W, padx=5)
        
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
        
        # Status label with fixed width
        status_label = ttk.Label(status_frame, textvariable=self.api_status_var, width=20, anchor='w')
        status_label.pack(side=tk.LEFT)
        
        # Buttons frame
        btn_frame = ttk.Frame(api_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(5, 0), sticky=tk.W, padx=5)
        
        # Test Connection Button
        self.api_test_btn = ttk.Button(
            btn_frame,
            text="Test Connection",
            command=self.test_api_connection,
            width=15
        )
        self.api_test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Save Button
        self.api_save_btn = ttk.Button(
            btn_frame,
            text="Save",
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
        
        # Get current values
        base_url = self.api_base_url_var.get().strip()
        ptt_on_path = self.api_ptt_on_var.get().strip()
        ptt_off_path = self.api_ptt_off_var.get().strip()
        
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
                self.ptt_on_entry.config(foreground='black')
            else:
                self.api_ptt_on_var.set("/ptt_on")
                self.ptt_on_entry.config(foreground='gray')
                
            if ptt_off_path:
                self.api_ptt_off_var.set(ptt_off_path)
                self.ptt_off_entry.config(foreground='black')
            else:
                self.api_ptt_off_var.set("/ptt_off")
                self.ptt_off_entry.config(foreground='gray')
            
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
