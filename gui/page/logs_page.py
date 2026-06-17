# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from tkinter import ttk
from gui.widgets import RoundedButton
from utils.languages import tr
from config import APPDATA_DIR

class LogsPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold

        self.was_at_bottom = True
        self.old_scroll_position = 1.0
        self.last_log_count = 0
        self.auto_scroll_enabled = True

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
            command=self.clear_logs,
            width=120, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.app.current_theme
        )
        clear_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        refresh_btn = RoundedButton(
            control_frame,
            text=tr('logs_refresh'),
            command=self.refresh_logs,
            width=120, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.app.current_theme
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
        
        self.scrollbar = ttk.Scrollbar(
            logs_container,
            command=self.logs_text.yview,
            style="Custom.Vertical.TScrollbar"
        )
        self.logs_text.configure(yscrollcommand=self.scrollbar.set)
        
        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.logs_text.bind("<MouseWheel>", self._on_scroll)
        self.logs_text.config(state=tk.DISABLED)
        self.update_logs_display()

    def _on_scroll(self, event):
        self.auto_scroll_enabled = False
        if self.logs_text and self.logs_text.winfo_exists():
            current_view = self.logs_text.yview()
            self.was_at_bottom = (current_view[1] >= 0.99)
            self.old_scroll_position = current_view[0]

    def refresh_logs(self):
        self.auto_scroll_enabled = True
        self.update_logs_display()

    def clear_logs(self):
        log_file = APPDATA_DIR / "logs.txt"
        try:
            if log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.delete(1.0, tk.END)
            self.logs_text.config(state=tk.DISABLED)
            self.last_log_count = 0
            self.auto_scroll_enabled = True
            self.logs_text.see(tk.END)
        except Exception:
            pass
    
    def update_logs_display(self):
        if not hasattr(self, 'logs_text') or not self.logs_text.winfo_exists():
            return
        
        try:
            if self.logs_text.tag_ranges(tk.SEL):
                if not hasattr(self, '_delayed_update'):
                    self._delayed_update = self.app.root.after(1000, self.update_logs_display)
                return
        except:
            pass
        
        try:
            sel_start = self.logs_text.index(tk.SEL_FIRST)
            sel_end = self.logs_text.index(tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False
            sel_start = None
            sel_end = None
        
        current_view = self.logs_text.yview()
        was_at_bottom = (current_view[1] >= 0.99)
        current_position = current_view[0]
        
        logs = self.app.load_logs()
        
        if len(logs) == self.last_log_count:
            return
        
        self.last_log_count = len(logs)
        self.logs_text.config(state=tk.NORMAL)
        self.logs_text.delete(1.0, tk.END)
        
        for log_line in logs:
            log_line = log_line.strip()
            if log_line:
                self.logs_text.insert(tk.END, log_line + "\n")
        
        self.logs_text.config(state=tk.DISABLED)
        
        if has_selection and sel_start and sel_end:
            try:
                self.logs_text.tag_add(tk.SEL, sel_start, sel_end)
                self.logs_text.mark_set(tk.INSERT, sel_start)
            except:
                pass
        
        if self.auto_scroll_enabled:
            self.logs_text.see(tk.END)
        else:
            if was_at_bottom:
                self.logs_text.see(tk.END)
            else:
                self.logs_text.yview_moveto(current_position)
    
    def get_frame(self):
        return self.frame
