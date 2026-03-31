import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import ZapretLauncher

from list_editor import ListEditor
from widgets import RoundedButton
from custom_provider_manager import load_custom_provider, save_custom_provider, delete_custom_provider
from custom_provider import edit_custom_provider
import os
import time
from pathlib import Path

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

def check_zapret_folder():
    if not ZAPRET_CORE_DIR.exists():
        messagebox.showerror(
            "Ошибка", 
            "Папка с Zapret не найдена!\n\n"
            f"Ожидаемая папка: {ZAPRET_CORE_DIR}\n\n"
            "Запустите программу заново для распаковки ресурсов."
        )
        return False
    return True

def open_zapret_folder():
    if not check_zapret_folder():
        return
    try:
        os.startfile(ZAPRET_CORE_DIR)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть папку: {str(e)}")

class Pages:
    def __init__(self, app: 'ZapretLauncher'):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.current_page = "main"
        self.pages = {}
        
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
                
                if page_name == "settings" and hasattr(self, '_refresh_provider_card'):
                    self._refresh_provider_card()
        
    def create_main_page(self, parent):
        self.main_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        tk.Label(self.main_page, text="Главная", font=("Segoe UI", 32, "bold"), 
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=20)
        
        status_frame = tk.Frame(self.main_page, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(status_frame, text="Статус:", font=self.font_bold, 
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.main_status = tk.Label(status_frame, text="Готов к работе", font=self.font_medium,
                                        fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.main_status.pack(side=tk.LEFT, padx=15, pady=10)
        
        mode_frame = tk.Frame(self.main_page, bg=self.colors['bg_light'])
        mode_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(mode_frame, text="Режим:", font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.mode_label = tk.Label(mode_frame, text="Не выбран", font=self.font_medium,
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.app.mode_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.app.stats_frame = tk.Frame(self.main_page, bg=self.colors['bg_medium'])
        self.app.stats_frame.pack(fill=tk.X, padx=30, pady=(0, 20), ipadx=20, ipady=15)
        
        tk.Label(self.app.stats_frame, text="Статистика сессии", font=("Segoe UI", 14, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(0, 10))
        
        stats_row1 = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        stats_row1.pack(fill=tk.X, padx=15, pady=2)
        
        self.app.stats_time_label = tk.Label(stats_row1, text="00:00:00", font=("Segoe UI", 18, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_time_label.pack(side=tk.LEFT)
        
        tk.Label(stats_row1, text="время работы", font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(5, 20))
        
        self.app.stats_traffic_label = tk.Label(stats_row1, text="⬇ 0 B  |  ⬆ 0 B", font=("Segoe UI", 12),
                                                fg=self.colors['text_primary'], bg=self.colors['bg_medium'])
        self.app.stats_traffic_label.pack(side=tk.LEFT, padx=(0, 20))
        self.app.stats_total_label = tk.Label(stats_row1, text="0 B", font=("Segoe UI", 12),
                                            fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        self.app.stats_total_label.pack(side=tk.LEFT)
        
        stats_speed_frame = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        stats_speed_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        stats_container = tk.Frame(stats_speed_frame, bg=self.colors['bg_medium'], width=550, height=80)
        stats_container.pack(anchor='w')
        stats_container.pack_propagate(False)

        speed_frame = tk.Frame(stats_container, bg=self.colors['bg_medium'])
        speed_frame.place(x=0, y=0, width=300, height=80)
        
        tk.Label(speed_frame, text="Скорость:", font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        self.app.stats_speed_up_label = tk.Label(speed_frame, text="⬆ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent_green'], bg=self.colors['bg_medium'])
        self.app.stats_speed_up_label.pack(anchor='w', pady=(5, 2))
        
        self.app.stats_speed_down_label = tk.Label(speed_frame, text="⬇ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_speed_down_label.pack(anchor='w', pady=2)

        rtt_frame = tk.Frame(stats_container, bg=self.colors['bg_medium'])
        rtt_frame.place(x=320, y=0, width=230, height=80)
        
        tk.Label(rtt_frame, text="Задержка (RTT):", font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        self.app.stats_rtt_label = tk.Label(rtt_frame, text="-- ms", font=("Segoe UI", 16, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_rtt_label.pack(anchor='w', pady=(5, 0))
        
        separator = tk.Frame(self.app.stats_frame, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        info_frame = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        info_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.interval_warning_label = tk.Label(
            info_frame,
            text="Чем выше скорость обновления интерфейса, тем больше степень нагрузки на ЦП",
            font=("Segoe UI", 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            justify=tk.LEFT
        )
        self.interval_warning_label.pack(anchor='w')
        
        button_frame = tk.Frame(self.main_page, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, padx=30, pady=20)
        
        self.app.connect_btn = RoundedButton(button_frame, text="ПОДКЛЮЧИТЬСЯ", command=self.app.toggle_connection,
                                    width=350, height=60, bg='#6c5579', 
                                    font=("Segoe UI", 18, "bold"), corner_radius=15)
        self.app.connect_btn.hover_color = '#3D3D45'
        self.app.connect_btn.pack()
        return self.main_page
    
    def create_service_page(self, parent):
        self.service_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        tk.Label(self.service_page, text="Сервис", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
        functions = [
            ("Фильтры", [
                ("Game Filter", "game_filter"),
                ("IPSet Filter", "ipset_filter"),
            ]),
            ("Обновление", [
                ("Обновить лаунчер", "check_launcher"),
                ("Обновить Zapret", "check_zapret"),
            ]),
        ]
        
        for title, items in functions:
            card = tk.Frame(self.service_page, bg=self.colors['bg_medium'])
            card.pack(fill=tk.X, padx=30, pady=10, ipadx=20, ipady=10)
            
            tk.Label(card, text=title, font=("Segoe UI", 14, "bold"),
                    fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(10, 5))
            
            for btn_text, cmd in items:
                if cmd == "check_launcher":
                    btn = RoundedButton(card, text=btn_text, 
                                    command=lambda: self.app.check_launcher_updates(self.app, silent=False),
                                    width=220, height=35, bg=self.colors['button_bg'],
                                    font=self.font_primary, corner_radius=8)
                elif cmd == "check_zapret":
                    btn = RoundedButton(card, text=btn_text, 
                                    command=lambda: self.app.check_zapret_updates(self.app, silent=False),
                                    width=220, height=35, bg=self.colors['button_bg'],
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
        
        tk.Label(self.lists_page, text="Редактор", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 30), padx=30)
        
        lists_content = tk.Frame(self.lists_page, bg=self.colors['bg_light'])
        lists_content.pack(fill=tk.X, padx=30, pady=10)
        
        for label, filename in [("General листы", "list-general.txt"), ("Google листы", "list-google.txt")]:
            frame = tk.Frame(lists_content, bg=self.colors['bg_light'])
            frame.pack(fill=tk.X, pady=15, padx=20)
            
            text_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(text_frame, text=label, font=("Segoe UI", 14, "bold"), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_light'], anchor='w', cursor="").pack(anchor='w')
            tk.Label(text_frame, text=filename, font=("Segoe UI", 11), 
                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w', cursor="").pack(anchor='w', pady=(5, 0))
            
            btn_frame = tk.Frame(frame, bg=self.colors['bg_light'], cursor="")
            btn_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            edit_btn = RoundedButton(btn_frame, text="ИЗМЕНИТЬ", 
                                    command=lambda f=filename: self.edit_list_file(f),
                                    width=100, height=35, bg=self.colors['button_bg'], 
                                    font=("Segoe UI", 10, "bold"), corner_radius=8)
            edit_btn.pack()
        
        folder_frame = tk.Frame(self.lists_page, bg=self.colors['bg_dark'], cursor="")
        folder_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        open_folder_btn = RoundedButton(folder_frame, text="Открыть папку с Zapret", 
                                    command=open_zapret_folder,
                                    width=300, height=40, bg=self.colors['button_bg'], 
                                    font=("Segoe UI", 11, "bold"), corner_radius=10)
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
        
        tk.Label(self.diagnostic_page, text="Диагностика", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 12), padx=30)
        
        main_container = tk.Frame(self.diagnostic_page, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=4)
        
        cards_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        cards_frame.pack(fill=tk.BOTH, expand=True)
        
        left_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        
        right_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        self._create_card(left_column, "Zapret", [
            ("Проверить статус", self.app.check_zapret_status),
            ("Логи winws.exe", self.app.check_zapret_logs),
            ("Перезапустить Zapret", self.app.restart_zapret),
            ("Авто-подбор", self.app.auto_select_strategy),
        ])
        
        self._create_card(left_column, "TGProxy", [
            ("Проверить статус", self.app.check_tgproxy_status),
            ("Перезапустить TGProxy", self.app.restart_tgproxy),
        ])
        
        self._create_card(left_column, "ByeDPI", [
            ("Проверить статус", self.app.check_byedpi_status),
            ("Перезапустить ByeDPI", self.app.restart_byedpi),
        ])
        
        self._create_card(right_column, "Система", [
            ("Папка AppData", self.app.open_appdata_folder),
            ("Автозапуск", self.app.toggle_autostart),
            ("Оптимизация сети", self.app.optimize_network_latency),
            ("Найти подходящий DNS", self.app.find_and_set_best_dns),
            ("Очистить DNS кеш", self.app.flush_dns_cache_command),
            ("Сбросить настройки", self.app.restore_network_defaults_command),
        ])
        
        self._create_card(right_column, "Состояние интернета", [
            ("Пинг до Google", self.app.check_ping_google),
            ("Пинг до YouTube", self.app.check_ping_youtube),
            ("Пинг до Discord", self.app.check_ping_discord),
            ("Проверить сайт", self.app.check_custom_site),
        ])
        
        self._create_card(right_column, "Общая диагностика", [
            ("Полная проверка", self.app.run_full_diagnostic),
            ("Сохранить отчет", self.app.save_diagnostic_report),
            ("Проверка файлов", self.app.check_file_integrity),
            ("Очистить кеш", self.app.clear_cache),
        ])
        
        result_frame = tk.Frame(main_container, bg=self.colors['bg_light'], height=280)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        result_frame.pack_propagate(False)
        
        result_header = tk.Frame(result_frame, bg=self.colors['bg_light'], height=32)
        result_header.pack(fill=tk.X)
        result_header.pack_propagate(False)
        
        tk.Label(result_header, text="Результаты диагностики:", font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(anchor='w', padx=12, pady=6)
        
        sep = tk.Frame(result_frame, bg=self.colors['separator'], height=1)
        sep.pack(fill=tk.X, padx=12)
        
        text_container = tk.Frame(result_frame, bg=self.colors['bg_light'])
        text_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.app.diagnostic_text = tk.Text(text_container, 
                                        bg=self.colors['bg_dark'],
                                        fg=self.colors['text_primary'],
                                        font=("Consolas", 9),
                                        wrap=tk.WORD,
                                        borderwidth=1,
                                        relief=tk.FLAT,
                                        highlightthickness=1,
                                        highlightbackground=self.colors['separator'],
                                        highlightcolor=self.colors['accent'])
        
        scrollbar = ttk.Scrollbar(text_container, command=self.app.diagnostic_text.yview, style="Custom.Vertical.TScrollbar")
        self.app.diagnostic_text.configure(yscrollcommand=scrollbar.set)
        
        self.app.diagnostic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return self.diagnostic_page

    def _create_card(self, parent, title, buttons):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="")
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'], cursor="")
        inner.pack(fill=tk.X, padx=8, pady=6)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        title_frame.pack(fill=tk.X, pady=(0, 4))
        
        title_label = tk.Label(title_frame, text=title, font=("Segoe UI", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="")
        title_label.pack(side=tk.LEFT)
        
        title_sep = tk.Frame(inner, bg=self.colors['separator'], height=1, cursor="")
        title_sep.pack(fill=tk.X, pady=(0, 4))
        
        buttons_container = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        buttons_container.pack(fill=tk.X)
        
        for i in range(0, len(buttons), 2):
            row = tk.Frame(buttons_container, bg=self.colors['bg_light'], cursor="")
            row.pack(fill=tk.X, pady=1)
            
            btn1_text, btn1_cmd = buttons[i]
            btn1 = RoundedButton(row, text=btn1_text,
                                command=lambda cmd=btn1_cmd: self.app.safe_command(cmd),
                                width=130, height=26,
                                bg=self.colors['button_bg'],
                                fg=self.colors['text_secondary'],
                                font=("Segoe UI", 9),
                                corner_radius=6)
            btn1.pack(side=tk.LEFT, padx=(0, 6))
            
            if i + 1 < len(buttons):
                btn2_text, btn2_cmd = buttons[i + 1]
                btn2 = RoundedButton(row, text=btn2_text,
                                    command=lambda cmd=btn2_cmd: self.app.safe_command(cmd),
                                    width=130, height=26,
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=("Segoe UI", 9),
                                    corner_radius=6)
                btn2.pack(side=tk.LEFT, padx=(6, 0))

    def create_traffic_page(self, parent):
        self.traffic_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        tk.Label(self.traffic_page, text="Трафик по процессам", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
        table_frame = tk.Frame(self.traffic_page, bg=self.colors['bg_light'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        columns = ("Процесс", "Скорость", "VPN", "Прямой", "Соед.", "Хост", "Всего")
        
        style = ttk.Style()
        style.theme_use('default')
        
        style.configure("Treeview.Heading",
                        background=self.colors['bg_medium'],
                        foreground=self.colors['text_primary'],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("Treeview.Heading",
                background=[('active', self.colors['bg_medium'])],
                foreground=[('active', self.colors['text_primary'])])
        
        style.configure("Treeview",
                        background=self.colors['bg_light'],
                        foreground=self.colors['text_primary'],
                        rowheight=25,
                        fieldbackground=self.colors['bg_light'],
                        font=("Segoe UI", 9))
        
        style.map("Treeview",
                background=[('selected', self.colors['accent'])],
                foreground=[('selected', 'white')])
        
        self.traffic_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, style="Treeview")
        
        self.traffic_tree.column("Процесс", width=200, anchor="w")
        self.traffic_tree.column("Скорость", width=100, anchor="e")
        self.traffic_tree.column("VPN", width=100, anchor="e")
        self.traffic_tree.column("Прямой", width=100, anchor="e")
        self.traffic_tree.column("Соед.", width=70, anchor="center")
        self.traffic_tree.column("Хост", width=180, anchor="w")
        self.traffic_tree.column("Всего", width=100, anchor="e")
        
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
        
        tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
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
                                font=("Segoe UI", 8),
                                corner_radius=4)
            btn1.pack(side=tk.LEFT, padx=(0, 2))
            
            if i + 1 < len(buttons):
                btn2_text, btn2_cmd = buttons[i + 1]
                btn2 = RoundedButton(row, text=btn2_text, 
                                    command=lambda cmd=btn2_cmd: self.app.safe_command(cmd),
                                    width=130, height=24,
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=("Segoe UI", 8),
                                    corner_radius=4)
                btn2.pack(side=tk.LEFT, padx=(2, 0))

    def create_all_pages(self, parent):
        self.main_page = self.create_main_page(parent)
        self.service_page = self.create_service_page(parent)
        self.lists_page = self.create_lists_page(parent)
        self.diagnostic_page = self.create_diagnostic_page(parent)
        self.traffic_page = self.create_traffic_page(parent)
        self.settings_page = self.create_settings_page(parent)
        
        self.pages = {
            "main": self.main_page,
            "service": self.service_page,
            "lists": self.lists_page,
            "diagnostic": self.diagnostic_page,
            "traffic": self.traffic_page,
            "settings": self.settings_page
        }
        
        self.main_page.place(x=0, y=0, width=950, height=800)
        self.current_page = "main"

    def create_settings_page(self, parent):
        self.settings_page = tk.Frame(parent, bg=self.colors['bg_dark'], cursor="")
        
        tk.Label(self.settings_page, text="Настройки лаунчера", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 12), padx=30)
        
        main_container = tk.Frame(self.settings_page, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=4)
        
        cards_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        cards_frame.pack(fill=tk.BOTH, expand=True)
        
        left_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        
        right_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        self._create_settings_card(left_column, "Обновление интерфейса", [
            ("Быстро", self._set_update_interval_0),
            ("5 секунд", self._set_update_interval_5),
            ("10 секунд", self._set_update_interval_10),
            ("30 секунд", self._set_update_interval_30),
            ("60 секунд", self._set_update_interval_60),
            ("Не обновлять", self._set_update_interval_none),
        ])

        self._create_provider_card(left_column)
        info_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        info_card.pack(fill=tk.X, pady=6)
        info_card.info_card = True
            
        info_inner = tk.Frame(info_card, bg=self.colors['bg_light'])
        info_inner.pack(fill=tk.X, padx=10, pady=8)
            
        tk.Label(info_inner, text="Текущие настройки", font=("Segoe UI", 12, "bold"),
            fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
            
        self.current_interval_label = tk.Label(info_inner, 
            text=f"Обновление интерфейса: {self._get_current_interval_text()}",
            font=("Segoe UI", 10), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.current_interval_label.pack(anchor='w', pady=2)
            
        self.current_provider_label = tk.Label(info_inner, 
            text=f"Провайдер ByeDPI: {self.app.current_provider}",
            font=("Segoe UI", 10), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.current_provider_label.pack(anchor='w', pady=2)
        return self.settings_page

    def _get_current_interval_text(self):
        intervals = {
            0: "быстро",
            5: "5 секунд",
            10: "10 секунд",
            30: "30 секунд",
            60: "60 секунд",
            None: "отключено"
        }
        return intervals.get(self.app.update_interval, "10 секунд")
    
    def _create_provider_card(self, parent):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="")
        card.pack(fill=tk.X, pady=4)
        card.provider_card = True
        
        inner = tk.Frame(card, bg=self.colors['bg_light'], cursor="")
        inner.pack(fill=tk.X, padx=8, pady=6)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        title_frame.pack(fill=tk.X, pady=(0, 4))
        
        title_label = tk.Label(title_frame, text="Провайдер для ByeDPI", font=("Segoe UI", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="")
        title_label.pack(side=tk.LEFT)
        
        title_sep = tk.Frame(inner, bg=self.colors['separator'], height=1, cursor="")
        title_sep.pack(fill=tk.X, pady=(0, 4))
        
        providers_container = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        providers_container.pack(fill=tk.X)
        
        providers = list(self.app.PROVIDER_PARAMS.keys())
        custom_provider = load_custom_provider()
        has_custom = custom_provider is not None
        
        if has_custom:
            custom_name = custom_provider.get("name", "Кастомный")
            if custom_name not in providers:
                providers.append(custom_name)
        
        rows = (len(providers) + 1) // 2
        for i in range(rows):
            row = tk.Frame(providers_container, bg=self.colors['bg_light'], cursor="")
            row.pack(fill=tk.X, pady=1)
            
            provider_left = providers[i * 2] if i * 2 < len(providers) else None
            if provider_left:
                btn_left = RoundedButton(row, text=provider_left, 
                                        command=lambda p=provider_left: self._set_provider(p),
                                        width=130, height=26,
                                        bg=self.colors['button_bg'],
                                        fg=self.colors['text_secondary'],
                                        font=("Segoe UI", 9),
                                        corner_radius=6)
                btn_left.pack(side=tk.LEFT, padx=(0, 6))
                
                if has_custom and provider_left == custom_name:
                    delete_btn = RoundedButton(row, text="🗑", 
                                            command=self._delete_custom_provider,
                                            width=26, height=26,
                                            bg=self.colors['accent_red'],
                                            fg='white',
                                            font=("Segoe UI", 12),
                                            corner_radius=6)
                    delete_btn.pack(side=tk.LEFT, padx=(2, 0))

            provider_right = providers[i * 2 + 1] if i * 2 + 1 < len(providers) else None
            if provider_right:
                btn_right = RoundedButton(row, text=provider_right, 
                                        command=lambda p=provider_right: self._set_provider(p),
                                        width=130, height=26,
                                        bg=self.colors['button_bg'],
                                        fg=self.colors['text_secondary'],
                                        font=("Segoe UI", 9),
                                        corner_radius=6)
                btn_right.pack(side=tk.LEFT, padx=(6, 0))
                
                if has_custom and provider_right == custom_name:
                    delete_btn = RoundedButton(row, text="🗑", 
                                            command=self._delete_custom_provider,
                                            width=26, height=26,
                                            bg=self.colors['accent_red'],
                                            fg='white',
                                            font=("Segoe UI", 12),
                                            corner_radius=6)
                    delete_btn.pack(side=tk.LEFT, padx=(2, 0))

            elif provider_left and i * 2 + 1 >= len(providers):
                if has_custom and provider_left == custom_name:
                    for widget in row.winfo_children():
                        widget.destroy()
                    btn_left = RoundedButton(row, text=provider_left, 
                                            command=lambda p=provider_left: self._set_provider(p),
                                            width=130, height=26,
                                            bg=self.colors['button_bg'],
                                            fg=self.colors['text_secondary'],
                                            font=("Segoe UI", 9),
                                            corner_radius=6)
                    btn_left.pack(side=tk.LEFT, padx=(0, 6))
                    
                    delete_btn = RoundedButton(row, text="🗑", 
                                            command=self._delete_custom_provider,
                                            width=26, height=26,
                                            bg=self.colors['accent_red'],
                                            fg='white',
                                            font=("Segoe UI", 12),
                                            corner_radius=6)
                    delete_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        create_frame = tk.Frame(providers_container, bg=self.colors['bg_light'], cursor="")
        create_frame.pack(fill=tk.X, pady=(6, 0))

        button_text = "Редактировать кастомный провайдер" if has_custom else "Создать кастомный провайдер"
        
        create_btn = RoundedButton(create_frame, text=button_text, 
                                command=self._create_custom_provider,
                                width=272, height=26,
                                bg=self.colors['button_bg'],
                                fg=self.colors['text_secondary'],
                                font=("Segoe UI", 9),
                                corner_radius=6)
        create_btn.pack(anchor='w')

    def _create_custom_provider(self):
        if load_custom_provider() is not None:
            self._edit_custom_provider()
            return
        
        result = edit_custom_provider(self.app.root, self.colors)
        if result:
            if save_custom_provider(result["name"], result["params"]):
                self.app.PROVIDER_PARAMS[result["name"]] = result["params"]
                messagebox.showinfo("Успех", f"Провайдер '{result['name']}' создан")
                self._refresh_provider_card()
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить провайдера")

    def _edit_custom_provider(self):
        custom = load_custom_provider()
        if not custom:
            return
        
        result = edit_custom_provider(self.app.root, self.colors, custom)
        if result:
            if save_custom_provider(result["name"], result["params"]):
                old_name = custom["name"]
                if old_name in self.app.PROVIDER_PARAMS:
                    del self.app.PROVIDER_PARAMS[old_name]
                self.app.PROVIDER_PARAMS[result["name"]] = result["params"]
                
                if self.app.current_provider == old_name:
                    self.app.current_provider = result["name"]
                    self.app.provider_var.set(result["name"])
                    self.app.byedpi.set_provider(result["name"])
                    if hasattr(self, 'current_provider_label'):
                        self.current_provider_label.config(text=f"Провайдер ByeDPI: {result['name']}")
                
                messagebox.showinfo("Успех", f"Провайдер '{result['name']}' обновлён")
                self._refresh_provider_card()
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить провайдера")

    def _delete_custom_provider(self):
        custom = load_custom_provider()
        if not custom:
            return
        
        result = messagebox.askyesno("Подтверждение", 
            f"Удалить кастомный провайдер '{custom['name']}'?\n\n"
            "Это действие нельзя отменить.")
        
        if result:
            if delete_custom_provider():
                if custom["name"] in self.app.PROVIDER_PARAMS:
                    del self.app.PROVIDER_PARAMS[custom["name"]]
                
                default_provider = "Телеком/Дом.ru/Tele2"
                self.app.current_provider = default_provider
                self.app.provider_var.set(default_provider)
                self.app.byedpi.set_provider(default_provider)
                self.app.save_settings()
                
                if hasattr(self, 'current_provider_label'):
                    self.current_provider_label.config(text=f"Провайдер ByeDPI: {default_provider}")
                
                self._refresh_provider_card()
                messagebox.showinfo("Успех", "Кастомный провайдер удалён")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить провайдера")

    def _refresh_provider_card(self):
        for widget in self.settings_page.winfo_children():
            if isinstance(widget, tk.Frame):
                for cards_frame in widget.winfo_children():
                    if isinstance(cards_frame, tk.Frame):
                        for left_column in cards_frame.winfo_children():
                            if isinstance(left_column, tk.Frame):
                                for child in left_column.winfo_children():
                                    if hasattr(child, 'provider_card') and child.provider_card:
                                        child.destroy()
                                self._create_provider_card(left_column)
                                
                                info_card = None
                                for child in left_column.winfo_children():
                                    if hasattr(child, 'info_card') and child.info_card:
                                        info_card = child
                                        break
                                
                                if info_card:
                                    info_card.pack_forget()
                                    info_card.pack(fill=tk.X, pady=8)
                                
                                self.settings_page.update_idletasks()
                                return

    def _create_settings_card(self, parent, title, options):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="")
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'], cursor="")
        inner.pack(fill=tk.X, padx=8, pady=6)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'], cursor="")
        title_frame.pack(fill=tk.X, pady=(0, 4))
        
        title_label = tk.Label(title_frame, text=title, font=("Segoe UI", 12, "bold"),
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
                                    font=("Segoe UI", 9),
                                    corner_radius=6)
                btn1.pack(side=tk.LEFT, padx=(0, 6))
            
            if i + 1 < len(options):
                opt2_text, opt2_cmd = options[i + 1]
                if opt2_cmd:
                    btn2 = RoundedButton(row, text=opt2_text, command=opt2_cmd,
                                        width=130, height=26,
                                        bg=self.colors['button_bg'],
                                        fg=self.colors['text_secondary'],
                                        font=("Segoe UI", 9),
                                        corner_radius=6)
                    btn2.pack(side=tk.LEFT, padx=(6, 0))
            else:
                pass

    def _set_provider(self, provider):
        if provider == self.app.current_provider:
            return
        
        self.app.current_provider = provider
        self.app.provider_var.set(provider)
        self.app.byedpi.set_provider(provider)
        self.app.save_settings()
        
        if hasattr(self, 'current_provider_label'):
            self.current_provider_label.config(text=f"Провайдер ByeDPI: {provider}")
        
        if self.app.byedpi_enabled:
            self.app.byedpi.stop()
            time.sleep(0.5)
            success, msg = self.app.byedpi.start()
            if not success:
                self.app.log_to_diagnostic(f"Ошибка перезапуска ByeDPI с провайдером {provider}: {msg}")
                self.app.byedpi_enabled = False
                self.app.byedpi_var.set(False)
            else:
                self.app.log_to_diagnostic(f"Провайдер ByeDPI изменен на: {provider}")
        
        self._update_provider_buttons_highlight(provider)
        self.app.show_notification(f"Провайдер ByeDPI: {provider}")

    def _update_provider_buttons_highlight(self, selected_provider, parent=None):
        if parent is None:
            parent = self.settings_page
        
        for widget in parent.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for btn in child.winfo_children():
                            if hasattr(btn, 'get_text') and btn.get_text() in self.app.PROVIDER_PARAMS:
                                if btn.get_text() == selected_provider:
                                    btn.update_colors(self.colors['accent'], self.colors['text_primary'], self.colors['accent_hover'])
                                else:
                                    btn.update_colors(self.colors['button_bg'], self.colors['text_secondary'], self.colors['button_bg'])

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
        
        self.app.show_notification("Обновление интерфейса: быстро")

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
        
        self.app.show_notification("Обновление интерфейса: 5 секунд")

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
        
        self.app.show_notification("Обновление интерфейса: 10 секунд")

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
        
        self.app.show_notification("Обновление интерфейса: 30 секунд")

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
        
        self.app.show_notification("Обновление интерфейса: 60 секунд")

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
        
        self.app.show_notification("Обновление интерфейса: отключено")

    def _update_interval_ui(self):
        if hasattr(self, 'current_interval_label'):
            self.current_interval_label.config(
                text=f"Обновление интерфейса: {self._get_current_interval_text()}"
            )
