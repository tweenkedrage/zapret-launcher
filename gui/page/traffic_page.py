# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from tkinter import ttk
from utils.languages import tr

class TrafficPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('traffic_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('traffic_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)

        warning_label = tk.Label(
            self.frame,
            text=tr('traffic_warning'),
            font=("Inter", 8),
            fg=self.colors['accent'],
            bg=self.colors['bg_dark']
        )
        warning_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        table_frame = tk.Frame(self.frame, bg=self.colors['bg_light'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        columns = (tr('traffic_process'), tr('traffic_speed'), tr('traffic_vpn'), tr('traffic_direct'), tr('traffic_connections'), tr('traffic_host'), tr('traffic_total'))

        style = ttk.Style()
        style.theme_use('default')
        
        style.configure("Treeview.Heading",
                        background=self.colors['bg_medium'],
                        foreground=self.colors['text_primary'],
                        font=("Inter", 10, "bold"),
                        relief="flat")
        
        style.map("Treeview.Heading",
                background=[('active', self.colors['bg_medium'])],
                foreground=[('active', self.colors['text_primary'])])
        
        style.configure("Treeview",
                        background=self.colors['bg_light'],
                        foreground=self.colors['text_primary'],
                        rowheight=25,
                        fieldbackground=self.colors['bg_light'],
                        font=("Inter", 9))
        
        style.map("Treeview",
                background=[('selected', self.colors['accent'])],
                foreground=[('selected', 'white')])
        
        self.traffic_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, style="Treeview")
        self.traffic_tree.column(tr('traffic_process'), width=200, anchor="w")
        self.traffic_tree.column(tr('traffic_speed'), width=100, anchor="e")
        self.traffic_tree.column(tr('traffic_vpn'), width=100, anchor="e")
        self.traffic_tree.column(tr('traffic_direct'), width=100, anchor="e")
        self.traffic_tree.column(tr('traffic_connections'), width=70, anchor="center")
        self.traffic_tree.column(tr('traffic_host'), width=180, anchor="w")
        self.traffic_tree.column(tr('traffic_total'), width=100, anchor="e")
        
        for col in columns:
            self.traffic_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.traffic_tree.yview, style="Custom.Vertical.TScrollbar")
        self.traffic_tree.configure(yscrollcommand=scrollbar.set)
        self.traffic_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def get_frame(self):
        return self.frame
