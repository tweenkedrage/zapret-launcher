import tkinter as tk
from gui.widgets import RoundedButton
import webbrowser
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance
import sys
from utils.languages import tr

class MainPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame, 
            text=tr('main_title'), 
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('main_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        status_frame = tk.Frame(self.frame, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(status_frame, text=tr('status'), font=self.font_bold, 
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.main_status = tk.Label(status_frame, text=tr('status_ready'), font=self.font_medium,
                                        fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.main_status.pack(side=tk.LEFT, padx=15, pady=10)
        
        mode_frame = tk.Frame(self.frame, bg=self.colors['bg_light'])
        mode_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(mode_frame, text=tr('mode'), font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.mode_label = tk.Label(mode_frame, text=tr('mode_not_selected'), font=self.font_medium,
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.mode_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.stats_frame = tk.Frame(self.frame, bg=self.colors['bg_medium'])
        self.app.stats_frame.pack(fill=tk.X, padx=30, pady=(0, 20), ipadx=20, ipady=15)
        
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
                                                fg=self.colors['accent_green'], bg=self.colors['bg_medium'])
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
        
        button_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, padx=30, pady=20)
        
        self.app.connect_btn = RoundedButton(button_frame, text=tr('button_connect'), command=self.app.toggle_connection,
                                    width=350, height=60, bg='#6c5579', 
                                    font=("Inter", 18, "bold"), corner_radius=15)
        self.app.connect_btn.hover_color = '#3D3D45'
        self.app.connect_btn.pack()

        self.icons_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        self.icons_frame.pack(side=tk.BOTTOM, anchor='se', padx=20, pady=15)
        self._create_icon_buttons()

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
