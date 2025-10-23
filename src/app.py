import tkinter as tk
from tkinter import ttk
import os
import sys

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import tab modules
from src.tabs.config_tab import ConfigTab
from src.tabs.studio_tab import StudioTab
from src.tabs.schedule_tab import ScheduleTab
from src.tabs.production_tab import ProductionTab

class HAMNAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configure main window
        self.title("HAMNA Desktop")
        self.geometry("1024x768")
        self.minsize(800, 600)
        
        # Set application icon if available
        try:
            self.iconbitmap(os.path.join("assets", "hamna.ico"))
        except:
            pass
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Initialize tabs
        self.tabs = {}
        self.init_tabs()
        
        # Status bar
        self.status_bar = ttk.Label(
            self.main_container, 
            text="Listo", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def init_tabs(self):
        """Initialize all application tabs"""
        
        # Production Tab
        self.tabs['production'] = ProductionTab(self.notebook)
        self.notebook.add(self.tabs['production'], text="Producción")

        # Schedule Tab
        self.tabs['schedule'] = ScheduleTab(self.notebook)
        self.notebook.add(self.tabs['schedule'], text="Programación")

        # Studio Tab
        self.tabs['studio'] = StudioTab(self.notebook)
        self.notebook.add(self.tabs['studio'], text="Estudio")

        # Configuration Tab
        self.tabs['config'] = ConfigTab(self.notebook)
        self.notebook.add(self.tabs['config'], text="Configuración")
    
    def update_status(self, message):
        """Update the status bar message"""
        self.status_bar.config(text=message)
        self.update_idletasks()

if __name__ == "__main__":
    # Set the application to use the 'vista' theme if available
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = HAMNAApp()
    app.mainloop()
