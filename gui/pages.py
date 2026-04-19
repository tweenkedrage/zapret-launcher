import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING
from utils.languages import tr
# from gui.theme import get_theme_names

if TYPE_CHECKING:
    from main import ZapretLauncher

from utils.list_editor import ListEditor
from gui.widgets import RoundedButton
import os
from pathlib import Path
import webbrowser

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'Zapret Launcher'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"
ZAPRET_LAUNCHER_DIR = APPDATA_DIR

def check_zapret_folder():
    if not ZAPRET_CORE_DIR.exists():
        messagebox.showerror(
            tr('error_zapret_folder'), 
            f"{tr('error_zapret_folder')}\n\n"
            f"Expected folder: {ZAPRET_CORE_DIR}\n\n"
            "Restart the program to extract resources."
        )
        return False
    return True

def open_zapret_folder():
    if not check_zapret_folder():
        return
    try:
        os.startfile(ZAPRET_LAUNCHER_DIR)
    except Exception as e:
        messagebox.showerror(tr('error_occurred'), f"Failed to open folder: {str(e)}")

class Pages:
    def __init__(self, app: 'ZapretLauncher'):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.current_page = "main"
        self.pages = {}

        self._pending_page = None
        self._animation_active = False
        
    def show_page(self, page_name):
        if page_name == self.current_page:
            return
        
        if hasattr(self, f"{self.current_page}_page"):
            current_page = getattr(self, f"{self.current_page}_page")
            if current_page:
                current_page.place_forget()
        
        if hasattr(self, f"{page_name}_page"):
            new_page = getattr(self, f"{page_name}_page")
            if new_page:
                new_page.place(x=0, y=0, width=950, height=800)
                new_page.tkraise()
                new_page.config(cursor="")
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
                    
    def create_main_page(self, parent):
        self.main_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.main_page, 
            text=tr('main_title'), 
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.main_page,
            text=tr('main_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        status_frame = tk.Frame(self.main_page, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(status_frame, text=tr('status'), font=self.font_bold, 
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.main_status = tk.Label(status_frame, text=tr('status_ready'), font=self.font_medium,
                                        fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.main_status.pack(side=tk.LEFT, padx=15, pady=10)
        
        mode_frame = tk.Frame(self.main_page, bg=self.colors['bg_light'])
        mode_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(mode_frame, text=tr('mode'), font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.mode_label = tk.Label(mode_frame, text=tr('mode_not_selected'), font=self.font_medium,
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.mode_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.stats_frame = tk.Frame(self.main_page, bg=self.colors['bg_medium'])
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
        
        button_frame = tk.Frame(self.main_page, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, padx=30, pady=20)
        
        self.app.connect_btn = RoundedButton(button_frame, text=tr('button_connect'), command=self.app.toggle_connection,
                                    width=350, height=60, bg='#6c5579', 
                                    font=("Inter", 18, "bold"), corner_radius=15)
        self.app.connect_btn.hover_color = '#3D3D45'
        self.app.connect_btn.pack()
        return self.main_page
    
    def create_service_page(self, parent):
        self.service_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.service_page,
            text=tr('service_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.service_page,
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
            (tr('service_updates'), [
                (tr('service_update_launcher'), "check_launcher"),
                (tr('service_update_zapret'), "check_zapret"),
            ]),
        ]
        
        for title, items in functions:
            card = tk.Frame(self.service_page, bg=self.colors['bg_medium'])
            card.pack(fill=tk.X, padx=30, pady=10, ipadx=20, ipady=10)
            
            tk.Label(card, text=title, font=("Inter", 14, "bold"),
                    fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(10, 5))
            
            for btn_text, cmd in items:
                if cmd == "check_launcher":
                    btn = RoundedButton(card, text=btn_text, 
                                    command=lambda: self.app.check_launcher_updates(self.app, silent=False),
                                    width=200, height=35, bg=self.colors['button_bg'],
                                    font=self.font_primary, corner_radius=8)
                elif cmd == "check_zapret":
                    btn = RoundedButton(card, text=btn_text, 
                                    command=lambda: self.app.check_zapret_updates(self.app, silent=False),
                                    width=200, height=35, bg=self.colors['button_bg'],
                                    font=self.font_primary, corner_radius=8)
                else:
                    btn = RoundedButton(card, text=btn_text, 
                                    command=lambda c=cmd: self.app.run_service_command(c),
                                    width=200, height=35, bg=self.colors['button_bg'],
                                    font=self.font_primary, corner_radius=8)
                btn.pack(anchor='w', padx=15, pady=2)
        return self.service_page
    
    def create_lists_page(self, parent):
        self.lists_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.lists_page,
            text=tr('lists_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.lists_page,
            text=tr('lists_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        lists_content = tk.Frame(self.lists_page, bg=self.colors['bg_light'])
        lists_content.pack(fill=tk.X, padx=30, pady=10)
        
        for label, filename in [
            (tr('lists_general'), "list-general.txt"), 
            (tr('lists_google'), "list-google.txt"), 
            (tr('lists_ipset'), "ipset-all.txt")
        ]:
            
            frame = tk.Frame(lists_content, bg=self.colors['bg_light'])
            frame.pack(fill=tk.X, pady=15, padx=20)
            
            text_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(text_frame, text=label, font=("Inter", 14, "bold"), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_light'], anchor='w', cursor="").pack(anchor='w')
            tk.Label(text_frame, text=filename, font=("Inter", 11), 
                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w', cursor="").pack(anchor='w', pady=(5, 0))
            
            btn_frame = tk.Frame(frame, bg=self.colors['bg_light'], cursor="")
            btn_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            edit_btn = RoundedButton(btn_frame, text=tr('lists_edit'), 
                                    command=lambda f=filename: self.edit_list_file(f),
                                    width=100, height=35, bg=self.colors['button_bg'], 
                                    font=("Inter", 10), corner_radius=8)
            edit_btn.pack()
        
        folder_frame = tk.Frame(self.lists_page, bg=self.colors['bg_dark'], cursor="")
        folder_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        open_folder_btn = RoundedButton(folder_frame, text=tr('lists_open_folder'), 
                                    command=open_zapret_folder,
                                    width=300, height=40, bg=self.colors['button_bg'], 
                                    font=("Inter", 11, "bold"), corner_radius=10)
        open_folder_btn.pack()
        return self.lists_page
    
    def edit_list_file(self, filename):
        if not check_zapret_folder():
            return
        lists_path = os.path.join(self.app.zapret.zapret_dir, "lists")
        file_path = os.path.join(lists_path, filename)
        ListEditor(self.app.root, file_path, filename)
    
    def create_diagnostic_page(self, parent):
        self.diagnostic_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.diagnostic_page,
            text=tr('diagnostic_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.diagnostic_page,
            text=tr('diagnostic_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        header_frame = tk.Frame(self.diagnostic_page, bg=self.colors['bg_dark'])
        header_frame.pack(fill=tk.X, pady=(20, 10), padx=30)
        
        main_container = tk.Frame(self.diagnostic_page, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        left_panel = tk.Frame(main_container, bg=self.colors['bg_dark'], width=420)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15), anchor='n')

        right_panel = tk.Frame(main_container, bg=self.colors['bg_dark'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, anchor='n')
        
        self._create_diagnostic_card(left_panel, "Zapret", [
            (tr('diagnostic_zapret_logs'), self.app.check_zapret_logs),
            (tr('diagnostic_zapret_auto'), self.app.auto_select_strategy),
        ])
        
        self._create_diagnostic_card(left_panel, tr('diagnostic_system'), [
            (tr('diagnostic_system_appdata'), self.app.open_appdata_folder),
            (tr('diagnostic_system_autostart'), self.app.toggle_autostart),
            (tr('diagnostic_system_optimize'), self.app.optimize_network_latency),
            (tr('diagnostic_system_dns_find'), self.app.find_and_set_best_dns),
            (tr('diagnostic_system_dns_flush'), self.app.flush_dns_cache_command),
            (tr('diagnostic_system_restore'), self.app.restore_network_defaults_command),
        ])
        
        self._create_diagnostic_card(left_panel, tr('diagnostic_general'), [
            (tr('diagnostic_general_integrity'), self.app.check_file_integrity),
            (tr('diagnostic_general_clear'), self.app.clear_cache),
            (tr('diagnostic_general_report'), self.app.save_diagnostic_report),
        ])
        
        result_frame = tk.Frame(right_panel, bg=self.colors['bg_medium'])
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        result_header = tk.Frame(result_frame, bg=self.colors['bg_medium'], height=35)
        result_header.pack(fill=tk.X)
        result_header.pack_propagate(False)
        
        tk.Label(
            result_header, 
            text=tr('diagnostic_results'), 
            font=("Inter", 12, "bold"),
            fg=self.colors['accent'], 
            bg=self.colors['bg_medium']
        ).pack(side=tk.LEFT, padx=12, pady=6)
        
        sep = tk.Frame(result_frame, bg=self.colors['separator'], height=1)
        sep.pack(fill=tk.X, padx=12)
        
        text_container = tk.Frame(result_frame, bg=self.colors['bg_medium'])
        text_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.app.diagnostic_text = tk.Text(
            text_container, 
            bg=self.colors['bg_dark'],
            fg=self.colors['text_primary'],
            font=("Consolas", 9),
            wrap=tk.WORD,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors['separator'],
            highlightcolor=self.colors['accent'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            padx=8,
            pady=8
        )
        
        scrollbar = ttk.Scrollbar(
            text_container, 
            command=self.app.diagnostic_text.yview, 
            style="Custom.Vertical.TScrollbar"
        )
        self.app.diagnostic_text.configure(yscrollcommand=scrollbar.set)
        
        self.app.diagnostic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return self.diagnostic_page

    def _create_diagnostic_card(self, parent, title, buttons):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'])
        inner.pack(fill=tk.X, padx=10, pady=6)
        
        title_label = tk.Label(
            inner, 
            text=title, 
            font=("Inter", 11, "bold"),
            fg=self.colors['accent'], 
            bg=self.colors['bg_light']
        )
        title_label.pack(anchor='w', pady=(0, 5))
        
        sep = tk.Frame(inner, bg=self.colors['separator'], height=1)
        sep.pack(fill=tk.X, pady=(0, 5))
        
        buttons_container = tk.Frame(inner, bg=self.colors['bg_light'])
        buttons_container.pack(fill=tk.X)
        
        row = None
        for i, (btn_text, btn_cmd) in enumerate(buttons):
            if i % 2 == 0:
                row = tk.Frame(buttons_container, bg=self.colors['bg_light'])
                row.pack(fill=tk.X, pady=2)
            
            btn = RoundedButton(
                row if row else buttons_container,
                text=btn_text,
                command=lambda cmd=btn_cmd: self.app.safe_command(cmd),
                width=130, height=26,
                bg=self.colors['button_bg'],
                fg=self.colors['text_secondary'],
                font=("Inter", 8),
                corner_radius=5
            )
            
            if i % 2 == 0:
                btn.pack(side=tk.LEFT, padx=(0, 6), expand=True, fill=tk.X)
            else:
                btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        if len(buttons) % 2 == 1 and row:
            filler = tk.Frame(row, bg=self.colors['bg_light'])
            filler.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def create_traffic_page(self, parent):
        self.traffic_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.traffic_page,
            text=tr('traffic_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.traffic_page,
            text=tr('traffic_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        table_frame = tk.Frame(self.traffic_page, bg=self.colors['bg_light'])
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
        return self.traffic_page
    
    def create_diagnostic_card(self, parent, title, buttons):
        card = tk.Frame(parent, bg=self.colors['bg_light'], cursor="")
        card.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(card, text=title, font=("Inter", 11, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_light'], cursor="").pack(anchor='w', padx=5, pady=(2, 0))
        separator = tk.Frame(card, bg=self.colors['separator'], height=1, cursor="")
        separator.pack(fill=tk.X, padx=5, pady=(0, 2))
        container = tk.Frame(card, bg=self.colors['bg_light'], cursor="")
        container.pack(fill=tk.X, padx=5, pady=(0, 2))
        
        for i in range(0, len(buttons), 2):
            row = tk.Frame(container, bg=self.colors['bg_light'], cursor="")
            row.pack(fill=tk.X, pady=1)
            
            btn1_text, btn1_cmd = buttons[i]
            btn1 = RoundedButton(row, text=btn1_text, 
                                command=lambda cmd=btn1_cmd: self.app.safe_command(cmd),
                                width=130, height=24,
                                bg=self.colors['button_bg'],
                                fg=self.colors['text_secondary'],
                                font=("Inter", 8),
                                corner_radius=4)
            btn1.pack(side=tk.LEFT, padx=(0, 2))
            
            if i + 1 < len(buttons):
                btn2_text, btn2_cmd = buttons[i + 1]
                btn2 = RoundedButton(row, text=btn2_text, 
                                    command=lambda cmd=btn2_cmd: self.app.safe_command(cmd),
                                    width=130, height=24,
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=("Inter", 8),
                                    corner_radius=4)
                btn2.pack(side=tk.LEFT, padx=(2, 0))

    def create_all_pages(self, parent):
        self.main_page = self.create_main_page(parent)
        self.service_page = self.create_service_page(parent)
        self.lists_page = self.create_lists_page(parent)
        self.diagnostic_page = self.create_diagnostic_page(parent)
        self.traffic_page = self.create_traffic_page(parent)
        self.settings_page = self.create_settings_page(parent)
        self.additionally_page = self.create_additionally_page(parent)
        
        self.pages = {
            "main": self.main_page,
            "service": self.service_page,
            "lists": self.lists_page,
            "diagnostic": self.diagnostic_page,
            "traffic": self.traffic_page,
            "settings": self.settings_page,
            "additionally": self.additionally_page
        }
        self.main_page.place(x=0, y=0, width=950, height=800)
        self.current_page = "main"

    def create_settings_page(self, parent):
        self.settings_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.settings_page,
            text=tr('settings_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.settings_page,
            text=tr('settings_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        main_container = tk.Frame(self.settings_page, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=4)
        cards_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        cards_frame.pack(fill=tk.BOTH, expand=True)
        left_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        self._create_settings_card(left_column, tr('settings_interface'), [
            (tr('settings_interval_fast'), self._set_update_interval_0),
            (tr('settings_interval_5'), self._set_update_interval_5),
            (tr('settings_interval_10'), self._set_update_interval_10),
            (tr('settings_interval_30'), self._set_update_interval_30),
            (tr('settings_interval_60'), self._set_update_interval_60),
            (tr('settings_interval_off'), self._set_update_interval_none),
        ])
        
        lang_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        lang_card.pack(fill=tk.X, pady=6)
        lang_inner = tk.Frame(lang_card, bg=self.colors['bg_light'])
        lang_inner.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(lang_inner, text=tr('settings_language'), font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        tk.Label(lang_inner, text=tr('settings_language_desc'),
                font=("Inter", 9), fg=self.colors['text_secondary'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        lang_var = tk.StringVar(value=self.app.languages.get_current_language())
        lang_combo = ttk.Combobox(lang_inner, textvariable=lang_var, 
                                   values=list(self.app.languages.LANGUAGES.keys()),
                                   state='readonly', width=15)
        lang_combo.pack(anchor='w', pady=5)
        
        def on_language_change(event=None):
            new_lang = lang_var.get()
            current_lang = self.app.languages.get_current_language()
            
            if new_lang != current_lang:
                restart_msg = tr('restart_manual_message')
                restart_title = tr('restart_manual_title')
                
                self.app.languages.set_language(new_lang)
                self.app.save_settings()
                
                result = messagebox.showwarning(
                    restart_title,
                    restart_msg + "\n\n",
                    type=messagebox.OKCANCEL
                )
                
                if result == 'ok':
                    self.app.quit_from_tray()

        lang_combo.bind("<<ComboboxSelected>>", on_language_change)

        tg_card = tk.Frame(right_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        tg_card.pack(fill=tk.X, pady=6)
        tg_inner = tk.Frame(tg_card, bg=self.colors['bg_light'])
        tg_inner.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(tg_inner, text="Telegram Proxy", font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))

        secret_value = getattr(self.app, '_tg_secret', None)
        if secret_value and len(secret_value) > 16:
            secret_text = f"{tr('settings_current_tg_secret')} {secret_value[:16]}..."
        elif secret_value:
            secret_text = f"{tr('settings_current_tg_secret')} {secret_value}"
        else:
            secret_text = tr('settings_current_tg_secret')

        self.secret_label = tk.Label(tg_inner, text=secret_text,
                            font=("Inter", 9), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.secret_label.pack(anchor='w', pady=(0, 5))

        regenerate_btn = RoundedButton(
            tg_inner,
            text=tr('tg_generate_secret'),
            command=lambda: [self.app.regenerate_tg_secret(), self.update_secret_display()],
            width=200, height=30,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Inter", 10),
            corner_radius=8
        )
        regenerate_btn.pack(anchor='w', pady=5)

        def copy_current_link():
            secret = getattr(self.app, '_tg_secret', None)
            if secret:
                link = f"{secret}"
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(link)
                self.app.root.update()
                self.app.show_notification(tr('notification_copied_secret'))
            else:
                messagebox.showwarning(tr('error_secret_not_found'), tr('error_telegram_proxy_start'))

        copy_btn = RoundedButton(
            tg_inner,
            text=tr('tg_copy_secret'),
            command=copy_current_link,
            width=200, height=30,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8
        )
        copy_btn.pack(anchor='w', pady=5)

        #theme_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        #theme_card.pack(fill=tk.X, pady=6)
        #theme_inner = tk.Frame(theme_card, bg=self.colors['bg_light'])
        #theme_inner.pack(fill=tk.X, padx=10, pady=8)

        #tk.Label(theme_inner, text=tr('settings_theme'), font=("Inter", 12, "bold"),
        #        fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))

        #tk.Label(theme_inner, text=tr('settings_theme_desc'),
        #        font=("Inter", 9), fg=self.colors['text_secondary'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))

        #theme_var = tk.StringVar(value=self.app.current_theme)
        #theme_combo = ttk.Combobox(theme_inner, textvariable=theme_var, 
        #                values=get_theme_names(),
        #                state='readonly', width=15)
        #theme_combo.pack(anchor='w', pady=5)

        #def on_theme_change(event=None):
        #    new_theme = theme_var.get()
        #    if new_theme != self.app.current_theme:
        #        self.app.current_theme = new_theme
        #        self.app.save_settings()
        #        result = messagebox.askyesno(
        #            tr('dialog_restart_title'),
        #            tr('notification_theme_restart')
        #        )
        #        if result:
        #            self.app.restart_main()

        #theme_combo.bind("<<ComboboxSelected>>", on_theme_change)

        info_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        info_card.pack(fill=tk.X, pady=6)
        info_card.info_card = True
            
        info_inner = tk.Frame(info_card, bg=self.colors['bg_light'])
        info_inner.pack(fill=tk.X, padx=10, pady=8)
            
        tk.Label(info_inner, text=tr('settings_current'), font=("Inter", 12, "bold"),
            fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
            
        self.current_interval_label = tk.Label(info_inner, 
            text=f"{tr('settings_current_interval')} {self._get_current_interval_text()}",
            font=("Inter", 10), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.current_interval_label.pack(anchor='w', pady=2)
        return self.settings_page
    
    def create_additionally_page(self, parent):
        frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            frame,
            text=tr('additionally_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            frame,
            text=tr('additionally_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        soundcloud_card = tk.Frame(
            frame,
            bg=self.colors['bg_medium'],
            relief=tk.FLAT,
            bd=0
        )
        soundcloud_card.pack(fill=tk.X, padx=30, pady=10)
        
        inner = tk.Frame(soundcloud_card, bg=self.colors['bg_medium'])
        inner.pack(fill=tk.X, padx=20, pady=15)
        
        sc_title = tk.Label(
            inner,
            text="SoundCloud",
            font=("Inter", 16, "bold"),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium'],
            cursor="hand2"
        )
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
        
        sc_desc = tk.Label(
            inner,
            text=tr('soundcloud_description'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            wraplength=800,
            justify=tk.LEFT
        )
        sc_desc.pack(anchor='w', pady=(5, 15))
        
        btn_frame = tk.Frame(inner, bg=self.colors['bg_medium'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        status_label = tk.Label(
            inner,
            text="",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        status_label.pack(anchor='w', pady=(10, 0))
        
        def update_buttons():
            is_enabled = self.app.check_soundcloud_enabled()
            
            if is_enabled:
                for widget in btn_frame.winfo_children():
                    widget.destroy()
                
                disable_btn = RoundedButton(
                    btn_frame,
                    text=tr('disable'),
                    command=lambda: [self.app.remove_soundcloud_unblock(), update_buttons()],
                    width=120, height=35,
                    bg=self.colors['button_bg'],
                    fg=self.colors['text_secondary'],
                    font=("Inter", 10),
                    corner_radius=8
                )
                disable_btn.pack(side=tk.LEFT)
                
                status_label.config(
                    text=f"{tr('enabled_additionally')}",
                    fg=self.colors['accent_green']
                )
            else:
                for widget in btn_frame.winfo_children():
                    widget.destroy()
                
                enable_btn = RoundedButton(
                    btn_frame,
                    text=tr('enable'),
                    command=lambda: [self.app.add_soundcloud_unblock(), update_buttons()],
                    width=120, height=35,
                    bg=self.colors['accent'],
                    fg=self.colors['text_primary'],
                    font=("Inter", 10),
                    corner_radius=8
                )
                enable_btn.pack(side=tk.LEFT)
                
                status_label.config(
                    text=f"{tr('disabled_additionally')}",
                    fg=self.colors['text_secondary']
                )

        meta_card = tk.Frame(
        frame,
        bg=self.colors['bg_medium'],
        relief=tk.FLAT,
        bd=0
        )
                
        meta_card.pack(fill=tk.X, padx=30, pady=5)
        meta_inner = tk.Frame(meta_card, bg=self.colors['bg_medium'])
        meta_inner.pack(fill=tk.X, padx=20, pady=10)

        meta_title = tk.Label(
            meta_inner,
            text="Meta",
            font=("Inter", 16, "bold"),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium'],
            cursor="hand2"
        )
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

        meta_desc = tk.Label(
            meta_inner,
            text=tr('meta_description'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            wraplength=800,
            justify=tk.LEFT
        )
        meta_desc.pack(anchor='w', pady=(5, 10))

        meta_btn_frame = tk.Frame(meta_inner, bg=self.colors['bg_medium'])
        meta_btn_frame.pack(fill=tk.X, pady=5)

        meta_status_label = tk.Label(
            meta_inner,
            text="",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        meta_status_label.pack(anchor='w', pady=(5, 0))

        def update_meta_buttons():
            is_enabled = self.app.check_meta_enabled()
            
            if is_enabled:
                for widget in meta_btn_frame.winfo_children():
                    widget.destroy()
                
                disable_btn = RoundedButton(
                    meta_btn_frame,
                    text=tr('disable'),
                    command=lambda: [self.app.remove_facebook_instagram_unblock(), update_meta_buttons()],
                    width=120, height=35,
                    bg=self.colors['button_bg'],
                    fg=self.colors['text_secondary'],
                    font=("Inter", 10),
                    corner_radius=8
                )
                disable_btn.pack(side=tk.LEFT)
                
                meta_status_label.config(
                    text=f"{tr('enabled_additionally')}",
                    fg=self.colors['accent_green']
                )
            else:
                for widget in meta_btn_frame.winfo_children():
                    widget.destroy()
                
                enable_btn = RoundedButton(
                    meta_btn_frame,
                    text=tr('enable'),
                    command=lambda: [self.app.add_facebook_instagram_unblock(), update_meta_buttons()],
                    width=120, height=35,
                    bg=self.colors['accent'],
                    fg=self.colors['text_primary'],
                    font=("Inter", 10),
                    corner_radius=8
                )
                enable_btn.pack(side=tk.LEFT)
                
                meta_status_label.config(
                    text=f"{tr('disabled_additionally')}",
                    fg=self.colors['text_secondary']
                )

        update_meta_buttons()
        update_buttons()
        return frame
    
    def update_secret_display(self):
        if hasattr(self, 'secret_label') and self.secret_label:
            new_secret = getattr(self.app, '_tg_secret', None)
            if new_secret and len(new_secret) > 16:
                self.secret_label.config(text=f"{tr('settings_current_tg_secret')} {new_secret[:16]}...")
            elif new_secret:
                self.secret_label.config(text=f"{tr('settings_current_tg_secret')} {new_secret}")
            else:
                self.secret_label.config(text={tr('settings_current_tg_secret')})

    def _get_current_interval_text(self):
        intervals = {
            0: tr('settings_interval_fast_text'),
            5: "5 seconds",
            10: "10 seconds",
            30: "30 seconds",
            60: "60 seconds",
            None: tr('settings_interval_off_text')
        }
        return intervals.get(self.app.update_interval, "10 seconds")

    def _create_settings_card(self, parent, title, options):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="")
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'], cursor="")
        inner.pack(fill=tk.X, padx=8, pady=6)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        title_frame.pack(fill=tk.X, pady=(0, 4))
        
        title_label = tk.Label(title_frame, text=title, font=("Inter", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="")
        title_label.pack(side=tk.LEFT)
        
        title_sep = tk.Frame(inner, bg=self.colors['separator'], height=1, cursor="")
        title_sep.pack(fill=tk.X, pady=(0, 4))
        
        options_container = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        options_container.pack(fill=tk.X)
        
        for i in range(0, len(options), 2):
            row = tk.Frame(options_container, bg=self.colors['bg_light'], cursor="")
            row.pack(fill=tk.X, pady=1)
            
            opt1_text, opt1_cmd = options[i]
            if opt1_cmd:
                btn1 = RoundedButton(row, text=opt1_text, command=opt1_cmd,
                                    width=130, height=26,
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=("Inter", 9),
                                    corner_radius=6)
                btn1.pack(side=tk.LEFT, padx=(0, 6))
            
            if i + 1 < len(options):
                opt2_text, opt2_cmd = options[i + 1]
                if opt2_cmd:
                    btn2 = RoundedButton(row, text=opt2_text, command=opt2_cmd,
                                        width=130, height=26,
                                        bg=self.colors['button_bg'],
                                        fg=self.colors['text_secondary'],
                                        font=("Inter", 9),
                                        corner_radius=6)
                    btn2.pack(side=tk.LEFT, padx=(6, 0))
            else:
                pass

    def _set_update_interval_0(self):
        if self.app.update_interval_index == 0:
            return
        
        self.app.update_interval_index = 0
        self.app.update_interval = self.app.update_intervals[0]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None
        
        if self.app.pages.current_page == "traffic":
            self.app.update_traffic_table()
        
        self.app.show_notification(tr('notification_interval_fast'))

    def _set_update_interval_5(self):
        if self.app.update_interval_index == 1:
            return
        
        self.app.update_interval_index = 1
        self.app.update_interval = self.app.update_intervals[1]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None
        
        if self.app.pages.current_page == "traffic":
            self.app.update_traffic_table()
        
        self.app.show_notification(tr('notification_interval_5'))

    def _set_update_interval_10(self):
        if self.app.update_interval_index == 2:
            return
        
        self.app.update_interval_index = 2
        self.app.update_interval = self.app.update_intervals[2]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None
        
        if self.app.pages.current_page == "traffic":
            self.app.update_traffic_table()
        
        self.app.show_notification(tr('notification_interval_10'))

    def _set_update_interval_30(self):
        if self.app.update_interval_index == 3:
            return
        
        self.app.update_interval_index = 3
        self.app.update_interval = self.app.update_intervals[3]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None
        
        if self.app.pages.current_page == "traffic":
            self.app.update_traffic_table()
        
        self.app.show_notification(tr('notification_interval_30'))

    def _set_update_interval_60(self):
        if self.app.update_interval_index == 4:
            return
        
        self.app.update_interval_index = 4
        self.app.update_interval = self.app.update_intervals[4]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None
        
        if self.app.pages.current_page == "traffic":
            self.app.update_traffic_table()
        
        self.app.show_notification(tr('notification_interval_60'))

    def _set_update_interval_none(self):
        if self.app.update_interval_index == 5:
            return
        
        self.app.update_interval_index = 5
        self.app.update_interval = None
        self._update_interval_ui()
        self.app.save_settings()
        
        self.app.stop_stats_monitoring()
        
        if hasattr(self.app, '_traffic_update_timer') and self.app._traffic_update_timer:
            try:
                self.app.root.after_cancel(self.app._traffic_update_timer)
            except:
                pass
            self.app._traffic_update_timer = None

        if self.app.pages.current_page == "traffic":
            for item in self.app.pages.traffic_tree.get_children():
                self.app.pages.traffic_tree.delete(item)
        
        self.app.show_notification(tr('notification_interval_off'))

    def _update_interval_ui(self):
        if hasattr(self, 'current_interval_label'):
            self.current_interval_label.config(
                text=f"{tr('settings_current_interval')} {self._get_current_interval_text()}"
            )
