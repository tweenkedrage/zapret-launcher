import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from byedpi_optimizer import ByeDPIOptimizer
import subprocess
import os
import json
import time
import threading
import atexit
import psutil
import winreg
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
import pystray
from PIL import Image, ImageDraw
from typing import Optional, List, Dict, Tuple
import webbrowser

from tg_proxy import run_proxy, parse_dc_ip_list
from list_editor import ListEditor

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
ZAPRET_RESOURCES_ZIP = "zapret_resources.zip"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

LAUNCHER_API_URL = "https://api.github.com/repos/tweenkedrage/zapret-launcher/releases/latest"
ZAPRET_API_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"
CURRENT_VERSION = "2.2c"

PROVIDER_PARAMS = {
    "Ростелеком/Дом.ru/Tele2/SamaraLan": ["--split", "1", "--disorder", "-1"],
    "МГТС (МТС)/Yota": ["-7", "-e1", "-q"],
    "Мегафон": ["-s0", "-o1", "-d1", "-r1+s", "-Ar", "-o1", "-At", "-f-1", "-r1+s", "-As"],
    "Билайн": ["--split", "1", "--disorder", "1", "--fake", "-1", "--ttl", "8"],
    "ТТК": ["-1", "-e1"],
}

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
            download_url = None
            
            for asset in data.get('assets', []):
                if asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    break
            
            if latest_version and latest_version > CURRENT_VERSION:
                if silent:
                    result = messagebox.askyesno(
                        "Обновление лаунчера",
                        f"Доступна новая версия {latest_version}\n"
                        f"Текущая версия: {CURRENT_VERSION}\n\n"
                        "Обновить сейчас? (Ваши настройки и списки будут сохранены)"
                    )
                else:
                    result = messagebox.askyesno(
                        "Обновление лаунчера",
                        f"Доступна новая версия лаунчера {latest_version}\n"
                        f"Текущая версия: {CURRENT_VERSION}\n\n"
                        "Хотите обновить? (Ваши настройки и списки будут сохранены)"
                    )
                
                if result and download_url:
                    parent.update_status("Обновление лаунчера...", parent.colors['accent'])
                    parent.root.update()
                    
                    threading.Thread(target=lambda: update_launcher(parent, download_url, latest_version), daemon=True).start()
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
    
def update_launcher(parent, download_url, new_version):
    try:
        parent.log_to_diagnostic(f"Скачивание обновления v{new_version}...")
        
        temp_dir = tempfile.gettempdir()
        new_exe_path = os.path.join(temp_dir, f"Zapret_Launcher_v{new_version}.exe")
        updater_script = os.path.join(temp_dir, "update_launcher.bat")
        
        urllib.request.urlretrieve(download_url, new_exe_path)
        
        parent.log_to_diagnostic(f"Файл загружен: {new_exe_path}")
        
        current_exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        
        with open(updater_script, 'w', encoding='utf-8') as f:
            f.write(f'''@echo off
timeout /t 2 /nobreak > nul
echo Обновление Zapret Launcher...
echo.
echo Закрываю старую версию...
taskkill /F /IM "{os.path.basename(current_exe)}" 2>nul
timeout /t 1 /nobreak > nul
echo.
echo Копирую новую версию...
copy /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo Ошибка копирования. Возможно, файл используется.
    pause
    exit /b 1
)
echo.
echo Запускаю новую версию...
start "" "{current_exe}"
echo.
echo Обновление завершено!
timeout /t 2 /nobreak > nul
del "%~f0"
''')
        
        parent.log_to_diagnostic(f"Создан скрипт обновления: {updater_script}")
        
        parent.log_to_diagnostic("Запуск обновления...")
        subprocess.Popen(['cmd', '/c', updater_script], shell=True)
        
        parent.root.after(500, parent.root.quit)
        
    except Exception as e:
        parent.log_to_diagnostic(f"Ошибка обновления: {str(e)}")
        messagebox.showerror("Ошибка", f"Не удалось обновить лаунчер: {str(e)}")

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
            
        return False, f"Неизвестная команда: {command}"

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

class SystemTrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.create_icon()

    def create_icon(self):
        try:
            image = Image.open("icon.ico")
            
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            image = image.resize((64, 64), Image.Resampling.LANCZOS)
            
        except Exception as e:
            print(f"Не удалось загрузить иконку для трея: {e}")
            image = Image.new('RGBA', (64, 64), '#4361ee')
            draw = ImageDraw.Draw(image)
            draw.rectangle([0, 0, 64, 64], fill='#4361ee', outline='#5a7aff', width=2)
            draw.text((20, 20), "Z", fill='white', font=None)
        
        self.update_menu(image)
        
    def update_menu(self, image=None):
        if self.app.is_connected:
            connection_text = "Отключиться"
        else:
            connection_text = "Подключиться"
        
        menu = pystray.Menu(
            pystray.MenuItem("Открыть лаунчер", self.show_window),
            pystray.MenuItem(connection_text, self.toggle_connection),
            pystray.MenuItem("Выход", self.quit_app)
        )
        
        if self.icon:
            self.icon.menu = menu
            if image:
                self.icon.icon = image
        else:
            if image is None:
                image = Image.new('RGBA', (64, 64), '#4361ee')
                draw = ImageDraw.Draw(image)
                draw.rectangle([0, 0, 64, 64], fill='#4361ee', outline='#5a7aff', width=2)
                draw.text((20, 20), "Z", fill='white', font=None)
            
            self.icon = pystray.Icon("zapret_launcher", image, "Zapret Launcher", menu)
        
    def show_window(self):
        self.app.root.deiconify()
        self.app.root.lift()
        self.app.root.focus_force()

    def toggle_connection(self):
        self.app.toggle_connection()
        self.update_menu()

    def quit_app(self):
        self.icon.stop()
        self.app.on_closing()

    def run(self):
        self.icon.run()

class ByeDPIWithProvider:
    def __init__(self, app_data_dir):
        self.base = ByeDPIOptimizer(app_data_dir)
        self.current_provider = "Ростелеком"
    
    def set_provider(self, provider):
        self.current_provider = provider
        params = PROVIDER_PARAMS.get(provider, PROVIDER_PARAMS["Ростелеком"])
        self.base.rostel_params = params + ["-i", "127.0.0.1", "-p", "10801"]
    
    def start(self):
        return self.base.start()
    
    def stop(self):
        return self.base.stop()
    
    def get_status(self):
        return self.base.get_status()

class ZapretLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Zapret Launcher")
        self.byedpi = ByeDPIWithProvider(APPDATA_DIR)
        self.byedpi_enabled = False
        
        try:
            self.root.iconbitmap(default='icon.ico')
        except Exception as e:
            pass
        try:
            icon = tk.PhotoImage(file='icon.ico')
            self.root.iconphoto(True, icon)
        except Exception as e2:
            pass
        
        self.window_width = 1200
        self.window_height = 800
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
            
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
        self.current_provider = "Ростелеком"
        
        self.ensure_appdata_dir()
        self.load_settings()
        
        self.setup_ui()
        self.root.after(100, self.check_initial_status)
        self.root.after(1000, lambda: check_launcher_updates(self, silent=True))
        self.root.after(2000, lambda: check_zapret_updates(self, silent=True))
        self.center_window()
        self.show_main_page()
        
        self.tray_icon = SystemTrayIcon(self)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.root.withdraw()

    def on_closing(self):
        try:
            self.zapret.stop_current_strategy()
            self.tg_proxy.stop()
            if self.byedpi_enabled:
                self.byedpi.stop()
        except:
            pass
        self.root.destroy()
        os._exit(0)

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
        self.create_diagnostic_page()
        self.create_help_page()

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
            ("Диагностика", self.show_diagnostic_page),
            ("Помощь", self.show_help_page),
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
        strategy_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(strategy_frame, text="Стратегия:", font=self.font_medium,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(strategy_frame, textvariable=self.strategy_var,
                                      values=self.zapret.available_strategies,
                                      width=40, font=self.font_primary)
        self.strategy_combo.pack(side=tk.LEFT, padx=10)
        self.strategy_combo.bind("<Enter>", lambda e: self.strategy_combo.config(cursor="hand2"))
        self.strategy_combo.bind("<Leave>", lambda e: self.strategy_combo.config(cursor=""))
        
        tgws_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        tgws_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(tgws_frame, text="TGProxy:", font=self.font_medium,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.tgws_var = tk.BooleanVar(value=False)
        tgws_check = tk.Checkbutton(tgws_frame, variable=self.tgws_var,
                                   bg=self.colors['bg_medium'], activebackground=self.colors['bg_medium'],
                                   cursor="hand2")
        tgws_check.pack(side=tk.LEFT)
        
        tk.Label(tgws_frame, text="Запустить вместе с Zapret", font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=5)
        
        byedpi_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        byedpi_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(byedpi_frame, text="ByeDPI Оптимизатор:", 
                 font=self.font_medium, fg=self.colors['text_secondary'], 
                 bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.byedpi_var = tk.BooleanVar(value=self.byedpi_enabled)
        byedpi_check = tk.Checkbutton(byedpi_frame, variable=self.byedpi_var,
                                      bg=self.colors['bg_medium'], 
                                      activebackground=self.colors['bg_medium'],
                                      cursor="hand2",
                                      command=self.on_byedpi_change)
        byedpi_check.pack(side=tk.LEFT)
        
        self.byedpi_status = tk.Label(byedpi_frame, text="", 
                                      font=self.font_primary, 
                                      fg=self.colors['text_secondary'], 
                                      bg=self.colors['bg_medium'])
        self.byedpi_status.pack(side=tk.LEFT, padx=5)
        
        provider_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        provider_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(provider_frame, text="Провайдер:", font=self.font_medium,
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.provider_var = tk.StringVar(value=self.current_provider)
        self.provider_combo = ttk.Combobox(provider_frame, textvariable=self.provider_var,
                                           values=list(PROVIDER_PARAMS.keys()),
                                           width=30, font=self.font_primary)
        self.provider_combo.pack(side=tk.LEFT, padx=10)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)
        
        button_frame = tk.Frame(quick_frame, bg=self.colors['bg_medium'])
        button_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        self.connect_btn = RoundedButton(button_frame, text="ПОДКЛЮЧИТЬСЯ", command=self.toggle_connection,
                                       width=300, height=55, bg=self.colors['accent'], 
                                       font=("Segoe UI", 16, "bold"), corner_radius=12)
        self.connect_btn.pack()
        
        if self.current_strategy and self.current_strategy in self.zapret.available_strategies:
            self.strategy_var.set(self.current_strategy)
        
        self.update_byedpi_status()

    def on_provider_change(self, event):
        self.current_provider = self.provider_var.get()
        self.byedpi.set_provider(self.current_provider)
        self.save_settings()
        
        if self.byedpi_enabled:
            self.byedpi.stop()
            time.sleep(0.5)
            success, msg = self.byedpi.start()
            if not success:
                messagebox.showerror("Ошибка ByeDPI", msg)
                self.byedpi_var.set(False)
                self.byedpi_enabled = False
            self.update_byedpi_status()

    def check_file_integrity(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("ПРОВЕРКА ЦЕЛОСТНОСТИ ФАЙЛОВ")
        self.log_to_diagnostic("="*50)
        
        errors = []
        
        required_files = [
            ("zapret_resources.zip", Path(__file__).parent / "zapret_resources.zip"),
            ("bin/ciadpi.exe", Path(__file__).parent / "bin" / "ciadpi.exe"),
        ]
        
        for name, path in required_files:
            if path.exists():
                size = path.stat().st_size
                if size > 0:
                    self.log_to_diagnostic(f"  {name} - {size} байт")
                else:
                    self.log_to_diagnostic(f"  {name} - файл пустой (0 байт)")
                    errors.append(f"{name} пустой")
            else:
                self.log_to_diagnostic(f"  {name} - отсутствует")
                errors.append(f"{name} отсутствует")
        
        if ZAPRET_CORE_DIR.exists():
            zapret_files = [
                "winws.exe",
                "general.bat",
                "WinDivert.dll",
                "WinDivert64.sys"
            ]
            
            bin_dir = ZAPRET_CORE_DIR / "bin"
            for file in zapret_files:
                file_path = bin_dir / file
                if file_path.exists():
                    size = file_path.stat().st_size
                    self.log_to_diagnostic(f"  bin/{file} - {size} байт")
                else:
                    self.log_to_diagnostic(f"  bin/{file} - отсутствует")
                    errors.append(f"bin/{file} отсутствует")
            
            strategies = list(ZAPRET_CORE_DIR.glob("general*.bat"))
            self.log_to_diagnostic(f"  Стратегии: {len(strategies)} файлов")
        else:
            self.log_to_diagnostic(f"  Папка zapret_core отсутствует")
            errors.append("zapret_core отсутствует")
        
        self.log_to_diagnostic("")
        if errors:
            self.log_to_diagnostic(f"Найдено проблем: {len(errors)}")
            for err in errors:
                self.log_to_diagnostic(f"  - {err}")
        else:
            self.log_to_diagnostic("Все файлы в порядке")
        
        self.log_to_diagnostic("="*50)
    
    def check_custom_site(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Проверка сайта")
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Введите URL сайта:", font=("Segoe UI", 11),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 5))
        
        url_entry = tk.Entry(dialog, width=50, font=("Segoe UI", 10),
                            bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                            insertbackground=self.colors['text_primary'])
        url_entry.pack(pady=5, padx=20, fill=tk.X)
        url_entry.insert(0, "youtube.com")
        
        result_label = tk.Label(dialog, text="", font=("Segoe UI", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        result_label.pack(pady=5)
        
        def check():
            url = url_entry.get().strip()
            if not url:
                result_label.config(text="Введите URL", fg=self.colors['accent_red'])
                return
            
            result_label.config(text="Проверка...", fg=self.colors['accent'])
            dialog.update()
            
            def check_thread():
                try:
                    import socket
                    
                    clean_url = url.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                    
                    try:
                        ip = socket.gethostbyname(clean_url)
                        dns_ok = True
                    except:
                        ip = "не определяется"
                        dns_ok = False
                    
                    if dns_ok:
                        result = subprocess.run(['ping', '-n', '2', clean_url], 
                                            capture_output=True, timeout=5)
                        if result.returncode == 0:
                            for line in result.stdout.decode('cp866', errors='ignore').split('\n'):
                                if "среднее" in line or "Average" in line:
                                    result_text = f"ДОСТУПЕН - {line.strip()}"
                                    break
                            else:
                                result_text = f"ДОСТУПЕН (IP: {ip})"
                            color = self.colors['accent_green']
                        else:
                            result_text = f"НЕ ДОСТУПЕН (IP: {ip})"
                            color = self.colors['accent_red']
                    else:
                        result_text = f"DNS ОШИБКА - сайт не найден"
                        color = self.colors['accent_red']
                        
                except subprocess.TimeoutExpired:
                    result_text = "ТАЙМАУТ - сайт не отвечает"
                    color = self.colors['accent_red']
                except Exception as e:
                    result_text = f"ОШИБКА: {str(e)}"
                    color = self.colors['accent_red']
                
                dialog.after(0, lambda: result_label.config(text=result_text, fg=color))
                dialog.after(0, lambda: check_btn.config(state="normal"))
            
            check_btn.config(state="disabled")
            threading.Thread(target=check_thread, daemon=True).start()
        
        button_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        button_frame.pack(pady=15)
        
        check_btn = RoundedButton(button_frame, text="Проверить", command=check,
                                width=120, height=32, bg=self.colors['accent'],
                                font=("Segoe UI", 10))
        check_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = RoundedButton(button_frame, text="Закрыть", command=dialog.destroy,
                                width=80, height=32, bg=self.colors['button_bg'],
                                font=("Segoe UI", 10))
        close_btn.pack(side=tk.LEFT, padx=5)
        
        url_entry.bind("<Return>", lambda e: check())

    def set_autostart(self, enabled):
        try:
            import winreg
            
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, "ZapretLauncher", 0, winreg.REG_SZ, exe_path)
                    self.log_to_diagnostic("Автозапуск включен")
                else:
                    try:
                        winreg.DeleteValue(key, "ZapretLauncher")
                        self.log_to_diagnostic("Автозапуск отключен")
                    except:
                        pass
            return True
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка настройки автозапуска: {e}")
            return False

    def check_autostart_status(self):
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, "ZapretLauncher")
                return value is not None
        except:
            return False

    def on_byedpi_change(self):
        self.byedpi_enabled = self.byedpi_var.get()
        
        if self.byedpi_enabled:
            self.byedpi.set_provider(self.current_provider)
            success, msg = self.byedpi.start()
            if not success:
                messagebox.showerror("Ошибка ByeDPI", msg)
                self.byedpi_var.set(False)
                self.byedpi_enabled = False
        else:
            self.byedpi.stop()
        
        self.update_byedpi_status()
        self.save_settings()

    def update_byedpi_status(self):
        status = self.byedpi.get_status()
        if status['running']:
            self.byedpi_status.config(text=f"v{status['version']} ({self.current_provider})", fg=self.colors['accent_green'])
        else:
            if status['binary_exists']:
                self.byedpi_status.config(text=f"v{status['version']}", fg=self.colors['text_secondary'])
            else:
                self.byedpi_status.config(text="не установлен", fg=self.colors['accent_red'])

    def safe_command(self, command):
        try:
            command()
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def log_to_diagnostic(self, message):
        self.diagnostic_text.insert(tk.END, message + "\n")
        self.diagnostic_text.see(tk.END)
        self.diagnostic_text.update()

    def check_ping_google(self):
        self.log_to_diagnostic("Проверка пинга до Google (8.8.8.8)...")
        try:
            result = subprocess.run(['ping', '-n', '4', '8.8.8.8'], 
                                capture_output=True, text=True, encoding='cp866')
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "среднее" in line or "Average" in line:
                        self.log_to_diagnostic(f"{line.strip()}")
                        return
                self.log_to_diagnostic("Пинг до Google успешен")
            else:
                self.log_to_diagnostic("Нет соединения с Google")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def check_ping_youtube(self):
        self.log_to_diagnostic("Проверка пинга до YouTube...")
        try:
            result = subprocess.run(['ping', '-n', '4', 'youtube.com'], 
                                capture_output=True, text=True, encoding='cp866')
            if result.returncode == 0:
                self.log_to_diagnostic("YouTube доступен")
            else:
                self.log_to_diagnostic("YouTube не отвечает (возможно заблокирован)")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def check_ping_discord(self):
        self.log_to_diagnostic("Проверка пинга до Discord...")
        try:
            result = subprocess.run(['ping', '-n', '4', 'discord.com'], 
                                capture_output=True, text=True, encoding='cp866')
            if result.returncode == 0:
                self.log_to_diagnostic("Discord доступен")
            else:
                self.log_to_diagnostic("Discord не отвечает (возможно заблокирован)")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def run_speedtest(self):
        self.log_to_diagnostic("="*40)
        self.log_to_diagnostic("ЗАПУСК ТЕСТА СКОРОСТИ")
        self.log_to_diagnostic("="*40)
        self.log_to_diagnostic("Тестирование загрузки...")
        
        try:
            import urllib.request
            import time
            
            test_url = "http://speedtest.tele2.net/100MB.zip"
            start_time = time.time()
            
            urllib.request.urlretrieve(test_url, "speedtest_temp.bin")
            
            end_time = time.time()
            download_time = end_time - start_time
            file_size_mb = 100
            speed_mbps = (file_size_mb * 8) / download_time
            
            os.remove("speedtest_temp.bin")
            
            self.log_to_diagnostic(f"Скорость загрузки: {speed_mbps:.2f} Мбит/с")
            self.log_to_diagnostic(f"Время загрузки: {download_time:.2f} сек")
            self.log_to_diagnostic("="*40)
            
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка теста: {str(e)}")
            self.log_to_diagnostic("Попробуйте использовать speedtest.net в браузере")

    def auto_select_strategy(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("АВТОМАТИЧЕСКИЙ ПОДБОР СТРАТЕГИИ")
        self.log_to_diagnostic("="*50)
        
        strategies = self.zapret.available_strategies
        if not strategies:
            self.log_to_diagnostic("Нет доступных стратегий")
            return None
        
        test_sites = [
            ("youtube.com", "YouTube"),
            ("google.com", "Google"),
            ("discord.com", "Discord"),
        ]
        
        was_connected = self.is_connected
        
        best_strategy = None
        best_score = -1
        best_success_count = 0
        
        for strategy in strategies:
            self.log_to_diagnostic(f"\nТестируем: {strategy}")
            
            if was_connected:
                self.disconnect()
                time.sleep(1)
            
            success, msg = self.zapret.run_strategy(strategy)
            
            if not success:
                self.log_to_diagnostic(f"  Не удалось запустить: {msg}")
                continue
            
            self.log_to_diagnostic(f"  Запущена")
            time.sleep(2)
            
            success_count = 0
            for site, name in test_sites:
                try:
                    result = subprocess.run(['ping', '-n', '2', site], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        self.log_to_diagnostic(f"    {name} доступен")
                        success_count += 1
                    else:
                        self.log_to_diagnostic(f"    {name} недоступен")
                except:
                    self.log_to_diagnostic(f"    {name} ошибка проверки")
            
            self.zapret.stop_current_strategy()
            
            score = success_count
            self.log_to_diagnostic(f"  Результат: {success_count}/{len(test_sites)}")
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
                best_success_count = success_count
        
        if best_strategy:
            self.log_to_diagnostic(f"\nЛучшая стратегия: {best_strategy}")
            self.log_to_diagnostic(f"Результат: {best_success_count}/{len(test_sites)}")
            
            self.strategy_var.set(best_strategy)
            self.current_strategy = best_strategy
            self.save_settings()
            
            if was_connected:
                self.log_to_diagnostic("Восстанавливаем подключение...")
                self.connect()
        else:
            self.log_to_diagnostic("\nНе найдена работающая стратегия")
        
        self.log_to_diagnostic("="*50)
        return best_strategy

    def check_zapret_status(self):
        self.log_to_diagnostic("Проверка статуса Zapret...")
        if self.zapret.is_winws_running():
            self.log_to_diagnostic(f"Zapret запущен (стратегия: {self.current_strategy or 'неизвестно'})")
        else:
            self.log_to_diagnostic("Zapret не запущен")

    def check_zapret_version(self):
        self.log_to_diagnostic("Доступные стратегии:")
        for s in self.zapret.available_strategies:
            self.log_to_diagnostic(f"  • {s}")
        self.log_to_diagnostic(f"Всего стратегий: {len(self.zapret.available_strategies)}")

    def check_zapret_logs(self):
        self.log_to_diagnostic("Поиск процессов winws.exe...")
        found = False
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                            time.localtime(proc.info['create_time']))
                    self.log_to_diagnostic(f"  • PID: {proc.info['pid']}, запущен: {create_time}")
                    found = True
            except:
                pass
        if not found:
            self.log_to_diagnostic("Процессы winws.exe не найдены")

    def restart_zapret(self):
        self.log_to_diagnostic("Перезапуск Zapret...")
        if self.is_connected:
            self.disconnect()
            time.sleep(2)
            self.connect()
            self.log_to_diagnostic("Zapret перезапущен")
        else:
            self.log_to_diagnostic("Zapret не был запущен")

    def check_byedpi_status(self):
        self.log_to_diagnostic("Проверка статуса ByeDPI...")
        status = self.byedpi.get_status()
        if status['running']:
            self.log_to_diagnostic(f"ByeDPI запущен (версия {status['version']}, провайдер: {self.current_provider})")
        else:
            if status['binary_exists']:
                self.log_to_diagnostic("ByeDPI не запущен (файл есть)")
            else:
                self.log_to_diagnostic("ByeDPI не установлен (нет ciadpi.exe)")

    def check_byedpi_port(self):
        self.log_to_diagnostic("Проверка порта 10801...")
        try:
            result = subprocess.run(['netstat', '-an'], 
                                capture_output=True, text=True, encoding='cp866')
            if "127.0.0.1:10801" in result.stdout and "LISTENING" in result.stdout:
                self.log_to_diagnostic("Порт 10801 открыт (ByeDPI слушает)")
            else:
                self.log_to_diagnostic("Порт 10801 не открыт")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def check_byedpi_version(self):
        status = self.byedpi.get_status()
        if status['binary_exists']:
            self.log_to_diagnostic(f"Версия ByeDPI: {status['version']}")
            self.log_to_diagnostic(f"Параметры: {status['params']}")
        else:
            self.log_to_diagnostic("ByeDPI не установлен")

    def restart_byedpi(self):
        self.log_to_diagnostic("Перезапуск ByeDPI...")
        if self.byedpi_enabled:
            self.byedpi.stop()
            time.sleep(1)
            self.byedpi.set_provider(self.current_provider)
            success, msg = self.byedpi.start()
            if success:
                self.log_to_diagnostic("ByeDPI перезапущен")
            else:
                self.log_to_diagnostic(f"{msg}")
        else:
            self.log_to_diagnostic("ByeDPI не был включен")

    def check_tgproxy_status(self):
        self.log_to_diagnostic("Проверка статуса TGProxy...")
        if hasattr(self, 'tg_proxy') and self.tg_proxy._running:
            self.log_to_diagnostic("TGProxy запущен")
        else:
            self.log_to_diagnostic("TGProxy не запущен")

    def check_tgproxy_port(self):
        self.log_to_diagnostic("Проверка порта 1080...")
        try:
            result = subprocess.run(['netstat', '-an'], 
                                capture_output=True, text=True, encoding='cp866')
            if "127.0.0.1:1080" in result.stdout and "LISTENING" in result.stdout:
                self.log_to_diagnostic("Порт 1080 открыт (TGProxy слушает)")
            else:
                self.log_to_diagnostic("Порт 1080 не открыт")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def check_telegram(self):
        self.log_to_diagnostic("Проверка доступности Telegram...")
        try:
            result = subprocess.run(['ping', '-n', '2', 'web.telegram.org'], 
                                capture_output=True, text=True, encoding='cp866')
            if result.returncode == 0:
                self.log_to_diagnostic("Telegram доступен")
            else:
                self.log_to_diagnostic("Telegram не отвечает, но может работать через приложение")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def restart_tgproxy(self):
        self.log_to_diagnostic("Перезапуск TGProxy...")
        if self.tg_proxy._running:
            self.tg_proxy.stop()
            time.sleep(1)
            self.tg_proxy.start()
            self.log_to_diagnostic("TGProxy перезапущен")
        else:
            self.log_to_diagnostic("TGProxy не был запущен")

    def check_admin_rights(self):
        self.log_to_diagnostic("Проверка прав администратора...")
        if is_admin():
            self.log_to_diagnostic("Программа запущена от имени администратора")
        else:
            self.log_to_diagnostic("Программа НЕ запущена от имени администратора")

    def check_launcher_version(self):
        self.log_to_diagnostic(f"Версия лаунчера: {CURRENT_VERSION}")

    def open_appdata_folder(self):
        self.log_to_diagnostic(f"Открытие папки: {APPDATA_DIR}")
        try:
            os.startfile(APPDATA_DIR)
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def clear_cache(self):
        self.log_to_diagnostic("Очистка кэша...")
        try:
            self.diagnostic_text.delete(1.0, tk.END)
            self.log_to_diagnostic("Кэш диагностики очищен")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def run_full_diagnostic(self):
        self.diagnostic_text.delete(1.0, tk.END)
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ")
        self.log_to_diagnostic("="*50)
        
        self.check_admin_rights()
        self.check_launcher_version()
        self.log_to_diagnostic("")
        
        self.check_ping_google()
        self.check_ping_youtube()
        self.log_to_diagnostic("")
        
        self.check_zapret_status()
        self.check_zapret_logs()
        self.log_to_diagnostic("")
        
        self.check_byedpi_status()
        self.check_byedpi_port()
        self.log_to_diagnostic("")
        
        self.check_tgproxy_status()
        self.check_tgproxy_port()
        self.log_to_diagnostic("")
        
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("Диагностика завершена")
        self.log_to_diagnostic("="*50)

    def save_diagnostic_report(self):
        try:
            report_path = APPDATA_DIR / f"diagnostic_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(self.diagnostic_text.get(1.0, tk.END))
            self.log_to_diagnostic(f"Отчет сохранен: {report_path}")
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка сохранения: {str(e)}")

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
            ("Пинг до Google", self.check_ping_google),
            ("Пинг до YouTube", self.check_ping_youtube),
            ("Пинг до Discord", self.check_ping_discord),
            ("Тест скорости", self.run_speedtest),
            ("Проверить сайт", self.check_custom_site),
        ])
        
        self.create_diagnostic_card(left_column, "Zapret", [
            ("Проверить статус", self.check_zapret_status),
            ("Версия стратегий", self.check_zapret_version),
            ("Логи winws.exe", self.check_zapret_logs),
            ("Перезапустить Zapret", self.restart_zapret),
            ("Авто-подбор", self.auto_select_strategy),
        ])
        
        self.create_diagnostic_card(left_column, "Общая диагностика", [
            ("Полная проверка", self.run_full_diagnostic),
            ("Сохранить отчет", self.save_diagnostic_report),
            ("Проверка файлов", self.check_file_integrity),
        ])
        
        self.create_diagnostic_card(right_column, "ByeDPI", [
            ("Проверить статус", self.check_byedpi_status),
            ("Порт 10801", self.check_byedpi_port),
            ("Версия", self.check_byedpi_version),
            ("Перезапустить ByeDPI", self.restart_byedpi),
        ])
        
        self.create_diagnostic_card(right_column, "TGProxy", [
            ("Проверить статус", self.check_tgproxy_status),
            ("Порт 1080", self.check_tgproxy_port),
            ("Проверить Telegram", self.check_telegram),
            ("Перезапустить TGProxy", self.restart_tgproxy),
        ])
        
        self.create_diagnostic_card(right_column, "Система", [
            ("Права администратора", self.check_admin_rights),
            ("Версия лаунчера", self.check_launcher_version),
            ("Папка AppData", self.open_appdata_folder),
            ("Очистить кэш", self.clear_cache),
            ("Автозапуск", self.toggle_autostart),
        ])
        
        result_frame = tk.Frame(self.diagnostic_page, bg=self.colors['bg_medium'])
        result_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(10, 20))
        
        tk.Label(result_frame, text="Результаты диагностики:", font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w', padx=15, pady=(8, 5))
        
        text_frame = tk.Frame(result_frame, bg=self.colors['bg_medium'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.diagnostic_text = tk.Text(text_frame, height=8, bg=self.colors['bg_dark'],
                                    fg=self.colors['text_primary'], font=("Consolas", 9),
                                    wrap=tk.WORD, borderwidth=0)
        scrollbar = tk.Scrollbar(text_frame, command=self.diagnostic_text.yview)
        self.diagnostic_text.configure(yscrollcommand=scrollbar.set)
        
        self.diagnostic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        tk.Label(scrollable_frame, text="Помощь", font=("Segoe UI", 28, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_dark']).pack(anchor='w', pady=(0, 20))
        
        self.help_section(scrollable_frame, "Установка:", [
            ("1.", "Скачивайте архив и распаковывайте в любое место 2 файла: ", "Zapret_Launcher.exe", " и ", "zapret_resources.zip"),
            ("2.", "Запускайте ", "Zapret_Launcher.exe", " от ", "имени администратора"),
            ("3.", "Выбирайте любой метод использования Zapret и подключайтесь к ", "стабильной сети", " находясь под ", "ограничениями РКН"),
            ("4.", "После всех 3-х действий ", "Zapret_Launcher.exe", " можно запускать в любой папке/в любом месте на компьютере ", "без файла zapret_resources.zip")
        ])
        
        self.help_section(scrollable_frame, "Telegram Proxy:", [
            ("1.", "Ставим галочку ", "Запустить вместе с Zapret", " в лаунчере"),
            ("2.", "Запускаем ", "Telegram", " на ПК"),
            ("3.", "Переходим в ", "настройки"),
            ("4.", "Продвинутые настройки"),
            ("5.", "Тип соединения"),
            ("6.", "Использовать собственное прокси (", "SOCKS5", ", Хост: ", "127.0.0.1", ", Порт: ", "1080", ")")
        ])
        
        self.help_section(scrollable_frame, "ByeDPI Оптимизатор:", [
            ("", "ByeDPI — это дополнительный инструмент для обхода DPI"),
            ("•", "Включайте, если интернет тормозит или стандартные стратегии не помогают"),
            ("•", "Особенно полезен для ", "YouTube", " и ", "онлайн-игр"),
            ("•", "Создает локальный SOCKS5 прокси на порту ", "10801"),
        ])
        
        self.help_section(scrollable_frame, "Что такое zapret_resources.zip:", [
            ("", "Это архив со всеми файлами Zapret, которые необходимы для работы лаунчера"),
            ("", "При первом запуске лаунчер распаковывает ", "zapret_resources.zip", " в ", "%APPDATA%/ZapretLauncher/zapret_core/"),
            ("", "Все файлы извлекаются в эту папку"),
            ("", "Стратегии запускаются оттуда"),
            ("", "Пользовательские списки (", "*-user.txt", ") сохраняются там же"),
        ])
        
        self.help_section(scrollable_frame, "В каких случаях можно удалить zapret_resources.zip:", [
            ("", "После успешной распаковки — если папка ", "zapret_core", " уже существует и полная"),
            ("", "Если ты обновляешь лаунчер — новый .exe уже содержит свежий архив"),
            ("", "Если ты хочешь сбросить Zapret — удали папку ", "zapret_core", " и при следующем запуске архив распакуется заново"),
        ])
        
        self.help_section(scrollable_frame, "НЕ УДАЛЯЙ, если:", [
            ("", "Папка ", "zapret_core", " отсутствует или повреждена"),
            ("", "Ты хочешь сохранить возможность переустановки без скачивания"),
            ("", "Ты распространяешь программу — архив должен быть рядом с .exe"),
        ])
        
        self.help_section(scrollable_frame, "Антивирус и WinDivert:", [
        ("", "Некоторые антивирусы могут реагировать на программу из-за использования компонента ", "WinDivert"),
        ("", " — это легальный драйвер с открытым исходным кодом, используемый для фильтрации сетевых пакетов. Это ", "НОРМАЛЬНО"),
        ])
        
        self.help_section(scrollable_frame, "Если антивирус ругается:", [
            ("1.", "Добавь папку с программой в ", "исключения"),
            ("2.", "Или скомпилируй программу сам из исходников или временно отключи антивирус при запуске"),
        ])
        
        self.help_section(scrollable_frame, "Возможные конфликты:", [
            ("", "Zapret и ByeDPI работают на разных уровнях и ", "в большинстве случаев не конфликтуют"),
            ("", "Если после включения всего интернет работает нестабильно:"),
            ("  •", "Отключай по одной галочке, чтобы найти виновника"),
            ("  •", "Для YouTube иногда помогает ", "отключение QUIC", " в браузере (chrome://flags/#enable-quic)"),
            ("  •", "Если пинг в играх вырос, отключи ", "TGProxy", " (он для игр не нужен)"),
            ("  •", "Разные стратегии Zapret могут вести себя по-разному с ByeDPI — экспериментируй"),
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
                            command=lambda cmd=btn1_cmd: self.safe_command(cmd),
                            width=180, height=22, bg=self.colors['button_bg'],
                            font=("Segoe UI", 7), corner_radius=4)
            btn1.pack(side=tk.LEFT, padx=(0, 2))
            
            if i + 1 < len(buttons):
                btn2_text, btn2_cmd = buttons[i + 1]
                btn2 = RoundedButton(row, text=btn2_text, 
                                command=lambda cmd=btn2_cmd: self.safe_command(cmd),
                                width=180, height=22, bg=self.colors['button_bg'],
                                font=("Segoe UI", 7), corner_radius=4)
                btn2.pack(side=tk.LEFT, padx=(2, 0))

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

    def toggle_autostart(self):
        current = self.check_autostart_status()
        new_state = not current
        
        if self.set_autostart(new_state):
            if new_state:
                messagebox.showinfo("Автозапуск", "Программа будет запускаться при старте Windows")
            else:
                messagebox.showinfo("Автозапуск", "Автозапуск отключен")
        else:
            messagebox.showerror("Ошибка", "Не удалось изменить настройки автозапуска")

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
            if hasattr(self, 'tray_icon'):
                self.tray_icon.update_menu()

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
        if hasattr(self, 'tray_icon'):
            self.tray_icon.update_menu()

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
            self.save_settings()
            
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
            if self.byedpi_enabled:
                self.byedpi.stop()
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
                    self.byedpi_enabled = data.get('byedpi_enabled', False)
                    saved_strategy = data.get('current_strategy')
                    if saved_strategy and saved_strategy in self.zapret.available_strategies:
                        self.current_strategy = saved_strategy
                    self.current_provider = data.get('byedpi_provider', 'Ростелеком')
                    self.provider_var.set(self.current_provider)
                    self.byedpi.set_provider(self.current_provider)
                    
                    autostart_enabled = data.get('autostart_enabled', False)
                    if autostart_enabled != self.check_autostart_status():
                        self.set_autostart(autostart_enabled)
        except:
            pass

    def save_settings(self):
        try:
            settings = {
                'tg_proxy_enabled': self.tg_proxy_enabled,
                'current_strategy': self.current_strategy,
                'byedpi_enabled': self.byedpi_enabled,
                'byedpi_provider': self.current_provider,
                'autostart_enabled': self.check_autostart_status()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass

    def show_page(self, page_name):
        if page_name == self.current_page:
            return
        
        if hasattr(self, f"{self.current_page}_page"):
            getattr(self, f"{self.current_page}_page").place_forget()
        
        if hasattr(self, f"{page_name}_page"):
            getattr(self, f"{page_name}_page").place(x=0, y=0, width=950, height=800)
            getattr(self, f"{page_name}_page").tkraise()
            self.current_page = page_name

    def show_main_page(self):
        self.show_page("main")
        
    def show_service_page(self):
        self.show_page("service")
        
    def show_lists_page(self):
        self.show_page("lists")

    def show_diagnostic_page(self):
        self.show_page("diagnostic")
    
    def show_help_page(self):
        self.show_page("help")

if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretLauncher(root)
    root.mainloop()
