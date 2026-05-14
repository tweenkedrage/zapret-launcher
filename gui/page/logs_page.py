import tkinter as tk
from tkinter import ttk
from gui.widgets import RoundedButton
from utils.languages import tr

class LogsPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('logs_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('logs_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        control_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        control_frame.pack(fill=tk.X, padx=30, pady=(0, 10))
        
        clear_btn = RoundedButton(
            control_frame,
            text=tr('logs_clear'),
            command=self.app.clear_logs,
            width=120, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8
        )
        clear_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        refresh_btn = RoundedButton(
            control_frame,
            text=tr('logs_refresh'),
            command=self.update_logs_display,
            width=120, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        logs_container = tk.Frame(self.frame, bg=self.colors['bg_medium'])
        logs_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.logs_text = tk.Text(
            logs_container,
            bg=self.colors['bg_light'],
            fg=self.colors['text_secondary'],
            font=("Consolas", 10),
            wrap=tk.WORD,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors['separator'],
            highlightcolor=self.colors['accent'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            padx=10,
            pady=10
        )
        
        scrollbar = ttk.Scrollbar(
            logs_container,
            command=self.logs_text.yview,
            style="Custom.Vertical.TScrollbar"
        )
        self.logs_text.configure(yscrollcommand=scrollbar.set)
        
        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.update_logs_display()
    
    def update_logs_display(self):
        if not hasattr(self, 'logs_text') or not self.logs_text.winfo_exists():
            return
        
        self.logs_text.delete(1.0, tk.END)
        
        logs = self.app.load_logs()
        
        for log_line in logs:
            log_line = log_line.strip()
            if log_line:
                self.logs_text.insert(tk.END, log_line + "\n")
        
        self.logs_text.see(tk.END)
    
    def get_frame(self):
        return self.frame