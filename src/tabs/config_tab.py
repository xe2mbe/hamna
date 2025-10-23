import tkinter as tk
from tkinter import ttk, messagebox

class ConfigTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the configuration tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different configuration sections
        config_notebook = ttk.Notebook(main_frame)
        config_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # General Settings Tab
        general_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_general_settings(general_frame)
        config_notebook.add(general_frame, text="General")
        
        # Audio Settings Tab
        audio_frame = ttk.Frame(config_notebook, padding="10")
        self.setup_audio_settings(audio_frame)
        config_notebook.add(audio_frame, text="Audio")
        
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
    
    def setup_audio_settings(self, parent):
        """Set up audio settings section"""
        # Output Device
        ttk.Label(parent, text="Dispositivo de salida:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.output_device_var = tk.StringVar()
        ttk.Combobox(
            parent,
            textvariable=self.output_device_var,
            values=["Predeterminado", "Auriculares", "Altavoces"],
            state="readonly",
            width=30
        ).grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Sample Rate
        ttk.Label(parent, text="Frecuencia de muestreo:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.sample_rate_var = tk.StringVar(value="44100 Hz")
        ttk.Combobox(
            parent,
            textvariable=self.sample_rate_var,
            values=["44100 Hz", "48000 Hz", "96000 Hz"],
            state="readonly",
            width=15
        ).grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Buffer Size
        ttk.Label(parent, text="Tamaño del búfer:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.buffer_size_var = tk.StringVar(value="512")
        ttk.Combobox(
            parent,
            textvariable=self.buffer_size_var,
            values=["128", "256", "512", "1024", "2048"],
            state="readonly",
            width=10
        ).grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
    
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
