import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import subprocess
import os
import json
import time
import threading
import atexit
import psutil
import asyncio
import zipfile
import shutil
import tempfile
from pathlib import Path
import sys
import re
import signal
import urllib.request
import urllib.error
import ctypes
from typing import Optional, List, Dict, Tuple

from tg_proxy import run_proxy, parse_dc_ip_list
from list_editor import ListEditor

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
ZAPRET_RESOURCES_ZIP = "zapret_resources.zip"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

LAUNCHER_API_URL = "https://api.github.com/repos/tweenkedrage/zapret-launcher/releases/latest"
ZAPRET_API_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"
CURRENT_VERSION = "2.1"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

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

def check_launcher_updates(parent, silent=False):
    try:
        with urllib.request.urlopen(LAUNCHER_API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get('tag_name', '').replace('v', '')
            
            if latest_version and latest_version > CURRENT_VERSION:
                result = messagebox.askyesno(
                    "Обновление лаунчера",
                    f"Доступна новая версия лаунчера {latest_version}\n"
                    f"Текущая версия: {CURRENT_VERSION}\n\n"
                    "Хотите перейти на страницу загрузки?"
                )
                if result:
                    import webbrowser
                    webbrowser.open(data.get('html_url', 'https://github.com/tweenkedrage/zapret-launcher/releases'))
                return True
            else:
                if not silent:
                    messagebox.showinfo("Обновления", "У вас установлена последняя версия лаунчера")
                return False
    except Exception as e:
        if not silent:
            messagebox.showerror("Ошибка", f"Не удалось проверить обновления лаунчера: {str(e)}")
        return False

def check_zapret_updates(parent, silent=False):
    try:
        with urllib.request.urlopen(ZAPRET_API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get('tag_name', '').replace('v', '')
            
            zapret_version_file = ZAPRET_CORE_DIR / "version.txt"
            current_zapret_version = "0.0"
            if zapret_version_file.exists():
                with open(zapret_version_file, 'r') as f:
                    current_zapret_version = f.read().strip()
            
            if latest_version and latest_version > current_zapret_version:
                result = messagebox.askyesno(
                    "Обновление Zapret",
                    f"Доступна новая версия Zapret {latest_version}\n"
                    f"Текущая версия: {current_zapret_version}\n\n"
                    "Хотите обновить? (Ваши пользовательские списки будут сохранены)"
                )
                if result:
                    update_zapret_core(parent, latest_version)
                return True
            else:
                if not silent:
                    messagebox.showinfo("Обновления", "У вас установлена последняя версия Zapret")
                return False
    except Exception as e:
        if not silent:
            messagebox.showerror("Ошибка", f"Не удалось проверить обновления Zapret: {str(e)}")
        return False

def update_zapret_core(parent, version):
    try:
        parent.update_status("Обновление Zapret...", parent.colors['accent'])
        parent.root.update()
        
        if parent.zapret.is_winws_running():
            parent.zapret.stop_current_strategy()
            time.sleep(1)

        user_lists = {}
        lists_dir = ZAPRET_CORE_DIR / "lists"
        if lists_dir.exists():
            for file in lists_dir.glob("*-user.txt"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        user_lists[file.name] = f.read()
                except:
                    pass
        
        download_url = f"https://github.com/flowseal/zapret-discord-youtube/archive/refs/heads/master.zip"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            urllib.request.urlretrieve(download_url, tmp_file.name)
            temp_zip = tmp_file.name
            time.sleep(2)

            try:
                subprocess.run('taskkill /F /IM winws.exe', shell=True, capture_output=True)
                subprocess.run('taskkill /F /IM ws2s.exe', shell=True, capture_output=True)
                subprocess.run('taskkill /F /IM nfqws.exe', shell=True, capture_output=True)
                subprocess.run('sc stop WinDivert*', shell=True, capture_output=True)
                time.sleep(1)
            except:
                pass

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    if ZAPRET_CORE_DIR.exists():
                        shutil.rmtree(ZAPRET_CORE_DIR)
                    break
                except Exception as delete_error:
                    print(f"Попытка {attempt + 1} не удалась: {delete_error}")
                    if attempt < max_attempts - 1:
                        try:
                            os.system(f'rmdir /s /q "{ZAPRET_CORE_DIR}"')
                            time.sleep(1)
                        except:
                            pass
                        continue
                    else:
                        raise Exception(f"Не удалось удалить папку после {max_attempts} попыток. Попробуйте перезагрузить компьютер.")
        
        ZAPRET_CORE_DIR.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(temp_zip, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            extracted_dirs = os.listdir(temp_dir)
            if extracted_dirs:
                source_dir = os.path.join(temp_dir, extracted_dirs[0])
                
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(ZAPRET_CORE_DIR, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
        
        os.unlink(temp_zip)
        
        with open(ZAPRET_CORE_DIR / "version.txt", 'w') as f:
            f.write(version)
        
        lists_dir = ZAPRET_CORE_DIR / "lists"
        lists_dir.mkdir(exist_ok=True)
        for filename, content in user_lists.items():
            try:
                file_path = lists_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except:
                pass
        
        parent.zapret.load_strategies()
        strategy_combo = parent.strategy_combo
        if hasattr(parent, 'strategy_combo'):
            parent.strategy_combo['values'] = parent.zapret.available_strategies
            if parent.zapret.available_strategies:
                parent.strategy_var.set(parent.zapret.available_strategies[0])
        
        parent.update_status("Готов к работе")
        messagebox.showinfo("Успех", f"Zapret успешно обновлен до версии {version}")
        
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось обновить Zapret: {str(e)}")
        parent.update_status("Готов к работе")

class TGProxyServer:
    def __init__(self):
        self._thread = None
        self._stop_event = None
        self._running = False
        self._port = 1080
        self._host = '127.0.0.1'
        
    def start(self):
        if self._running:
            return True
        try:
            self._stop_event = asyncio.Event()
            dc_opt = {2: '149.154.167.220', 4: '149.154.167.220', 1: '149.154.175.50', 3: '149.154.175.100', 5: '91.108.56.100'}
            def run_server():
                try:
                    asyncio.run(run_proxy(self._port, dc_opt, self._stop_event, self._host))
                except:
                    pass
            self._thread = threading.Thread(target=run_server, daemon=True)
            self._thread.start()
            self._running = True
            time.sleep(1)
            return True
        except:
            return False
        
    def stop(self):
        if not self._running:
            return
        if self._stop_event:
            self._stop_event.set()
        self._running = False

class ZapretCore:
    def __init__(self, parent):
        self.parent = parent
        self.zapret_dir = ZAPRET_CORE_DIR
        self.bin_dir = self.zapret_dir / "bin"
        self.lists_dir = self.zapret_dir / "lists"
        self.utils_dir = self.zapret_dir / "utils"
        
        self.current_process: Optional[subprocess.Popen] = None
        self.game_filter_enabled = False
        self.ipset_filter_mode = "none"
        self.available_strategies: List[str] = []
        
        self.ensure_resources()
        self.load_strategies()
        
    def ensure_resources(self):
        if self.zapret_dir.exists():
            return
            
        self.zapret_dir.mkdir(parents=True, exist_ok=True)
        
        possible_paths = [
            Path(__file__).parent / ZAPRET_RESOURCES_ZIP,
            Path(sys.executable).parent / ZAPRET_RESOURCES_ZIP if getattr(sys, 'frozen', False) else None,
        ]
        
        archive_path = None
        for p in possible_paths:
            if p and p.exists():
                archive_path = p
                break
                
        if not archive_path:
            messagebox.showerror(
                "Ошибка", 
                f"Не найден файл ресурсов {ZAPRET_RESOURCES_ZIP}.\n"
                "Запусти build_resources.py для его создания."
            )
            sys.exit(1)
            
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(self.zapret_dir)
            
            version_file = self.zapret_dir / "version.txt"
            if not version_file.exists():
                with open(version_file, 'w') as f:
                    f.write("1.9.7")
                    
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось распаковать ресурсы: {e}")
            sys.exit(1)
            
    def load_strategies(self):
        self.available_strategies = []
        for item in self.zapret_dir.glob("general*.bat"):
            self.available_strategies.append(item.name)
        self.available_strategies.sort()
        
    def get_strategy_display_name(self, filename: str) -> str:
        name = filename.replace(".bat", "").replace("general", "")
        if not name:
            return "GENERAL"
        return name.strip()
        
    def run_strategy(self, strategy_name: str) -> Tuple[bool, str]:
        if not is_admin():
            return False, "Запустите программу от имени администратора!"
            
        if not check_zapret_folder():
            return False, "Папка с Zapret не найдена!"
            
        strategy_path = self.zapret_dir / strategy_name
        if not strategy_path.exists():
            return False, f"Стратегия {strategy_name} не найдена"
            
        try:
            self.stop_current_strategy()
            
            self.current_process = subprocess.Popen(
                [str(strategy_path)],
                shell=True,
                cwd=str(self.zapret_dir),
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(1.5)
            if self.is_winws_running():
                return True, f"Запущена стратегия: {self.get_strategy_display_name(strategy_name)}"
            else:
                return False, "Стратегия запущена, но winws.exe не обнаружен"
                
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"
            
    def stop_current_strategy(self):
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            except:
                try:
                    self.current_process.kill()
                except:
                    pass
            self.current_process = None
            
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    proc.kill()
            except:
                pass
                
    def is_winws_running(self) -> bool:
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    return True
            except:
                pass
        return False
        
    def run_service_command(self, command: str) -> Tuple[bool, str]:
        if command == "game_filter":
            self.game_filter_enabled = not self.game_filter_enabled
            return True, f"Game Filter: {'включен' if self.game_filter_enabled else 'выключен'}"
            
        elif command == "ipset_filter":
            modes = ["none", "loaded", "any"]
            current_idx = modes.index(self.ipset_filter_mode)
            self.ipset_filter_mode = modes[(current_idx + 1) % 3]
            return True, f"IPSet Filter: {self.ipset_filter_mode}"
            
        elif command == "update_ipset":
            return self.download_ipset_list()
            
        return False, f"Неизвестная команда: {command}"
        
    def download_ipset_list(self) -> Tuple[bool, str]:
        try:
            url = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/master/lists/ipset-all.txt"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode('utf-8')
            
            ipset_path = self.lists_dir / "ipset-all.txt"
            with open(ipset_path, 'w', encoding='utf-8') as f:
                f.write(data)
                
            return True, "IPSet список обновлен"
        except urllib.error.URLError as e:
            return False, f"Ошибка загрузки: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

class ModernSwitch(tk.Canvas):
    def __init__(self, parent, width=50, height=24, bg_color='#25252B', 
                 active_color='#4361ee', command=None, initial=False):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent['bg'])
        self.active_color = active_color
        self.inactive_color = bg_color
        self.state = initial
        self.command = command
        self.width = width
        self.height = height
        
        self.bg_rect = self.create_oval(2, 2, width-2, height-2, fill=self.inactive_color, outline='#2D2D35', width=1)
        self.slider = self.create_oval(4, 4, height-4, height-4, fill='#ffffff', outline='', tags=('slider',))
        
        if self.state:
            self.coords(self.slider, width-height+4, 4, width-4, height-4)
            self.itemconfig(self.bg_rect, fill=self.active_color)
        
        self.tag_bind(self.bg_rect, "<Button-1>", self.on_click)
        self.tag_bind("slider", "<Button-1>", self.on_click)

    def on_click(self, event):
        self.state = not self.state
        if self.state:
            self.coords(self.slider, self.width-self.height+4, 4, self.width-4, self.height-4)
            self.itemconfig(self.bg_rect, fill=self.active_color)
        else:
            self.coords(self.slider, 4, 4, self.height-4, self.height-4)
            self.itemconfig(self.bg_rect, fill=self.inactive_color)
        if self.command:
            self.command(self.state)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=200, height=40, 
                 bg='#4361ee', fg='white', font=("Segoe UI", 11, "bold"), corner_radius=8):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent['bg'], cursor="hand2")
        self.command = command
        self.bg = bg
        self.fg = fg
        self.font = font
        self.enabled = True
        self.normal_color = bg
        self.hover_color = '#5a7aff'
        self.corner_radius = corner_radius
        
        points = []
        points.extend([corner_radius, 0, width-corner_radius, 0])
        points.extend([width, 0, width, corner_radius, width, height-corner_radius, width, height])
        points.extend([width-corner_radius, height, corner_radius, height])
        points.extend([0, height, 0, height-corner_radius, 0, corner_radius, 0, 0])
        self.rect = self.create_polygon(points, smooth=True, fill=bg, outline='')
        self.text_id = self.create_text(width//2, height//2, text=text, fill=fg, font=font)
        
        for item in [self.rect, self.text_id]:
            self.tag_bind(item, "<Button-1>", self.on_click)
            self.tag_bind(item, "<Enter>", self.on_enter)
            self.tag_bind(item, "<Leave>", self.on_leave)

    def on_click(self, event):
        if self.enabled and self.command:
            self.command()

    def on_enter(self, event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.hover_color)

    def on_leave(self, event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.normal_color)

    def set_text(self, text):
        self.itemconfig(self.text_id, text=text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        color = self.normal_color if enabled else '#666666'
        self.itemconfig(self.rect, fill=color)

class ZapretLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Zapret Launcher")
        self.window_width = 1200
        self.window_height = 800
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        
        self.colors = {
            'bg_dark': '#0F0F12', 
            'bg_medium': '#1A1A1F', 
            'bg_light': '#25252B',
            'accent': '#4361ee', 
            'accent_hover': '#5a7aff', 
            'accent_green': '#10b981',
            'accent_red': '#ef4444', 
            'text_primary': '#FFFFFF', 
            'text_secondary': '#9CA3AF',
            'border': '#2D2D35', 
            'button_bg': '#33333D',
            'separator': '#2D2D35',
        }
        self.root.configure(bg=self.colors['bg_dark'])
        
        self.font_primary = ("Segoe UI", 10)
        self.font_medium = ("Segoe UI", 12)
        self.font_title = ("Segoe UI", 28, "bold")
        self.font_bold = ("Segoe UI", 12, "bold")
        
        if not is_admin():
            result = messagebox.askyesno(
                "Права администратора",
                "Программа требует прав администратора для работы.\n\n"
                "Запустить от имени администратора?"
            )
            if result:
                run_as_admin()
            else:
                messagebox.showerror(
                    "Ошибка", 
                    "Программа не может работать без прав администратора."
                )
                sys.exit(1)
        
        self.zapret = ZapretCore(self)
        self.tg_proxy = TGProxyServer()
        
        self.is_connected = False
        self.current_strategy = None
        self.tg_proxy_enabled = False
        self.current_page = "main"
        
        self.ensure_appdata_dir()
        self.load_settings()
        
        self.setup_ui()
        self.root.after(100, self.check_initial_status)
        self.root.after(1000, lambda: check_launcher_updates(self, silent=True))
        self.root.after(2000, lambda: check_zapret_updates(self, silent=True))
        self.center_window()
        self.show_main_page()

    def center_window(self):
        x = (self.root.winfo_screenwidth() // 2) - (self.window_width // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.window_height // 2)
        self.root.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')

    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_left_panel()
        
        self.content_panel = tk.Frame(self.main_container, bg=self.colors['bg_dark'])
        self.content_panel.place(x=250, y=0, width=950, height=800)
        
        self.create_main_page()
        self.create_service_page()
        self.create_lists_page()

    def create_left_panel(self):
        left_panel = tk.Frame(self.main_container, bg=self.colors['bg_medium'], width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        logo_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'], height=120)
        logo_frame.pack(fill=tk.X, pady=(40, 30))
        logo_frame.pack_propagate(False)
        
        tk.Label(logo_frame, text="ZAPRET", font=("Segoe UI", 28, "bold"), 
                fg=self.colors['accent'], bg=self.colors['bg_medium']).pack(expand=True)
        tk.Label(logo_frame, text="LAUNCHER", font=("Segoe UI", 11), 
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack()
        
        nav_buttons = [
            ("Главная", self.show_main_page),
            ("Сервис", self.show_service_page),
            ("Редактор", self.show_lists_page),
        ]
        
        for text, command in nav_buttons:
            btn_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'])
            btn_frame.pack(fill=tk.X, pady=2, padx=15)
            
            btn = RoundedButton(btn_frame, text=text, command=command,
                width=220, height=45, bg=self.colors['bg_light'], 
                fg=self.colors['text_secondary'], font=("Segoe UI", 11), corner_radius=10)
            btn.pack()
        
        separator = tk.Frame(left_panel, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=20)
        
        credit_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'])
        credit_frame.pack(side=tk.BOTTOM, pady=(0, 30), fill=tk.X)
        
        self.left_status = tk.Label(credit_frame, text="●", font=("Segoe UI", 12), 
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        self.left_status.pack()
        
        tk.Label(credit_frame, text=f"v{CURRENT_VERSION}", font=("Segoe UI", 9), 
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(pady=(5, 0))
        
        self.credit_label = tk.Label(credit_frame, text="by trimansberg", font=("Segoe UI", 8), 
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                                    cursor="hand2")
        self.credit_label.pack(pady=(2, 0))

        self.credit_label.bind("<Enter>", lambda e: self.credit_label.config(fg=self.colors['accent']))
        self.credit_label.bind("<Leave>", lambda e: self.credit_label.config(fg=self.colors['text_secondary']))
        self.credit_label.bind("<Button-1>", lambda e: self.open_github())

    def create_main_page(self):
        self.main_page = tk.Frame(self.content_panel, bg=self.colors['bg_dark'])
        self.main_page.place(x=0, y=0, width=950, height=800)
        
        tk.Label(self.main_page, text="Главная", font=("Segoe UI", 32, "bold"), 
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(30, 20), padx=30)
        
        status_frame = tk.Frame(self.main_page, bg=self.colors['bg_light'])
        status_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        tk.Label(status_frame, text="Статус:", font=self.font_bold, 
                fg=self.colors['text_primary'], bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.main_status = tk.Label(status_frame, text="Готов к работе", font=self.font_medium,
                                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.main_status.pack(side=tk.LEFT, padx=15, pady=10)
        
        quick_frame = tk.Frame(self.main_page, bg=self.colors['bg_medium'])
        quick_frame.pack(fill=tk.X, padx=30, pady=20, ipadx=20, ipady=20)
        
        tk.Label(quick_frame, text="Быстрый запуск", font=("Segoe UI", 16, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(10, 15))
        
        strategy_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        strategy_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(strategy_frame, text="Стратегия:", font=self.font_medium,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(strategy_frame, textvariable=self.strategy_var,
                                      values=self.zapret.available_strategies,
                                      width=40, font=self.font_primary)
        self.strategy_combo.pack(side=tk.LEFT, padx=10)
        self.strategy_combo.bind("<Enter>", lambda e: self.strategy_combo.config(cursor="hand2"))
        self.strategy_combo.bind("<Leave>", lambda e: self.strategy_combo.config(cursor=""))
        if self.zapret.available_strategies:
            self.strategy_var.set(self.zapret.available_strategies[0])
        
        tgws_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        tgws_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(tgws_frame, text="TGProxy:", font=self.font_medium,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.tgws_var = tk.BooleanVar(value=False)
        tgws_check = tk.Checkbutton(tgws_frame, variable=self.tgws_var,
                                   bg=self.colors['bg_medium'], activebackground=self.colors['bg_medium'],
                                   cursor="hand2")
        tgws_check.pack(side=tk.LEFT)
        
        tk.Label(tgws_frame, text="Запустить вместе с Zapret", font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=5)
        
        button_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        button_frame.pack(fill=tk.X, padx=15, pady=(20, 10))
        
        self.connect_btn = RoundedButton(button_frame, text="ПОДКЛЮЧИТЬСЯ", command=self.toggle_connection,
                                       width=300, height=55, bg=self.colors['accent'], 
                                       font=("Segoe UI", 16, "bold"), corner_radius=12)
        self.connect_btn.pack()

    def create_service_page(self):
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
                                       command=lambda: check_launcher_updates(self, silent=False),
                                       width=220, height=35, bg=self.colors['button_bg'],
                                       font=self.font_primary, corner_radius=8)
                elif cmd == "check_zapret":
                    btn = RoundedButton(card, text=btn_text, 
                                       command=lambda: check_zapret_updates(self, silent=False),
                                       width=220, height=35, bg=self.colors['button_bg'],
                                       font=self.font_primary, corner_radius=8)
                else:
                    btn = RoundedButton(card, text=btn_text, 
                                       command=lambda c=cmd: self.run_service_command(c),
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
        lists_path = os.path.join(self.zapret.zapret_dir, "lists")
        file_path = os.path.join(lists_path, filename)
        ListEditor(self.root, file_path, filename)

    def open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher")

    def check_initial_status(self):
        if not check_zapret_folder():
            return
        if self.zapret.is_winws_running():
            self.is_connected = True
            self.update_status("Подключено", self.colors['accent_green'])
            self.update_ui_state()

    def update_status(self, text, color=None):
        if color is None:
            color = self.colors['accent_green'] if self.is_connected else self.colors['text_secondary']
        
        self.main_status.config(text=text, fg=color)
        self.left_status.config(fg=color)

    def update_ui_state(self):
        if self.is_connected:
            self.connect_btn.set_text("ОТКЛЮЧИТЬСЯ")
            self.connect_btn.normal_color = self.colors['bg_light']
            self.connect_btn.itemconfig(self.connect_btn.rect, fill=self.colors['bg_light'])
        else:
            self.connect_btn.set_text("ПОДКЛЮЧИТЬСЯ")
            self.connect_btn.normal_color = self.colors['accent']
            self.connect_btn.itemconfig(self.connect_btn.rect, fill=self.colors['accent'])

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        strategy = self.strategy_var.get()
        if not strategy:
            messagebox.showerror("Ошибка", "Выберите стратегию")
            return
        
        self.update_status("Запуск...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        success, msg = self.zapret.run_strategy(strategy)
        
        if success:
            self.current_strategy = strategy
            self.is_connected = True
            self.update_status(f"Подключено: {self.zapret.get_strategy_display_name(strategy)}", 
                              self.colors['accent_green'])
            self.update_ui_state()
            
            if self.tgws_var.get():
                self.tg_proxy.start()
        else:
            self.update_status("Ошибка запуска", self.colors['accent_red'])
            messagebox.showerror("Ошибка", msg)
        
        self.connect_btn.set_enabled(True)

    def disconnect(self):
        if not self.is_connected and not self.zapret.is_winws_running():
            return
            
        self.update_status("Отключение...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        def stop_all():
            self.zapret.stop_current_strategy()
            self.tg_proxy.stop()
            time.sleep(1)
            self.root.after(0, self.finish_disconnect)
        
        threading.Thread(target=stop_all, daemon=True).start()

    def finish_disconnect(self):
        self.is_connected = False
        self.current_strategy = None
        self.update_status("Готов к работе", self.colors['text_secondary'])
        self.update_ui_state()
        self.connect_btn.set_enabled(True)

    def run_service_command(self, command):
        if not check_zapret_folder():
            return
        success, result = self.zapret.run_service_command(command)
        if success:
            messagebox.showinfo("Успех", result)
        else:
            messagebox.showerror("Ошибка", result)

    def ensure_appdata_dir(self):
        try:
            APPDATA_DIR.mkdir(parents=True, exist_ok=True)
        except:
            pass

    def load_settings(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tg_proxy_enabled = data.get('tg_proxy_enabled', False)
        except:
            pass

    def show_page(self, page_name):
        if page_name == self.current_page:
            return
        
        pages = {
            "main": self.main_page,
            "service": self.service_page,
            "lists": self.lists_page,
        }
        
        if hasattr(self, f"{self.current_page}_page"):
            getattr(self, f"{self.current_page}_page").place_forget()
        
        pages[page_name].place(x=0, y=0, width=950, height=800)
        pages[page_name].tkraise()
        self.current_page = page_name

    def show_main_page(self):
        self.show_page("main")
        
    def show_service_page(self):
        self.show_page("service")
        
    def show_lists_page(self):
        self.show_page("lists")

if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretLauncher(root)
    root.mainloop()
