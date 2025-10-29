import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from func.events import get_event_types, get_event, save_event, get_db_connection

class StudioTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.event_types = {}
        self.current_event_id = None
        # Dictionary to map listbox indices to event IDs
        self.event_id_map = {}
        self.setup_ui()
        self.load_events()
        
    def load_events(self):
        """Load events into the listbox"""
        try:
            conn = get_db_connection()
            if conn is None:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
                
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT e.id, e.nombre, et.nombre as tipo
                    FROM eventos e
                    LEFT JOIN eventos_type et ON e.tipo_evento_id = et.id
                    ORDER BY e.fecha_creacion DESC
                """)
                
                self.events_listbox.delete(0, tk.END)
                self.event_id_map.clear()  # Clear the existing map
                
                for event_id, nombre, tipo in cursor.fetchall():
                    # Store the event ID in our map
                    index = self.events_listbox.size()
                    self.event_id_map[index] = event_id
                    # Add the item to the listbox
                    self.events_listbox.insert(tk.END, f"{nombre} ({tipo})")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar eventos: {e}")
            finally:
                conn.close()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error de conexión: {e}")
            
    def get_selected_event_id(self):
        """Get the ID of the currently selected event"""
        selection = self.events_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        return self.event_id_map.get(index)
            
    def clear_event_form(self):
        """Clear the event form"""
        self.current_event_id = None
        self.event_id_var.set("")
        self.event_name_var.set("")
        if self.event_type_combo['values']:
            self.event_type_combo.current(0)
            
    def on_event_select(self, event):
        """Handle event selection from list"""
        self.edit_selected_event()
        
    def edit_selected_event(self):
        """Load selected event for editing"""
        event_id = self.get_selected_event_id()
        if event_id is None:
            return
            
        try:
            event = get_event(event_id)
            
            if event:
                self.current_event_id = event[0]
                self.event_id_var.set(str(event[0]))
                self.event_name_var.set(event[1])
                
                # Set the event type in the combobox
                if event[3]:  # If there's a type name
                    for i, name in enumerate(self.event_type_combo['values']):
                        if name == event[3]:
                            self.event_type_combo.current(i)
                            break
                            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar el evento: {e}")
            
    def delete_selected_event(self):
        """Delete the selected event"""
        event_id = self.get_selected_event_id()
        if event_id is None:
            messagebox.showwarning("Advertencia", "Por favor selecciona un evento para eliminar")
            return
            
        if not messagebox.askyesno("Confirmar", "¿Estás seguro de que deseas eliminar este evento?"):
            return
            
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
                
            cursor = conn.cursor()
            cursor.execute("DELETE FROM eventos WHERE id = ?", (event_id,))
            conn.commit()
            
            # Reload events and clear the form
            self.load_events()
            self.clear_event_form()
            messagebox.showinfo("Éxito", "Evento eliminado correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar el evento: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
            
    def load_event_types(self):
        """Load event types into the combobox"""
        try:
            event_types = get_event_types()
            self.event_types = {name: id for id, name in event_types}
            self.event_type_combo['values'] = list(self.event_types.keys())
            if self.event_types:
                self.event_type_combo.current(0)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los tipos de evento: {e}")
    
    def save_event(self):
        """Save the current event"""
        try:
            name = self.event_name_var.get().strip()
            event_type_name = self.event_type_var.get()
            
            if not name:
                messagebox.showwarning("Campo requerido", "Por favor ingrese un nombre para el evento")
                return
                
            if not event_type_name:
                messagebox.showwarning("Campo requerido", "Por favor seleccione un tipo de evento")
                return
                
            event_type_id = self.event_types.get(event_type_name)
            if not event_type_id:
                messagebox.showerror("Error", "Tipo de evento no válido")
                return
                
            # Save the event
            event_id = self.event_id_var.get()
            saved_id = save_event(int(event_id) if event_id else None, name, event_type_id)
            
            if saved_id:
                self.event_id_var.set(str(saved_id))
                self.load_events()  # Refresh the events list
                self.clear_event_form()  # Clear the form
                messagebox.showinfo("Éxito", "Evento guardado correctamente")
            else:
                messagebox.showerror("Error", "No se pudo guardar el evento")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar el evento: {str(e)}")
    
    def setup_ui(self):
        """Set up the studio tab UI"""
        # Main container with padding
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create paned window for resizable panels
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Left panel - Event list
        left_panel = ttk.Frame(paned, padding="5")
        paned.add(left_panel, weight=1)
        
        # Right panel - Event details and sections
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=3)
        
        # Configure right panel grid
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)
        
        # Top section - Event details
        event_frame = ttk.LabelFrame(right_panel, text="Detalles del Evento", padding="5")
        event_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Event name
        ttk.Label(event_frame, text="Nombre:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.event_name_var = tk.StringVar()
        ttk.Entry(event_frame, textvariable=self.event_name_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        # Event type
        ttk.Label(event_frame, text="Tipo:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.event_type_combo = ttk.Combobox(event_frame, state='readonly', width=37)
        self.event_type_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        self.load_event_types()
        
        # Buttons frame
        btn_frame = ttk.Frame(event_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Nuevo", command=self.clear_event_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=self.save_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_selected_event).pack(side=tk.LEFT, padx=5)
        
        # Configure columns to expand
        event_frame.columnconfigure(1, weight=1)
        
        # Bottom section - Sections notebook
        self.sections_notebook = ttk.Notebook(right_panel)
        self.sections_notebook.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # TTS Tab
        self.tts_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.tts_tab, text='TTS')
        self.setup_tts_tab()
        
        # Audio Tab
        self.audio_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.audio_tab, text='Audio')
        self.setup_audio_tab()
        
        # Efectos Tab
        self.effects_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.effects_tab, text='Efectos')
        self.setup_effects_tab()
        
        # Create ID Evento frame
        id_frame = ttk.LabelFrame(left_panel, text="ID Evento", padding="5")
        id_frame.grid(row=0, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
        
        # Event ID
        ttk.Label(id_frame, text="ID:").grid(row=0, column=0, sticky='w', pady=2, padx=5)
        self.event_id_var = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.event_id_var, state='readonly', width=10).grid(row=0, column=1, sticky='w', pady=2)
        
        # Create Event Details frame
        event_details_frame = ttk.LabelFrame(left_panel, text="Detalles del Evento", padding="5")
        event_details_frame.grid(row=1, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
        
        # Event Name
        ttk.Label(event_details_frame, text="Nombre:").grid(row=0, column=0, sticky='w', pady=2, padx=5)
        self.event_name_var = tk.StringVar()
        ttk.Entry(event_details_frame, textvariable=self.event_name_var, width=30).grid(row=0, column=1, columnspan=3, sticky='w', pady=2)
        
        # Event Type
        ttk.Label(event_details_frame, text="Tipo:").grid(row=1, column=0, sticky='w', pady=2, padx=5)
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(
            event_details_frame, 
            textvariable=self.event_type_var,
            state='readonly',
            width=27
        )
        self.event_type_combo.grid(row=1, column=1, columnspan=3, sticky='w', pady=2)
        
        # Load event types
        self.load_event_types()
        
        # Buttons frame
        button_frame = ttk.Frame(event_details_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')
        
        # Save button
        ttk.Button(
            button_frame, 
            text="Guardar", 
            command=self.save_event,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Clear button
        ttk.Button(
            button_frame,
            text="Nuevo",
            command=self.clear_event_form,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Events list
        ttk.Label(left_panel, text="Eventos:").grid(row=2, column=0, columnspan=4, sticky='w', pady=(10, 5), padx=5)
        
        # Create a frame for the listbox and scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.grid(row=3, column=0, columnspan=4, sticky='nsew', padx=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Create listbox
        self.events_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            width=40
        )
        self.events_listbox.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=self.events_listbox.yview)
        
        # Configure grid weights
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double click to edit
        self.events_listbox.bind('<Double-1>', self.on_event_select)
        
        # Buttons frame for edit/delete
        btn_frame = ttk.Frame(left_panel)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=5, sticky='ew')
        
        ttk.Button(
            btn_frame,
            text="Editar",
            command=self.edit_selected_event,
            width=10
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Eliminar",
            command=self.delete_selected_event,
            width=10
        ).grid(row=0, column=1, padx=2)
        
        # Configure button frame grid
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        # Right panel - Audio controls
        right_panel = ttk.Frame(self)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        
        # Configure grid weights for the main container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Audio waveform display (moved to right panel)
        waveform_frame = ttk.LabelFrame(right_panel, text="Onda de audio", padding="5")
        waveform_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        
        # Placeholder for waveform visualization
        self.waveform_canvas = tk.Canvas(waveform_frame, bg='#f0f0f0', height=150)
        self.waveform_canvas.grid(row=0, column=0, sticky='nsew')
        
        # Configure grid weights for waveform frame
        waveform_frame.grid_rowconfigure(0, weight=1)
        waveform_frame.grid_columnconfigure(0, weight=1)
        
        self.draw_waveform_placeholder(self.waveform_canvas)
        
        # Transport controls (moved to right panel)
        transport_frame = ttk.Frame(right_panel)
        transport_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        
        # Configure grid weights for right panel
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=0)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Transport buttons
        ttk.Button(transport_frame, text="|◀", width=5, command=self.skip_backward).grid(row=0, column=0, padx=2)
        ttk.Button(transport_frame, text="◀▶", width=5, command=self.play).grid(row=0, column=1, padx=2)
        ttk.Button(transport_frame, text="■", width=5, command=self.stop).grid(row=0, column=2, padx=2)
        ttk.Button(transport_frame, text="▶▶", width=5, command=self.record).grid(row=0, column=3, padx=2)
        ttk.Button(transport_frame, text="▶|", width=5, command=self.skip_forward).grid(row=0, column=4, padx=2)
        
        # Time display
        self.time_var = tk.StringVar(value="00:00.000 / 00:00.000")
        ttk.Label(transport_frame, textvariable=self.time_var).grid(row=0, column=5, padx=10)
        
        # Configure transport frame columns
        transport_frame.grid_columnconfigure(5, weight=1)
        
        # Volume control - moved to right panel
        volume_frame = ttk.Frame(right_panel)
        volume_frame.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        
        ttk.Label(volume_frame, text="Volumen:").grid(row=0, column=0, padx=(0, 5))
        self.volume_scale = ttk.Scale(
            volume_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            value=80
        )
        self.volume_scale.grid(row=0, column=1, sticky='ew')
        
        # Configure volume frame columns
        volume_frame.grid_columnconfigure(1, weight=1)
        
        # Right panel - Tracks and mixer
        right_panel = ttk.Frame(self, width=250)
        right_panel.grid(row=0, column=2, sticky='nsew', padx=(10, 0))
        
        # Configure grid weights for right panel
        self.grid_columnconfigure(2, weight=0)  # Fixed width for right panel
        
        # Tracks list
        tracks_frame = ttk.LabelFrame(right_panel, text="Pistas", padding="5")
        tracks_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        
        # Configure grid weights for tracks frame
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Track list with scrollbar
        track_list_frame = ttk.Frame(tracks_frame)
        track_list_frame.grid(row=0, column=0, sticky='nsew')
        
        scrollbar = ttk.Scrollbar(track_list_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.track_listbox = tk.Listbox(
            track_list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            selectmode=tk.SINGLE
        )
        self.track_listbox.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=self.track_listbox.yview)
        
        # Configure grid weights for track list frame
        track_list_frame.grid_rowconfigure(0, weight=1)
        track_list_frame.grid_columnconfigure(0, weight=1)
        
        # Track controls
        track_controls = ttk.Frame(tracks_frame)
        track_controls.grid(row=1, column=0, sticky='ew', pady=(5, 0))
        
        ttk.Button(track_controls, text="+", width=3, command=self.add_track).grid(row=0, column=0, padx=2)
        ttk.Button(track_controls, text="-", width=3, command=self.remove_track).grid(row=0, column=1, padx=2)
        ttk.Button(track_controls, text="M", width=3, command=self.mute_track).grid(row=0, column=2, padx=2)
        ttk.Button(track_controls, text="S", width=3, command=self.solo_track).grid(row=0, column=3, padx=2)
        
        # Configure track controls grid
        for i in range(4):
            track_controls.grid_columnconfigure(i, weight=1)
        
        # Effects panel
        effects_frame = ttk.Frame(right_panel)
        effects_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
        
        effects_list = ttk.Combobox(
            effects_frame,
            values=["Sin efectos", "Ecualizador", "Reverb", "Delay", "Compresor"],
            state="readonly"
        )
        effects_list.current(0)
        effects_list.grid(row=0, column=0, sticky='ew', pady=5)
        effects_frame.grid_columnconfigure(0, weight=1)
        
        # Recording settings
        record_frame = ttk.LabelFrame(right_panel, text="Grabación", padding="5")
        record_frame.grid(row=2, column=0, sticky='ew')
        
        self.record_source = tk.StringVar(value="Micrófono")
        
        ttk.Radiobutton(
            record_frame, 
            text="Micrófono", 
            variable=self.record_source, 
            value="Micrófono"
        ).grid(row=0, column=0, sticky='w', pady=2)
        
        ttk.Radiobutton(
            record_frame, 
            text="Entrada de línea", 
            variable=self.record_source, 
            value="Línea"
        ).grid(row=1, column=0, sticky='w', pady=2)
        
        ttk.Radiobutton(
            record_frame, 
            text="Reproducción estéreo", 
            variable=self.record_source, 
            value="Estéreo"
        ).grid(row=2, column=0, sticky='w', pady=2)
        
        # Configure record frame grid
        record_frame.grid_columnconfigure(0, weight=1)
    
    def draw_waveform_placeholder(self, canvas):
        """Draw a placeholder waveform on the canvas"""
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Clear canvas
        canvas.delete("waveform")
        
        # Draw a simple waveform
        center_y = height // 2
        amplitude = height * 0.4
        
        points = []
        for x in range(0, width, 2):
            # Simple sine wave pattern
            t = x / width * 20
            y = center_y + amplitude * (0.7 * self.sine_wave(t) + 0.3 * self.sine_wave(t * 3 + 1) * 0.5)
            points.extend([x, y])
        
        if points:
            canvas.create_line(*points, fill="#4a7cff", tags="waveform", smooth=True)
        
        # Schedule the next update
        self.after(100, lambda: self.draw_waveform_placeholder(canvas))
    
    def sine_wave(self, t):
        """Generate a sine wave value"""
        import math
        return math.sin(t)
    
    def play(self):
        """Play button handler"""
        print("Play pressed")
    
    def stop(self):
        """Stop button handler"""
        print("Stop pressed")
    
    def record(self):
        """Record button handler"""
        print(f"Recording from {self.record_source.get()}")
    
    def skip_backward(self):
        """Skip backward button handler"""
        print("Skip backward")
    
    def skip_forward(self):
        """Skip forward button handler"""
        print("Skip forward")
    
    def add_track(self):
        """Add a new track"""
        track_num = self.track_list.size() + 1
        self.track_list.insert(tk.END, f"Pista {track_num}")
    
    def remove_track(self):
        """Remove selected track"""
        selection = self.track_list.curselection()
        if selection:
            self.track_list.delete(selection[0])
    
    def mute_track(self):
        """Mute selected track"""
        selection = self.track_list.curselection()
        if selection:
            print(f"Mute track {selection[0] + 1}")
    
    def solo_track(self):
        """Solo selected track"""
        selection = self.track_list.curselection()
        if selection:
            print(f"Solo track {selection[0] + 1}")
            
    # ===== TTS Tab Methods =====
    def setup_tts_tab(self):
        """Set up the TTS tab"""
        # Configure grid
        self.tts_tab.columnconfigure(0, weight=1)
        self.tts_tab.rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ttk.Frame(self.tts_tab)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        ttk.Button(toolbar, text="Agregar TTS", command=self.add_tts_section).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Eliminar", command=self.remove_tts_section).pack(side=tk.LEFT, padx=2)
        
        # TTS List
        tts_frame = ttk.LabelFrame(self.tts_tab, text="Secciones de TTS")
        tts_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        tts_frame.columnconfigure(0, weight=1)
        tts_frame.rowconfigure(0, weight=1)
        
        # Treeview for TTS sections
        columns = ('id', 'texto', 'voz', 'idioma', 'duracion')
        self.tts_tree = ttk.Treeview(
            tts_frame, 
            columns=columns[1:], 
            show='headings',
            selectmode='browse'
        )
        
        # Define headings
        self.tts_tree.heading('texto', text='Texto')
        self.tts_tree.heading('voz', text='Voz')
        self.tts_tree.heading('idioma', text='Idioma')
        self.tts_tree.heading('duracion', text='Duración')
        
        # Configure column widths
        self.tts_tree.column('texto', width=300)
        self.tts_tree.column('voz', width=100, anchor='center')
        self.tts_tree.column('idioma', width=80, anchor='center')
        self.tts_tree.column('duracion', width=80, anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tts_frame, orient=tk.VERTICAL, command=self.tts_tree.yview)
        self.tts_tree.configure(yscroll=scrollbar.set)
        
        # Grid the tree and scrollbar
        self.tts_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Bind double click to edit
        self.tts_tree.bind('<Double-1>', self.edit_tts_section)
    
    def add_tts_section(self):
        """Add a new TTS section"""
        print("Adding new TTS section")
        
    def remove_tts_section(self):
        """Remove selected TTS section"""
        selection = self.tts_tree.selection()
        if selection:
            self.tts_tree.delete(selection[0])
    
    def edit_tts_section(self, event=None):
        """Edit selected TTS section"""
        selection = self.tts_tree.selection()
        if selection:
            print(f"Editing TTS section: {selection[0]}")
    
    # ===== Audio Tab Methods =====
    def setup_audio_tab(self):
        """Set up the audio tab"""
        # Configure grid
        self.audio_tab.columnconfigure(0, weight=1)
        self.audio_tab.rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ttk.Frame(self.audio_tab)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        ttk.Button(toolbar, text="Agregar Audio", command=self.add_audio_section).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Eliminar", command=self.remove_audio_section).pack(side=tk.LEFT, padx=2)
        
        # Audio List
        audio_frame = ttk.LabelFrame(self.audio_tab, text="Archivos de Audio")
        audio_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        audio_frame.columnconfigure(0, weight=1)
        audio_frame.rowconfigure(0, weight=1)
        
        # Treeview for audio sections
        columns = ('id', 'nombre', 'archivo', 'duracion', 'formato')
        self.audio_tree = ttk.Treeview(
            audio_frame, 
            columns=columns[1:], 
            show='headings',
            selectmode='browse'
        )
        
        # Define headings
        self.audio_tree.heading('nombre', text='Nombre')
        self.audio_tree.heading('archivo', text='Archivo')
        self.audio_tree.heading('duracion', text='Duración')
        self.audio_tree.heading('formato', text='Formato')
        
        # Configure column widths
        self.audio_tree.column('nombre', width=150)
        self.audio_tree.column('archivo', width=250)
        self.audio_tree.column('duracion', width=80, anchor='center')
        self.audio_tree.column('formato', width=80, anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(audio_frame, orient=tk.VERTICAL, command=self.audio_tree.yview)
        self.audio_tree.configure(yscroll=scrollbar.set)
        
        # Grid the tree and scrollbar
        self.audio_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Bind double click to play/select
        self.audio_tree.bind('<Double-1>', self.play_audio_section)
    
    def add_audio_section(self):
        """Add a new audio section"""
        print("Adding new audio section")
        
    def remove_audio_section(self):
        """Remove selected audio section"""
        selection = self.audio_tree.selection()
        if selection:
            self.audio_tree.delete(selection[0])
    
    def play_audio_section(self, event=None):
        """Play selected audio section"""
        selection = self.audio_tree.selection()
        if selection:
            print(f"Playing audio section: {selection[0]}")
    
    # ===== Effects Tab Methods =====
    def setup_effects_tab(self):
        """Set up the sound effects tab"""
        # Configure grid
        self.effects_tab.columnconfigure(0, weight=1)
        self.effects_tab.rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ttk.Frame(self.effects_tab)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        ttk.Button(toolbar, text="Agregar Efecto", command=self.add_effect_section).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Eliminar", command=self.remove_effect_section).pack(side=tk.LEFT, padx=2)
        
        # Effects List
        effects_frame = ttk.LabelFrame(self.effects_tab, text="Efectos de Sonido")
        effects_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        effects_frame.columnconfigure(0, weight=1)
        effects_frame.rowconfigure(0, weight=1)
        
        # Treeview for effect sections
        columns = ('id', 'nombre', 'efecto', 'duracion', 'archivo')
        self.effects_tree = ttk.Treeview(
            effects_frame, 
            columns=columns[1:], 
            show='headings',
            selectmode='browse'
        )
        
        # Define headings
        self.effects_tree.heading('nombre', text='Nombre')
        self.effects_tree.heading('efecto', text='Tipo de Efecto')
        self.effects_tree.heading('duracion', text='Duración')
        self.effects_tree.heading('archivo', text='Archivo')
        
        # Configure column widths
        self.effects_tree.column('nombre', width=150)
        self.effects_tree.column('efecto', width=150)
        self.effects_tree.column('duracion', width=80, anchor='center')
        self.effects_tree.column('archivo', width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(effects_frame, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscroll=scrollbar.set)
        
        # Grid the tree and scrollbar
        self.effects_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Bind double click to play/select
        self.effects_tree.bind('<Double-1>', self.play_effect_section)
    
    def add_effect_section(self):
        """Add a new effect section"""
        print("Adding new effect section")
        
    def remove_effect_section(self):
        """Remove selected effect section"""
        selection = self.effects_tree.selection()
        if selection:
            self.effects_tree.delete(selection[0])
    
    def play_effect_section(self, event=None):
        """Play selected effect section"""
        selection = self.effects_tree.selection()
        if selection:
            print(f"Playing effect section: {selection[0]}")
            print(f"Solo track {selection[0] + 1}")
