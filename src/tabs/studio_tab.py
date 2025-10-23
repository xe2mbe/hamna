import tkinter as tk
from tkinter import ttk, messagebox

class StudioTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the studio tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Audio controls
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Audio waveform display
        waveform_frame = ttk.LabelFrame(left_panel, text="Onda de audio", padding="5")
        waveform_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Placeholder for waveform visualization
        waveform_canvas = tk.Canvas(waveform_frame, bg='#f0f0f0', height=150)
        waveform_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_waveform_placeholder(waveform_canvas)
        
        # Transport controls
        transport_frame = ttk.Frame(left_panel)
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
        
        # Volume control
        volume_frame = ttk.Frame(left_panel)
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
