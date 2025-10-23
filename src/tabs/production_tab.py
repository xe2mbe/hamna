import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class ProductionTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the production tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Program list
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Program list
        program_frame = ttk.LabelFrame(left_panel, text="Programas", padding="5")
        program_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Search box
        search_frame = ttk.Frame(program_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind('<KeyRelease>', lambda e: self.filter_programs(search_var.get()))
        
        # Program list with scrollbar
        list_frame = ttk.Frame(program_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.program_list = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            height=15
        )
        self.program_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.program_list.yview)
        
        # Add some sample programs
        self.all_programs = [
            "Noticias de la mañana",
            "Música relajante",
            "Entrevistas",
            "Magazine cultural",
            "Deportes al día",
            "Tertulia política",
            "Música clásica",
            "Programa infantil",
            "Documentales",
            "Actualidad tecnológica"
        ]
        
        for program in sorted(self.all_programs):
            self.program_list.insert(tk.END, program)
        
        # Program controls
        button_frame = ttk.Frame(program_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="Nuevo", command=self.new_program).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Editar", command=self.edit_program).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Eliminar", command=self.delete_program).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Program details and controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Now playing section
        now_playing_frame = ttk.LabelFrame(right_panel, text="En emisión", padding="10")
        now_playing_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.now_playing_var = tk.StringVar(value="Ningún programa en emisión")
        ttk.Label(
            now_playing_frame, 
            textvariable=self.now_playing_var,
            font=('Helvetica', 12, 'bold')
        ).pack(pady=5)
        
        self.time_elapsed_var = tk.StringVar(value="00:00:00 / 00:00:00")
        ttk.Label(
            now_playing_frame, 
            textvariable=self.time_elapsed_var,
            font=('Courier', 10)
        ).pack(pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(
            now_playing_frame, 
            orient=tk.HORIZONTAL,
            length=400,
            mode='determinate',
            variable=self.progress_var
        ).pack(fill=tk.X, pady=5)
        
        # Transport controls
        transport_frame = ttk.Frame(now_playing_frame)
        transport_frame.pack(pady=5)
        
        ttk.Button(
            transport_frame, 
            text="|◀", 
            width=5, 
            command=self.skip_backward
        ).pack(side=tk.LEFT, padx=2)
        
        self.play_button = ttk.Button(
            transport_frame, 
            text="▶", 
            width=5, 
            command=self.toggle_play_pause
        )
        self.play_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            transport_frame, 
            text="■", 
            width=5, 
            command=self.stop
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            transport_frame, 
            text="▶|", 
            width=5, 
            command=self.skip_forward
        ).pack(side=tk.LEFT, padx=2)
        
        # Volume control
        volume_frame = ttk.Frame(now_playing_frame)
        volume_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(volume_frame, text="Volumen:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.volume_var = tk.IntVar(value=80)
        ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=lambda v: self.set_volume(float(v))
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Program schedule
        schedule_frame = ttk.LabelFrame(right_panel, text="Programación", padding="10")
        schedule_frame.pack(fill=tk.BOTH, expand=True)
        
        # Schedule treeview
        columns = ('time', 'program', 'duration', 'status')
        self.schedule_tree = ttk.Treeview(
            schedule_frame,
            columns=columns,
            show='headings',
            selectmode='browse',
            height=8
        )
        
        # Configure columns
        self.schedule_tree.heading('time', text='Hora')
        self.schedule_tree.column('time', width=80, anchor=tk.CENTER)
        
        self.schedule_tree.heading('program', text='Programa')
        self.schedule_tree.column('program', width=200, anchor=tk.W)
        
        self.schedule_tree.heading('duration', text='Duración')
        self.schedule_tree.column('duration', width=80, anchor=tk.CENTER)
        
        self.schedule_tree.heading('status', text='Estado')
        self.schedule_tree.column('status', width=100, anchor=tk.CENTER)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(schedule_frame, orient=tk.VERTICAL, command=self.schedule_tree.yview)
        self.schedule_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.schedule_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add some sample schedule items
        self.add_sample_schedule()
        
        # Status bar
        self.status_var = tk.StringVar()
        ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN, 
            anchor=tk.W
        ).pack(fill=tk.X, pady=(10, 0))
        
        self.update_status("Listo")
        
        # Bind double-click event on program list
        self.program_list.bind('<Double-1>', lambda e: self.play_selected_program())
    
    def add_sample_schedule(self):
        """Add sample schedule items"""
        schedule_items = [
            ("08:00", "Noticias de la mañana", "30:00", "Pendiente"),
            ("08:30", "Música relajante", "60:00", "Pendiente"),
            ("09:30", "Entrevistas", "45:00", "Pendiente"),
            ("10:15", "Magazine cultural", "45:00", "Pendiente"),
            ("11:00", "Deportes al día", "30:00", "Pendiente"),
            ("11:30", "Música clásica", "60:00", "Pendiente"),
            ("12:30", "Noticias del mediodía", "30:00", "Pendiente")
        ]
        
        for item in schedule_items:
            self.schedule_tree.insert('', 'end', values=item)
    
    def filter_programs(self, search_text):
        """Filter program list based on search text"""
        search_text = search_text.lower()
        self.program_list.delete(0, tk.END)
        
        for program in self.all_programs:
            if search_text in program.lower():
                self.program_list.insert(tk.END, program)
    
    def play_selected_program(self):
        """Play the selected program"""
        selection = self.program_list.curselection()
        if not selection:
            return
        
        program_name = self.program_list.get(selection[0])
        self.now_playing_var.set(f"En emisión: {program_name}")
        self.play_button.config(text="⏸")  # Pause symbol
        self.update_status(f"Reproduciendo: {program_name}")
        
        # Start updating the progress bar
        self.update_progress()
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        current_text = self.play_button.cget('text')
        if current_text == "▶":  # Play
            self.play_selected_program()
        else:  # Pause
            self.play_button.config(text="▶")
            self.update_status("Pausado")
    
    def stop(self):
        """Stop playback"""
        self.play_button.config(text="▶")  # Play symbol
        self.now_playing_var.set("Ningún programa en emisión")
        self.time_elapsed_var.set("00:00:00 / 00:00:00")
        self.progress_var.set(0)
        self.update_status("Detenido")
    
    def skip_backward(self):
        """Skip backward 10 seconds"""
        self.update_status("Retrocediendo 10 segundos")
        # Implementation would update the current position
    
    def skip_forward(self):
        """Skip forward 10 seconds"""
        self.update_status("Avanzando 10 segundos")
        # Implementation would update the current position
    
    def set_volume(self, volume):
        """Set playback volume"""
        # Implementation would set the actual volume
        pass
    
    def update_progress(self):
        """Update the progress bar and time display"""
        current_value = self.progress_var.get()
        if current_value < 100 and self.play_button.cget('text') == "⏸":
            # Update progress (simulated)
            self.progress_var.set(current_value + 1)
            
            # Update time display (simulated)
            elapsed_seconds = int((current_value + 1) * 30)  # 30 seconds total
            total_seconds = 30 * 100  # 100% = 30 seconds (for demo)
            
            elapsed_str = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"
            total_str = f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"
            self.time_elapsed_var.set(f"{elapsed_str} / {total_str}")
            
            # Schedule the next update
            self.after(300, self.update_progress)  # Update every 300ms
    
    def new_program(self):
        """Create a new program"""
        self.show_program_dialog()
    
    def edit_program(self):
        """Edit selected program"""
        selection = self.program_list.curselection()
        if not selection:
            messagebox.showwarning("Editar programa", "Por favor seleccione un programa para editar.")
            return
        
        program_name = self.program_list.get(selection[0])
        self.show_program_dialog(program_name)
    
    def delete_program(self):
        """Delete selected program"""
        selection = self.program_list.curselection()
        if not selection:
            messagebox.showwarning("Eliminar programa", "Por favor seleccione un programa para eliminar.")
            return
        
        program_name = self.program_list.get(selection[0])
        if messagebox.askyesno("Confirmar eliminación", f"¿Está seguro de que desea eliminar el programa '{program_name}'?"):
            # In a real app, you would remove it from your data store
            self.all_programs.remove(program_name)
            self.filter_programs("")  # Refresh the list
            self.update_status(f"Programa eliminado: {program_name}")
    
    def show_program_dialog(self, program_name=None):
        """Show program editing dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Nuevo programa" if program_name is None else "Editar programa")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        width = 400
        height = 300
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Form frame
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Program name
        ttk.Label(form_frame, text="Nombre del programa:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=program_name if program_name else "")
        ttk.Entry(form_frame, textvariable=name_var, width=40).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=5
        )
        
        # Description
        ttk.Label(form_frame, text="Descripción:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(form_frame, width=40, height=8)
        desc_text.grid(row=1, column=1, sticky=tk.NSEW, pady=5, padx=5)
        
        # Duration
        ttk.Label(form_frame, text="Duración (minutos):").grid(row=2, column=0, sticky=tk.W, pady=5)
        duration_var = tk.StringVar(value="30")
        ttk.Spinbox(
            form_frame,
            from_=1,
            to=240,
            textvariable=duration_var,
            width=5
        ).grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_program():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre del programa no puede estar vacío.")
                return
            
            # In a real app, you would save the program to your data store
            if program_name is None:  # New program
                if name in self.all_programs:
                    messagebox.showerror("Error", "Ya existe un programa con ese nombre.")
                    return
                self.all_programs.append(name)
                self.filter_programs("")  # Refresh the list
                message = f"Programa '{name}' creado correctamente."
            else:  # Edit existing program
                if name != program_name and name in self.all_programs:
                    messagebox.showerror("Error", "Ya existe un programa con ese nombre.")
                    return
                
                if name != program_name:
                    self.all_programs.remove(program_name)
                    self.all_programs.append(name)
                    self.filter_programs("")  # Refresh the list
                message = f"Programa '{name}' actualizado correctamente."
            
            self.update_status(message)
            dialog.destroy()
        
        ttk.Button(button_frame, text="Guardar", command=save_program).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def update_status(self, message):
        """Update the status bar"""
        self.status_var.set(f" {message}")
        print(f"Status: {message}")  # For debugging
