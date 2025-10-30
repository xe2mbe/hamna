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
        # Referencias a los frames
        self.event_frame = None
        self.right_panel = None
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
        """Clear the event form and reset fields to default state"""
        self.current_event_id = None
        self.event_id_var.set("")
        self.event_name_var.set("")
        
        # Resetear el estado de los campos
        self.event_id_entry.config(state='normal')
        self.event_name_entry.config(state='normal')
        
        # Limpiar los campos
        self.event_id_entry.delete(0, tk.END)
        self.event_name_entry.delete(0, tk.END)
        
        # Configurar el estado inicial
        self.event_id_entry.config(state='readonly')
        self.event_name_entry.config(state='normal')
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
            messagebox.showerror("Error", f"Error al cargar el evento: {str(e)}")
            logger.error(f"Error loading event: {str(e)}", exc_info=True)
            
    def edit_details(self):
        """Copia el ID y nombre del evento seleccionado a la sección de detalles en el panel derecho"""
        # Obtener el evento seleccionado en la lista
        selection = self.events_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selección requerida", "Por favor selecciona un evento primero")
            return
            
        try:
            # Obtener el texto completo del evento seleccionado
            event_text = self.events_listbox.get(selection[0])
            
            # Extraer el ID del evento del diccionario de mapeo
            event_id = self.event_id_map.get(selection[0])
            if not event_id:
                messagebox.showerror("Error", "No se pudo identificar el evento seleccionado")
                return
            
            # Extraer el nombre del evento (eliminando el tipo si existe)
            if '(' in event_text and ')' in event_text:
                event_name = event_text.split('(')[0].strip()
            else:
                event_name = event_text.strip()
            
            # Imprimir valores para depuración
            print(f"ID del evento: {event_id}")
            print(f"Nombre del evento: {event_name}")
            
            # Actualizar los campos del panel derecho
            # Actualizar las variables primero
            self.event_id_var.set(str(event_id))
            self.event_name_var.set(event_name)
            
            # Forzar la actualización de los widgets
            self.event_id_entry.config(state='normal')
            self.event_name_entry.config(state='normal')
            
            # Actualizar manualmente los campos
            self.event_id_entry.delete(0, tk.END)
            self.event_id_entry.insert(0, str(event_id))
            self.event_name_entry.delete(0, tk.END)
            self.event_name_entry.insert(0, event_name)
            
            # Forzar la actualización de la interfaz
            self.event_id_entry.update_idletasks()
            self.event_name_entry.update_idletasks()
            
            # Mostrar los datos en la consola para depuración
            print(f"Panel derecho - ID: {self.event_id_var.get()}")
            print(f"Panel derecho - Nombre: {self.event_name_var.get()}")
            
            # Poner los campos en modo de solo lectura
            self.event_id_entry.config(state='readonly')
            self.event_name_entry.config(state='readonly')
            
            # Forzar un redibujado completo
            self.event_frame.update_idletasks()
            self.right_panel.update_idletasks()
            
            # Actualizar el ID actual
            self.current_event_id = event_id
            
            # Mostrar mensaje de depuración
            print("Valores establecidos en los campos:")
            print(f"ID: {self.event_id_var.get()}")
            print(f"Nombre: {self.event_name_var.get()}")
            
            # Actualizar la interfaz
            self.update_idletasks()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error en edit_details: {error_details}")
            messagebox.showerror("Error", f"Error al cargar los detalles del evento: {str(e)}\n\nDetalles:\n{error_details}")
        finally:
            # Asegurarse de que los campos vuelvan a su estado original
            self.event_id_entry.config(state='readonly')
            self.event_name_entry.config(state='readonly')

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
        self.right_panel = ttk.Frame(paned)
        paned.add(self.right_panel, weight=3)
        
        # Configure right panel grid
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)
        
        # Top section - Event details
        self.event_frame = ttk.LabelFrame(self.right_panel, text="Detalles del Evento", padding="5")
        self.event_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Campos para mostrar los detalles del evento
        row = 0
        
        # ID del evento
        ttk.Label(self.event_frame, text="ID:").grid(row=row, column=0, sticky='w', padx=5, pady=2)
        self.event_id_var = tk.StringVar()
        self.event_id_entry = ttk.Entry(self.event_frame, textvariable=self.event_id_var, width=40, state='readonly')
        self.event_id_entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Nombre del evento
        ttk.Label(self.event_frame, text="Nombre:").grid(row=row, column=0, sticky='w', padx=5, pady=2)
        self.event_name_var = tk.StringVar()
        self.event_name_entry = ttk.Entry(self.event_frame, textvariable=self.event_name_var, width=40, state='readonly')
        self.event_name_entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Buttons frame - Solo el botón Guardar
        btn_frame = ttk.Frame(self.event_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1
        
        ttk.Button(btn_frame, text="Guardar", command=self.save_event).pack(side=tk.LEFT, padx=5)
        
        # Configure columns to expand
        self.event_frame.columnconfigure(1, weight=1)
        
        # Bottom section - Sections notebook
        self.sections_notebook = ttk.Notebook(self.right_panel)
        self.sections_notebook.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # TTS Tab
        self.tts_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.tts_tab, text='TTS')
        self.setup_tts_tab()
        
        # Audio Tab - Cambiado de 'Audio' a 'Audios'
        self.audio_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.audio_tab, text='Audios')
        self.setup_audio_tab()
        
        # Efectos Tab - Cambiado de 'Efectos' a 'Sonidos'
        self.effects_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.effects_tab, text='Sonidos')
        self.setup_effects_tab()
        
        # Nueva pestaña de Efectos
        self.sounds_tab = ttk.Frame(self.sections_notebook)
        self.sections_notebook.add(self.sounds_tab, text='Efectos')
        # Aquí puedes agregar la configuración inicial para la pestaña de Efectos
        ttk.Label(self.sounds_tab, text="Configuración de Efectos").pack(pady=10)
        
        # Create Evento frame
        id_frame = ttk.LabelFrame(left_panel, text="Evento", padding="10")
        id_frame.grid(row=0, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
        
        # Configurar grid del frame principal
        id_frame.columnconfigure(1, weight=1)
        
        # Fila 0: Tipo (ocupa todo el ancho)
        ttk.Label(id_frame, text="Tipo:").grid(row=0, column=0, sticky='w', pady=2, padx=5)
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(
            id_frame, 
            textvariable=self.event_type_var,
            state='readonly',
            width=40
        )
        self.event_type_combo.grid(row=0, column=1, columnspan=3, sticky='ew', pady=2, padx=(0, 10))
        
        # Fila 1: ID
        ttk.Label(id_frame, text="ID:").grid(row=1, column=0, sticky='w', pady=2, padx=5)
        self.event_id_var = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.event_id_var, state='readonly').grid(row=1, column=1, columnspan=3, sticky='ew', pady=2, padx=(0, 10))
        
        # Fila 2: Nombre (ocupa todo el ancho)
        ttk.Label(id_frame, text="Nombre:").grid(row=2, column=0, sticky='w', pady=2, padx=5)
        self.event_name_var = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.event_name_var).grid(row=2, column=1, columnspan=3, sticky='ew', pady=2, padx=(0, 10))
        
        # Load event types
        self.load_event_types()
        
        # Buttons frame (fila 3)
        button_frame = ttk.Frame(id_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky='e')
        
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
        btn_frame.grid(row=4, column=0, columnspan=4, pady=(10, 5), sticky='ew')
        
        # Delete button
        ttk.Button(
            btn_frame,
            text="Eliminar",
            command=self.delete_selected_event,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True)
        
        # Edit Event button
        ttk.Button(
            btn_frame,
            text="Editar Evento",
            command=self.edit_selected_event,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True)
        
        # Edit Details button
        ttk.Button(
            btn_frame,
            text="Editar Detalles",
            command=self.edit_details,  # Nueva función a implementar
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True)
        
        # Configure button frame grid
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        
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
            
    def setup_tts_tab(self):
        """Set up the TTS tab"""
        # Add TTS section button
        ttk.Button(
            self.tts_tab, 
            text="Agregar TTS", 
            command=self.add_tts_section
        ).pack(pady=10)
        
        # TTS sections listbox with scrollbar
        list_frame = ttk.Frame(self.tts_tab)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tts_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            height=10
        )
        self.tts_listbox.pack(expand=True, fill='both')
        scrollbar.config(command=self.tts_listbox.yview)
        
        self.tts_listbox.bind('<<ListboxSelect>>', self.edit_tts_section)
        
        # Frame para botones de acción
        btn_frame = ttk.Frame(self.tts_tab)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            btn_frame, 
            text="Eliminar", 
            command=self.remove_tts_section
        ).pack(side=tk.LEFT, padx=5)
        
    def show_add_tts_dialog(self, section_data=None):
        """Muestra el diálogo para agregar o editar una sección TTS
        
        Args:
            section_data (dict, optional): Datos de la sección a editar. Si es None, se crea una nueva.
        """
        # Crear ventana emergente
        dialog = tk.Toplevel(self)
        dialog.title("Agregar/Editar Sección TTS")
        dialog.transient(self)  # Hacer que la ventana sea modal
        dialog.grab_set()
        
        # Configurar grid
        dialog.columnconfigure(1, weight=1)
        
        # Variables
        name_var = tk.StringVar()
        voice_var = tk.StringVar()
        
        # Cargar datos de la sección si se está editando
        if section_data:
            name_var.set(section_data.get('name', ''))
            voice_var.set(section_data.get('voice_display', ''))
        
        # Frame principal para mejor organización
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.columnconfigure(1, weight=1)
        
        # Campo: Nombre de la sección
        ttk.Label(main_frame, text="Nombre de la sección:").grid(
            row=0, column=0, sticky='w', padx=5, pady=5)
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5, columnspan=2)
        
        # Configurar el grid para el frame de texto
        text_preview_frame = ttk.Frame(main_frame)
        text_preview_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
        text_preview_frame.columnconfigure(0, weight=1)
        
        # Campo: Texto
        text_frame = ttk.LabelFrame(text_preview_frame, text="Texto", padding=5)
        text_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        text_entry = tk.Text(text_frame, wrap=tk.WORD, width=40, height=10)
        text_entry.grid(row=0, column=0, sticky='nsew')
        
        # Scrollbar para el área de texto
        text_scroll = ttk.Scrollbar(text_frame, orient='vertical', command=text_entry.yview)
        text_scroll.grid(row=0, column=1, sticky='ns')
        text_entry['yscrollcommand'] = text_scroll.set
        
        # Botón de escuchar
        listen_btn = ttk.Button(
            text_preview_frame,
            text="Escuchar",
            command=lambda: self._preview_tts(
                text_entry.get("1.0", tk.END).strip(), 
                voice_codes.get(voice_var.get())
            )
        )
        listen_btn.grid(row=1, column=0, pady=(5, 0), sticky='w')
        
        # Campo: Voz
        ttk.Label(main_frame, text="Voz:").grid(
            row=2, column=0, sticky='w', padx=5, pady=5)
        
        # Obtener configuración del motor TTS
        from func.tts_config import get_tts_config, get_filtered_voices
        
        try:
            # Obtener configuración actual
            tts_config = get_tts_config()
            engine = tts_config.get('engine', 'azure')
            
            # Inicializar variables
            voices = []
            max_retries = 2
            error_message = None
            
            for attempt in range(max_retries):
                try:
                    # Obtener voces filtradas
                    voices = get_filtered_voices(engine)
                    
                    if not voices and attempt < max_retries - 1:
                        # Intentar recargar las voces una sola vez
                        from func.azure_tts import refresh_voices_cache
                        refresh_voices_cache()
                        continue
                        
                    if not voices:
                        error_message = (
                            "Advertencia",
                            f"No se encontraron voces para el motor {engine}.\n\n"
                            "Por favor verifica que:\n"
                            "1. Tienes conexión a internet\n"
                            "2. Los filtros de idioma están configurados correctamente\n"
                            "3. El motor TTS está correctamente configurado"
                        )
                        break
                        
                    # Si llegamos aquí, todo está bien
                    break
                    
                except Exception as e:
                    if attempt == max_retries - 1:  # Último intento
                        error_message = (
                            "Error",
                            f"No se pudieron cargar las voces después de {max_retries} intentos.\n\n"
                            f"Error: {str(e)}\n\n"
                            "Por favor verifica tu conexión a internet y la configuración del motor TTS."
                        )
                    continue
            
            # Mostrar mensaje de error si es necesario
            if error_message:
                dialog.destroy()
                self.after(100, lambda: messagebox.showwarning(*error_message) if error_message[0] == "Advertencia" 
                              else messagebox.showerror(*error_message))
                return
            
            # Preparar datos para el combobox
            voice_names = [v['display_name'] for v in voices]
            voice_codes = {v['display_name']: v['id'] for v in voices}
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar las voces: {str(e)}")
            dialog.destroy()
            return
        
        # Frame para los controles de voz
        voice_frame = ttk.Frame(main_frame)
        voice_frame.grid(row=2, column=1, sticky='ew', padx=5, pady=5, columnspan=3)
        voice_frame.columnconfigure(1, weight=1)
        
        # Combo de voces
        voice_combo = ttk.Combobox(
            voice_frame, 
            textvariable=voice_var,
            values=voice_names,
            state='readonly',
            width=40
        )
        voice_combo.grid(row=0, column=0, sticky='ew')
        
        # Botón para actualizar voces
        refresh_btn = ttk.Button(
            voice_frame,
            text="↻",
            width=3,
            command=self._refresh_tts_voices
        )
        refresh_btn.grid(row=0, column=1, padx=(5, 0), sticky='e')
        
        # Configurar el grid para que el combo se expanda
        voice_frame.columnconfigure(0, weight=1)
        
        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky='e')
        
        def on_ok():
            # Validar campos
            if not name_var.get().strip():
                messagebox.showerror("Error", "El nombre de la sección es requerido")
                return
                
            text = text_entry.get("1.0", tk.END).strip()
            if not text:
                messagebox.showerror("Error", "El texto es requerido")
                return
                
            selected_voice_name = voice_var.get()
            if not selected_voice_name:
                messagebox.showerror("Error", "Debe seleccionar una voz")
                return
                
            # Obtener el código de voz seleccionado
            selected_voice_code = voice_codes.get(selected_voice_name)
            if not selected_voice_code:
                messagebox.showerror("Error", "No se pudo determinar la voz seleccionada")
                return
            
            # Crear diccionario con los datos de la sección
            section_data = {
                'name': name_var.get().strip(),
                'text': text,
                'voice': selected_voice_code,
                'voice_display': selected_voice_name
            }
            
            # Si estamos editando, agregar el ID si existe
            if hasattr(self, 'editing_tts_id') and self.editing_tts_id is not None:
                section_data['id'] = self.editing_tts_id
            
            # Llamar al método para guardar la sección
            self._save_tts_section(section_data)
            
            # Cerrar el diálogo
            dialog.destroy()
            
            # Limpiar el ID de edición
            if hasattr(self, 'editing_tts_id'):
                del self.editing_tts_id
        
        # Si estamos editando, cargar los datos en los campos
        if section_data:
            name_var.set(section_data.get('name', ''))
            text_entry.delete('1.0', tk.END)
            text_entry.insert('1.0', section_data.get('text', ''))
            voice_var.set(section_data.get('voice_display', ''))
            
            # Guardar el ID de la sección que se está editando
            if 'id' in section_data:
                self.editing_tts_id = section_data['id']
        
        ttk.Button(btn_frame, text="Aceptar", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Configurar estilos
        style = ttk.Style()
        style.configure('Play.TButton', font=('Arial', 10, 'bold'))
        style.configure('Small.TLabel', font=('Arial', 9))
        
        # Mostrar información del motor actual
        engine_label = ttk.Label(
            main_frame,
            text=f"Motor TTS: {engine.upper()}",
            style='Small.TLabel'
        )
        engine_label.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky='w')
        
        # Agregar nota sobre cómo cambiar el motor
        note_label = ttk.Label(
            main_frame,
            text="Puedes cambiar el motor TTS en Configuración > TTS",
            style='Small.TLabel',
            foreground='gray'
        )
        note_label.grid(row=5, column=0, columnspan=3, pady=(0, 10), sticky='w')
        
        # Configurar el peso de las filas y columnas para que se expandan
        dialog.rowconfigure(0, weight=1)
        dialog.columnconfigure(0, weight=1)
        text_preview_frame.rowconfigure(0, weight=1)
        text_preview_frame.columnconfigure(0, weight=1, weight_=1)
        text_preview_frame.columnconfigure(1, weight=1, weight_=1)
        
        # Hacer que la ventana sea redimensionable
        dialog.resizable(True, True)
        
        # Ajustar el tamaño de la ventana
        dialog.update_idletasks()
        width = max(800, dialog.winfo_reqwidth())
        height = max(500, dialog.winfo_reqheight())
        
        # Centrar la ventana en la pantalla
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Enfocar el campo de nombre
        name_entry.focus_set()
        
    def add_tts_section(self):
        """Maneja el evento de agregar una nueva sección TTS"""
        if hasattr(self, 'editing_tts_id'):
            del self.editing_tts_id
        self.show_add_tts_dialog()
        
    def remove_tts_section(self):
        """Elimina la sección TTS seleccionada"""
        selection = self.tts_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor seleccione una sección TTS para eliminar")
            return
            
        # Aquí iría la lógica para eliminar la sección TTS
        self.tts_listbox.delete(selection[0])
        
    def edit_tts_section(self, event=None):
        """Edita la sección TTS seleccionada"""
        selection = self.tts_listbox.curselection()
        if not selection:
            return
            
        # Obtener los datos de la sección seleccionada
        selected_item = self.tts_listbox.get(selection[0])
        # Aquí deberías obtener los datos completos de la sección seleccionada
        # Por ahora, pasamos un diccionario vacío como ejemplo
        section_data = {
            'name': selected_item,  # Esto es solo un ejemplo, ajusta según tu estructura de datos
            'text': '',  # Aquí deberías obtener el texto real
            'voice': '',  # Aquí deberías obtener la voz real
            'voice_display': selected_item  # Esto es solo un ejemplo
        }
        
        self.show_add_tts_dialog(section_data)
    
    # ===== TTS Helper Methods =====
    def _preview_tts(self, text, voice_code):
        """Reproduce una vista previa del texto con la voz seleccionada"""
        if not text or not voice_code:
            messagebox.showwarning("Advertencia", "Texto o voz no válidos para la vista previa")
            return
            
        # Deshabilitar el botón de reproducción mientras se procesa
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button) and widget['text'] == '▶':
                widget.config(state='disabled')
        
        def play_tts():
            try:
                from func.tts_config import get_tts_config
                from func.azure_tts import synthesize_text as azure_synthesize, speech_config
                
                print(f"Iniciando vista previa con voz: {voice_code}")
                
                # Configurar la voz
                speech_config.speech_synthesis_voice_name = voice_code
                
                # Llamar a la función de síntesis
                success, message = azure_synthesize(text)
                if not success:
                    raise Exception(f"Azure TTS: {message}")
                
                print("Vista previa completada exitosamente")
                
            except Exception as e:
                error_msg = f"Error al reproducir la vista previa: {str(e)}"
                print(error_msg)
                self.after(0, lambda: messagebox.showerror("Error", error_msg))
            finally:
                # Re-habilitar el botón de reproducción
                self.after(0, self._enable_play_button)
        
        # Iniciar la reproducción en un hilo separado
        import threading
        tts_thread = threading.Thread(target=play_tts, daemon=True)
        tts_thread.start()
    
    def _enable_play_button(self):
        """Habilita el botón de reproducción"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button) and widget['text'] == '▶':
                widget.config(state='normal')
    
    def _refresh_tts_voices(self):
        """Actualiza la lista de voces disponibles"""
        try:
            # Mostrar indicador de carga
            self._show_loading(True, "Actualizando voces...")
            
            # Usar after para ejecutar en el hilo principal
            self.after(100, self._do_refresh_voices)
            
        except Exception as e:
            self._show_loading(False)
            self.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Error al iniciar la actualización de voces: {str(e)}"
            ))
    
    def _do_refresh_voices(self):
        """Método auxiliar para actualizar las voces en segundo plano"""
        from func.azure_tts import refresh_voices_cache
        import threading
        
        def refresh_task():
            try:
                refresh_voices_cache()
                self.after(0, self._on_voices_refreshed, True, None)
            except Exception as e:
                self.after(0, self._on_voices_refreshed, False, str(e))
        
        # Iniciar la tarea en segundo plano
        threading.Thread(target=refresh_task, daemon=True).start()
    
    def _on_voices_refreshed(self, success, error_msg=None):
        """Maneja la finalización de la actualización de voces"""
        self._show_loading(False)
        
        if success:
            messagebox.showinfo("Éxito", "Lista de voces actualizada correctamente")
            # Volver a abrir el diálogo para actualizar la lista
            self.after(100, self.show_add_tts_dialog)
        else:
            messagebox.showerror(
                "Error", 
                f"No se pudieron actualizar las voces: {error_msg or 'Error desconocido'}"
            )
    
    def _show_loading(self, show, message=""):
        """Muestra u oculta el indicador de carga"""
        if hasattr(self, '_loading_label'):
            self._loading_label.destroy()
            
        if show:
            self._loading_label = ttk.Label(
                self, 
                text=message,
                style='Info.TLabel'
            )
            self._loading_label.pack(pady=10)
            self.update()
    
    def _save_tts_section(self, section_data):
        """Guarda la sección TTS en la lista"""
        try:
            # Aquí deberías implementar la lógica para guardar la sección TTS
            # Por ahora, solo mostramos un mensaje de ejemplo
            print(f"Guardando sección TTS: {section_data}")
            
            # Si es una edición, actualizamos el ítem existente
            if hasattr(self, 'editing_tts_id') and self.editing_tts_id is not None:
                # Lógica para actualizar la sección existente
                print(f"Actualizando sección TTS con ID: {self.editing_tts_id}")
                messagebox.showinfo("Éxito", "Sección TTS actualizada correctamente")
            else:
                # Lógica para agregar una nueva sección
                print("Agregando nueva sección TTS")
                messagebox.showinfo("Éxito", "Sección TTS agregada correctamente")
                
            # Aquí deberías actualizar la interfaz de usuario para reflejar los cambios
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar la sección TTS: {str(e)}")
    
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
