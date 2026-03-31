import tkinter as tk
from tkinter import messagebox, ttk
from byedpi_optimizer import ByeDPIOptimizer
from pages import Pages, check_zapret_folder
from theme import get_theme
from network_optimizer import (
    optimize_network_latency,
    find_best_dns,
    set_dns_windows,
    flush_dns_cache,
    restore_network_defaults,
    list_network_adapters,
    set_dns_manual
)
from widgets import RoundedButton
from tg_proxy import _run
import subprocess
import os
import json
import time
import threading
import psutil
import socket
import winreg
import asyncio
import zipfile
import shutil
import tempfile
from pathlib import Path
import sys
import re
import urllib.request
import ctypes
import pystray
from PIL import Image, ImageDraw
from typing import Optional, List, Tuple
import webbrowser

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
ZAPRET_RESOURCES_ZIP = "zapret_resources.zip"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

LAUNCHER_API_URL = "https://api.github.com/repos/tweenkedrage/zapret-launcher/releases/latest"
ZAPRET_API_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"
CURRENT_VERSION = "2.6c"

PROVIDER_PARAMS = {
    "Ростелеком/Дом.ru/Tele2": ["--split", "1", "--disorder", "-1"],
    "МТС/Yota": ["-7", "-e1", "-q"],
    "Мегафон": ["-s0", "-o1", "-d1", "-r1+s", "-Ar", "-o1", "-At", "-f-1", "-r1+s", "-As"],
    "Билайн": ["--split", "1", "--disorder", "1", "--fake", "-1", "--ttl", "8"],
    "АКАДО": ["--split", "2", "--disorder", "1", "--fake", "-1", "--ttl", "8"],
    "ТТК": ["-1", "-e1"]
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
                        "Обновление Zapret Launcher",
                        f"Доступна новая версия лаунчера {latest_version}\n"
                        f"Текущая версия: {CURRENT_VERSION}\n\n"
                        f"Перейти на страницу загрузки?"
                    )
                    if result:
                        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher/releases/latest")
                    return True
                else:
                    result = messagebox.askyesno(
                        "Обновление Zapret Launcher",
                        f"Доступна новая версия {latest_version}\n"
                        f"Текущая версия: {CURRENT_VERSION}\n\n"
                        f"Перейти на страницу загрузки?"
                    )
                    if result and download_url:
                        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher/releases/latest")
                    return True
            else:
                if not silent:
                    messagebox.showinfo("Обновления", "У вас установлена последняя версия лаунчера")
                return False
    except Exception as e:
        if not silent:
            messagebox.showerror("Ошибка", f"Не удалось проверить обновления: {str(e)}")
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
                subprocess.run('sc stop windivert', shell=True, capture_output=True)
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

class StatsMonitor:
    def __init__(self):
        self.session_start = None
        self.total_up_bytes = 0
        self.total_down_bytes = 0
        self.connection_count = 0
        self.disconnection_count = 0
        self.is_monitoring = False
        self._monitor_thread = None
        self._stop_event = None
        self.last_up = 0
        self.last_down = 0
        self.current_speed_up = 0
        self.current_speed_down = 0
        self.last_update_time = 0
        
    def start_session(self):
        self.session_start = time.time()
        self.connection_count += 1
        self.is_monitoring = True
        self.last_up, self.last_down = self._get_network_stats()
        self.last_update_time = time.time()
        
    def end_session(self):
        self.is_monitoring = False
        self.disconnection_count += 1
        
    def _get_network_stats(self):
        current_time = time.time()
        if hasattr(self, '_cached_stats') and current_time - self._cached_time < 1:
            return self._cached_stats
        
        try:
            result = subprocess.run(
                ['netstat', '-e'],
                capture_output=True, text=True, encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=1
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Байт' in line or 'Bytes' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            recv = int(parts[1].replace(',', ''))
                            sent = int(parts[2].replace(',', ''))
                            self._cached_stats = (recv, sent)
                            self._cached_time = current_time
                            return recv, sent
                        except:
                            pass
            return 0, 0
        except:
            return 0, 0
    
    def update_speed(self):
        if not self.is_monitoring:
            return
        try:
            current_up, current_down = self._get_network_stats()
            now = time.time()
            time_diff = now - self.last_update_time
            
            if time_diff > 0.5:
                self.current_speed_up = (current_up - self.last_up) / time_diff
                self.current_speed_down = (current_down - self.last_down) / time_diff
                self.last_update_time = now
            
            if current_up > self.last_up:
                self.total_up_bytes += (current_up - self.last_up)
            if current_down > self.last_down:
                self.total_down_bytes += (current_down - self.last_down)
            
            self.last_up = current_up
            self.last_down = current_down
            
            self.current_speed_up = max(0, self.current_speed_up)
            self.current_speed_down = max(0, self.current_speed_down)
        except:
            pass
    
    def get_session_time(self):
        if self.session_start:
            return time.time() - self.session_start
        return 0
    
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def format_bytes(self, bytes_val):
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
    
    def format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    
    def get_stats_dict(self):
        self.update_speed()
        return {
            'session_time': self.get_session_time(),
            'session_time_str': self.format_time(self.get_session_time()),
            'up_bytes': self.total_up_bytes,
            'up_str': self.format_bytes(self.total_up_bytes),
            'down_bytes': self.total_down_bytes,
            'down_str': self.format_bytes(self.total_down_bytes),
            'total_bytes': self.total_up_bytes + self.total_down_bytes,
            'total_str': self.format_bytes(self.total_up_bytes + self.total_down_bytes),
            'connections': self.connection_count,
            'disconnections': self.disconnection_count,
            'speed_up': self.current_speed_up,
            'speed_up_str': self.format_speed(self.current_speed_up),
            'speed_down': self.current_speed_down,
            'speed_down_str': self.format_speed(self.current_speed_down),
        }

class TGProxyServer:
    def __init__(self):
        self._thread = None
        self._stop_event = None
        self._running = False
        self._port = 1080
        self._host = '127.0.0.1'
        self._process = None
        self._loop = None
        
    def _kill_process_on_port(self, port):
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True
            )
            pids = set()
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        pids.add(pid)
            
            for pid in pids:
                try:
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                except:
                    pass
        except:
            pass
    
    def start(self):
        if self._running:
            return True
        
        try:
            self._kill_process_on_port(1080)
            self._stop_event = asyncio.Event()
            
            dc_opt = {
                1: '149.154.175.50',
                2: '149.154.167.220',
                3: '149.154.175.100',
                4: '149.154.167.91',
                5: '91.108.56.100',
            }
            
            self._thread = threading.Thread(
                target=self._run_proxy,
                args=(self._port, dc_opt, self._stop_event, self._host),
                daemon=True
            )
            self._thread.start()

            for _ in range(10):
                time.sleep(0.5)
                if self._is_port_open(1080):
                    self._running = True
                    return True
            return False  
        except Exception as e:
            print(f"TGProxy start error: {e}")
            return False
        
    def _is_port_open(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    
    def _run_proxy(self, port, dc_opt, stop_event, host):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_until_complete(self._run_proxy_async(port, dc_opt, stop_event, host))
        except Exception as e:
            print(f"TGProxy run error: {e}")
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self._loop = None
    
    async def _run_proxy_async(self, port, dc_opt, stop_event, host):
        proxy_task = asyncio.create_task(_run(port, dc_opt, stop_event, host))
        await stop_event.wait()
        proxy_task.cancel()

        try:
            await proxy_task
        except asyncio.CancelledError:
            pass
    
    def stop(self):
        if not self._running:
            return
        
        if self._stop_event:
            self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._kill_process_on_port(1080)

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
                f"Не найден файл ресурсов {ZAPRET_RESOURCES_ZIP}\n"
                "Запустите build_resources.py для его создания"
            )
            sys.exit(1)
            
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(self.zapret_dir)
            
            version_file = self.zapret_dir / "version.txt"
            if not version_file.exists():
                with open(version_file, 'w') as f:
                    f.write("1.9.7b")  
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

class SystemTrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.create_icon()

    def create_icon(self):
        try:
            image = None
            icon_paths = [
                Path(__file__).parent / "icon.ico",
                Path(sys.executable).parent / "icon.ico" if getattr(sys, 'frozen', False) else None,
                Path("icon.ico"),
                Path(__file__).parent / "icon.png",
                Path("icon.png")
            ]
            
            for path in icon_paths:
                if path and path.exists():
                    try:
                        image = Image.open(str(path))
                        break
                    except:
                        continue
            
            if image is None:
                raise Exception("Иконка не найдена")
            
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            image = image.resize((256, 256), Image.Resampling.LANCZOS)
            
        except Exception as e:
            print(f"Не удалось загрузить иконку для трея: {e}")
            image = Image.new('RGBA', (64, 64), color='#d0a2e9')
            draw = ImageDraw.Draw(image)
            draw.text((20, 20), "Z", fill='white', font=None)

        self.update_menu(image)
        
    def update_menu(self, image=None):
        if self.app.is_connected:
            connection_text = "Отключиться"
        else:
            connection_text = "Подключиться"
        
        menu = pystray.Menu(
            pystray.MenuItem("Открыть лаунчер", self.show_window, default=True),
            pystray.MenuItem(connection_text, self.toggle_connection),
            pystray.MenuItem("Выход", self.quit_app)
        )
        
        if self.icon:
            self.icon.menu = menu
            if image:
                self.icon.icon = image
        else:
            if image is None:
                image = Image.new('RGBA', (64, 64), color='#d0a2e9')
                draw = ImageDraw.Draw(image)
                draw.text((20, 20), "Z", fill='white', font=None)
            
            self.icon = pystray.Icon("zapret_launcher", image, "Zapret Launcher", menu)
        
    def show_window(self):
        self.app.root.deiconify()
        self.app.root.lift()
        self.app.root.focus_force()

    def toggle_connection(self):
        if self.app.is_connected:
            self.app.disconnect()
        else:
            self.app.show_mode_selector()
        self.update_menu()

    def quit_app(self):
        self.icon.stop()
        self.app.on_closing()

    def run(self):
        self.icon.run()

class ByeDPIWithProvider:
    def __init__(self, app_data_dir):
        self.base = ByeDPIOptimizer(app_data_dir)
        self.current_provider = "Ростелеком/Дом.ru/Tele2"
    
    def set_provider(self, provider):
        self.current_provider = provider
        params = PROVIDER_PARAMS.get(provider, PROVIDER_PARAMS["Ростелеком/Дом.ru/Tele2"])
        full_params = params + ["-i", "127.0.0.1", "-p", "10801"]
        self.base.set_params(full_params)
        
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
        self.stats = StatsMonitor()
        self.stats_update_id = None
        self._pending_mode = None
        self.PROVIDER_PARAMS = PROVIDER_PARAMS

        self.strategy_var = tk.StringVar()
        self.provider_var = tk.StringVar(value="Ростелеком/Дом.ru/Tele2")
        self.tgws_var = tk.BooleanVar(value=False)
        self.byedpi_var = tk.BooleanVar(value=False)

        self._tg_instruction = False

        self.update_intervals = [0, 5, 10, 30, 60, None]
        self.update_interval_index = 0
        self.update_interval = self.update_intervals[self.update_interval_index]
        self.update_timer_id = None

        self.rtt_timer_id = None
        self.rtt_update_interval = 5000

        self.traffic_history = {}
        self.traffic_history_vpn = {}
        self.traffic_history_direct = {}
        self.traffic_speed_history = {}
        self.traffic_speed_vpn_history = {}
        self.traffic_speed_direct_history = {}
        self.traffic_last_update = time.time()
        self._traffic_update_scheduled = False
        self._traffic_collecting = False
        self._traffic_collecting_start = 0
        self._traffic_update_timer = None
        self.hostname_cache = {}
        self.hostname_cache_time = {}
        
        self.byedpi_status = tk.Label()

        self._cached_processes = []
        self._last_process_time = 0

        try:
            icon_paths = [
                Path(__file__).parent / "icon.ico",
                Path(sys.executable).parent / "icon.ico" if getattr(sys, 'frozen', False) else None,
                Path("icon.ico"),
                Path(__file__).parent / "icon.png",
                Path("icon.png")
            ]
            
            icon_loaded = False
            for path in icon_paths:
                if path and path.exists():
                    try:
                        if path.suffix.lower() == '.ico':
                            self.root.iconbitmap(default=str(path))
                            icon_loaded = True
                            break
                        elif path.suffix.lower() == '.png':
                            icon_img = tk.PhotoImage(file=str(path))
                            self.root.iconphoto(True, icon_img)
                            icon_loaded = True
                            break
                    except:
                        continue
            
            if not icon_loaded:
                print("Иконка не загружена")
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")
        
        self.window_width = 1200
        self.window_height = 800
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.font_primary = ("Segoe UI", 10)
        self.font_medium = ("Segoe UI", 12)
        self.font_title = ("Segoe UI", 28, "bold")
        self.font_bold = ("Segoe UI", 12, "bold")
        
        self.colors = get_theme('dark')
        self.setup_scrollbar_style()
        self.root.configure(bg=self.colors['bg_dark'])
        
        if not is_admin():
            result = messagebox.askyesno(
                "Права администратора",
                "Программа требует прав администратора для работы\n\n"
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
        self.current_page = "main"
        self.current_provider = "Ростелеком/Дом.ru/Tele2"
        
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
            
            time.sleep(2)
            
            for port in [1080, 10801]:
                try:
                    result = subprocess.run(
                        f'netstat -ano | findstr :{port} | findstr LISTENING',
                        shell=True, capture_output=True, text=True
                    )
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                try:
                                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                                except:
                                    pass
                except:
                    pass
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
        self.pages = Pages(self)
        self.pages.create_all_pages(self.content_panel)

    def create_left_panel(self):
        left_panel = tk.Frame(self.main_container, bg=self.colors['bg_medium'], width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        logo_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'], height=140)
        logo_frame.pack(fill=tk.X, pady=(40, 20))
        logo_frame.pack_propagate(False)
        
        try:
            icon_paths = [
                Path(__file__).parent / "icon.png",
                Path(sys.executable).parent / "icon.png" if getattr(sys, 'frozen', False) else None,
                Path("icon.png")
            ]
            
            icon_image = None
            for path in icon_paths:
                if path and path.exists():
                    icon_image = tk.PhotoImage(file=str(path))
                    break
            
            if icon_image:
                icon_image = icon_image.subsample(icon_image.width() // 120, icon_image.height() // 120)
                icon_label = tk.Label(logo_frame, image=icon_image, bg=self.colors['bg_medium'], cursor="hand2")
                icon_label.image = icon_image
                icon_label.pack(expand=True, pady=10)
                icon_label.bind("<Button-1>", lambda e: self.show_settings_page())
                icon_label.bind("<Enter>", lambda e: icon_label.config(cursor="hand2"))
                icon_label.bind("<Leave>", lambda e: icon_label.config(cursor=""))
            else:
                raise Exception("Иконка не найдена")
                
        except Exception as e:
            print(f"Не удалось загрузить иконку: {e}")
            logo_btn = RoundedButton(
                logo_frame,
                text="ZAPRET\nLAUNCHER",
                command=self.show_settings_page,
                width=120, height=120,
                bg=self.colors['accent'],
                fg=self.colors['text_primary'],
                font=("Segoe UI", 14, "bold"),
                corner_radius=60
            )
            logo_btn.pack(expand=True, pady=10)
            logo_btn.bind("<Enter>", lambda e: logo_btn.config(cursor="hand2"))
            logo_btn.bind("<Leave>", lambda e: logo_btn.config(cursor=""))

        nav_buttons = [
            ("Главная", self.show_main_page),
            ("Сервис", self.show_service_page),
            ("Редактор", self.show_lists_page),
            ("Диагностика", self.show_diagnostic_page),
            ("Трафик", self.show_traffic_page),
        ]
        
        for text, command in nav_buttons:
            btn_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'])
            btn_frame.pack(fill=tk.X, pady=2, padx=15)
            
            btn = RoundedButton(
                btn_frame,
                text=text,
                command=command,
                width=220, height=45,
                bg=self.colors['bg_light'],
                fg=self.colors['text_secondary'],
                font=("Segoe UI", 11),
                corner_radius=10
            )
            btn.pack()
            
            btn.bind("<Enter>", lambda e: btn.config(cursor="hand2"))
            btn.bind("<Leave>", lambda e: btn.config(cursor=""))
        
        separator = tk.Frame(left_panel, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=20)
        
        credit_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'])
        credit_frame.pack(side=tk.BOTTOM, pady=(0, 30), fill=tk.X)

        self.left_status = tk.Label(
            credit_frame,
            text="●",
            font=("Segoe UI", 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        self.left_status.pack()
        
        tk.Label(
            credit_frame,
            text=f"v{CURRENT_VERSION}",
            font=("Segoe UI", 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        ).pack(pady=(5, 0))
        
        self.credit_label = tk.Label(
            credit_frame,
            text="by trimansberg",
            font=("Segoe UI", 8),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            cursor="hand2"
        )
        self.credit_label.pack(pady=(2, 0))

        self.credit_label.bind("<Enter>", lambda e: self.credit_label.config(fg=self.colors['accent']))
        self.credit_label.bind("<Leave>", lambda e: self.credit_label.config(fg=self.colors['text_secondary']))
        self.credit_label.bind("<Button-1>", lambda e: self.open_github())

    def show_mode_selector(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Выбор режима запуска")
        dialog.geometry("500x550")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Выберите режим запуска", font=("Segoe UI", 16, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.colors['bg_medium'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, style="Custom.Vertical.TScrollbar")
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_medium'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=440)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            try:
                if canvas and canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except (tk.TclError, AttributeError):
                pass
        
        dialog.bind_all("<MouseWheel>", _on_mousewheel)
        dialog._mousewheel_handler = _on_mousewheel
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        modes = [
            {"name": "Стандартный", "desc": "Обход блокировок через Zapret", 
            "zapret": True, "tgproxy": False, "byedpi": False, "game": False},
            {"name": "TG Proxy", "desc": "Ускорение работы Telegram", 
            "zapret": False, "tgproxy": True, "byedpi": False, "game": False},
            {"name": "ByeDPI", "desc": "Оптимизация игр, снижение задержки", 
            "zapret": False, "tgproxy": False, "byedpi": True, "game": False},
            {"name": "Игровой", "desc": "Максимальная производительность для игр", 
            "zapret": True, "tgproxy": False, "byedpi": False, "game": True},
            {"name": "Кастомный", "desc": "Выберите что включить самостоятельно", 
            "zapret": False, "tgproxy": False, "byedpi": False, "game": False, "custom": True}
        ]
        
        selected_mode = [None]
        selected_widget = [None]
        select_btn = [None]
        
        def update_select_button():
            if select_btn[0]:
                if selected_mode[0]:
                    select_btn[0].set_enabled(True)
                    select_btn[0].update_colors(
                        self.colors['accent'],
                        self.colors['text_primary'],
                        self.colors['button_hover']
                    )
                    select_btn[0].config(cursor="hand2")
                else:
                    select_btn[0].set_enabled(False)
                    select_btn[0].update_colors(
                        self.colors['button_bg'],
                        self.colors['text_secondary'],
                        self.colors['button_bg']
                    )
                    select_btn[0].config(cursor="arrow")
        
        def on_single_click(mode, frame, name_label, desc_label):
            if selected_widget[0]:
                prev_frame, prev_name, prev_desc = selected_widget[0]
                prev_frame.configure(bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
                prev_name.configure(fg=self.colors['accent'], bg=self.colors['bg_light'])
                prev_desc.configure(fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
            
            frame.configure(bg=self.colors['accent'], relief=tk.RIDGE, bd=2)
            name_label.configure(fg=self.colors['text_primary'], bg=self.colors['accent'])
            desc_label.configure(fg=self.colors['text_secondary'], bg=self.colors['accent'])
            
            selected_widget[0] = (frame, name_label, desc_label)
            selected_mode[0] = mode
            update_select_button()
        
        def on_double_click(mode):
            if mode:
                dialog.destroy()
                self.start_with_mode(mode)
        
        def on_select_click():
            if selected_mode[0]:
                dialog.destroy()
                self.start_with_mode(selected_mode[0])
        
        for mode in modes:
            mode_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="hand2")
            mode_frame.pack(fill=tk.X, padx=10, pady=5, ipady=8)
            
            original_bg = self.colors['bg_light']
            name_label = tk.Label(mode_frame, text=mode["name"], font=("Segoe UI", 12, "bold"),
                                fg=self.colors['accent'], bg=original_bg)
            name_label.pack(anchor='w', padx=15, pady=(8, 2))
            desc_label = tk.Label(mode_frame, text=mode["desc"], font=("Segoe UI", 9),
                                fg=self.colors['text_secondary'], bg=original_bg)
            desc_label.pack(anchor='w', padx=15, pady=(0, 8))

            def make_on_click(m, f, nl, dl):
                return lambda e: on_single_click(m, f, nl, dl)
            
            def make_on_double(m):
                return lambda e: on_double_click(m)
            
            click_handler = make_on_click(mode, mode_frame, name_label, desc_label)
            double_handler = make_on_double(mode)
            
            mode_frame.bind("<Button-1>", click_handler)
            mode_frame.bind("<Double-Button-1>", double_handler)
            name_label.bind("<Button-1>", click_handler)
            name_label.bind("<Double-Button-1>", double_handler)
            desc_label.bind("<Button-1>", click_handler)
            desc_label.bind("<Double-Button-1>", double_handler)
            
            def make_on_enter(frame, nl, dl, orig_bg):
                def on_enter_func(e):
                    if selected_widget[0] and selected_widget[0][0] == frame:
                        return
                    frame.configure(bg=self.colors['bg_light_hover'])
                    nl.configure(bg=self.colors['bg_light_hover'])
                    dl.configure(bg=self.colors['bg_light_hover'])
                return on_enter_func
            
            def make_on_leave(frame, nl, dl, orig_bg):
                def on_leave_func(e):
                    if selected_widget[0] and selected_widget[0][0] == frame:
                        return
                    frame.configure(bg=orig_bg)
                    nl.configure(bg=orig_bg)
                    dl.configure(bg=orig_bg)
                return on_leave_func
            
            mode_frame.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg))
            mode_frame.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg))
            name_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg))
            name_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg))
            desc_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg))
            desc_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg))
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=20, pady=15)
        
        select_btn[0] = RoundedButton(
            bottom_frame,
            text="Выбрать",
            command=on_select_click,
            width=100, height=35,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Segoe UI", 10),
            corner_radius=8
        )
        select_btn[0].set_enabled(False)
        select_btn[0].config(cursor="arrow")
        select_btn[0].pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = RoundedButton(
            bottom_frame,
            text="Отмена",
            command=dialog.destroy,
            width=100, height=35,
            bg=self.colors['button_bg'],
            fg=self.colors['text_primary'],
            font=("Segoe UI", 10),
            corner_radius=8
        )
        cancel_btn.config(cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)

    def start_with_mode(self, mode):
        if self.is_connected:
            return
        
        if mode["name"] == "TG Proxy":
            dont_show = False
            try:
                settings = self.load_settings_data()
                dont_show = settings.get('tg_instruction', False)
            except:
                pass
            
            if dont_show:
                self._start_tg_proxy_mode(None, False)
            else:
                self.show_tg_proxy_instruction()
            return
        
        if mode["name"] == "Стандартный" or mode["name"] == "Игровой":
            if not self.zapret.available_strategies:
                messagebox.showerror("Ошибка", "Нет доступных стратегий Zapret")
                return
            
            self._pending_mode = mode
            self.select_strategy_for_mode(mode["name"])
            return
        
        if mode["name"] == "ByeDPI":
            self.show_provider_selector(mode)
            return
        
        if mode["name"] == "Кастомный":
            self.show_custom_selector()
            return

        self._reset_traffic_history()

        self.update_status("Запуск...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        success = True
        msg = ""
        
        if mode.get("tgproxy", False):
            self.tg_proxy.start()
        
        if mode.get("byedpi", False):
            self.byedpi.set_provider(self.current_provider)
            success, msg = self.byedpi.start()
            if not success:
                messagebox.showerror("Ошибка ByeDPI", msg)
                self.connect_btn.set_enabled(True)
                return
            self.byedpi_enabled = True
            self.byedpi_var.set(True)
        
        self.is_connected = True
        self.stats.start_session()
        self.start_stats_monitoring()
        
        mode_name = mode["name"]
        self.mode_label.config(text=mode_name, fg=self.colors['accent_green'])
        self.update_status(f"Подключено: {mode_name}", self.colors['accent_green'])
        self.update_ui_state()
        self.save_settings()
        self.root.after(100, self.update_stats_display)
        self.connect_btn.set_enabled(True)

    def select_strategy_for_mode(self, mode_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Выбор стратегии")
        dialog.geometry("450x450")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 225
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text=f"Выберите стратегию Zapret", 
                font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        list_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        strategy_listbox = tk.Listbox(list_frame, height=10, font=("Segoe UI", 10),
                                    bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                    selectbackground=self.colors['accent'],
                                    yscrollcommand=scrollbar.set)
        strategy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=strategy_listbox.yview)
        
        for s in self.zapret.available_strategies:
            strategy_listbox.insert(tk.END, s)
        
        desc_label = tk.Label(dialog, text="", font=("Segoe UI", 9),
                            fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                            wraplength=400, justify=tk.LEFT)
        desc_label.pack(pady=5, padx=20)
        
        def on_select(event):
            selection = strategy_listbox.curselection()
            if selection:
                strategy = self.zapret.available_strategies[selection[0]]
                desc_label.config(text=f"Выбрано: {strategy}")
        
        strategy_listbox.bind("<<ListboxSelect>>", on_select)
        
        if self.current_strategy:
            try:
                idx = self.zapret.available_strategies.index(self.current_strategy)
                strategy_listbox.selection_set(idx)
                strategy_listbox.see(idx)
                desc_label.config(text=f"Выбрано: {self.current_strategy}")
            except:
                pass
        
        def start_with_strategy():
            selection = strategy_listbox.curselection()
            if not selection:
                messagebox.showerror("Ошибка", "Выберите стратегию")
                return
            selected_strategy = self.zapret.available_strategies[selection[0]]
            self.strategy_var.set(selected_strategy)
            dialog.destroy()
            
            mode = self._pending_mode
            self.update_status(f"Запуск {mode['name']} режим...", self.colors['accent'])
            self.connect_btn.set_enabled(False)
            self.root.update()
            
            success, msg = self.zapret.run_strategy(selected_strategy)
            if not success:
                self.update_status("Ошибка запуска", self.colors['accent_red'])
                messagebox.showerror("Ошибка", msg)
                self.connect_btn.set_enabled(True)
                return
            
            self.current_strategy = selected_strategy
            
            if mode.get("tgproxy", False):
                self.tg_proxy.start()
            
            if mode.get("byedpi", False):
                self.byedpi.set_provider(self.current_provider)
                success, msg = self.byedpi.start()
                if not success:
                    messagebox.showerror("Ошибка ByeDPI", msg)
                    self.zapret.stop_current_strategy()
                    self.connect_btn.set_enabled(True)
                    return
                self.byedpi_enabled = True
                self.byedpi_var.set(True)
            
            self.is_connected = True
            self.stats.start_session()
            self.start_stats_monitoring()
            
            mode_display = mode["name"]
            strategy_display = self.zapret.get_strategy_display_name(selected_strategy)
            self.mode_label.config(text=mode_display, fg=self.colors['accent_green'])
            self.update_status(f"Подключено: Стратегия {strategy_display}", self.colors['accent_green'])
            self.update_ui_state()
            self.save_settings()
            self.root.after(100, self.update_stats_display)
            self.connect_btn.set_enabled(True)
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=15)
        
        start_btn = RoundedButton(btn_frame, text="Запустить", command=start_with_strategy,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI", 10), corner_radius=8)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text="Отмена", command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI", 10), corner_radius=8)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def show_provider_selector(self, mode):
        dialog = tk.Toplevel(self.root)
        dialog.title("Выбор провайдера для ByeDPI")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 175
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Выберите вашего провайдера", 
                font=("Segoe UI", 14, "bold"),
                fg=self.colors['text_primary'], 
                bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        providers = list(PROVIDER_PARAMS.keys())
        
        listbox_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        provider_listbox = tk.Listbox(listbox_frame, height=6, font=("Segoe UI", 10),
                                    bg=self.colors['bg_light'], 
                                    fg=self.colors['text_primary'],
                                    selectbackground=self.colors['accent'],
                                    yscrollcommand=scrollbar.set)
        provider_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=provider_listbox.yview)
        
        for provider in providers:
            provider_listbox.insert(tk.END, provider)
        
        try:
            idx = providers.index(self.current_provider)
            provider_listbox.selection_set(idx)
            provider_listbox.see(idx)
        except:
            pass
        
        def start_with_provider():
            selection = provider_listbox.curselection()
            if selection:
                provider = providers[selection[0]]
                self.current_provider = provider
                self.provider_var.set(provider)
                self.byedpi.set_provider(provider)
            
            dialog.destroy()
            
            if hasattr(self, 'connect_btn'):
                self.connect_btn.set_enabled(False)
            
            self.update_status("Запуск ByeDPI...", self.colors['accent'])
            self.root.update()
            
            def run_byedpi():
                success, msg = self.byedpi.start()
                self.root.after(0, lambda: on_byedpi_result(success, msg))
            
            def on_byedpi_result(success, msg):
                if not success:
                    self.update_status("Ошибка запуска", self.colors['accent_red'])
                    messagebox.showerror("Ошибка ByeDPI", msg)
                    if hasattr(self, 'connect_btn'):
                        self.connect_btn.set_enabled(True)
                    return
                
                self.byedpi_enabled = True
                self.byedpi_var.set(True)
                self.is_connected = True
                
                self.stats.start_session()
                self.start_stats_monitoring()
                
                mode_name = f"ByeDPI ({self.current_provider})"
                self.mode_label.config(text=mode_name, fg=self.colors['accent_green'])
                self.update_status(f"Подключено: {mode_name}", self.colors['accent_green'])
                self.update_ui_state()
                self.save_settings()
                self.root.after(100, self.update_stats_display)
                
                if hasattr(self, 'connect_btn'):
                    self.connect_btn.set_enabled(True)
            
            threading.Thread(target=run_byedpi, daemon=True).start()
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=15)
        
        start_btn = RoundedButton(btn_frame, text="Запустить", command=start_with_provider,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI", 10), corner_radius=8)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text="Отмена", command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI", 10), corner_radius=8)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def show_custom_selector(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Кастомный режим")
        dialog.geometry("450x500")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 250
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Выберите компоненты для запуска", font=("Segoe UI", 14, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        custom_zapret = tk.IntVar(value=1)
        custom_tgproxy = tk.IntVar(value=0)
        custom_byedpi = tk.IntVar(value=0)
        
        zapret_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        zapret_frame.pack(fill=tk.X, padx=20, pady=5, ipady=5)
        
        zapret_cb = tk.Checkbutton(zapret_frame, text="Zapret", variable=custom_zapret,
                                    bg=self.colors['bg_light'], activebackground=self.colors['bg_light'],
                                    fg=self.colors['text_primary'], selectcolor=self.colors['bg_light'])
        zapret_cb.pack(side=tk.LEFT, padx=10)
        
        strategy_frame = tk.Frame(zapret_frame, bg=self.colors['bg_light'])
        strategy_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(strategy_frame, text="Стратегия:", font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_light']).pack(side=tk.LEFT)
        strategy_combo = ttk.Combobox(strategy_frame, values=self.zapret.available_strategies,
                                    width=25, font=self.font_primary)
        strategy_combo.pack(side=tk.LEFT, padx=5)
        if self.current_strategy:
            strategy_combo.set(self.current_strategy)
        elif self.zapret.available_strategies:
            strategy_combo.set(self.zapret.available_strategies[0])
        
        tg_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        tg_frame.pack(fill=tk.X, padx=20, pady=5, ipady=5)
        tg_cb = tk.Checkbutton(tg_frame, text="TG Proxy (Telegram)", variable=custom_tgproxy,
                                bg=self.colors['bg_light'], activebackground=self.colors['bg_light'],
                                fg=self.colors['text_primary'], selectcolor=self.colors['bg_light'])
        tg_cb.pack(side=tk.LEFT, padx=10)
        
        byedpi_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        byedpi_frame.pack(fill=tk.X, padx=20, pady=5, ipady=5)
        
        byedpi_cb = tk.Checkbutton(byedpi_frame, text="ByeDPI Оптимизатор", variable=custom_byedpi,
                                    bg=self.colors['bg_light'], activebackground=self.colors['bg_light'],
                                    fg=self.colors['text_primary'], selectcolor=self.colors['bg_light'],
                                    command=lambda: toggle_byedpi_provider())
        byedpi_cb.pack(side=tk.LEFT, padx=10)
        provider_container = tk.Frame(byedpi_frame, bg=self.colors['bg_light'])
        
        def toggle_byedpi_provider():
            if custom_byedpi.get() == 1:
                provider_container.pack(side=tk.RIGHT, padx=10)
            else:
                provider_container.pack_forget()
        tk.Label(provider_container, text="Провайдер:", font=self.font_primary,
                fg=self.colors['text_secondary'], bg=self.colors['bg_light']).pack(side=tk.LEFT)
        
        provider_combo = ttk.Combobox(provider_container, values=list(PROVIDER_PARAMS.keys()),
                                    width=18, font=self.font_primary)
        provider_combo.set(self.current_provider)
        provider_combo.pack(side=tk.LEFT, padx=5)
        
        if custom_byedpi.get() == 1:
            provider_container.pack(side=tk.RIGHT, padx=10)
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)
        
        def apply_custom():
            mode = {
                "name": "Кастомный",
                "zapret": custom_zapret.get() == 1,
                "tgproxy": custom_tgproxy.get() == 1,
                "byedpi": custom_byedpi.get() == 1,
                "game": False,
                "strategy": strategy_combo.get() if custom_zapret.get() == 1 else None,
                "byedpi_provider": provider_combo.get() if custom_byedpi.get() == 1 else None
            }
            
            dialog.destroy()
            self.start_custom_mode(mode)
        
        def cancel():
            dialog.destroy()
        
        apply_btn = RoundedButton(btn_frame, text="Запустить", command=apply_custom,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI", 10), corner_radius=8)
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text="Отмена", command=cancel,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI", 10), corner_radius=8)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def start_custom_mode(self, mode):
        self.update_status("Запуск...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        def run_all():
            success = True
            msg = ""
            
            if mode.get("byedpi", False):
                provider = mode.get("byedpi_provider")
                if provider:
                    self.current_provider = provider
                    self.provider_var.set(provider)
                    self.byedpi.set_provider(provider)
                
                success, msg = self.byedpi.start()
                if not success:
                    self.root.after(0, lambda: on_error("ByeDPI", msg))
                    return
                self.byedpi_enabled = True
                self.byedpi_var.set(True)
            
            if mode.get("zapret", False):
                strategy = mode.get("strategy")
                if not strategy:
                    self.root.after(0, lambda: on_error("Zapret", "Выберите стратегию"))
                    return
                success, msg = self.zapret.run_strategy(strategy)
                if not success:
                    self.root.after(0, lambda: on_error("Zapret", msg))
                    return
                self.current_strategy = strategy
                self.strategy_var.set(strategy)
            
            if mode.get("tgproxy", False):
                self.tg_proxy.start()
            
            self.is_connected = True
            self.stats.start_session()
            self.start_stats_monitoring()
            
            components = []
            if mode.get("zapret", False):
                components.append("Zapret")
            if mode.get("tgproxy", False):
                components.append("TGProxy")
            if mode.get("byedpi", False):
                provider_str = f" ({self.current_provider})" if mode.get("byedpi_provider") else ""
                components.append(f"ByeDPI{provider_str}")

            mode_label_text = "Кастомный"

            if components:
                status_text = "" + ", ".join(components) + ""
            else:
                status_text = "Кастомный"
            
            self._current_mode_name = mode_label_text
            self._current_status_text = status_text
            self.root.after(0, lambda: on_success(mode_label_text, status_text))
        
        def on_error(component, error_msg):
            self.update_status("Ошибка запуска", self.colors['accent_red'])
            messagebox.showerror(f"Ошибка {component}", error_msg)
            self.connect_btn.set_enabled(True)
        
        def on_success(mode_label_text, status_text):
            self.mode_label.config(text=mode_label_text, fg=self.colors['accent_green'])
            self.update_status(f"Подключено: {status_text}", self.colors['accent_green'])
            self.update_ui_state()
            self.save_settings()
            self.root.after(100, self.update_stats_display)
            self.connect_btn.set_enabled(True)
        
        threading.Thread(target=run_all, daemon=True).start()

    def update_stats_display(self):
        if not hasattr(self, 'stats_frame'):
            return
        
        stats = self.stats.get_stats_dict()

        if hasattr(self, 'stats_time_label'):
            self.stats_time_label.config(text=stats['session_time_str'])
        
        if hasattr(self, 'stats_traffic_label'):
            self.stats_traffic_label.config(text=f"⬇ {stats['down_str']}  |  ⬆ {stats['up_str']}")
        
        if hasattr(self, 'stats_total_label'):
            self.stats_total_label.config(text=stats['total_str'])
        
        if hasattr(self, 'stats_speed_up_label'):
            self.stats_speed_up_label.config(text=f"⬆ {stats['speed_up_str']}")
        if hasattr(self, 'stats_speed_down_label'):
            self.stats_speed_down_label.config(text=f"⬇ {stats['speed_down_str']}")

    def _update_rtt(self):
        if hasattr(self, 'stats_rtt_label'):
            rtt = self.measure_rtt()
            if rtt > 0:
                self.stats_rtt_label.config(text=f"{rtt:.0f} ms", fg=self.colors['accent'])
            else:
                self.stats_rtt_label.config(text="-- ms", fg=self.colors['text_secondary'])
        
        self.rtt_timer_id = self.root.after(self.rtt_update_interval, self._update_rtt)

    def start_rtt_monitoring(self):
        self.stop_rtt_monitoring()
        self.rtt_timer_id = self.root.after(1000, self._update_rtt)

    def stop_rtt_monitoring(self):
        if self.rtt_timer_id:
            self.root.after_cancel(self.rtt_timer_id)
            self.rtt_timer_id = None

    def measure_rtt(self) -> float:
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '8.8.8.8'],
                capture_output=True, text=True, encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                match = re.search(r'(?:время|time)[=<>]\s*(\d+)\s*мс', output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
                
                match = re.search(r'time[=<>](\d+)ms', output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
                
                match = re.search(r'(\d+)\s*мс', output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return -1
        except Exception as e:
            print(f"RTT measurement error: {e}")
            return -1

    def start_stats_monitoring(self):
        self.stop_stats_monitoring()
        self.start_rtt_monitoring()
        
        if self.is_connected:
            self._schedule_stats_update()

    def stop_stats_monitoring(self):
        if self.update_timer_id:
            self.root.after_cancel(self.update_timer_id)
            self.update_timer_id = None

    def _schedule_stats_update(self):
        if not self.is_connected:
            if self.update_interval is None:
                return
                
            if not self.root.winfo_viewable():
                interval = 5000
            elif self.update_interval == 0:
                interval = 500
            elif self.update_interval > 0:
                interval = int(self.update_interval * 1000)
            else:
                interval = 1000
            
            self.update_timer_id = self.root.after(interval, self._schedule_stats_update)
            return
        
        self.stats.update_speed()
        self.update_stats_display()

        if self.update_interval is None:
            return
        
        if not self.root.winfo_viewable():
            interval = 5000
        elif self.update_interval == 0:
            interval = 500
        elif self.update_interval > 0:
            interval = int(self.update_interval * 1000)
        else:
            interval = 1000
        
        self.update_timer_id = self.root.after(interval, self._schedule_stats_update)

    def show_notification(self, message, duration=2000):
        notification = tk.Toplevel(self.root)
        notification.overrideredirect(True)
        
        notification.configure(bg=self.colors['bg_medium'])
        
        try:
            notification.attributes('-alpha', 0.95)
            notification.attributes('-topmost', True)
        except:
            pass
        
        x = self.root.winfo_x() + self.root.winfo_width() - 300
        y = self.root.winfo_y() + 50
        notification.geometry(f"280x40+{x}+{y}")
        
        frame = tk.Frame(notification, bg=self.colors['accent'], padx=1, pady=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(frame, bg=self.colors['bg_medium'])
        inner.pack(fill=tk.BOTH, expand=True)
        
        label = tk.Label(inner, text=message, 
                        font=("Segoe UI", 10),
                        fg=self.colors['text_primary'], 
                        bg=self.colors['bg_medium'],
                        padx=12, pady=8)
        label.pack()
        
        notification.attributes('-alpha', 0.0)
        
        def fade_in(alpha=0.0):
            if alpha < 0.95:
                alpha += 0.1
                notification.attributes('-alpha', alpha)
                notification.after(30, lambda: fade_in(alpha))
            else:
                notification.after(duration, fade_out)
        
        def fade_out(alpha=0.95):
            if alpha > 0.0:
                alpha -= 0.1
                notification.attributes('-alpha', alpha)
                notification.after(30, lambda: fade_out(alpha))
            else:
                notification.destroy()
        
        fade_in()

    def save_interval_setting(self):
        try:
            settings = self.load_settings_data()
            settings['update_interval'] = self.update_interval_index
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass

    def load_settings_data(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}

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

    def optimize_network_latency(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("ОПТИМИЗАЦИЯ СЕТИ")
        self.log_to_diagnostic("="*50)
        
        if not is_admin():
            self.log_to_diagnostic("ОШИБКА: Требуются права администратора!")
            messagebox.showerror("Ошибка", "Для оптимизации сети требуются права администратора!")
            return
        
        self.log_to_diagnostic("Настройка TCP параметров...")
        success, msg = optimize_network_latency()
        
        if success:
            self.log_to_diagnostic(msg)
            self.log_to_diagnostic("Оптимизация завершена")
            messagebox.showinfo("Успех", "Сетевые параметры оптимизированы!\n\nПерезагрузите компьютер для применения изменений")
        else:
            self.log_to_diagnostic(f"Ошибка: {msg}")
            messagebox.showerror("Ошибка", msg)
        
        self.log_to_diagnostic("="*50)


    def find_and_set_best_dns(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("ПОИСК ЛУЧШЕГО DNS СЕРВЕРА")
        self.log_to_diagnostic("="*50)
        
        self.log_to_diagnostic("Тестирование DNS серверов...")
        self.update_status("Поиск DNS...", self.colors['accent'])
        self.root.update()
        
        def find_dns_thread():
            try:
                primary, secondary, latency, name = find_best_dns()
                
                self.log_to_diagnostic(f"Установлен подходящий DNS: {name}")
                self.log_to_diagnostic(f"Primary: {primary} (задержка: {latency:.1f} мс)")
                self.log_to_diagnostic(f"Secondary: {secondary}")
                
                if not is_admin():
                    self.log_to_diagnostic("ОШИБКА: Требуются права администратора!")
                    self.root.after(0, lambda: messagebox.showerror("Ошибка", "Для установки DNS требуются права администратора!"))
                    self.root.after(0, lambda: self.update_status("Готов к работе"))
                    return
                
                success, msg = set_dns_windows(primary, secondary)
                
                if not success:
                    adapters = list_network_adapters()
                    if adapters:
                        self.root.after(0, lambda: self.show_adapter_selector(primary, secondary, name, adapters))
                    else:
                        self.log_to_diagnostic(f"{msg}")
                        self.root.after(0, lambda: messagebox.showerror("Ошибка", msg))
                else:
                    self.log_to_diagnostic(f"{msg}")
                    self.root.after(0, lambda: messagebox.showinfo("Успех", 
                        f"Установлен DNS: {name}\n\n"
                        f"Primary: {primary}\n"
                        f"Secondary: {secondary}\n"
                        f"Задержка: {latency:.1f} мс"))
                
                self.root.after(0, lambda: self.update_status("Готов к работе"))
                self.log_to_diagnostic("="*50)
                
            except Exception as e:
                self.log_to_diagnostic(f"Ошибка: {str(e)}")
                self.root.after(0, lambda: self.update_status("Готов к работе"))
        
        threading.Thread(target=find_dns_thread, daemon=True).start()


    def show_adapter_selector(self, primary, secondary, dns_name, adapters):
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Выбор сетевого адаптера")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Выберите сетевой адаптер:", font=("Segoe UI", 12),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(15, 10))
        
        listbox = tk.Listbox(dialog, height=8, font=("Segoe UI", 10),
                            bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                            selectbackground=self.colors['accent'])
        listbox.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        
        for adapter in adapters:
            listbox.insert(tk.END, adapter)
        
        def apply():
            selection = listbox.curselection()
            if not selection:
                return
            adapter = adapters[selection[0]]
            
            success, msg = set_dns_manual(primary, secondary, adapter)
            if success:
                messagebox.showinfo("Успех", f"DNS установлен для адаптера {adapter}")
                self.log_to_diagnostic(f"DNS установлен для адаптера {adapter}")
            else:
                messagebox.showerror("Ошибка", msg)
                self.log_to_diagnostic(f"{msg}")
            
            dialog.destroy()
        
        button_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        button_frame.pack(pady=15)
        
        apply_btn = RoundedButton(button_frame, text="Применить", command=apply,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI", 10))
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(button_frame, text="Отмена", command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI", 10))
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def flush_dns_cache_command(self):
        self.log_to_diagnostic("Очистка DNS кеша...")
        success, msg = flush_dns_cache()
        if success:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showinfo("Успех", msg)
        else:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showerror("Ошибка", msg)


    def restore_network_defaults_command(self):
        self.log_to_diagnostic("Восстановление стандартных настроек сети...")
        if not is_admin():
            messagebox.showerror("Ошибка", "Требуются права администратора!")
            return
        
        success, msg = restore_network_defaults()
        if success:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showinfo("Успех", msg)
        else:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showerror("Ошибка", msg)

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
                "WinDivert.dll",
                "WinDivert64.sys",
                "general.bat"
            ]
            
            bin_dir = ZAPRET_CORE_DIR / "bin"
            for file in zapret_files:
                if file == "general.bat":
                    file_path = ZAPRET_CORE_DIR / file
                else:
                    file_path = bin_dir / file
                
                if file_path.exists():
                    size = file_path.stat().st_size
                    self.log_to_diagnostic(f"  {file} - {size} байт")
                else:
                    self.log_to_diagnostic(f"  {file} - отсутствует")
                    errors.append(f"{file} отсутствует")
            
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
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, "ZapretLauncher", 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, "ZapretLauncher")
                    except:
                        pass
            return True
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка настройки автозапуска: {e}")
            return False

    def check_autostart_status(self):
        try:
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
            self.log_to_diagnostic(f"\Подходящая стратегия: {best_strategy}")
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
            self.log_to_diagnostic(f"Zapret запущен (Стратегия: {self.current_strategy or 'неизвестно'})")
        else:
            self.log_to_diagnostic("Zapret не запущен")

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
            self.log_to_diagnostic(f"ByeDPI запущен (провайдер: {self.current_provider})")
        else:
            if status['binary_exists']:
                self.log_to_diagnostic("ByeDPI не запущен (файл есть)")
            else:
                self.log_to_diagnostic("ByeDPI не установлен (нет ciadpi.exe)")

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

    def restart_tgproxy(self):
        self.log_to_diagnostic("Перезапуск TGProxy...")
        if self.tg_proxy._running:
            self.tg_proxy.stop()
            time.sleep(1)
            self.tg_proxy.start()
            self.log_to_diagnostic("TGProxy перезапущен")
        else:
            self.log_to_diagnostic("TGProxy не был запущен")

    def open_appdata_folder(self):
        self.log_to_diagnostic(f"Открытие папки: AppData/Local/ZapretLauncher")
        try:
            os.startfile(APPDATA_DIR)
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def get_current_dns_info(self):
        result = []
        try:
            result_nslookup = subprocess.run(
                ['nslookup', 'google.com'],
                capture_output=True, text=True, encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            
            for line in result_nslookup.stdout.split('\n'):
                if 'Server:' in line or 'Сервер:' in line:
                    server = line.split(':')[1].strip()
                    if server:
                        result.append(f"  DNS сервер: {server}")
                        break
            
            if not result:
                result_ipconfig = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True, text=True, encoding='cp866',
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                
                for line in result_ipconfig.stdout.split('\n'):
                    if 'DNS-серверы' in line or 'DNS Servers' in line:
                        ips = re.findall(r'\d+\.\d+\.\d+\.\d+', line)
                        for ip in ips:
                            if ip not in ['0.0.0.0', '127.0.0.1']:
                                result.append(f"  DNS сервер: {ip}")
                                break
                        if result:
                            break
            
            if not result:
                result.append("  DNS сервер не определен (используется автоматический)")
                
        except Exception as e:
            result.append(f"  Ошибка: {e}")
        return result

    def clear_cache(self):
        self.log_to_diagnostic("Очистка кеша...")
        try:
            self.diagnostic_text.delete(1.0, tk.END)
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка: {str(e)}")

    def run_full_diagnostic(self):
        self.diagnostic_text.delete(1.0, tk.END)
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic("ПОЛНАЯ ДИАГНОСТИКА")
        self.log_to_diagnostic("="*50)
        
        if is_admin():
            self.log_to_diagnostic("Права администратора: есть")
        else:
            self.log_to_diagnostic("Права администратора: нет")
        self.log_to_diagnostic("")
        
        self.log_to_diagnostic(f"Версия лаунчера: {CURRENT_VERSION}")
        self.log_to_diagnostic("")
        
        self.log_to_diagnostic("Текущие DNS серверы:")
        dns_info = self.get_current_dns_info()
        for line in dns_info:
            self.log_to_diagnostic(line)
        self.log_to_diagnostic("")
        
        self.check_ping_google()
        self.check_ping_youtube()
        self.log_to_diagnostic("")
        
        self.check_zapret_status()
        self.check_zapret_logs()
        self.log_to_diagnostic("")
        
        self.check_byedpi_status()
        self.log_to_diagnostic("")
        
        self.check_tgproxy_status()
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

    def refresh_page(self, page_name):
        page = getattr(self, f"{page_name}_page")
        page.configure(bg=self.colors['bg_dark'])
        
        for widget in page.winfo_children():
            self.update_widget_colors(widget)
        
        if page_name == 'diagnostic' and hasattr(self, 'diagnostic_text'):
            self.diagnostic_text.configure(bg=self.colors['bg_dark'], fg=self.colors['text_primary'])

    def update_widget_colors(self, widget):
        try:
            widget_type = type(widget)
            
            if widget_type == tk.Frame:
                widget.configure(bg=self.colors['bg_dark'])
            elif widget_type == tk.Label:
                current_fg = widget.cget('fg')
                accent_colors = [self.colors['accent'], self.colors['accent_green'], 
                            self.colors['accent_red'], self.colors['accent_hover']]
                if current_fg and current_fg not in accent_colors:
                    widget.configure(fg=self.colors['text_secondary'])
                widget.configure(bg=self.colors['bg_dark'])
            elif widget_type == tk.Canvas:
                widget.configure(bg=self.colors['bg_dark'])
            elif widget_type == ttk.Combobox:
                widget.configure(background=self.colors['bg_light'])
            elif widget_type == tk.Text:
                widget.configure(bg=self.colors['bg_dark'], fg=self.colors['text_primary'])
            elif hasattr(widget, 'update_colors'):
                widget.update_colors(self.colors['button_bg'], self.colors['text_secondary'], self.colors['accent_hover'])
            elif hasattr(widget, 'configure') and 'bg' in widget.keys():
                try:
                    widget.configure(bg=self.colors['bg_dark'])
                except:
                    pass
            
            for child in widget.winfo_children():
                self.update_widget_colors(child)
        except Exception as e:
            pass

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

    def check_launcher_updates(self, parent, silent=False):
        return check_launcher_updates(parent, silent)
    
    def check_zapret_updates(self, parent, silent=False):
        return check_zapret_updates(parent, silent)

    def update_status(self, text, color=None):
        if color is None:
            color = self.colors['accent_green'] if self.is_connected else self.colors['text_secondary']
        
        self.main_status.config(text=text, fg=color)
        self.left_status.config(fg=color)

    def update_ui_state(self):
        if self.is_connected:
            self.connect_btn.set_text("ОТКЛЮЧИТЬСЯ")
            self.connect_btn.normal_color = self.colors['bg_light']
            self.connect_btn.hover_color = '#6c5579'
            self.connect_btn.itemconfig(self.connect_btn.rect, fill=self.colors['bg_light'])
        else:
            self.connect_btn.set_text("ПОДКЛЮЧИТЬСЯ")
            self.connect_btn.normal_color = '#6c5579'
            self.connect_btn.hover_color = '#3D3D45'
            self.connect_btn.itemconfig(self.connect_btn.rect, fill='#6c5579')
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.update_menu()

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.show_mode_selector()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.update_menu()

    def connect(self):
        strategy = self.strategy_var.get()
        if not strategy:
            messagebox.showerror("Ошибка", "Выберите стратегию")
            return
        
        self._reset_traffic_history()

        self.update_status("Запуск...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        success, msg = self.zapret.run_strategy(strategy)
        
        if success:
            self.current_strategy = strategy
            self.is_connected = True
            
            self.stats.start_session()
            
            self.update_status(f"Подключено: Стратегия {self.zapret.get_strategy_display_name(strategy)}", 
                            self.colors['accent_green'])
            self.update_ui_state()
            self.save_settings()
            
            self.start_stats_monitoring()
            
            self.root.after(100, self.update_stats_display)
            
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
                self.byedpi_enabled = False
                self.byedpi_var.set(False)
            
            time.sleep(2)
            
            self.tg_proxy._kill_process_on_port(1080)
            
            self.byedpi.base._kill_process_on_port(10801)
            
            self._stop_windivert_service()
            self.stats.end_session()
            
            self.root.after(0, self.finish_disconnect)
        
        threading.Thread(target=stop_all, daemon=True).start()

    def finish_disconnect(self):
        self._cached_processes = []
        self.is_connected = False
        self.current_strategy = None
        self.mode_label.config(text="Не выбран", fg=self.colors['text_secondary'])
        self.update_status("Готов к работе", self.colors['text_secondary'])
        self.update_ui_state()
        self.connect_btn.set_enabled(True)

        if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
            try:
                self.root.after_cancel(self._traffic_update_timer)
            except:
                pass
            self._traffic_update_timer = None

        self.traffic_history = {}
        self.traffic_history_vpn = {}
        self.traffic_history_direct = {}
        self.traffic_speed_history = {}
        self.traffic_speed_vpn_history = {}
        self.traffic_speed_direct_history = {}
        self.traffic_last_update = time.time()
        self._traffic_collecting = False
        self._traffic_update_scheduled = False
        self.hostname_cache = {}
        self.hostname_cache_time = {}

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

    def _stop_windivert_service(self):
        try:
            result = subprocess.run(
                ['sc', 'query', 'WinDivert'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            
            if 'RUNNING' in result.stdout:
                subprocess.run(
                    ['sc', 'stop', 'WinDivert'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                
                time.sleep(2)
                
                verify = subprocess.run(
                    ['sc', 'query', 'WinDivert'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                
                return 'RUNNING' not in verify.stdout
            else:
                return True   
        except (subprocess.TimeoutExpired, Exception):
            return False

    def load_settings(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    saved_strategy = data.get('current_strategy')
                    if saved_strategy and saved_strategy in self.zapret.available_strategies:
                        self.current_strategy = saved_strategy
                    self.current_provider = data.get('byedpi_provider', 'Ростелеком/Дом.ru/Tele2')
                    self.provider_var.set(self.current_provider)
                    self.byedpi.set_provider(self.current_provider)
                    
                    autostart_enabled = data.get('autostart_enabled', False)
                    if autostart_enabled != self.check_autostart_status():
                        self.set_autostart(autostart_enabled)

                    interval_index = data.get('update_interval', 0)
                    if 0 <= interval_index < len(self.update_intervals):
                        self.update_interval_index = interval_index
                        self.update_interval = self.update_intervals[self.update_interval_index]
                        
                        if self.update_interval is None:
                            self.stop_stats_monitoring()

                    self._tg_instruction = data.get('tg_instruction', False)
        except:
            pass

    def save_settings(self):
        try:
            settings = {
                'current_strategy': self.current_strategy,
                'byedpi_provider': self.current_provider,
                'autostart_enabled': self.check_autostart_status(),
                'update_interval': self.update_interval_index,
                'tg_instruction': getattr(self, '_tg_instruction', False)
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass

    def show_main_page(self):
        self.pages.show_page("main")
        
    def show_service_page(self):
        self.pages.show_page("service")
        
    def show_lists_page(self):
        self.pages.show_page("lists")

    def show_diagnostic_page(self):
        self.pages.show_page("diagnostic")

    def show_settings_page(self):
        self.pages.show_page("settings")

    def show_traffic_page(self):
        self.pages.show_page("traffic")
        self._cached_processes = []
        if hasattr(self, '_traffic_collecting'):
            self._traffic_collecting = False
        if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
            try:
                self.root.after_cancel(self._traffic_update_timer)
            except:
                pass
        self.update_traffic_table()

    def _reset_traffic_history(self):
        self.traffic_history = {}
        self.traffic_history_vpn = {}
        self.traffic_history_direct = {}
        self.traffic_speed_history = {}
        self.traffic_speed_vpn_history = {}
        self.traffic_speed_direct_history = {}
        self.traffic_last_update = time.time()
    
    def get_process_traffic(self):
        processes = []
        current_time = time.time()
        time_diff = current_time - self.traffic_last_update

        if hasattr(self, '_cached_processes') and (current_time - self._last_process_time < 0.5):
            return self._cached_processes
        
        if time_diff < 0.1:
            time_diff = 0.5
        elif time_diff > 5:
            time_diff = 5
        
        self.traffic_last_update = current_time
        
        try:
            connections = psutil.net_connections(kind='inet')
            
            pid_counts = {}
            pid_hosts = {}
            
            for conn in connections:
                if conn.pid and conn.pid > 0:
                    pid_counts[conn.pid] = pid_counts.get(conn.pid, 0) + 1
                    
                    if conn.raddr and conn.raddr.ip and conn.raddr.port:
                        remote_ip = conn.raddr.ip
                        if remote_ip not in ['127.0.0.1', '0.0.0.0', '::1']:
                            if conn.pid not in pid_hosts:
                                pid_hosts[conn.pid] = {}
                            pid_hosts[conn.pid][remote_ip] = pid_hosts[conn.pid].get(remote_ip, 0) + 1
            
            top_pids = sorted(pid_counts.items(), key=lambda x: x[1], reverse=True)[:50]
            top_pids_set = {pid for pid, _ in top_pids}
            
            vpn_ports = {1080, 10801}
            vpn_connections = {}
            
            for conn in connections:
                if conn.pid and conn.pid in top_pids_set:
                    is_vpn = False
                    if conn.raddr and conn.raddr.port in vpn_ports:
                        is_vpn = True
                    elif conn.laddr and conn.laddr.port in vpn_ports:
                        is_vpn = True
                    
                    if is_vpn:
                        if conn.pid not in vpn_connections:
                            vpn_connections[conn.pid] = []
                        vpn_connections[conn.pid].append(conn)
            
            proc_data = {}
            
            for pid in top_pids_set:
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    
                    if proc_name not in proc_data:
                        try:
                            if hasattr(proc, 'io_counters'):
                                net_io = proc.io_counters()
                            elif hasattr(proc, 'net_io_counters'):
                                net_io = proc.net_io_counters()
                            else:
                                net_io = None
                            
                            if net_io:
                                bytes_sent = net_io.write_bytes if hasattr(net_io, 'write_bytes') else 0
                                bytes_recv = net_io.read_bytes if hasattr(net_io, 'read_bytes') else 0
                            else:
                                bytes_sent = 0
                                bytes_recv = 0
                        except:
                            bytes_sent = 0
                            bytes_recv = 0
                        
                        main_host = ''
                        if pid in pid_hosts and pid_hosts[pid]:
                            top_ip = max(pid_hosts[pid].items(), key=lambda x: x[1])[0]
                            main_host = self._get_hostname(top_ip)
                        
                        proc_data[proc_name] = {
                            'name': proc_name,
                            'connections': pid_counts.get(pid, 0),
                            'bytes_sent': bytes_sent,
                            'bytes_recv': bytes_recv,
                            'host': main_host,
                            'pid': pid
                        }
                    
                    if pid in vpn_connections:
                        proc_data[proc_name]['vpn_connections'] = proc_data[proc_name].get('vpn_connections', 0) + len(vpn_connections[pid])
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            for proc_name, data in proc_data.items():
                total_connections = data['connections']
                vpn_conn_count = data.get('vpn_connections', 0)
                direct_conn_count = total_connections - vpn_conn_count
                
                total_bytes = data['bytes_sent'] + data['bytes_recv']
                
                if total_connections > 0 and total_bytes > 0:
                    vpn_bytes = int(total_bytes * vpn_conn_count / total_connections)
                    direct_bytes = total_bytes - vpn_bytes
                else:
                    vpn_bytes = 0
                    direct_bytes = 0
                
                speed = 0
                if proc_name in self.traffic_history:
                    prev_total = self.traffic_history[proc_name]
                    if time_diff > 0 and total_bytes >= prev_total:
                        raw_speed = (total_bytes - prev_total) / time_diff
                        raw_speed = max(0, raw_speed)
                        
                        raw_speed = min(raw_speed, 100 * 1024 * 1024)
                        
                        if proc_name in self.traffic_speed_history:
                            speed = self.traffic_speed_history[proc_name] * 0.7 + raw_speed * 0.3
                        else:
                            speed = raw_speed
                        
                        self.traffic_speed_history[proc_name] = speed
                else:
                    speed = 0
                    if proc_name not in self.traffic_speed_history:
                        self.traffic_speed_history[proc_name] = 0
                
                speed_vpn = 0
                speed_direct = 0
                
                if proc_name in self.traffic_history_vpn:
                    prev_vpn = self.traffic_history_vpn[proc_name]
                    if time_diff > 0 and vpn_bytes >= prev_vpn:
                        raw_speed_vpn = (vpn_bytes - prev_vpn) / time_diff
                        raw_speed_vpn = max(0, min(raw_speed_vpn, 100 * 1024 * 1024))
                        
                        if proc_name in self.traffic_speed_vpn_history:
                            speed_vpn = self.traffic_speed_vpn_history[proc_name] * 0.7 + raw_speed_vpn * 0.3
                        else:
                            speed_vpn = raw_speed_vpn
                        
                        self.traffic_speed_vpn_history[proc_name] = speed_vpn
                
                if proc_name in self.traffic_history_direct:
                    prev_direct = self.traffic_history_direct[proc_name]
                    if time_diff > 0 and direct_bytes >= prev_direct:
                        raw_speed_direct = (direct_bytes - prev_direct) / time_diff
                        raw_speed_direct = max(0, min(raw_speed_direct, 100 * 1024 * 1024))
                        
                        if proc_name in self.traffic_speed_direct_history:
                            speed_direct = self.traffic_speed_direct_history[proc_name] * 0.7 + raw_speed_direct * 0.3
                        else:
                            speed_direct = raw_speed_direct
                        
                        self.traffic_speed_direct_history[proc_name] = speed_direct
                
                self.traffic_history[proc_name] = total_bytes
                self.traffic_history_vpn[proc_name] = vpn_bytes
                self.traffic_history_direct[proc_name] = direct_bytes
                
                vpn_display = self._format_speed(speed_vpn) if speed_vpn > 0 else '-'
                direct_display = self._format_speed(speed_direct) if speed_direct > 0 else '-'
                
                processes.append({
                    'name': proc_name[:35],
                    'speed': self._format_speed(speed),
                    'vpn': vpn_display,
                    'direct': direct_display,
                    'connections': data['connections'],
                    'host': data['host'][:40] if data['host'] else '',
                    'total': self._format_bytes(total_bytes)
                })
            
            processes.sort(key=lambda x: (x['connections'], self._parse_speed_value(x['speed'])), reverse=True)
            processes = processes[:50]
            
        except Exception as e:
            self.log_to_diagnostic(f"Ошибка сбора трафика: {e}")
        
        if not processes:
            processes.append({
                'name': 'Нет активных соединений',
                'speed': '-',
                'vpn': '-',
                'direct': '-',
                'connections': 0,
                'host': '',
                'total': '-'
            })
        self._cached_processes = processes
        self._last_process_time = current_time
        return processes

    def _parse_speed_value(self, speed_str):
        if speed_str == '-' or not speed_str:
            return 0
        try:
            if 'KB/s' in speed_str:
                return float(speed_str.replace(' KB/s', '')) * 1024
            elif 'MB/s' in speed_str:
                return float(speed_str.replace(' MB/s', '')) * 1024 * 1024
            elif 'B/s' in speed_str:
                return float(speed_str.replace(' B/s', ''))
        except:
            pass
        return 0
    
    def _format_bytes(self, bytes_val):
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
    
    def _format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"

    def _get_hostname(self, ip):
        if not ip or ip in ['127.0.0.1', '0.0.0.0', '::1']:
            return ip
        
        current_time = time.time()
        
        if ip in self.hostname_cache and (current_time - self.hostname_cache_time.get(ip, 0)) < 300:
            return self.hostname_cache[ip]
        
        try:
            socket.setdefaulttimeout(1)
            hostname = socket.gethostbyaddr(ip)[0]
            if len(hostname) > 40:
                hostname = hostname[:37] + '...'
            self.hostname_cache[ip] = hostname
            self.hostname_cache_time[ip] = current_time
            return hostname
        except (socket.herror, socket.gaierror, socket.timeout):
            self.hostname_cache[ip] = ip
            self.hostname_cache_time[ip] = current_time
            return ip
        except Exception:
            return ip
        finally:
            socket.setdefaulttimeout(None)

    def update_traffic_table(self):
        if self.update_interval is None:
            return
    
        if self.pages.current_page != "traffic":
            self._schedule_next_traffic_update()
            return
        
        if hasattr(self, '_traffic_collecting') and self._traffic_collecting:
            if time.time() - self._traffic_collecting_start > 5:
                self._traffic_collecting = False
                self._traffic_collecting_start = 0
            else:
                self._schedule_next_traffic_update()
                return
        
        self._traffic_collecting = True
        self._traffic_collecting_start = time.time()
        
        def collect_data():
            try:
                processes = self.get_process_traffic()
                self.root.after(0, lambda: self._update_traffic_table_ui(processes))
            finally:
                self._traffic_collecting = False
                self.root.after(0, self._schedule_next_traffic_update)
        
        threading.Thread(target=collect_data, daemon=True).start()

    def _schedule_next_traffic_update(self):
        if self.update_interval is None:
            return
        
        if self.update_interval == 0:
            interval_ms = 500
        else:
            interval_ms = int(self.update_interval * 1000)
        
        if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
            try:
                self.root.after_cancel(self._traffic_update_timer)
            except:
                pass
        
        self._traffic_update_timer = self.root.after(interval_ms, self.update_traffic_table)

    def _schedule_traffic_update(self):
        self._schedule_next_traffic_update()

    def _update_traffic_table_ui(self, processes):
        for item in self.pages.traffic_tree.get_children():
            self.pages.traffic_tree.delete(item)
        
        for proc in processes:
            speed_display = proc['speed'] if proc['speed'] != '-' else '-'
            
            self.pages.traffic_tree.insert("", "end", values=(
                proc['name'],
                speed_display,
                proc['vpn'],
                proc['direct'],
                str(proc['connections']) if proc['connections'] > 0 else '-',
                proc['host'],
                proc['total']
            ))

    def setup_scrollbar_style(self):
        style = ttk.Style()
        style.theme_use('default')
        
        style.configure(
            "Custom.Vertical.TScrollbar",
            background=self.colors['bg_light'],
            troughcolor=self.colors['bg_dark'],
            bordercolor=self.colors['bg_dark'],
            arrowcolor=self.colors['text_secondary'],
            lightcolor=self.colors['bg_light'],
            darkcolor=self.colors['bg_light'],
            relief="flat"
        )
        
        style.map(
            "Custom.Vertical.TScrollbar",
            background=[
                ('pressed', self.colors['accent']),
                ('active', self.colors['accent_hover']),
                ('!active', self.colors['bg_light'])
            ],
            arrowcolor=[
                ('pressed', self.colors['text_primary']),
                ('active', self.colors['text_primary']),
                ('!active', self.colors['text_secondary'])
            ]
        )
        
        style.configure(
            "Custom.Horizontal.TScrollbar",
            background=self.colors['bg_light'],
            troughcolor=self.colors['bg_dark'],
            bordercolor=self.colors['bg_dark'],
            arrowcolor=self.colors['text_secondary'],
            lightcolor=self.colors['bg_light'],
            darkcolor=self.colors['bg_light'],
            relief="flat"
        )
        
        style.map(
            "Custom.Horizontal.TScrollbar",
            background=[
                ('pressed', self.colors['accent']),
                ('active', self.colors['accent_hover']),
                ('!active', self.colors['bg_light'])
            ],
            arrowcolor=[
                ('pressed', self.colors['text_primary']),
                ('active', self.colors['text_primary']),
                ('!active', self.colors['text_secondary'])
            ]
        )

    def show_tg_proxy_instruction(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Telegram Proxy (ZL)")
        dialog.geometry("500x580")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 260
        dialog.geometry(f"+{x}+{y}")
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(20, 5))
        
        title_label = tk.Label(title_frame, text="Настройка Telegram", 
                            font=("Segoe UI", 20, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Для использования TG Proxy выполните следующие шаги:",
                                font=("Segoe UI", 11),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        subtitle_label.pack(pady=(5, 0))
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=2)
        separator.pack(fill=tk.X, padx=30, pady=10)
        instruction_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        instruction_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        steps = [
            ("1.", "Откройте Telegram и перейдите в"),
            ("", "Настройки —> Продвинутые настройки"),
            ("2.", "В разделе «Тип соединения» выберите"),
            ("", "«Использовать собственный прокси»"),
            ("3.", "Заполните поля прокси:"),
            ("", "Тип: SOCKS5"),
            ("", "Хост: 127.0.0.1"),
            ("", "Порт: 1080"),
            ("4.", "Нажмите «Сохранить» и пользуйтесь.")
        ]
        
        current_step = 0
        
        for i, step in enumerate(steps):
            text, desc = step
            if text:
                step_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                step_frame.pack(fill=tk.X, pady=(10 if current_step > 0 else 0, 2))
                
                step_num = tk.Label(step_frame, text=text, font=("Segoe UI", 13, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                step_num.pack(side=tk.LEFT)
                
                step_text = tk.Label(step_frame, text=desc, font=("Segoe UI", 11),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                step_text.pack(side=tk.LEFT, padx=(5, 0))
                current_step += 1
            else:
                sub_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                sub_frame.pack(fill=tk.X, pady=1)
                
                spacer = tk.Label(sub_frame, text="   ", font=("Segoe UI", 11),
                                fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                spacer.pack(side=tk.LEFT)
                
                bullet = tk.Label(sub_frame, text="▸", font=("Segoe UI", 10),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                bullet.pack(side=tk.LEFT, padx=(10, 5))
                
                sub_text = tk.Label(sub_frame, text=desc, font=("Segoe UI", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
                sub_text.pack(side=tk.LEFT)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=30, pady=15)
        dont_show_var = tk.BooleanVar(value=False)
        
        dont_show_cb = tk.Checkbutton(
            bottom_frame,
            text="Больше не показывать",
            variable=dont_show_var,
            bg=self.colors['bg_medium'],
            fg=self.colors['text_secondary'],
            selectcolor=self.colors['bg_medium'],
            activebackground=self.colors['bg_medium'],
            activeforeground=self.colors['text_secondary'],
            highlightthickness=0,
            bd=0,
            padx=0,
            font=("Segoe UI", 10)
        )
        dont_show_cb.pack(side=tk.LEFT)
        
        buttons_frame = tk.Frame(bottom_frame, bg=self.colors['bg_medium'])
        buttons_frame.pack(side=tk.RIGHT)
        
        start_btn = RoundedButton(
            buttons_frame,
            text="Запустить",
            command=lambda: self._start_tg_proxy_mode(dialog, dont_show_var.get()),
            width=100, height=35,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI", 10, "bold"),
            corner_radius=8
        )
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(
            buttons_frame,
            text="Отмена",
            command=lambda: self._cancel_tg_proxy_mode(dialog, dont_show_var.get()),
            width=100, height=35,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Segoe UI", 10),
            corner_radius=8
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        start_btn.config(cursor="hand2")
        cancel_btn.config(cursor="hand2")
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

    def _start_tg_proxy_mode(self, dialog, dont_show=False):
        if dialog:
            dialog.destroy()
        
        if dont_show:
            self._tg_instruction = True
        
        self._reset_traffic_history()
        self.update_status("Запуск TG Proxy...", self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        self.tg_proxy.start()
        
        self.is_connected = True
        self.stats.start_session()
        self.start_stats_monitoring()
        
        mode_name = "TG Proxy"
        self.mode_label.config(text=mode_name, fg=self.colors['accent_green'])
        self.update_status(f"Подключено: {mode_name}", self.colors['accent_green'])
        self.update_ui_state()
        self.save_settings()
        self.root.after(100, self.update_stats_display)
        self.connect_btn.set_enabled(True)

    def _cancel_tg_proxy_mode(self, dialog, dont_show=False):
        if dialog:
            dialog.destroy()
        
        if dont_show:
            self._tg_instruction = True
            self.save_settings()
        
        self.update_status("Готов к работе", self.colors['text_secondary'])
        self.connect_btn.set_enabled(True)

if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretLauncher(root)
    root.mainloop()
