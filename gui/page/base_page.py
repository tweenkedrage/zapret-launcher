import tkinter as tk

class BasePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.colors['bg_dark'])
        self.app = app
        self.colors = app.colors
        
        self.create_header()
        self.create_content()
    
    def create_header(self):
        title = tk.Label(
            self,
            text=self.get_title(),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc = tk.Label(
            self,
            text=self.get_description(),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc.pack(anchor='w', pady=(0, 20), padx=30)
    
    def get_title(self) -> str:
        return ""
    
    def get_description(self) -> str:
        return ""
    
    def create_content(self):
        pass