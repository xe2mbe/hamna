import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, time as dt_time
from tkcalendar import DateEntry
import calendar

class ScheduleTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the schedule tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Date selection
        ttk.Label(controls_frame, text="Fecha:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_picker = DateEntry(
            controls_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        self.date_picker.pack(side=tk.LEFT, padx=(0, 10))
        
        # Week navigation
        ttk.Button(
            controls_frame, 
            text="< Semana anterior", 
            command=self.previous_week
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            controls_frame, 
            text="Hoy", 
            command=self.show_today
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            controls_frame, 
            text="Siguiente semana >", 
            command=self.next_week
        ).pack(side=tk.LEFT, padx=2)
        
        # Schedule view (calendar + timeline)
        schedule_frame = ttk.Frame(main_frame)
        schedule_frame.pack(fill=tk.BOTH, expand=True)
        
        # Calendar view on the left
        calendar_frame = ttk.LabelFrame(schedule_frame, text="Calendario", padding="5")
        calendar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Calendar widget
        self.cal = calendar.monthcalendar(datetime.now().year, datetime.now().month)
        self.calendar_widget = ttk.Treeview(
            calendar_frame, 
            columns=('D', 'L', 'M', 'X', 'J', 'V', 'S'), 
            show='headings',
            height=6
        )
        
        # Configure calendar headers
        for i, day in enumerate(['D', 'L', 'M', 'X', 'J', 'V', 'S']):
            self.calendar_widget.heading(i, text=day)
            self.calendar_widget.column(i, width=30, anchor=tk.CENTER)
        
        # Add days to calendar
        for week in self.cal:
            self.calendar_widget.insert('', 'end', values=week)
        
        self.calendar_widget.pack(fill=tk.BOTH, expand=True)
        
        # Timeline view on the right
        timeline_frame = ttk.LabelFrame(schedule_frame, text="Programación", padding="5")
        timeline_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Timeline controls
        timeline_controls = ttk.Frame(timeline_frame)
        timeline_controls.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            timeline_controls, 
            text="Nuevo evento", 
            command=self.new_event
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            timeline_controls, 
            text="Editar", 
            command=self.edit_event
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            timeline_controls, 
            text="Eliminar", 
            command=self.delete_event
        ).pack(side=tk.LEFT, padx=2)
        
        # Timeline view (using Treeview as a simple timeline)
        columns = ('time', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
        self.timeline = ttk.Treeview(
            timeline_frame,
            columns=columns,
            show='headings',
            selectmode='browse',
            height=15
        )
        
        # Configure columns
        self.timeline.heading('time', text='Hora')
        self.timeline.column('time', width=60, anchor=tk.CENTER)
        
        for day in columns[1:]:
            day_name = day.capitalize()
            if day == 'monday': day_name = 'Lunes'
            elif day == 'tuesday': day_name = 'Martes'
            elif day == 'wednesday': day_name = 'Miércoles'
            elif day == 'thursday': day_name = 'Jueves'
            elif day == 'friday': day_name = 'Viernes'
            elif day == 'saturday': day_name = 'Sábado'
            elif day == 'sunday': day_name = 'Domingo'
            
            self.timeline.heading(day, text=day_name[:3])
            self.timeline.column(day, width=100, anchor=tk.CENTER)
        
        # Add time slots (every hour from 6:00 to 22:00)
        for hour in range(6, 23):
            time_str = f"{hour:02d}:00"
            self.timeline.insert('', 'end', values=[time_str] + [''] * 7)
        
        # Add some sample events
        self.add_sample_events()
        
        # Add scrollbar to timeline
        scrollbar = ttk.Scrollbar(timeline_frame, orient=tk.VERTICAL, command=self.timeline.yview)
        self.timeline.configure(yscrollcommand=scrollbar.set)
        
        # Pack timeline and scrollbar
        self.timeline.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_var = tk.StringVar()
        ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN, 
            anchor=tk.W
        ).pack(fill=tk.X, pady=(10, 0))
        
        self.update_status("Listo")
    
    def add_sample_events(self):
        """Add some sample events to the timeline"""
        # Sample events: (day_index, hour, title)
        sample_events = [
            (0, 8, "Desayuno informativo"),  # Monday
            (2, 14, "Entrevista"),          # Wednesday
            (4, 10, "Boletín de noticias"), # Friday
            (6, 20, "Programa especial")    # Sunday
        ]
        
        for day_idx, hour, title in sample_events:
            # Find the item for this hour
            for item in self.timeline.get_children():
                time_str = self.timeline.item(item)['values'][0]
                if time_str.startswith(f"{hour:02d}:"):
                    # Update the cell for this day
                    values = self.timeline.item(item)['values']
                    values[day_idx + 1] = title
                    self.timeline.item(item, values=values)
                    break
    
    def update_status(self, message):
        """Update the status bar"""
        self.status_var.set(f" {message}")
    
    def previous_week(self):
        """Navigate to previous week"""
        current_date = self.date_picker.get_date()
        new_date = current_date - datetime.timedelta(days=7)
        self.date_picker.set_date(new_date)
        self.update_calendar()
    
    def next_week(self):
        """Navigate to next week"""
        current_date = self.date_picker.get_date()
        new_date = current_date + datetime.timedelta(days=7)
        self.date_picker.set_date(new_date)
        self.update_calendar()
    
    def show_today(self):
        """Show today's date"""
        self.date_picker.set_date(datetime.now().date())
        self.update_calendar()
    
    def update_calendar(self):
        """Update the calendar view"""
        # This would update the calendar based on the selected date
        # For now, we'll just update the status
        selected_date = self.date_picker.get_date()
        self.update_status(f"Mostrando semana del {selected_date.strftime('%d/%m/%Y')}")
    
    def new_event(self):
        """Create a new scheduled event"""
        # Get selected date and time
        selected_date = self.date_picker.get_date()
        
        # Show event dialog
        self.show_event_dialog(selected_date)
    
    def edit_event(self):
        """Edit selected event"""
        selected = self.timeline.selection()
        if not selected:
            messagebox.showwarning("Editar evento", "Por favor seleccione un evento para editar.")
            return
        
        # Get event details
        item = selected[0]
        values = self.timeline.item(item)['values']
        
        # Find which day has content
        day_idx = -1
        for i in range(1, 8):  # Skip time column (0)
            if values[i]:
                day_idx = i - 1
                break
        
        if day_idx == -1:
            messagebox.showerror("Error", "No se puede editar un evento vacío.")
            return
        
        # Get the time from the first column
        time_str = values[0]
        
        # Show edit dialog
        self.show_event_dialog(
            date=None,  # Will be calculated from day_idx
            time=time_str,
            title=values[day_idx + 1],
            day_index=day_idx,
            item=item
        )
    
    def delete_event(self):
        """Delete selected event"""
        selected = self.timeline.selection()
        if not selected:
            messagebox.showwarning("Eliminar evento", "Por favor seleccione un evento para eliminar.")
            return
        
        if messagebox.askyesno("Confirmar", "¿Está seguro de que desea eliminar este evento?"):
            # Get the item and its values
            item = selected[0]
            values = self.timeline.item(item)['values']
            
            # Find which day has content and clear it
            for i in range(1, 8):  # Skip time column (0)
                if values[i]:
                    values[i] = ''
                    break
            
            # Update the item
            self.timeline.item(item, values=values)
            self.update_status("Evento eliminado")
    
    def show_event_dialog(self, date=None, time=None, title="", day_index=None, item=None):
        """Show event editing dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Nuevo evento" if item is None else "Editar evento")
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
        
        # Event title
        ttk.Label(form_frame, text="Título:").grid(row=0, column=0, sticky=tk.W, pady=5)
        title_var = tk.StringVar(value=title)
        ttk.Entry(form_frame, textvariable=title_var, width=40).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=5, columnspan=2
        )
        
        # Date selection (if not provided)
        row = 1
        if date is None and day_index is not None:
            ttk.Label(form_frame, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=5)
            date_picker = DateEntry(
                form_frame, 
                width=12, 
                background='darkblue',
                foreground='white', 
                borderwidth=2,
                date_pattern='dd/mm/yyyy'
            )
            date_picker.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
            row += 1
        
        # Time selection
        ttk.Label(form_frame, text="Hora:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        # Time comboboxes
        time_frame = ttk.Frame(form_frame)
        time_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Parse time if provided (format: "HH:MM")
        hour = 12
        minute = 0
        if time:
            try:
                hour, minute = map(int, time.split(':'))
            except:
                pass
        
        # Hour combobox
        hour_var = tk.StringVar(value=f"{hour:02d}")
        hour_cb = ttk.Combobox(
            time_frame,
            textvariable=hour_var,
            values=[f"{h:02d}" for h in range(24)],
            width=3,
            state="readonly"
        )
        hour_cb.pack(side=tk.LEFT)
        
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT, padx=2)
        
        # Minute combobox
        minute_var = tk.StringVar(value=f"{minute:02d}")
        minute_cb = ttk.Combobox(
            time_frame,
            textvariable=minute_var,
            values=[f"{m:02d}" for m in range(0, 60, 5)],
            width=3,
            state="readonly"
        )
        minute_cb.pack(side=tk.LEFT)
        
        # Duration (in minutes)
        row += 1
        ttk.Label(form_frame, text="Duración (min):").grid(row=row, column=0, sticky=tk.W, pady=5)
        duration_var = tk.StringVar(value="30")
        ttk.Spinbox(
            form_frame,
            from_=1,
            to=240,
            increment=5,
            textvariable=duration_var,
            width=5
        ).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Recurrence
        row += 1
        ttk.Label(form_frame, text="Repetir:").grid(row=row, column=0, sticky=tk.W, pady=5)
        recur_var = tk.StringVar(value="No")
        recur_options = ["No", "Diario", "Semanal", "Mensual"]
        ttk.Combobox(
            form_frame,
            textvariable=recur_var,
            values=recur_options,
            state="readonly",
            width=15
        ).grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Description
        row += 1
        ttk.Label(form_frame, text="Descripción:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(form_frame, width=30, height=5)
        desc_text.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5, columnspan=2)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_event():
            # Get values from form
            event_title = title_var.get().strip()
            if not event_title:
                messagebox.showerror("Error", "El título del evento no puede estar vacío.")
                return
            
            # Get time
            try:
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                duration = int(duration_var.get())
                
                # Format time as "HH:MM"
                time_str = f"{hour:02d}:{minute:02d}"
                
                # For now, just show a message
                if item is None:
                    messagebox.showinfo("Evento creado", f"Evento '{event_title}' programado para las {time_str}")
                else:
                    # Update the timeline
                    values = self.timeline.item(item)['values']
                    if day_index is not None:
                        values[day_index + 1] = event_title
                        self.timeline.item(item, values=values)
                    messagebox.showinfo("Evento actualizado", f"Evento '{event_title}' actualizado")
                
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Valores inválidos: {e}")
        
        ttk.Button(button_frame, text="Guardar", command=save_event).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
