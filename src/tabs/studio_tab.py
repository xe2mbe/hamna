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
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Eventos section
        left_panel = ttk.LabelFrame(main_frame, text="Sección Eventos", padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10), anchor='n')
        
        # Configure grid weights for left panel
        left_panel.columnconfigure(1, weight=1)
        
        # Event ID
        ttk.Label(left_panel, text="ID Evento:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.event_id_var = tk.StringVar()
        ttk.Entry(left_panel, textvariable=self.event_id_var, state='readonly', width=10).grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Event Name
        ttk.Label(left_panel, text="Nombre Evento:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.event_name_var = tk.StringVar()
        ttk.Entry(left_panel, textvariable=self.event_name_var, width=30).grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=2, padx=5)
        
        # Event Type
        ttk.Label(left_panel, text="Tipo Evento:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(
            left_panel, 
            textvariable=self.event_type_var,
            state='readonly',
            width=27
        )
        self.event_type_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=2, padx=5)
        
        # Load event types
        self.load_event_types()
        
        # Buttons frame
        button_frame = ttk.Frame(left_panel)
        button_frame.grid(row=3, column=0, columnspan=3, pady=5, sticky='ew')
        
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
        ttk.Label(left_panel, text="Eventos:").grid(row=4, column=0, columnspan=3, sticky='w', pady=(10, 5))
        
        # Create a frame for the listbox and scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.grid(row=5, column=0, columnspan=3, sticky='nsew')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox
        self.events_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            width=40
        )
        self.events_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.events_listbox.yview)
        
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
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Eliminar",
            command=self.delete_selected_event,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Audio controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Audio waveform display (moved to right panel)
        waveform_frame = ttk.LabelFrame(right_panel, text="Onda de audio", padding="5")
        waveform_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Placeholder for waveform visualization
        self.waveform_canvas = tk.Canvas(waveform_frame, bg='#f0f0f0', height=150)
        self.waveform_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_waveform_placeholder(self.waveform_canvas)
        
        # Transport controls (moved to right panel)
        transport_frame = ttk.Frame(right_panel)
        transport_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Transport buttons
        ttk.Button(transport_frame, text="|◀", width=5, command=self.skip_backward).pack(side=tk.LEFT, padx=2)
        ttk.Button(transport_frame, text="◀▶", width=5, command=self.play).pack(side=tk.LEFT, padx=2)
        ttk.Button(transport_frame, text="■", width=5, command=self.stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(transport_frame, text="▶▶", width=5, command=self.record).pack(side=tk.LEFT, padx=2)
        ttk.Button(transport_frame, text="▶|", width=5, command=self.skip_forward).pack(side=tk.LEFT, padx=2)
        
        # Time display
        self.time_var = tk.StringVar(value="00:00.000 / 00:00.000")
        ttk.Label(transport_frame, textvariable=self.time_var).pack(side=tk.LEFT, padx=10)
        
        # Volume control - moved to right panel
        volume_frame = ttk.Frame(right_panel)
        volume_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(volume_frame, text="Volumen:").pack(side=tk.LEFT, padx=(0, 5))
        self.volume_scale = ttk.Scale(
            volume_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            value=80
        )
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Right panel - Tracks and mixer
        right_panel = ttk.Frame(main_frame, width=250)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tracks list
        tracks_frame = ttk.LabelFrame(right_panel, text="Pistas", padding="5")
        tracks_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Track list with scrollbar
        track_list_frame = ttk.Frame(tracks_frame)
        track_list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(track_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.track_list = tk.Listbox(
            track_list_frame, 
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            height=8
        )
        self.track_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.track_list.yview)
        
        # Add some sample tracks
        for i in range(1, 6):
            self.track_list.insert(tk.END, f"Pista {i}")
        
        # Track controls
        track_buttons = ttk.Frame(tracks_frame)
        track_buttons.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(track_buttons, text="+", width=3, command=self.add_track).pack(side=tk.LEFT, padx=2)
        ttk.Button(track_buttons, text="-", width=3, command=self.remove_track).pack(side=tk.LEFT, padx=2)
        ttk.Button(track_buttons, text="M", width=3, command=self.mute_track).pack(side=tk.LEFT, padx=2)
        ttk.Button(track_buttons, text="S", width=3, command=self.solo_track).pack(side=tk.LEFT, padx=2)
        
        # Effects panel
        effects_frame = ttk.LabelFrame(right_panel, text="Efectos", padding="5")
        effects_frame.pack(fill=tk.X, pady=(0, 10))
        
        effects_list = ttk.Combobox(
            effects_frame,
            values=["Sin efectos", "Ecualizador", "Reverb", "Delay", "Compresor"],
            state="readonly"
        )
        effects_list.current(0)
        effects_list.pack(fill=tk.X, pady=5)
        
        # Recording settings
        record_frame = ttk.LabelFrame(right_panel, text="Grabación", padding="5")
        record_frame.pack(fill=tk.X)
        
        self.record_source = tk.StringVar(value="Micrófono")
        ttk.Radiobutton(
            record_frame, 
            text="Micrófono", 
            variable=self.record_source, 
            value="Micrófono"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            record_frame, 
            text="Entrada de línea", 
            variable=self.record_source, 
            value="Línea"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            record_frame, 
            text="Reproducción estéreo", 
            variable=self.record_source, 
            value="Estéreo"
        ).pack(anchor=tk.W)
    
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
