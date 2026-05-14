import tkinter as tk
from .page.main_page import MainPage
from .page.service_page import ServicePage
from .page.lists_page import ListsPage
from .page.diagnostic_page import DiagnosticPage
from .page.traffic_page import TrafficPage
from .page.logs_page import LogsPage
from .page.settings_page import SettingsPage
from .page.additionally_page import AdditionallyPage

class Pages:
    def __init__(self, app):
        self.app = app
        self.colors = app.colors
        self.current_page = "main"
        self.pages = {}

        self._pending_page = None
        self._animation_active = False
        
        self.main_page = MainPage(app.content_panel, app).get_frame()
        self.service_page = ServicePage(app.content_panel, app).get_frame()
        self.lists_page = ListsPage(app.content_panel, app).get_frame()
        self.diagnostic_page = DiagnosticPage(app.content_panel, app).get_frame()
        self.traffic_page = TrafficPage(app.content_panel, app).get_frame()
        self.logs_page = LogsPage(app.content_panel, app).get_frame()
        self.settings_page = SettingsPage(app.content_panel, app).get_frame()
        self.additionally_page = AdditionallyPage(app.content_panel, app).get_frame()
        
        self.pages = {
            "main": self.main_page,
            "service": self.service_page,
            "lists": self.lists_page,
            "diagnostic": self.diagnostic_page,
            "traffic": self.traffic_page,
            "logs": self.logs_page,
            "settings": self.settings_page,
            "additionally": self.additionally_page
        }
        
        self.main_page.place(x=0, y=0, width=950, height=800)
        self.current_page = "main"
    
    def show_page(self, page_name):
        if page_name == self.current_page:
            return
        
        if self.current_page in self.pages:
            self.pages[self.current_page].place_forget()
        
        if page_name in self.pages:
            self.pages[page_name].place(x=0, y=0, width=950, height=800)
            self.current_page = page_name
    
    def show_page_with_animation(self, page_name):
        if page_name == self.current_page and not self._animation_active:
            return
        
        self._pending_page = page_name
        
        if self._animation_active:
            return
        
        self._start_animation(page_name)
    
    def _start_animation(self, page_name):
        self._animation_active = True
        self._pending_page = None
        
        overlay = tk.Toplevel(self.app.root)
        overlay.overrideredirect(True)
        overlay.configure(bg=self.app.colors['bg_dark'])
        
        x = self.app.content_panel.winfo_rootx()
        y = self.app.content_panel.winfo_rooty()
        width = self.app.content_panel.winfo_width()
        height = self.app.content_panel.winfo_height()
        overlay.geometry(f"{width}x{height}+{x}+{y}")
        
        self._animate_fade_out(overlay, page_name)
    
    def _animate_fade_out(self, overlay, page_name, alpha=0.0):
        if alpha <= 1.0:
            try:
                overlay.attributes('-alpha', alpha)
                self.app.root.after(16, lambda: self._animate_fade_out(overlay, page_name, alpha + 0.08))
            except:
                self._finish_animation()
        else:
            self.show_page(page_name)
            self._animate_fade_in(overlay)
    
    def _animate_fade_in(self, overlay, alpha=1.0):
        if alpha >= 0.0:
            try:
                overlay.attributes('-alpha', alpha)
                self.app.root.after(16, lambda: self._animate_fade_in(overlay, alpha - 0.08))
            except:
                self._finish_animation()
        else:
            try:
                overlay.destroy()
            except:
                pass
            self._finish_animation()
    
    def _finish_animation(self):
        self._animation_active = False
        
        if self._pending_page and self._pending_page != self.current_page:
            self._start_animation(self._pending_page)
    
    def update_logs_display(self):
        if hasattr(self, 'logs_page'):
            self.logs_page.update_logs_display()
