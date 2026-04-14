import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import ZapretLauncher

from list_editor import ListEditor
from widgets import RoundedButton
import os
from pathlib import Path

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"
ZAPRET_LAUNCHER_DIR = APPDATA_DIR

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
        os.startfile(ZAPRET_LAUNCHER_DIR)
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

        self.shutdown_status_label = None
        self.shutdown_last_update_label = None
        self.shutdown_tree = None

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
        overlay.configure(bg='black')
        
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
            text="Главная", 
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.main_page,
            text="Управление подключением и мониторинг состояния",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
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
        
        tk.Label(self.app.stats_frame, text="Статистика сессии", font=("Inter", 14, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(0, 10))
        
        stats_row1 = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        stats_row1.pack(fill=tk.X, padx=15, pady=2)
        
        self.app.stats_time_label = tk.Label(stats_row1, text="00:00:00", font=("Inter", 18, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_time_label.pack(side=tk.LEFT)
        
        tk.Label(stats_row1, text="время работы", font=self.font_primary,
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
        
        self.app.stats_rtt_label = tk.Label(rtt_frame, text="-- ms", font=("Inter", 16, "bold"),
                                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_rtt_label.pack(anchor='w', pady=(5, 0))
        
        separator = tk.Frame(self.app.stats_frame, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        info_frame = tk.Frame(self.app.stats_frame, bg=self.colors['bg_medium'])
        info_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.interval_warning_label = tk.Label(
            info_frame,
            text="Чем выше скорость обновления интерфейса, тем больше степень нагрузки на ЦП",
            font=("Inter", 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            justify=tk.LEFT
        )
        self.interval_warning_label.pack(anchor='w')
        
        button_frame = tk.Frame(self.main_page, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, padx=30, pady=20)
        
        self.app.connect_btn = RoundedButton(button_frame, text="ПОДКЛЮЧИТЬСЯ", command=self.app.toggle_connection,
                                    width=350, height=60, bg='#6c5579', 
                                    font=("Inter", 18, "bold"), corner_radius=15)
        self.app.connect_btn.hover_color = '#3D3D45'
        self.app.connect_btn.pack()
        return self.main_page
    
    def create_service_page(self, parent):
        self.service_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.service_page,
            text="Сервис",
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.service_page,
            text="Дополнительные сервисы и функции программы",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
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
            text="Редактор списков",
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.lists_page,
            text="Редактирование списков для обхода блокировок",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        lists_content = tk.Frame(self.lists_page, bg=self.colors['bg_light'])
        lists_content.pack(fill=tk.X, padx=30, pady=10)
        
        for label, filename in [("General листы", "list-general.txt"), ("Google листы", "list-google.txt")]:
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
            
            edit_btn = RoundedButton(btn_frame, text="Изменить", 
                                    command=lambda f=filename: self.edit_list_file(f),
                                    width=100, height=35, bg=self.colors['button_bg'], 
                                    font=("Inter", 10), corner_radius=8)
            edit_btn.pack()
        
        folder_frame = tk.Frame(self.lists_page, bg=self.colors['bg_dark'], cursor="")
        folder_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        open_folder_btn = RoundedButton(folder_frame, text="Расположение ZL", 
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
            text="Диагностика",
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.diagnostic_page,
            text="Проверка состояния компонентов и диагностика сети",
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
            ("Проверить статус", self.app.check_zapret_status),
            ("Логи winws.exe", self.app.check_zapret_logs),
            ("Перезапустить", self.app.restart_zapret),
            ("Авто-подбор", self.app.auto_select_strategy),
        ])
        
        self._create_diagnostic_card(left_panel, "TGProxy", [
            ("Проверить статус", self.app.check_tgproxy_status),
            ("Перезапустить", self.app.restart_tgproxy),
        ])
        
        self._create_diagnostic_card(left_panel, "Система", [
            ("Папка AppData", self.app.open_appdata_folder),
            ("Автозапуск", self.app.toggle_autostart),
            ("Оптимизация сети", self.app.optimize_network_latency),
            ("Найти DNS", self.app.find_and_set_best_dns),
            ("Очистить DNS", self.app.flush_dns_cache_command),
            ("Сбросить настройки", self.app.restore_network_defaults_command),
        ])
        
        self._create_diagnostic_card(left_panel, "Общая диагностика", [
            ("Полная проверка", self.app.run_full_diagnostic),
            ("Сохранить отчет", self.app.save_diagnostic_report),
            ("Проверка файлов", self.app.check_file_integrity),
            ("Очистить кеш", self.app.clear_cache),
        ])
        
        result_frame = tk.Frame(right_panel, bg=self.colors['bg_medium'])
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        result_header = tk.Frame(result_frame, bg=self.colors['bg_medium'], height=35)
        result_header.pack(fill=tk.X)
        result_header.pack_propagate(False)
        
        tk.Label(
            result_header, 
            text="Результаты диагностики", 
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

    def create_shutdown_sites_page(self, parent):
        page = tk.Frame(parent, bg=self.app.colors['bg_dark'])
        
        main_container = tk.Frame(page, bg=self.app.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        title_label = tk.Label(
            main_container,
            text="Сбои интернета",
            font=("Inter", 20, "bold"),
            fg=self.app.colors['text_primary'],
            bg=self.app.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(0, 5))
        
        desc_label = tk.Label(
            main_container,
            text="Проверка доступности популярных сервисов и провайдеров",
            font=("Inter", 10),
            fg=self.app.colors['text_secondary'],
            bg=self.app.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20))
        
        top_frame = tk.Frame(main_container, bg=self.app.colors['bg_dark'])
        top_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.shutdown_refresh_btn = RoundedButton(
            top_frame,
            text="Обновить",
            command=lambda: self.app.refresh_all_shutdown_status(manual=True),
            width=120, height=35,
            bg=self.app.colors['accent'],
            fg=self.app.colors['text_primary'],
            font=("Inter", 10),
            corner_radius=8
        )
        self.shutdown_refresh_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        self.shutdown_status_label = tk.Label(
            top_frame,
            text="Активен",
            font=("Inter", 10),
            fg=self.app.colors['accent_green'],
            bg=self.app.colors['bg_dark']
        )
        self.shutdown_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.shutdown_update_info = tk.Label(
            top_frame,
            text="Данные обновляются в течение 60 секунд",
            font=("Inter", 9),
            fg=self.app.colors['text_secondary'],
            bg=self.app.colors['bg_dark']
        )
        self.shutdown_update_info.pack(side=tk.LEFT, padx=(10, 0))
        
        self.shutdown_last_update_label = tk.Label(
            top_frame,
            text="Последнее обновление: --:--:--",
            font=("Inter", 9),
            fg=self.app.colors['text_secondary'],
            bg=self.app.colors['bg_dark']
        )
        self.shutdown_last_update_label.pack(side=tk.RIGHT)
        
        table_card = tk.Frame(main_container, bg=self.app.colors['bg_light'], relief=tk.FLAT, bd=0)
        table_card.pack(fill=tk.BOTH, expand=True)
        
        table_inner = tk.Frame(table_card, bg=self.app.colors['bg_light'])
        table_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        tree_frame = tk.Frame(table_inner, bg=self.app.colors['bg_light'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", style="Custom.Vertical.TScrollbar")
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", style="Custom.Horizontal.TScrollbar")
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.shutdown_tree = ttk.Treeview(
            tree_frame,
            columns=("service", "status", "source"),
            show="headings",
            height=18,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            style="Custom.Treeview"
        )
        
        self.shutdown_tree.heading("service", text="Сервис/Сайт")
        self.shutdown_tree.heading("status", text="Статус")
        self.shutdown_tree.heading("source", text="Источник")
        self.shutdown_tree.column("service", width=250, anchor='w')
        self.shutdown_tree.column("status", width=150, anchor='center')
        self.shutdown_tree.column("source", width=300, anchor='w')
        self.shutdown_tree.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.shutdown_tree.yview)
        h_scrollbar.config(command=self.shutdown_tree.xview)
        
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background=self.app.colors['bg_light'],
            foreground=self.app.colors['text_primary'],
            fieldbackground=self.app.colors['bg_light'],
            rowheight=28,
            font=("Inter", 9)
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=self.app.colors['bg_medium'],
            foreground=self.app.colors['text_primary'],
            font=("Inter", 10, "bold")
        )
        style.map('Custom.Treeview', background=[('selected', self.app.colors['accent'])])
        return page

    def create_traffic_page(self, parent):
        self.traffic_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.traffic_page,
            text="Трафик",
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.traffic_page,
            text="Мониторинг сетевого трафика по процессам",
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        table_frame = tk.Frame(self.traffic_page, bg=self.colors['bg_light'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        columns = ("Процесс", "Скорость", "VPN", "Прямой", "Соед.", "Хост", "Всего")
        
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
        self.shutsites_page = self.create_shutdown_sites_page(parent)
        
        self.pages = {
            "main": self.main_page,
            "service": self.service_page,
            "lists": self.lists_page,
            "diagnostic": self.diagnostic_page,
            "traffic": self.traffic_page,
            "settings": self.settings_page,
            "shutsites": self.shutsites_page
        }
        
        self.main_page.place(x=0, y=0, width=950, height=800)
        self.current_page = "main"

    def create_settings_page(self, parent):
        self.settings_page = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.settings_page,
            text="Настройки",
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.settings_page,
            text="Настройка интерфейса и параметров работы",
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
        
        self._create_settings_card(left_column, "Обновление интерфейса", [
            ("Быстро", self._set_update_interval_0),
            ("5 секунд", self._set_update_interval_5),
            ("10 секунд", self._set_update_interval_10),
            ("30 секунд", self._set_update_interval_30),
            ("60 секунд", self._set_update_interval_60),
            ("Не обновлять", self._set_update_interval_none),
        ])

        info_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        info_card.pack(fill=tk.X, pady=6)
        info_card.info_card = True
            
        info_inner = tk.Frame(info_card, bg=self.colors['bg_light'])
        info_inner.pack(fill=tk.X, padx=10, pady=8)
            
        tk.Label(info_inner, text="Текущие настройки", font=("Inter", 12, "bold"),
            fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
            
        self.current_interval_label = tk.Label(info_inner, 
            text=f"Обновление интерфейса: {self._get_current_interval_text()}",
            font=("Inter", 10), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.current_interval_label.pack(anchor='w', pady=2)
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
