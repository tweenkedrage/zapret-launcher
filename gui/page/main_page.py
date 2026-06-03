# Zapret Launcher - GUI for zapret
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from gui.widgets import RoundedButton
import webbrowser
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance
import sys
import time
from utils.languages import tr

class MainPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        header_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        header_frame.pack(fill=tk.X, padx=30, pady=(30, 5))
        
        title_label = tk.Label(
            header_frame, 
            text=tr('main_title'), 
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w')
        
        desc_label = tk.Label(
            header_frame,
            text=tr('main_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(5, 0))
        
        main_content = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        main_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))
        
        left_column = tk.Frame(main_content, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        right_column = tk.Frame(main_content, bg=self.colors['bg_dark'], width=340)
        right_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        right_column.pack_propagate(False)
        
        status_frame = tk.Frame(left_column, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(status_frame, text=tr('status'), font=self.font_bold, 
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.main_status = tk.Label(status_frame, text=tr('status_ready'), font=self.font_medium,
                                        fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.main_status.pack(side=tk.LEFT, padx=15, pady=10)
        
        mode_frame = tk.Frame(left_column, bg=self.colors['bg_light'])
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(mode_frame, text=tr('mode'), font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.mode_label = tk.Label(mode_frame, text=tr('mode_not_selected'), font=self.font_medium,
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.mode_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.stats_frame = tk.Frame(left_column, bg=self.colors['bg_medium'])
        self.app.stats_frame.pack(fill=tk.X, pady=(0, 15), ipadx=20, ipady=15)
        
        tk.Label(self.app.stats_frame, text=tr('stats_session'), font=("Inter", 14, "bold"),
            fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(8, 5))
        
        stats_row1 = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        stats_row1.pack(fill=tk.X, padx=15, pady=2)
        
        self.app.stats_time_label = tk.Label(stats_row1, text="00:00:00", font=("Inter", 18, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_time_label.pack(side=tk.LEFT)
        
        tk.Label(stats_row1, text=tr('stats_time'), font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(5, 20))
        
        self.app.stats_traffic_label = tk.Label(stats_row1, text="⬇ 0 B  |  ⬆ 0 B", font=("Inter", 12),
                                                fg=self.colors['text_primary'], bg=self.colors['bg_medium'])
        self.app.stats_traffic_label.pack(side=tk.LEFT, padx=(0, 20))
        self.app.stats_total_label = tk.Label(stats_row1, text="0 B", font=("Inter", 12),
                                            fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        self.app.stats_total_label.pack(side=tk.LEFT)
        
        stats_speed_frame = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        stats_speed_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        stats_container = tk.Frame(stats_speed_frame, bg=self.colors['bg_medium'], width=550, height=80)
        stats_container.pack(anchor='w')
        stats_container.pack_propagate(False)

        speed_frame = tk.Frame(stats_container, bg=self.colors['bg_medium'])
        speed_frame.place(x=0, y=0, width=300, height=80)
        
        tk.Label(speed_frame, text=tr('stats_speed'), font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        self.app.stats_speed_up_label = tk.Label(speed_frame, text="⬆ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_speed_up_label.pack(anchor='w', pady=(5, 2))
        
        self.app.stats_speed_down_label = tk.Label(speed_frame, text="⬇ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_speed_down_label.pack(anchor='w', pady=2)

        rtt_frame = tk.Frame(stats_container, bg=self.colors['bg_medium'])
        rtt_frame.place(x=320, y=0, width=230, height=80)
        
        tk.Label(rtt_frame, text=tr('stats_rtt'), font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        self.app.stats_rtt_label = tk.Label(rtt_frame, text="-- ms", font=("Inter", 16, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_rtt_label.pack(anchor='w', pady=(5, 0))
        
        button_frame = tk.Frame(left_column, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.app.connect_btn = RoundedButton(button_frame, text=tr('button_connect'), command=self.app.toggle_connection,
                                    width=350, height=60, bg=self.colors['accent'], 
                                    font=("Inter", 18, "bold"), corner_radius=15,
                                    theme_name=self.app.current_theme)
        self.app.connect_btn.hover_color = '#3D3D45'
        self.app.connect_btn.pack()
        
        self._create_tg_proxy_card(right_column)
        
        self.icons_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        self.icons_frame.pack(side=tk.BOTTOM, anchor='se', padx=20, pady=15)
        self._create_icon_buttons()
        self._setup_focus_handling()
        self.load_tg_proxy_settings()

    def load_tg_proxy_settings(self):
        if hasattr(self.app, 'tg_host'):
            self.tg_host_entry.delete(0, tk.END)
            self.tg_host_entry.insert(0, self.app.tg_host)
        
        if hasattr(self.app, 'tg_port'):
            self.tg_port_entry.delete(0, tk.END)
            self.tg_port_entry.insert(0, str(self.app.tg_port))
        
        if hasattr(self.app, 'tg_fake_tls'):
            self.fake_tls_var.set(self.app.tg_fake_tls)
            if self.app.tg_fake_tls:
                self.fake_tls_text.config(text=tr('status_enabled'), fg=self.colors['accent_green'])
            else:
                self.fake_tls_text.config(text=tr('status_disabled'), fg=self.colors['text_secondary'])
        
        if hasattr(self.app, 'tg_fake_tls_domain'):
            self.tg_domain_entry.delete(0, tk.END)
            self.tg_domain_entry.insert(0, self.app.tg_fake_tls_domain)

    def save_tg_proxy_settings(self):
        try:
            new_host = self.tg_host_entry.get().strip()
            new_port = int(self.tg_port_entry.get().strip())
            new_fake_tls = self.fake_tls_var.get()
            new_domain = self.tg_domain_entry.get().strip()

            settings_changed = (
                new_host != self.app.tg_host or
                new_port != self.app.tg_port or
                new_fake_tls != self.app.tg_fake_tls or
                new_domain != self.app.tg_fake_tls_domain
            )
            
            if not settings_changed:
                return
            
            self.app.tg_host = new_host
            self.app.tg_port = new_port
            self.app.tg_fake_tls = new_fake_tls
            self.app.tg_fake_tls_domain = new_domain
            
            if hasattr(self.app, 'tg_proxy'):
                self.app.tg_proxy._host = new_host
                self.app.tg_proxy._port = new_port
                self.app.tg_proxy._fake_tls_domain = new_domain if new_fake_tls else ''
            
            self.app.save_settings()
            self.app.show_notification(tr('notification_save_settings'), 2000)
            
        except ValueError:
            self.app.show_notification(tr('error_port_have_words'), 2000)

    def _setup_focus_handling(self):
        def remove_focus(event=None):
            focused = self.app.root.focus_get()
            if focused and isinstance(focused, (tk.Entry, tk.Text)):
                if event and event.widget != focused:
                    self.app.root.focus_set()
        
        self.app.root.bind_all("<Button-1>", remove_focus)

    def _create_tg_proxy_card(self, parent):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(card, bg=self.colors['bg_light'])
        inner.pack(fill=tk.X, padx=15, pady=12)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        title_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(title_frame, text="Telegram Proxy", font=("Inter", 13, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(side=tk.LEFT)
        
        tk.Frame(inner, bg=self.colors['separator'], height=1).pack(fill=tk.X, pady=(0, 10))
        
        row1 = tk.Frame(inner, bg=self.colors['bg_light'])
        row1.pack(fill=tk.X, pady=(0, 8))
        
        host_frame = tk.Frame(row1, bg=self.colors['bg_light'])
        host_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        tk.Label(host_frame, text=tr('main_page_tg_proxy_host'), font=("Inter", 9),
                fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w')
        
        self.tg_host_entry = tk.Entry(host_frame, font=("Inter", 10),
                                    bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                    relief=tk.FLAT, highlightthickness=1,
                                    highlightcolor=self.colors['accent'],
                                    highlightbackground=self.colors['separator'])
        self.tg_host_entry.pack(fill=tk.X, pady=(2, 0), ipady=4)
        self.tg_host_entry.insert(0, "127.0.0.1")
        
        port_frame = tk.Frame(row1, bg=self.colors['bg_light'])
        port_frame.pack(side=tk.RIGHT)
        
        tk.Label(port_frame, text=tr('main_page_tg_proxy_port'), font=("Inter", 9),
                fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w')
        
        self.tg_port_entry = tk.Entry(port_frame, font=("Inter", 10),
                                    bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                    relief=tk.FLAT, highlightthickness=1,
                                    highlightcolor=self.colors['accent'],
                                    highlightbackground=self.colors['separator'],
                                    width=7)
        self.tg_port_entry.pack(pady=(2, 0), ipady=4)
        self.tg_port_entry.insert(0, "1443")
        
        row2 = tk.Frame(inner, bg=self.colors['bg_light'])
        row2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row2, text="Fake TLS", font=("Inter", 9),
                fg=self.colors['text_secondary'], bg=self.colors['bg_light'], width=8, anchor='w').pack(side=tk.LEFT)

        self.fake_tls_var = tk.BooleanVar(value=True)
        self.fake_tls_text = tk.Label(row2, text=tr('status_enabled'), font=("Inter", 9),
                                    fg=self.colors['accent_green'], bg=self.colors['bg_light'])

        def on_fake_tls_toggle():
            if self.fake_tls_var.get():
                self.fake_tls_text.config(text=tr('status_enabled'), fg=self.colors['accent_green'])
            else:
                self.fake_tls_text.config(text=tr('status_disabled'), fg=self.colors['text_secondary'])

        self.fake_tls_switch = tk.Checkbutton(
            row2,
            variable=self.fake_tls_var,
            command=on_fake_tls_toggle,
            bg=self.colors['bg_light'],
            activebackground=self.colors['bg_light'],
            selectcolor=self.colors['bg_light'],
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.fake_tls_switch.pack(side=tk.LEFT, padx=(5, 0))
        self.fake_tls_text.pack(side=tk.LEFT, padx=(5, 0))
        
        row3 = tk.Frame(inner, bg=self.colors['bg_light'])
        row3.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(row3, text=tr('main_page_tg_proxy_domain'), font=("Inter", 9),
                fg=self.colors['text_secondary'], bg=self.colors['bg_light'], width=8, anchor='w').pack(side=tk.LEFT)
        
        self.tg_domain_entry = tk.Entry(row3, font=("Inter", 10),
                                        bg=self.colors['bg_light'], fg=self.colors['text_secondary'],
                                        relief=tk.FLAT, highlightthickness=1,
                                        highlightcolor=self.colors['accent'],
                                        highlightbackground=self.colors['separator'])
        self.tg_domain_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=4)
        self.tg_domain_entry.insert(0, "www.google.com")
        
        apply_btn = RoundedButton(
            inner,
            text=tr('button_apply'),
            command=self.save_tg_proxy_settings,
            width=200, height=32,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        apply_btn.pack(pady=(5, 5))

    def _get_icon_path(self, filename):
        base_path = Path("resources") / filename
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS) / "resources" / filename
        return base_path

    def _create_icon_buttons(self):
        icon_size = (24, 24)
        
        icons = [
            ("tg.png", "https://t.me/zapret_launcher"),
            ("star.png", "https://github.com/tweenkedrage/zapret-launcher")
        ]
        
        for icon_file, url in icons:
            icon_path = self._get_icon_path(icon_file)
            if icon_path.exists():
                img = Image.open(icon_path)
                img = img.resize(icon_size, Image.Resampling.LANCZOS)
                img = img.convert('RGBA')
                
                dark_img = img.copy()
                pixels = dark_img.load()
                for y in range(dark_img.size[1]):
                    for x in range(dark_img.size[0]):
                        r, g, b, a = pixels[x, y]
                        dark_r = int(r * 61 / 255)
                        dark_g = int(g * 61 / 255)
                        dark_b = int(b * 69 / 255)
                        pixels[x, y] = (dark_r, dark_g, dark_b, a)
                dark_photo = ImageTk.PhotoImage(dark_img)
                
                light_img = self._lighten_image(img)
                light_photo = ImageTk.PhotoImage(light_img)
                
                btn = tk.Label(self.icons_frame, image=dark_photo, bg=self.colors['bg_dark'], cursor="hand2")
                btn.image = dark_photo
                btn.light_image = light_photo
                btn.dark_image = dark_photo
                btn.url = url
                
                btn.bind("<Enter>", lambda e, b=btn: b.config(image=b.light_image))
                btn.bind("<Leave>", lambda e, b=btn: b.config(image=b.dark_image))
                btn.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                btn.pack(side=tk.RIGHT, padx=5)

    def _lighten_image(self, img):
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(1.3)
    
    def get_frame(self):
        return self.frame
