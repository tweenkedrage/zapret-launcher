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
import webbrowser

class AdditionallyPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('additionally_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('additionally_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)

        hosts_card = tk.Frame(self.frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        hosts_card.pack(fill=tk.X, padx=30, pady=5)
        hosts_inner = tk.Frame(hosts_card, bg=self.colors['bg_light'])
        hosts_inner.pack(fill=tk.X, padx=20, pady=10)
        
        hosts_title = tk.Label(hosts_inner, text="Telegram Web", font=("Inter", 16, "bold"),
                               fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        hosts_title.pack(anchor='w')
        
        def on_enter_tgweb(event):
            hosts_title.config(fg=self.colors['accent_hover'])
        def on_leave_tgweb(event):
            hosts_title.config(fg=self.colors['accent'])
        def on_click_tgweb(event):
            webbrowser.open("https://web.telegram.org")
        
        hosts_title.bind("<Enter>", on_enter_tgweb)
        hosts_title.bind("<Leave>", on_leave_tgweb)
        hosts_title.bind("<Button-1>", on_click_tgweb)
        
        hosts_desc = tk.Label(hosts_inner, text=tr('hosts_desc_on_page'), font=("Inter", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'],
                                wraplength=800, justify=tk.LEFT)
        hosts_desc.pack(anchor='w', pady=(5, 10))
        
        hosts_btn = RoundedButton(hosts_inner, text=tr('hosts_button_unblock'),
                                command=self.app.show_hosts_instruction,
                                width=120, height=35, bg=self.colors['accent'],
                                fg=self.colors['text_primary'], font=("Inter", 10), corner_radius=8, 
                                hover_color=self.colors['accent'], theme_name=self.app.current_theme)
        hosts_btn.pack(side=tk.LEFT)
        
        soundcloud_card = tk.Frame(self.frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        soundcloud_card.pack(fill=tk.X, padx=30, pady=10)
        
        inner = tk.Frame(soundcloud_card, bg=self.colors['bg_light'])
        inner.pack(fill=tk.X, padx=20, pady=15)
        
        sc_title = tk.Label(inner, text="SoundCloud", font=("Inter", 16, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        sc_title.pack(anchor='w')
        
        def on_enter(event):
            sc_title.config(fg=self.colors['accent_hover'])
        def on_leave(event):
            sc_title.config(fg=self.colors['accent'])
        def on_click(event):
            webbrowser.open("https://soundcloud.com")
        
        sc_title.bind("<Enter>", on_enter)
        sc_title.bind("<Leave>", on_leave)
        sc_title.bind("<Button-1>", on_click)
        
        sc_desc = tk.Label(inner, text=tr('soundcloud_description'), font=("Inter", 10),
                           fg=self.colors['text_secondary'], bg=self.colors['bg_light'],
                           wraplength=800, justify=tk.LEFT)
        sc_desc.pack(anchor='w', pady=(5, 15))
        
        btn_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        status_label = tk.Label(inner, text="", font=("Inter", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        status_label.pack(anchor='w', pady=(10, 0))
        
        def update_buttons():
            is_enabled = self.app.check_soundcloud_enabled()
            for widget in btn_frame.winfo_children():
                widget.destroy()
            if is_enabled:
                disable_btn = RoundedButton(btn_frame, text=tr('disable'),
                    command=lambda: [self.app.remove_soundcloud_unblock(), update_buttons()],
                    width=120, height=35, bg=self.colors['button_bg'],
                    fg=self.colors['text_secondary'], font=("Inter", 10), corner_radius=8, 
                                hover_color=self.colors['accent'], theme_name=self.app.current_theme)
                disable_btn.pack(side=tk.LEFT)
                status_label.config(text=tr('enabled_additionally'), fg=self.colors['accent_green'])
            else:
                enable_btn = RoundedButton(btn_frame, text=tr('enable'),
                    command=lambda: [self.app.add_soundcloud_unblock(), update_buttons()],
                    width=120, height=35, bg=self.colors['accent'],
                    fg=self.colors['text_primary'], font=("Inter", 10), corner_radius=8, 
                                hover_color=self.colors['accent'], theme_name=self.app.current_theme)
                enable_btn.pack(side=tk.LEFT)
                status_label.config(text=tr('disabled_additionally'), fg=self.colors['text_secondary'])

        ghub_card = tk.Frame(self.frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        ghub_card.pack(fill=tk.X, padx=30, pady=5)
        ghub_inner = tk.Frame(ghub_card, bg=self.colors['bg_light'])
        ghub_inner.pack(fill=tk.X, padx=20, pady=10)
        
        ghub_title = tk.Label(ghub_inner, text="GitHub", font=("Inter", 16, "bold"),
                               fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        ghub_title.pack(anchor='w')
        
        def on_enter_ghub(event):
            ghub_title.config(fg=self.colors['accent_hover'])
        def on_leave_ghub(event):
            ghub_title.config(fg=self.colors['accent'])
        def on_click_ghub(event):
            webbrowser.open("https://github.com")
        
        ghub_title.bind("<Enter>", on_enter_ghub)
        ghub_title.bind("<Leave>", on_leave_ghub)
        ghub_title.bind("<Button-1>", on_click_ghub)
        
        ghub_desc = tk.Label(ghub_inner, text=tr('ghub_desc_on_page'), font=("Inter", 10),
                              fg=self.colors['text_secondary'], bg=self.colors['bg_light'],
                              wraplength=800, justify=tk.LEFT)
        ghub_desc.pack(anchor='w', pady=(5, 10))
        
        ghub_btn = RoundedButton(ghub_inner, text=tr('ghub_button_unblock'),
                                  command=self.app.show_github_instruction,
                                  width=120, height=35, bg=self.colors['accent'],
                                  fg=self.colors['text_primary'], font=("Inter", 10), corner_radius=8, 
                                  hover_color=self.colors['accent'], theme_name=self.app.current_theme)
        ghub_btn.pack(side=tk.LEFT)
        
        meta_card = tk.Frame(self.frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        meta_card.pack(fill=tk.X, padx=30, pady=5)
        meta_inner = tk.Frame(meta_card, bg=self.colors['bg_light'])
        meta_inner.pack(fill=tk.X, padx=20, pady=10)
        
        meta_title = tk.Label(meta_inner, text="Meta", font=("Inter", 16, "bold"),
                              fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        meta_title.pack(anchor='w')
        
        def on_enter_meta(event):
            meta_title.config(fg=self.colors['accent_hover'])
        def on_leave_meta(event):
            meta_title.config(fg=self.colors['accent'])
        def on_click_meta(event):
            webbrowser.open("https://www.facebook.com")
        
        meta_title.bind("<Enter>", on_enter_meta)
        meta_title.bind("<Leave>", on_leave_meta)
        meta_title.bind("<Button-1>", on_click_meta)
        
        meta_desc = tk.Label(meta_inner, text=tr('meta_description'), font=("Inter", 10),
                             fg=self.colors['text_secondary'], bg=self.colors['bg_light'],
                             wraplength=800, justify=tk.LEFT)
        meta_desc.pack(anchor='w', pady=(5, 10))
        
        meta_btn_frame = tk.Frame(meta_inner, bg=self.colors['bg_light'])
        meta_btn_frame.pack(fill=tk.X, pady=5)
        
        meta_status_label = tk.Label(meta_inner, text="", font=("Inter", 10),
                                     fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        meta_status_label.pack(anchor='w', pady=(5, 0))
        
        def update_meta_buttons():
            is_enabled = self.app.check_meta_enabled()
            for widget in meta_btn_frame.winfo_children():
                widget.destroy()
            if is_enabled:
                disable_btn = RoundedButton(meta_btn_frame, text=tr('disable'),
                    command=lambda: [self.app.remove_facebook_instagram_unblock(), update_meta_buttons()],
                    width=120, height=35, bg=self.colors['button_bg'],
                    fg=self.colors['text_secondary'], font=("Inter", 10), corner_radius=8, hover_color=self.colors['accent'],
                    theme_name=self.app.current_theme)
                disable_btn.pack(side=tk.LEFT)
                meta_status_label.config(text=tr('enabled_additionally'), fg=self.colors['accent_green'])
            else:
                enable_btn = RoundedButton(meta_btn_frame, text=tr('enable'),
                    command=lambda: [self.app.add_facebook_instagram_unblock(), update_meta_buttons()],
                    width=120, height=35, bg=self.colors['accent'],
                    fg=self.colors['text_primary'], font=("Inter", 10), corner_radius=8, hover_color=self.colors['accent'],
                    theme_name=self.app.current_theme)
                enable_btn.pack(side=tk.LEFT)
                meta_status_label.config(text=tr('disabled_additionally'), fg=self.colors['text_secondary'])
        
        update_meta_buttons()
        update_buttons()
    
    def get_frame(self):
        return self.frame
