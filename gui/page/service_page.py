# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from gui.widgets import RoundedButton
from utils.languages import tr

class ServicePage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('service_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('service_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        functions = [
            (tr('service_filters'), [
                (tr('service_game_filter'), "game_filter"),
                (tr('service_ipset_filter'), "ipset_filter"),
            ]),
        ]
        
        for title, items in functions:
            card = tk.Frame(self.frame, bg=self.colors['bg_medium'])
            card.pack(fill=tk.X, padx=30, pady=10, ipadx=20, ipady=10)
            
            tk.Label(card, text=title, font=("Inter", 14, "bold"),
                    fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(10, 5))
            
            for btn_text, cmd in items:
                btn = RoundedButton(card, text=btn_text, 
                                command=lambda c=cmd: self.app.run_service_command(c),
                                width=200, height=35, bg=self.colors['button_bg'],
                                font=self.font_primary, corner_radius=8,
                                hover_color=self.colors['accent'], theme_name=self.app.current_theme)
                btn.pack(anchor='w', padx=15, pady=2)
        
        self.game_filter_btn = None
        self.ipset_filter_btn = None
    
    def get_frame(self):
        return self.frame
