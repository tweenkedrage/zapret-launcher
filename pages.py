import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zapret_gui import ZapretLauncher

from theme import get_theme
from list_editor import ListEditor
from widgets import RoundedButton
import webbrowser
import os
import subprocess
import json
import time
import threading
import sys
from pathlib import Path

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"
CURRENT_VERSION = "2.3b"

PROVIDER_PARAMS = {
    "Ростелеком/Дом.ru/Tele2/SamaraLan": ["--split", "1", "--disorder", "-1"],
    "МГТС (МТС)/Yota": ["-7", "-e1", "-q"],
    "Мегафон": ["-s0", "-o1", "-d1", "-r1+s", "-Ar", "-o1", "-At", "-f-1", "-r1+s", "-As"],
    "Билайн": ["--split", "1", "--disorder", "1", "--fake", "-1", "--ttl", "8"],
    "ТТК": ["-1", "-e1"],
    "SkyNet (Киргизия)": ["--split", "1", "--disorder", "1", "--fake", "-1", "--ttl", "8"],
}

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
        
    def create_all_pages(self, content_panel):
        self.content_panel = content_panel
        
        self.create_main_page()
        self.create_service_page()
        self.create_lists_page()
        self.create_diagnostic_page()
        self.create_help_page()
        
    def show_page(self, page_name):
        if page_name == self.current_page:
            return
        
        if hasattr(self, f"{self.current_page}_page"):
            getattr(self, f"{self.current_page}_page").place_forget()
        
        if hasattr(self, f"{page_name}_page"):
            getattr(self, f"{page_name}_page").place(x=0, y=0, width=950, height=800)
            getattr(self, f"{page_name}_page").tkraise()
            self.current_page = page_name
    
    def create_main_page(self):
        self.main_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        self.main_page.place(x=0, y=0, width=950, height=800)
        
        tk.Label(self.main_page, text="Главная", font=("Segoe UI", 32, "bold"), 
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
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
        
        tk.Label(stats_speed_frame, text="Скорость:", font=self.font_bold,
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        speed_row = tk.Frame(stats_speed_frame, bg=self.colors['bg_medium'])
        speed_row.pack(fill=tk.X, pady=5)
        
        self.app.stats_speed_up_label = tk.Label(speed_row, text="⬆ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent_green'], bg=self.colors['bg_medium'])
        self.app.stats_speed_up_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.app.stats_speed_down_label = tk.Label(speed_row, text="⬇ 0 B/s", font=self.font_primary,
                                                fg=self.colors['accent'], bg=self.colors['bg_medium'])
        self.app.stats_speed_down_label.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(self.main_page, bg=self.colors['bg_dark'])
        button_frame.pack(fill=tk.X, padx=30, pady=30)
        
        self.app.connect_btn = RoundedButton(button_frame, text="ПОДКЛЮЧИТЬСЯ", command=self.app.toggle_connection,
                                    width=350, height=60, bg=self.colors['accent'], 
                                    font=("Segoe UI", 18, "bold"), corner_radius=15)
        self.app.connect_btn.pack()
    
    def create_service_page(self):
        from zapret_gui import check_launcher_updates, check_zapret_updates
        
        self.service_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        
        tk.Label(self.service_page, text="Сервис", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
        functions = [
            ("Фильтры", [
                ("Game Filter", "game_filter"),
                ("IPSet Filter", "ipset_filter"),
            ]),
            ("Обновление", [
                ("Проверить обновление лаунчера", "check_launcher"),
                ("Проверить обновление Zapret", "check_zapret"),
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
                                       command=lambda: check_launcher_updates(self.app, silent=False),
                                       width=220, height=35, bg=self.colors['button_bg'],
                                       font=self.font_primary, corner_radius=8)
                elif cmd == "check_zapret":
                    btn = RoundedButton(card, text=btn_text, 
                                       command=lambda: check_zapret_updates(self.app, silent=False),
                                       width=220, height=35, bg=self.colors['button_bg'],
                                       font=self.font_primary, corner_radius=8)
                else:
                    btn = RoundedButton(card, text=btn_text, 
                                       command=lambda c=cmd: self.app.run_service_command(c),
                                       width=200, height=35, bg=self.colors['button_bg'],
                                       font=self.font_primary, corner_radius=8)
                btn.pack(anchor='w', padx=15, pady=2)
    
    def create_lists_page(self):
        self.lists_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        
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
                    fg=self.colors['text_primary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w')
            tk.Label(text_frame, text=filename, font=("Segoe UI", 11), 
                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w', pady=(5, 0))
            
            btn_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            btn_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            edit_btn = RoundedButton(btn_frame, text="ИЗМЕНИТЬ", 
                                     command=lambda f=filename: self.edit_list_file(f),
                                     width=100, height=35, bg=self.colors['button_bg'], 
                                     font=("Segoe UI", 10, "bold"), corner_radius=8)
            edit_btn.pack()
        
        folder_frame = tk.Frame(self.lists_page, bg=self.colors['bg_dark'])
        folder_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        open_folder_btn = RoundedButton(folder_frame, text="Открыть папку с Zapret", 
                                       command=open_zapret_folder,
                                       width=300, height=45, bg=self.colors['button_bg'], 
                                       font=("Segoe UI", 11, "bold"), corner_radius=10)
        open_folder_btn.pack()
    
    def edit_list_file(self, filename):
        if not check_zapret_folder():
            return
        lists_path = os.path.join(self.app.zapret.zapret_dir, "lists")
        file_path = os.path.join(lists_path, filename)
        ListEditor(self.app.root, file_path, filename)
    
    def create_diagnostic_page(self):
        self.diagnostic_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        
        tk.Label(self.diagnostic_page, text="Диагностика", font=("Segoe UI", 32, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
        cards_frame = tk.Frame(self.diagnostic_page, bg=self.colors['bg_dark'])
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        left_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.create_diagnostic_card(left_column, "Состояние интернета", [
            ("Пинг до Google", self.app.check_ping_google),
            ("Пинг до YouTube", self.app.check_ping_youtube),
            ("Пинг до Discord", self.app.check_ping_discord),
            ("Проверить сайт", self.app.check_custom_site),
        ])
        
        self.create_diagnostic_card(left_column, "Zapret", [
            ("Проверить статус", self.app.check_zapret_status),
            ("Версия стратегий", self.app.check_zapret_version),
            ("Логи winws.exe", self.app.check_zapret_logs),
            ("Перезапустить Zapret", self.app.restart_zapret),
            ("Авто-подбор", self.app.auto_select_strategy),
        ])
        
        self.create_diagnostic_card(left_column, "Общая диагностика", [
            ("Полная проверка", self.app.run_full_diagnostic),
            ("Сохранить отчет", self.app.save_diagnostic_report),
            ("Проверка файлов", self.app.check_file_integrity),
        ])
        
        self.create_diagnostic_card(right_column, "ByeDPI", [
            ("Проверить статус", self.app.check_byedpi_status),
            ("Порт 10801", self.app.check_byedpi_port),
            ("Версия", self.app.check_byedpi_version),
            ("Перезапустить ByeDPI", self.app.restart_byedpi),
        ])
        
        self.create_diagnostic_card(right_column, "TGProxy", [
            ("Проверить статус", self.app.check_tgproxy_status),
            ("Порт 1080", self.app.check_tgproxy_port),
            ("Проверить Telegram", self.app.check_telegram),
            ("Перезапустить TGProxy", self.app.restart_tgproxy),
        ])
        
        self.create_diagnostic_card(right_column, "Система", [
            ("Права администратора", self.app.check_admin_rights),
            ("Версия лаунчера", self.app.check_launcher_version),
            ("Папка AppData", self.app.open_appdata_folder),
            ("Очистить кэш", self.app.clear_cache),
            ("Автозапуск", self.app.toggle_autostart),
            ("Оптимизация сети", self.app.optimize_network_latency),
            ("Найти лучший DNS", self.app.find_and_set_best_dns),
            ("Очистить DNS кэш", self.app.flush_dns_cache_command),
            ("Сбросить настройки", self.app.restore_network_defaults_command),
        ])
        
        result_frame = tk.Frame(self.diagnostic_page, bg=self.colors['bg_light'])
        result_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(10, 20))
        
        tk.Label(result_frame, text="Результаты диагностики:", font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(anchor='w', padx=15, pady=(8, 5))
        
        text_frame = tk.Frame(result_frame, bg=self.colors['bg_light'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.app.diagnostic_text = tk.Text(text_frame, height=8, bg=self.colors['bg_dark'],
                                          fg=self.colors['text_primary'], font=("Consolas", 9),
                                          wrap=tk.WORD, borderwidth=0)
        scrollbar = tk.Scrollbar(text_frame, command=self.app.diagnostic_text.yview)
        self.app.diagnostic_text.configure(yscrollcommand=scrollbar.set)
        
        self.app.diagnostic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_diagnostic_card(self, parent, title, buttons):
        card = tk.Frame(parent, bg=self.colors['bg_light'])
        card.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(anchor='w', padx=5, pady=(2, 0))
        
        separator = tk.Frame(card, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=5, pady=(0, 2))
        
        container = tk.Frame(card, bg=self.colors['bg_light'])
        container.pack(fill=tk.X, padx=5, pady=(0, 2))
        
        for i in range(0, len(buttons), 2):
            row = tk.Frame(container, bg=self.colors['bg_light'])
            row.pack(fill=tk.X, pady=1)
            
            btn1_text, btn1_cmd = buttons[i]
            btn1 = RoundedButton(row, text=btn1_text, 
                                command=lambda cmd=btn1_cmd: self.app.safe_command(cmd),
                                width=180, height=22, bg=self.colors['button_bg'],
                                font=("Segoe UI", 7), corner_radius=4)
            btn1.pack(side=tk.LEFT, padx=(0, 2))
            
            if i + 1 < len(buttons):
                btn2_text, btn2_cmd = buttons[i + 1]
                btn2 = RoundedButton(row, text=btn2_text, 
                                    command=lambda cmd=btn2_cmd: self.app.safe_command(cmd),
                                    width=180, height=22, bg=self.colors['button_bg'],
                                    font=("Segoe UI", 7), corner_radius=4)
                btn2.pack(side=tk.LEFT, padx=(2, 0))
    
    def create_help_page(self):
        self.help_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        
        container = tk.Frame(self.help_page, bg=self.colors['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas_frame = tk.Frame(container, bg=self.colors['bg_dark'])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_dark'], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_dark'])
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((20, 0), window=scrollable_frame, anchor="nw", width=880)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.help_page.bind("<Enter>", lambda e: self.help_page.bind_all("<MouseWheel>", _on_mousewheel))
        self.help_page.bind("<Leave>", lambda e: self.help_page.unbind_all("<MouseWheel>"))
            
        tk.Label(scrollable_frame, text="Помощь", font=("Segoe UI", 28, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(0, 20))
        
        self.help_section(scrollable_frame, "Установка:", [
            ("1.", "Скачивайте архив и распаковывайте в любое место 2 файла: ", "Zapret_Launcher.exe", " и ", "zapret_resources.zip", ";"),
            ("2.", "Запускайте ", "Zapret_Launcher.exe", " от ", "имени администратора", ";"),
            ("3.", "Выбирайте любой метод использования Zapret и подключайтесь к ", "стабильной сети", " находясь под ", "ограничениями РКН", ";"),
            ("4.", "После всех 3-х действий ", "Zapret_Launcher.exe", " можно запускать в любой папке/в любом месте на компьютере ", "без файла zapret_resources.zip", "."),
        ])
        
        self.help_section(scrollable_frame, "Telegram Proxy:", [
            ("1.", "Ставим галочку ", '"Запустить вместе с Zapret"', " в лаунчере", ";"),
            ("2.", "Запускаем ", "Telegram", " на ПК", ";"),
            ("3.", "Переходим в ", "настройки", ";"),
            ("4.", "Продвинутые настройки", ""),
            ("5.", "Тип соединения", ""),
            ("6.", "Использовать собственное прокси (", "SOCKS5", ", Хост: ", "127.0.0.1", ", Порт: ", "1080", ")."),
        ])
        
        self.help_section(scrollable_frame, "ByeDPI Оптимизатор:", [
            ("", "ByeDPI", " — это дополнительный инструмент для обхода DPI;"),
            ("1.", "Включайте только если тормозит интернет или стандартные стратегии не помогают", ";"),
            ("2.", "Особенно полезен для ", "YouTube", " и ", "онлайн-игр", ";"),
            ("3.", "Создает локальный SOCKS5 прокси на порту ", "10801", ";"),
        ])
        
        self.help_section(scrollable_frame, "Что такое zapret_resources.zip:", [
            ("1.", "Это архив со всеми файлами Zapret, которые необходимы для работы лаунчера", ";"),
            ("2.", "При первом запуске лаунчер распаковывает ", "zapret_resources.zip", " в ", "%APPDATA%/ZapretLauncher/zapret_core/", ";"),
            ("3.", "Все файлы извлекаются в эту папку", ";"),
            ("4.", "Стратегии запускаются оттуда", ";"),
            ("5.", "Пользовательские списки (", "*-user.txt", ") сохраняются там же", "."),
        ])
        
        self.help_section(scrollable_frame, "В каких случаях можно удалить zapret_resources.zip:", [
            ("1.", "После успешной распаковки — если папка ", "zapret_core", " в appdata/local уже существует и полная", ";"),
            ("2.", "Если вы обновляете лаунчер — новый .exe уже содержит свежий архив", ";"),
            ("3.", "Если вы хотите сбросить Zapret — удали папку ", "zapret_core", ", и при следующем запуске архив распакуется заново", "."),
        ])
        
        self.help_section(scrollable_frame, "НЕ УДАЛЯЙТЕ, если:", [
            ("1.", "Папка ", "zapret_core", " отсутствует или повреждена", ";"),
            ("2.", "Вы хотите сохранить возможность переустановки без скачивания", ";"),
            ("3.", "Вы делитесь программой — архив (", "zapret_resources.zip", ") должен быть рядом с .exe", "."),
        ])
        
        self.help_section(scrollable_frame, "Антивирус и WinDivert:", [
            ("", "Некоторые антивирусы могут реагировать на программу из-за использования компонента ", "WinDivert", ". ", "Это НОРМАЛЬНО", "."),
            ("", "WinDivert", " — это легальный драйвер с открытым исходным кодом, используемый для фильтрации сетевых пакетов.", ""),
        ])
        
        self.help_section(scrollable_frame, "Если антивирус ругается:", [
            ("1.", "Добавьте папку с программой в ", "исключения", ";"),
            ("2.", "Или скомпилируйте программу сам из исходников или временно отключите антивирус при запуске", "."),
        ])
        
        self.help_section(scrollable_frame, "Возможные конфликты:", [
            ("", "Zapret", " и ", "ByeDPI", " работают на разных уровнях и ", "в большинстве случаев не конфликтуют", "."),
            ("", "", ""),
            ("", "Если после включения всего интернет работает нестабильно:", ""),
            ("  •", "Отключайте по одной галочке, чтобы найти виновника", ""),
            ("  •", "Для YouTube иногда помогает ", "отключение QUIC", " в браузере (chrome://flags/#enable-quic)", ""),
            ("  •", "Если пинг в играх вырос, отключите ", "TGProxy", " (он для игр не нужен)", ""),
            ("  •", "Разные стратегии Zapret могут вести себя по-разному с ByeDPI — экспериментируйте", ""),
        ])
        
        links_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_dark'])
        links_frame.pack(fill=tk.X, pady=(20, 10))
        
        tk.Label(links_frame, text="Полезные ссылки:", font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(0, 10))
        
        def on_enter(e):
            e.widget.config(fg=self.colors['accent_hover'])
        
        def on_leave(e):
            e.widget.config(fg=self.colors['accent'])
        
        link1 = tk.Label(links_frame, text="Оригинальный Zapret", font=("Segoe UI", 9),
                        fg=self.colors['accent'], bg=self.colors['bg_dark'], cursor="hand2")
        link1.pack(anchor='w', pady=2)
        link1.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/flowseal/zapret-discord-youtube"))
        link1.bind("<Enter>", on_enter)
        link1.bind("<Leave>", on_leave)
        
        link2 = tk.Label(links_frame, text="Оригинальный TG Proxy", font=("Segoe UI", 9),
                        fg=self.colors['accent'], bg=self.colors['bg_dark'], cursor="hand2")
        link2.pack(anchor='w', pady=2)
        link2.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Flowseal/tg-ws-proxy"))
        link2.bind("<Enter>", on_enter)
        link2.bind("<Leave>", on_leave)
        
        link3 = tk.Label(links_frame, text="Оригинальный ByeDPI", font=("Segoe UI", 9),
                        fg=self.colors['accent'], bg=self.colors['bg_dark'], cursor="hand2")
        link3.pack(anchor='w', pady=2)
        link3.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/hufrea/byedpi"))
        link3.bind("<Enter>", on_enter)
        link3.bind("<Leave>", on_leave)
        
        author_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_dark'])
        author_frame.pack(fill=tk.X, pady=(30, 30))
        
        tk.Label(author_frame, text="by trimansberg", font=("Segoe UI", 10, "italic"),
                fg=self.colors['text_secondary'], bg=self.colors['bg_dark']).pack()
    
    def help_section(self, parent, title, lines):
        tk.Label(parent, text=title, font=("Segoe UI", 14, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(15, 5))
        
        section_frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        section_frame.pack(fill=tk.X, pady=2)
        
        for line in lines:
            if len(line) == 2:
                tk.Label(section_frame, text=line[0] + " " + line[1], 
                        font=("Segoe UI", 9),
                        fg=self.colors['text_secondary'], 
                        bg=self.colors['bg_dark'], wraplength=850, justify=tk.LEFT).pack(anchor='w', pady=1)
            
            elif len(line) >= 3:
                frame = tk.Frame(section_frame, bg=self.colors['bg_dark'])
                frame.pack(anchor='w', pady=1, fill=tk.X)
                
                if line[0]:
                    tk.Label(frame, text=line[0], font=("Segoe UI", 9),
                            fg=self.colors['text_secondary'], bg=self.colors['bg_dark']).pack(side=tk.LEFT)
                
                for i in range(1, len(line)):
                    if i % 2 == 1:
                        tk.Label(frame, text=line[i], font=("Segoe UI", 9, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_dark']).pack(side=tk.LEFT)
                    else:
                        tk.Label(frame, text=line[i], font=("Segoe UI", 9),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_dark']).pack(side=tk.LEFT)
