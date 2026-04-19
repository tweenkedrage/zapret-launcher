import tkinter as tk
from tkinter import messagebox, ttk
from gui.pages import Pages, check_zapret_folder
from gui.tray import ModernSystemTray
from utils.languages import tr, get_languages
from typing import List, Optional
from gui.theme import get_theme
from tg_proxy import run_proxy
from utils.updater import check_launcher_updates, check_zapret_updates
from utils.network_set import (
    optimize_network_latency,
    find_best_dns,
    set_dns_windows,
    flush_dns_cache,
    restore_network_defaults,
    list_network_adapters,
    set_dns_manual
)
from gui.widgets import RoundedButton
try:
    from tg_proxy import run_proxy_server
    TG_PROXY_AVAILABLE = True
except ImportError:
    TG_PROXY_AVAILABLE = False
import subprocess
import os
import json
import time
import threading
import webbrowser
import asyncio
import zipfile
import psutil
import socket
import winreg
from pathlib import Path
import sys
import re
import ctypes
from ctypes import windll, byref, c_int
from typing import Optional, List, Tuple

BASE_DIR = Path(__file__).parent

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'Zapret Launcher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
ICON_PATH = BASE_DIR / "resources" / "icon.ico"
ICON_PNG_PATH = BASE_DIR / "resources" / "icon.png"
ZAPRET_RESOURCES_ZIP = "zapret_resources.zip"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

LAUNCHER_API_URL = "https://api.github.com/repos/tweenkedrage/zapret-launcher/releases/latest"
ZAPRET_API_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"
CURRENT_VERSION = "3.1b"

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

class StatsMonitor:
    def __init__(self):
        self.session_start = None
        self.total_up_bytes = 0
        self.total_down_bytes = 0
        self.connection_count = 0
        self.disconnection_count = 0
        self.is_monitoring = False
        self._monitor_thread = None
        self._cache_duration = 3.0
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
        if hasattr(self, '_cached_stats') and current_time - self._cached_time < self._cache_duration:
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
        self._running = False
        self._port = 1080
        self._host = '127.0.0.1'
        self._secret = None
        self._stop_event = None

    def set_secret(self, secret):
        self._secret = secret
        if self._running:
            self.stop()
            time.sleep(1)
            self.start()
    
    def _is_port_open(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            result = sock.connect_ex((self._host, port))
            return result == 0
        finally:
            sock.close()
    
    def wait_for_start(self, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_port_open(1080):
                return True
            time.sleep(0.2)
        return False
    
    def start(self):
        if self._running:
            self.stop()
            time.sleep(1)

        self._stop_event = None
        
        def run_tg_proxy():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._stop_event = asyncio.Event()
                run_proxy(self._host, self._port, self._secret, self._stop_event)
            except Exception as e:
                print(f"TGProxy error: {e}")

        self._thread = threading.Thread(target=run_tg_proxy, daemon=True)
        self._thread.start()
        
        if self.wait_for_start(10):
            self._running = True
            return True
        return False
    
    def stop(self):
        if not self._running and not self._thread:
            return
        
        self._running = False
        
        if self._stop_event:
            try:
                self._stop_event.set()
            except Exception as e:
                print(f"Error setting stop event: {e}")
            self._stop_event = None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((self._host, self._port))
            sock.close()
        except Exception:
            pass
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                try:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(self._thread.ident), 
                        ctypes.py_object(SystemExit)
                    )
                except:
                    pass
                self._thread.join(timeout=1)
        
        self._thread = None
        print("Telegram Proxy stopped")

    @property
    def is_running(self):
        return self._running and self._is_port_open(1080)
    
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
                tr('error_zapret_folder'), 
                f"{tr('error_zapret_folder')}\n"
                f"Resource file not found {ZAPRET_RESOURCES_ZIP}\n"
                "Start build_resources.py"
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
            messagebox.showerror(tr('error_zapret_folder'), f"Failed to unpack resources: {e}")
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
            return False, tr('error_admin_required')
            
        if not check_zapret_folder():
            return False, tr('error_zapret_folder')

        strategy_path = self.zapret_dir / strategy_name
        if not strategy_path.exists():
            return False, f"{tr('error_strategy_not_found')} {strategy_name}"
            
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
            
            time.sleep(3.0)
            for _ in range(10):
                if self.is_winws_running():
                    return True, f"{tr('status_strategy_started')}: {self.get_strategy_display_name(strategy_name)}"
                time.sleep(0.5)
            return False, tr('error_winws_not_found')
        except Exception as e:
            return False, f"{tr('error_startup')}: {str(e)}"
            
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
            return True, f"Game Filter: {tr('status_enabled') if self.game_filter_enabled else tr('status_disabled')}"
            
        elif command == "ipset_filter":
            modes = ["none", "loaded", "any"]
            current_idx = modes.index(self.ipset_filter_mode)
            self.ipset_filter_mode = modes[(current_idx + 1) % 3]
            return True, f"IPSet Filter: {self.ipset_filter_mode}"
        return False, f"{tr('error_unknown_command')}: {command}"

class ZapretLauncher:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(False)
        self.root.attributes('-toolwindow', False)

        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            
            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            current_style = current_style & ~WS_EX_TOOLWINDOW
            current_style = current_style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001)
            self.root.title("Zapret Launcher")
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetWindowTextW(hwnd, "Zapret Launcher")
        except Exception:
            pass

        self.stats = StatsMonitor()
        self.stats_update_id = None
        self._pending_mode = None

        self.mode_label = None
        self.connect_btn = None
        self.main_status = None
        self.diagnostic_text = None
        self.stats_frame = None
        self.stats_time_label = None
        self.stats_traffic_label = None
        self.stats_total_label = None
        self.stats_speed_up_label = None
        self.stats_speed_down_label = None
        self.stats_rtt_label = None

        self._shutdown_update_timer = None
        self._shutdown_first_update_done = False

        self.strategy_var = tk.StringVar()
        self.tgws_var = tk.BooleanVar(value=False)

        self._tg_instruction = False
        self._tg_secret = None

        self._notification_queue = []
        self._notification_active = False

        self.update_intervals = [0, 5, 10, 30, 60, None]
        self.update_interval_index = 0
        self.update_interval = self.update_intervals[self.update_interval_index]
        self.update_timer_id = None

        self.rtt_timer_id = None
        self.rtt_update_interval = 10000

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

        self._cached_processes = []
        self._last_process_time = 0
        self.hostname_cache_maxsize = 100
        self.traffic_history_maxsize = 50

        self.dns_cache_ttl = 240

        try:
            icon_paths = [
                BASE_DIR / "resources" / "icon.ico",
                BASE_DIR / "resources" / "icon.png",
                Path("resources/icon.ico"),
                Path("icon.ico"),
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
        except Exception:
                    pass
        
        self.window_width = 1200
        self.window_height = 800
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        self.center_window()
        self.root.update_idletasks()
        self.apply_rounded_corners(20)
                        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.font_primary = ("Segoe UI Variable", 10)
        self.font_medium = ("Segoe UI Variable", 12)
        self.font_title = ("Segoe UI Variable", 28, "bold")
        self.font_bold = ("Segoe UI Variable", 12, "bold")
        
        self.colors = get_theme('Dark')
        self.setup_scrollbar_style()
        self.root.configure(bg=self.colors['bg_dark'])
        
        if not is_admin():
            result = messagebox.askyesno(
                tr('dialog_admin_required'),
                tr('dialog_admin_message')
            )
            if result:
                run_as_admin()
            else:
                messagebox.showerror(
                    tr('error_no_connection'), 
                    tr('dialog_no_connection')
                )
                sys.exit(1)
        
        self.is_connected = False
        self.current_strategy = None
        self.current_page = "main"

        self.zapret = ZapretCore(self)
        self.tg_proxy = TGProxyServer()
        
        self.ensure_appdata_dir()
        self.languages = get_languages()
        self.current_theme = 'Dark'
        self.load_settings()
        self.apply_theme()

        if not self._tg_secret:
            self._tg_secret = os.urandom(16).hex()
            self.save_settings()

        self.tg_proxy.set_secret(getattr(self, '_tg_secret', None))
        
        self.setup_ui()
        self.root.after(100, self.check_initial_status)
        self.root.after(1000, lambda: check_launcher_updates(self, silent=True))
        self.root.after(2000, lambda: check_zapret_updates(self, silent=True))
        self.show_main_page()
                
        self.tray_icon = ModernSystemTray(self)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def update_tray_icon_state(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_icon_state()
            except Exception as e:
                print(f"Error updating tray icon: {e}")

    def apply_rounded_corners(self, radius=20):
        try:
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            
            try:
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    byref(c_int(DWMWCP_ROUND)),
                    ctypes.sizeof(c_int)
                )
            except Exception:
                hrgn = windll.gdi32.CreateRoundRectRgn(0, 0, self.window_width + 1, self.window_height + 1, radius * 2, radius * 2)
                windll.user32.SetWindowRgn(hwnd, hrgn, True)
        except Exception:
            pass

    def hide_window(self):
        self.root.withdraw()
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

    def on_closing(self):
        try:
            self.root.withdraw()
        except Exception as e:
            print(f"Error hiding window: {e}")

    def _force_exit(self):
        try:
            self._stop_windivert_before_restart()
            self.zapret.stop_current_strategy()
            if hasattr(self, 'tg_proxy'):
                self.tg_proxy.stop()
            if hasattr(self, 'tray_icon') and self.tray_icon.icon:
                self.tray_icon.icon.stop()
            time.sleep(0.5)
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        finally:
            sys.exit(0)

    def update_ui_colors(self):
        def update_widget(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
                    current_bg = widget.cget('bg')
                    if current_bg and current_bg not in [self.colors['accent'], self.colors['accent_green'], self.colors['accent_red']]:
                        widget.configure(bg=self.colors['bg_dark'])
                
                if isinstance(widget, tk.Label):
                    current_fg = widget.cget('fg')
                    accent_colors = [self.colors['accent'], self.colors['accent_green'], 
                                self.colors['accent_red'], self.colors['accent_hover']]
                    if current_fg and current_fg not in accent_colors:
                        widget.configure(fg=self.colors['text_secondary'])
                
                if hasattr(widget, 'update_colors'):
                    widget.update_colors(self.colors['button_bg'], self.colors['text_secondary'], self.colors['button_hover'])
                
                for child in widget.winfo_children():
                    update_widget(child)
            except:
                pass
        update_widget(self.root)

    def update_nav_buttons_colors(self):
        if hasattr(self, 'left_panel'):
            for child in self.left_panel.winfo_children():
                if isinstance(child, tk.Frame):
                    for btn in child.winfo_children():
                        if hasattr(btn, 'update_colors'):
                            btn.update_colors(
                                self.colors['bg_light'], 
                                self.colors['text_secondary'], 
                                self.colors['bg_light_hover']
                            )

    def apply_theme(self):
        self.colors = get_theme(self.current_theme)
        self.root.configure(bg=self.colors['bg_dark'])
        self.setup_scrollbar_style()
        self.update_ui_colors()
        
        if hasattr(self, 'pages') and self.pages:
            self.pages.colors = self.colors
            
            for page_name in ['main_page', 'service_page', 'lists_page', 'diagnostic_page', 
                            'traffic_page', 'settings_page']:
                if hasattr(self.pages, page_name):
                    page = getattr(self.pages, page_name)
                    if page:
                        page.configure(bg=self.colors['bg_dark'])
                        
            if hasattr(self, 'left_panel') and self.left_panel:
                self.left_panel.configure(bg=self.colors['bg_medium'])
                
            self.update_nav_buttons_colors()

        if hasattr(self, 'pages'):
            self.pages.update_animation_color()

    def _stop_windivert_before_restart(self):
        try:
            subprocess.run(
                'sc stop windivert > nul 2>&1',
                shell=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(0.5)
        except:
            pass

    def quit_from_tray(self):
        self._force_exit()

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
        self.left_panel = left_panel
        
        try:
            icon_paths = [
                BASE_DIR / "resources" / "icon.png",
                BASE_DIR / "resources" / "icon.ico",
                Path("resources/icon.png"),
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
                raise Exception(tr('error_icon_not_found'))
                
        except Exception as e:
            logo_btn = RoundedButton(
                logo_frame,
                text="ZAPRET\nLAUNCHER",
                command=self.show_settings_page,
                width=120, height=120,
                bg=self.colors['accent'],
                fg=self.colors['text_primary'],
                font=("Segoe UI Variable", 14, "bold"),
                corner_radius=60
            )
            logo_btn.pack(expand=True, pady=10)
            logo_btn.bind("<Enter>", lambda e: logo_btn.config(cursor="hand2"))
            logo_btn.bind("<Leave>", lambda e: logo_btn.config(cursor=""))

        nav_buttons = [
            (tr('main_title'), self.show_main_page),
            (tr('service_title'), self.show_service_page),
            (tr('lists_title'), self.show_lists_page),
            (tr('diagnostic_title'), self.show_diagnostic_page),
            (tr('additionally_title'), self.show_additionally_page),
            (tr('traffic_title'), self.show_traffic_page),
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
                font=("Segoe UI Variable", 11),
                corner_radius=10,
                hover_color=self.colors['accent']
            )

            if self.current_theme == 'light':
                btn.hover_color = self.colors['accent']
                btn.normal_color = self.colors['bg_light']
                btn.update_colors(self.colors['bg_light'], self.colors['text_secondary'], self.colors['accent'])
            else:
                btn.hover_color = self.colors['accent']
                btn.normal_color = self.colors['bg_light']
                btn.update_colors(self.colors['bg_light'], self.colors['text_secondary'], self.colors['accent'])
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
            font=("Segoe UI Variable", 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        self.left_status.pack()
        
        tk.Label(
            credit_frame,
            text=f"v{CURRENT_VERSION}",
            font=("Segoe UI Variable", 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        ).pack(pady=(5, 0))
        
        self.credit_label = tk.Label(
            credit_frame,
            text="by trimansberg",
            font=("Segoe UI Variable", 8),
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
        dialog.title(tr('mode_select'))
        dialog.geometry("500x550")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text=tr('mode_select'), font=("Segoe UI Variable", 16, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.colors['bg_medium'], highlightthickness=0)
        #scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, style="Custom.Vertical.TScrollbar")
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_medium'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=440)
        canvas.configure(yscrollcommand=None)
        canvas.pack(side="left", fill="both", expand=True)
        #scrollbar.pack(side="right", fill="y")
        
        #def _on_mousewheel(event):
        #    try:
        #        if canvas and canvas.winfo_exists():
        #           canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        #    except (tk.TclError, AttributeError):
        #        pass
        
        #dialog.bind_all("<MouseWheel>", _on_mousewheel)
        #dialog._mousewheel_handler = _on_mousewheel
        #canvas.bind("<MouseWheel>", _on_mousewheel)
        #scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        modes = [
            {"name": tr('mode_standard'), "desc": tr('mode_standard_desc'), 
            "zapret": True, "tgproxy": False, "game": False},
            {"name": tr('mode_tgproxy'), "desc": tr('mode_tgproxy_desc'), 
            "zapret": False, "tgproxy": True, "game": False},
            {"name": tr('mode_zapret_tgproxy'), "desc": tr('mode_zapret_tgproxy_desc'), 
            "zapret": True, "tgproxy": True, "game": False},
            {"name": tr('mode_game'), "desc": tr('mode_game_desc'), 
            "zapret": True, "tgproxy": False, "game": True}
        ]
        
        selected_mode = [None]
        selected_widget = [None]
        select_btn = [None]
        
        def update_select_button():
            if select_btn[0]:
                if selected_mode[0]:
                    select_btn[0].set_enabled(True)
                    select_btn[0].normal_color = self.colors['accent']
                    select_btn[0].hover_color = self.colors['button_hover']
                    select_btn[0].update_colors(
                        self.colors['accent'],
                        self.colors['text_primary'],
                        self.colors['button_hover']
                    )
                    select_btn[0].config(cursor="hand2")
                else:
                    select_btn[0].set_enabled(False)
                    select_btn[0].normal_color = self.colors['button_bg']
                    select_btn[0].hover_color = self.colors['accent']
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
            name_label = tk.Label(mode_frame, text=mode["name"], font=("Segoe UI Variable", 12, "bold"),
                                fg=self.colors['accent'], bg=original_bg)
            name_label.pack(anchor='w', padx=15, pady=(8, 2))
            desc_label = tk.Label(mode_frame, text=mode["desc"], font=("Segoe UI Variable", 9),
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
            text=tr('mode_select_button'),
            command=on_select_click,
            width=100, height=35,
            bg=self.colors['button_bg'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        select_btn[0].normal_color = self.colors['button_bg']
        select_btn[0].hover_color = self.colors['accent']
        select_btn[0].set_enabled(False)
        select_btn[0].config(cursor="arrow")
        select_btn[0].pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = RoundedButton(
            bottom_frame,
            text=tr('mode_cancel'),
            command=dialog.destroy,
            width=100, height=35,
            bg=self.colors['button_bg'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        cancel_btn.normal_color = self.colors['button_bg']
        cancel_btn.hover_color = self.colors['accent']
        cancel_btn.config(cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)

    def start_with_mode(self, mode):
        if self.is_connected:
            return
        
        if mode["name"] == tr('mode_zapret_tgproxy'):
            if not self.zapret.available_strategies:
                messagebox.showerror(tr('error_no_strategies'), tr('error_no_strategies'))
                return
            
            self._pending_mode = mode
            self.select_strategy_for_mode(mode["name"])
            return
        
        if mode["name"] == tr('mode_tgproxy'):
            self._start_tg_proxy_direct()
            return
        
        if mode["name"] == tr('mode_standard') or mode["name"] == tr('mode_game'):
            if not self.zapret.available_strategies:
                messagebox.showerror(tr('error_no_strategies'), tr('error_no_strategies'))
                return
            
            self._pending_mode = mode
            self.select_strategy_for_mode(mode["name"])
            return

        self._reset_traffic_history()

        self.update_status(tr('status_starting'), self.colors['accent'])
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(False)
        self.root.update()
        
        if mode.get("tgproxy", False):
            self.tg_proxy.start()
        
        self.is_connected = True
        self.stats.start_session()
        self.start_stats_monitoring()
        
        mode_name = mode["name"]
        if hasattr(self, 'mode_label') and self.mode_label:
            self.mode_label.config(text=mode_name, fg=self.colors['accent_green'])
        self.update_status(f"{tr('status_connected')}", self.colors['accent_green'])
        self.update_ui_state()
        self.save_settings()
        self.root.after(100, self.update_stats_display)
        self.root.after(500, self.update_tray_icon_state)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def _start_tg_proxy_direct(self):
        if self.is_connected:
            return
        
        if not hasattr(self, '_tg_secret') or not self._tg_secret:
            result = messagebox.askyesno(
                tr('error_secret_not_found'),
                tr('tg_secret_required_message')
            )
            if result:
                self._tg_secret = os.urandom(16).hex()
                self.save_settings()
                self.show_notification(tr('notification_copied'), 2000)
                if hasattr(self, 'pages') and hasattr(self.pages, 'settings_page'):
                    self.pages.update_secret_display()
            else:
                self.update_status(tr('status_ready'), self.colors['text_secondary'])
                return
        
        self._do_start_tg_proxy()

    def regenerate_tg_secret(self):
        self._tg_secret = os.urandom(16).hex()
        self.save_settings()
        
        self.tg_proxy.set_secret(self._tg_secret)

        if hasattr(self, 'pages') and hasattr(self.pages, 'settings_page'):
            self.pages.update_secret_display()
        
        link = f"tg://proxy?server=127.0.0.1&port=1080&secret={self._tg_secret}"
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        self.root.update()
        
        self.show_notification(tr('notification_copied'), 3000)
        messagebox.showinfo(
            tr('tg_secret_updated'),
            f"{tr('tg_secret_new')} {self._tg_secret}\n\n"
            f"{tr('notification_copied')}\n"
            f"{tr('tg_paste_instruction')}\n\n"
            f"{tr('tg_proxy_restarted')}"
        )
        
    def _do_start_tg_proxy(self):
        self._reset_traffic_history()
        self.update_status(tr('status_starting_tg'), self.colors['accent'])
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(False)
        self.root.update()
        
        self.tg_proxy.set_secret(self._tg_secret)
        
        def start_thread():
            try:
                success = self.tg_proxy.start()
                
                if success:
                    if self.tg_proxy.wait_for_start(8):
                        self.root.after(0, lambda: self._on_tg_proxy_started_direct())
                    else:
                        self.root.after(0, lambda: self._on_tg_proxy_failed_direct(tr('error_tgproxy_timeout')))
                else:
                    self.root.after(0, lambda: self._on_tg_proxy_failed_direct(tr('error_tgproxy_start')))
            except Exception as e:
                print(f"Start thread error: {e}")
                self.root.after(0, lambda: self._on_tg_proxy_failed_direct(str(e)))
        
        threading.Thread(target=start_thread, daemon=True).start()

    def _on_tg_proxy_started_direct(self):
        if not self.is_connected:
            self.is_connected = True
            self.stats.start_session()
            self.start_stats_monitoring()
            
            self.mode_label.config(text=tr('mode_tgproxy'), fg=self.colors['accent_green'])
            self.update_status(tr('status_connected'), self.colors['accent_green'])
            self.update_ui_state()
            self.save_settings()
            self.root.after(100, self.update_stats_display)

            if not self._tg_instruction:
                self.root.after(500, self.show_tg_proxy_instruction)
        
        self.connect_btn.set_enabled(True)
        self.root.after(500, self.update_tray_icon_state)

    def _on_tg_proxy_failed_direct(self, error_msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_tgproxy_start'), f"{tr('error_tgproxy_start')}: {error_msg}")
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def select_strategy_for_mode(self, mode_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('select_strategy'))
        dialog.geometry("550x550")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 275
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        dialog.geometry(f"+{x}+{y}")
        
        if mode_name == tr('mode_zapret_tgproxy'):
            title_text = f"{tr('select_strategy')}"
            desc_text = ""
        else:
            title_text = tr('select_strategy')
            desc_text = ""
        
        tk.Label(dialog, text=title_text, font=("Segoe UI Variable", 18, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(25, 15))
        
        if desc_text:
            tk.Label(dialog, text=desc_text, font=("Segoe UI Variable", 10),
                    fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                    wraplength=450).pack(pady=(0, 15))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=5)
        
        list_card = tk.Frame(main_frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        list_card.pack(fill=tk.BOTH, expand=True)
        
        list_inner = tk.Frame(list_card, bg=self.colors['bg_light'])
        list_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        tk.Label(list_inner, text=tr('available_strategies'), font=("Segoe UI Variable", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        list_frame = tk.Frame(list_inner, bg=self.colors['bg_light'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        strategy_listbox = tk.Listbox(list_frame, height=10, font=("Segoe UI Variable", 10),
                                    bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                    selectbackground=self.colors['accent'],
                                    yscrollcommand=scrollbar.set)
        strategy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=strategy_listbox.yview)
        
        for s in self.zapret.available_strategies:
            strategy_listbox.insert(tk.END, s)
        
        desc_label = tk.Label(dialog, text="", font=("Segoe UI Variable", 9),
                            fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                            wraplength=400, justify=tk.LEFT)
        desc_label.pack(pady=5, padx=20)
        
        def on_select(event):
            selection = strategy_listbox.curselection()
            if selection:
                strategy = self.zapret.available_strategies[selection[0]]
                desc_label.config(text=f"{tr('selected')}: {strategy}")
        
        strategy_listbox.bind("<<ListboxSelect>>", on_select)
        
        if self.current_strategy:
            try:
                idx = self.zapret.available_strategies.index(self.current_strategy)
                strategy_listbox.selection_set(idx)
                strategy_listbox.see(idx)
                desc_label.config(text=f"{tr('selected')}: {self.current_strategy}")
            except:
                pass
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)
        
        def start_with_strategy():
            selection = strategy_listbox.curselection()
            if not selection:
                messagebox.showerror(tr('error_select_strategy'), tr('error_select_strategy'))
                return
            selected_strategy = self.zapret.available_strategies[selection[0]]
            self.strategy_var.set(selected_strategy)
            dialog.destroy()
            
            mode = self._pending_mode
            self.update_status(f"{tr('status_starting')}", self.colors['accent'])
            if hasattr(self, 'connect_btn') and self.connect_btn:
                self.connect_btn.set_enabled(False)
            self.root.update()
            
            if mode["name"] == tr('mode_zapret_tgproxy'):
                def start_combined():
                    success, msg = self.zapret.run_strategy(selected_strategy)
                    if not success:
                        self.root.after(0, lambda: self._on_combined_start_failed(msg))
                        return
                    
                    self.current_strategy = selected_strategy
                    
                    tg_success = self.tg_proxy.start()
                    if not tg_success:
                        self.zapret.stop_current_strategy()
                        self.root.after(0, lambda: self._on_combined_start_failed(tr('error_tgproxy_start')))
                        return
                    
                    if not self.tg_proxy.wait_for_start(8):
                        self.zapret.stop_current_strategy()
                        self.tg_proxy.stop()
                        self.root.after(0, lambda: self._on_combined_start_failed(tr('error_tgproxy_timeout')))
                        return
                    
                    self.is_connected = True
                    self.stats.start_session()
                    self.start_stats_monitoring()
                    
                    self.root.after(0, lambda: self._on_combined_start_success(mode["name"]))
                
                threading.Thread(target=start_combined, daemon=True).start()
            else:
                success, msg = self.zapret.run_strategy(selected_strategy)
                if not success:
                    self.update_status(tr('status_error'), self.colors['accent_red'])
                    messagebox.showerror(tr('error_startup'), msg)
                    if hasattr(self, 'connect_btn') and self.connect_btn:
                        self.connect_btn.set_enabled(True)
                    return
                
                self.current_strategy = selected_strategy
                
                if mode.get("tgproxy", False):
                    self.tg_proxy.start()
                
                self.is_connected = True
                self.stats.start_session()
                self.start_stats_monitoring()
                
                if hasattr(self, 'mode_label') and self.mode_label:
                    self.mode_label.config(text=mode["name"], fg=self.colors['accent_green'])
                self.update_status(f"{tr('status_connected')}", self.colors['accent_green'])
                self.update_ui_state()
                self.save_settings()
                self.root.after(500, self.update_tray_icon_state)
                if hasattr(self, 'connect_btn') and self.connect_btn:
                    self.connect_btn.set_enabled(True)
        
        start_btn = RoundedButton(btn_frame, text=tr('button_start'), command=start_with_strategy,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI Variable", 10), corner_radius=8)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text=tr('mode_cancel'), command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI Variable", 10), corner_radius=8)
        cancel_btn.pack(side=tk.LEFT, padx=5)

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

        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_tooltip()
            except:
                pass

    def _update_rtt(self):
        try:
            if hasattr(self, 'stats_rtt_label') and self.stats_rtt_label.winfo_exists():
                rtt = self.measure_rtt()
                if rtt > 0:
                    self.stats_rtt_label.config(text=f"{rtt:.0f} {tr('stats_rtt_ms')}", fg=self.colors['accent'])
                else:
                    self.stats_rtt_label.config(text="-- ms", fg=self.colors['text_secondary'])
        except (tk.TclError, AttributeError):
            return
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
        except Exception:
            pass
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
        try:
            if not self.root.winfo_viewable():
                return
            
            notification = tk.Toplevel(self.root)
            notification.overrideredirect(True)
            notification.configure(bg=self.colors['bg_medium'])
            notification._is_alive = True

            try:
                notification.attributes('-topmost', True)
            except:
                pass
            
            def on_iconify():
                if notification and notification.winfo_exists() and notification._is_alive:
                    try:
                        notification.withdraw()
                    except:
                        pass
            
            def on_deiconify():
                if notification and notification.winfo_exists() and notification._is_alive and self.root.winfo_viewable():
                    try:
                        notification.deiconify()
                    except:
                        pass
            
            for binding in self.root.bindtags():
                if '<Map>' in binding or '<Unmap>' in binding:
                    pass
            
            self.root.bind('<Map>', lambda e: on_deiconify(), add=True)
            self.root.bind('<Unmap>', lambda e: on_iconify(), add=True)
            
            try:
                notification.attributes('-alpha', 0.95)
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
                            font=("Segoe UI Variable", 10),
                            fg=self.colors['text_primary'], 
                            bg=self.colors['bg_medium'],
                            padx=12, pady=8)
            label.pack()
            notification.lift()
            notification.attributes('-alpha', 0.0)
            
            def fade_in(alpha=0.0):
                if not self.root.winfo_viewable():
                    try:
                        notification.destroy()
                    except:
                        pass
                    return
                if alpha < 0.95:
                    alpha += 0.1
                    try:
                        if notification and notification.winfo_exists() and notification._is_alive:
                            notification.attributes('-alpha', alpha)
                            notification.after(30, lambda: fade_in(alpha))
                    except:
                        pass
                else:
                    notification.after(duration, fade_out)
            
            def fade_out(alpha=0.95):
                if alpha > 0.0:
                    alpha -= 0.1
                    try:
                        if notification and notification.winfo_exists() and notification._is_alive:
                            notification.attributes('-alpha', alpha)
                            notification.after(30, lambda: fade_out(alpha))
                    except:
                        pass
                else:
                    try:
                        if notification and notification.winfo_exists():
                            notification._is_alive = False
                            notification.destroy()
                    except:
                        pass
            
            fade_in()
        except Exception:
                    pass

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

    def optimize_network_latency(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic(tr('dns_optimize_network'))
        self.log_to_diagnostic("="*50)
        
        if not is_admin():
            self.log_to_diagnostic(tr('error_admin_required'))
            messagebox.showerror(tr('error_admin_required'), tr('error_admin_required'))
            return
        
        self.log_to_diagnostic(tr('dns_configuring_tcp'))
        success, msg = optimize_network_latency()
        
        if success:
            self.log_to_diagnostic(msg)
            self.log_to_diagnostic(tr('dns_optimize_complete'))
            messagebox.showinfo(tr('dns_optimize_success'), tr('dns_optimize'))
        else:
            self.log_to_diagnostic(f"{tr('error_occurred')}: {msg}")
            messagebox.showerror(tr('error_occurred'), msg)
        
        self.log_to_diagnostic("="*50)

    def find_and_set_best_dns(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic(tr('dns_searching_best'))
        self.log_to_diagnostic("="*50)
        
        self.log_to_diagnostic(tr('dns_testing_servers'))
        self.update_status(tr('status_searching_dns'), self.colors['accent'])
        self.root.update()
        
        def find_dns_thread():
            try:
                primary, secondary, latency, name = find_best_dns()
                
                self.log_to_diagnostic(f"{tr('dns_best_set')}: {name}")
                self.log_to_diagnostic(f"{tr('dns_primary')}: {primary} ({tr('dns_latency')}: {latency:.1f} ms)")
                self.log_to_diagnostic(f"{tr('dns_secondary')}: {secondary}")
                
                if not is_admin():
                    self.log_to_diagnostic(tr('error_admin_required'))
                    self.root.after(0, lambda: messagebox.showerror(tr('error_admin_required'), tr('error_admin_required')))
                    self.root.after(0, lambda: self.update_status(tr('status_ready')))
                    return
                
                success, msg = set_dns_windows(primary, secondary)
                
                if not success:
                    adapters = list_network_adapters()
                    if adapters:
                        self.root.after(0, lambda: self.show_adapter_selector(primary, secondary, name, adapters))
                    else:
                        self.log_to_diagnostic(f"{msg}")
                        self.root.after(0, lambda: messagebox.showerror(tr('error_occurred'), msg))
                else:
                    self.log_to_diagnostic(f"{msg}")
                    self.root.after(0, lambda: messagebox.showinfo(tr('dns_set_success'), 
                        f"{tr('dns_set')} {name}\n\n"
                        f"{tr('dns_primary')}: {primary}\n"
                        f"{tr('dns_secondary')}: {secondary}\n"
                        f"{tr('dns_latency')}: {latency:.1f} ms"))
                
                self.root.after(0, lambda: self.update_status(tr('status_ready')))
                self.log_to_diagnostic("="*50)
                
            except Exception as e:
                self.log_to_diagnostic(f"{tr('error_occurred')}: {str(e)}")
                self.root.after(0, lambda: self.update_status(tr('status_ready')))
        
        threading.Thread(target=find_dns_thread, daemon=True).start()

    def show_adapter_selector(self, primary, secondary, dns_name, adapters):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('dns_select_adapter'))
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text=tr('dns_select_adapter'), font=("Segoe UI Variable", 12),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(15, 10))
        
        listbox = tk.Listbox(dialog, height=8, font=("Segoe UI Variable", 10),
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
                messagebox.showinfo(tr('dns_set_success'), f"{tr('dns_set')} {tr('dns_for_adapter')} {adapter}")
                self.log_to_diagnostic(f"{tr('dns_set')} {tr('dns_for_adapter')} {adapter}")
            else:
                messagebox.showerror(tr('error_occurred'), msg)
                self.log_to_diagnostic(f"{msg}")
            
            dialog.destroy()
        
        button_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        button_frame.pack(pady=15)
        
        apply_btn = RoundedButton(button_frame, text=tr('button_apply'), command=apply,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI Variable", 10))
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(button_frame, text=tr('mode_cancel'), command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI Variable", 10))
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def flush_dns_cache_command(self):
        self.log_to_diagnostic(tr('dns_flushing'))
        success, msg = flush_dns_cache()
        if success:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showinfo(tr('dns_flush_success'), msg)
        else:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showerror(tr('error_occurred'), msg)

    def restore_network_defaults_command(self):
        self.log_to_diagnostic(tr('dns_restoring_defaults'))
        if not is_admin():
            messagebox.showerror(tr('error_admin_required'), tr('error_admin_required'))
            return
        
        success, msg = restore_network_defaults()
        if success:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showinfo(tr('dns_restore_success'), msg)
        else:
            self.log_to_diagnostic(f"{msg}")
            messagebox.showerror(tr('error_occurred'), msg)

    def check_file_integrity(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic(tr('diagnostic_file_integrity'))
        self.log_to_diagnostic("="*50)
        
        errors = []
        
        required_files = [
            ("zapret_resources.zip", Path(__file__).parent / "zapret_resources.zip"),
        ]
        
        for name, path in required_files:
            if path.exists():
                size = path.stat().st_size
                if size > 0:
                    self.log_to_diagnostic(f"  {name} - {size} {tr('diagnostic_bytes')}")
                else:
                    self.log_to_diagnostic(f"  {name} - empty file (0 {tr('diagnostic_bytes')})")
                    errors.append(f"{name} {tr('is_empty')}")
            else:
                self.log_to_diagnostic(f"  {name} - {tr('not_found')}")
                errors.append(f"{name} {tr('not_found')}")
        
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
                    self.log_to_diagnostic(f"  {file} - {size} {tr('diagnostic_bytes')}")
                else:
                    self.log_to_diagnostic(f"  {file} - {tr('not_found')}")
                    errors.append(f"{file} {tr('not_found')}")
            
            strategies = list(ZAPRET_CORE_DIR.glob("general*.bat"))
            self.log_to_diagnostic(f"  {tr('strategies_count')}: {len(strategies)} {tr('files')}")
        else:
            self.log_to_diagnostic(f"  {tr('diagnostic_zapret_missing')}")
            errors.append(tr('diagnostic_zapret_missing'))
        
        self.log_to_diagnostic("")
        if errors:
            self.log_to_diagnostic(f"{tr('diagnostic_problems_found')} {len(errors)}")
            for err in errors:
                self.log_to_diagnostic(f"  - {err}")
        else:
            self.log_to_diagnostic(tr('diagnostic_all_ok'))
        
        self.log_to_diagnostic("="*50)
    
    def check_custom_site(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('diagnostic_check_site'))
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text=tr('diagnostic_enter_url'), font=("Segoe UI Variable", 11),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 5))
        
        url_entry = tk.Entry(dialog, width=50, font=("Segoe UI Variable", 10),
                            bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                            insertbackground=self.colors['text_primary'])
        url_entry.pack(pady=5, padx=20, fill=tk.X)
        url_entry.insert(0, "youtube.com")
        
        result_label = tk.Label(dialog, text="", font=("Segoe UI Variable", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        result_label.pack(pady=5)
        
        def check():
            url = url_entry.get().strip()
            if not url:
                result_label.config(text=tr('diagnostic_enter_url'), fg=self.colors['accent_red'])
                return
            
            result_label.config(text=tr('diagnostic_checking'), fg=self.colors['accent'])
            dialog.update()
            
            def check_thread():
                try:
                    clean_url = url.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                    
                    try:
                        ip = socket.gethostbyname(clean_url)
                        dns_ok = True
                    except:
                        ip = tr('diagnostic_not_determined')
                        dns_ok = False
                    
                    if dns_ok:
                        result = subprocess.run(['ping', '-n', '2', clean_url], 
                                            capture_output=True, timeout=5)
                        if result.returncode == 0:
                            for line in result.stdout.decode('cp866', errors='ignore').split('\n'):
                                if "среднее" in line or "Average" in line:
                                    result_text = f"{tr('diagnostic_available')} - {line.strip()}"
                                    break
                            else:
                                result_text = f"{tr('diagnostic_available')} (IP: {ip})"
                            color = self.colors['accent_green']
                        else:
                            result_text = f"{tr('diagnostic_not_available')} (IP: {ip})"
                            color = self.colors['accent_red']
                    else:
                        result_text = f"{tr('diagnostic_dns_error')}"
                        color = self.colors['accent_red']
                        
                except subprocess.TimeoutExpired:
                    result_text = tr('diagnostic_timeout')
                    color = self.colors['accent_red']
                except Exception as e:
                    result_text = f"{tr('error_occurred')}: {str(e)}"
                    color = self.colors['accent_red']
                
                dialog.after(0, lambda: result_label.config(text=result_text, fg=color))
                dialog.after(0, lambda: check_btn.config(state="normal"))
            
            check_btn.config(state="disabled")
            threading.Thread(target=check_thread, daemon=True).start()
        
        button_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        button_frame.pack(pady=15)
        
        check_btn = RoundedButton(button_frame, text=tr('diagnostic_check'), command=check,
                                width=120, height=32, bg=self.colors['accent'],
                                font=("Segoe UI Variable", 10))
        check_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = RoundedButton(button_frame, text=tr('button_close'), command=dialog.destroy,
                                width=80, height=32, bg=self.colors['button_bg'],
                                font=("Segoe UI Variable", 10))
        close_btn.pack(side=tk.LEFT, padx=5)
        
        url_entry.bind("<Return>", lambda e: check())

    def set_autostart(self, enabled):
        try:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, "Zapret Launcher", 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, "Zapret Launcher")
                    except:
                        pass
            return True
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_autostart')}: {e}")
            return False

    def check_autostart_status(self):
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, "Zapret Launcher")
                return value is not None
        except:
            return False

    def safe_command(self, command):
        try:
            command()
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_occurred')}: {str(e)}")

    def log_to_diagnostic(self, message):
        self.diagnostic_text.insert(tk.END, message + "\n")
        self.diagnostic_text.see(tk.END)
        self.diagnostic_text.update()

    def auto_select_strategy(self):
        self.log_to_diagnostic("="*50)
        self.log_to_diagnostic(tr('diagnostic_auto_strategy'))
        self.log_to_diagnostic("="*50)
        
        strategies = self.zapret.available_strategies
        if not strategies:
            self.log_to_diagnostic(tr('error_no_strategies'))
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
            self.log_to_diagnostic(f"\n{tr('diagnostic_testing')}: {strategy}")
            
            if was_connected:
                self.disconnect()
                time.sleep(1)
            
            success, msg = self.zapret.run_strategy(strategy)
            
            if not success:
                self.log_to_diagnostic(f"  {tr('diagnostic_failed_to_start')}: {msg}")
                continue
            
            self.log_to_diagnostic(f"  {tr('diagnostic_started')}")
            time.sleep(2)
            
            success_count = 0
            for site, name in test_sites:
                try:
                    result = subprocess.run(['ping', '-n', '2', site], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        self.log_to_diagnostic(f"    {name} {tr('diagnostic_available')}")
                        success_count += 1
                    else:
                        self.log_to_diagnostic(f"    {name} {tr('diagnostic_not_available')}")
                except:
                    self.log_to_diagnostic(f"    {name} {tr('diagnostic_check_error')}")
            
            self.zapret.stop_current_strategy()
            
            score = success_count
            self.log_to_diagnostic(f"  {tr('diagnostic_result')}: {success_count}/{len(test_sites)}")
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
                best_success_count = success_count
        
        if best_strategy:
            self.log_to_diagnostic(f"\n{tr('diagnostic_best_strategy')}: {best_strategy}")
            self.log_to_diagnostic(f"{tr('diagnostic_result')}: {best_success_count}/{len(test_sites)}")
            
            self.strategy_var.set(best_strategy)
            self.current_strategy = best_strategy
            self.save_settings()
            
            if was_connected:
                self.log_to_diagnostic(tr('diagnostic_restoring_connection'))
                self.connect()
        else:
            self.log_to_diagnostic(f"\n{tr('diagnostic_no_working_strategy')}")
        
        self.log_to_diagnostic("="*50)
        return best_strategy

    def check_zapret_logs(self):
        self.log_to_diagnostic(tr('diagnostic_searching_winws'))
        found = False
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                            time.localtime(proc.info['create_time']))
                    self.log_to_diagnostic(f"  • PID: {proc.info['pid']}, {tr('diagnostic_started_at')}: {create_time}")
                    found = True
            except:
                pass
        if not found:
            self.log_to_diagnostic(tr('diagnostic_winws_not_found'))

    def open_appdata_folder(self):
        self.log_to_diagnostic(f"{tr('diagnostic_opening_folder')}: AppData/Local/Zapret Launcher")
        try:
            os.startfile(APPDATA_DIR)
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_occurred')}: {str(e)}")

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
                        result.append(f"  DNS server: {server}")
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
                                result.append(f"  DNS server: {ip}")
                                break
                        if result:
                            break
            
            if not result:
                result.append("  DNS server not determined (using automatic)")
                
        except Exception as e:
            result.append(f"  Error: {e}")
        return result

    def clear_cache(self):
        self.log_to_diagnostic(tr('diagnostic_clearing_cache'))
        try:
            self.diagnostic_text.delete(1.0, tk.END)
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_occurred')}: {str(e)}")

    def save_diagnostic_report(self):
        try:
            report_path = APPDATA_DIR / f"diagnostic_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(self.diagnostic_text.get(1.0, tk.END))
            self.log_to_diagnostic(f"{tr('diagnostic_report_saved')}: {report_path}")
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_occurred')}: {str(e)}")

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
                messagebox.showinfo(tr('autostart_enabled'), tr('autostart_enabled'))
            else:
                messagebox.showinfo(tr('autostart_disabled'), tr('autostart_disabled'))
        else:
            messagebox.showerror(tr('error_occurred'), tr('autostart_error'))

    def open_github(self):
        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher")

    def check_initial_status(self):
        if not check_zapret_folder():
            return
        if self.zapret.is_winws_running():
            self.is_connected = True
            self.update_status(tr('status_connected'), self.colors['accent_green'])
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
        
        if hasattr(self, 'main_status') and self.main_status:
            self.main_status.config(text=text, fg=color)
        
        if hasattr(self, 'left_status') and self.left_status:
            self.left_status.config(fg=color)

    def update_ui_state(self):
        try:
            if hasattr(self, 'connect_btn') and self.connect_btn:
                if not self.connect_btn.winfo_exists():
                    return
                    
                if self.is_connected:
                    self.connect_btn.set_text(tr('button_disconnect'))
                    if self.current_theme == 'light':
                        self.connect_btn.normal_color = '#9CA3AF'
                        self.connect_btn.update_colors('#9CA3AF', '#FFFFFF', '#6B7280')
                    else:
                        self.connect_btn.normal_color = '#3D3D45'
                        self.connect_btn.update_colors('#3D3D45', '#FFFFFF', self.colors['accent'])
                else:
                    self.connect_btn.set_text(tr('button_connect'))
                    self.connect_btn.normal_color = self.colors['accent']
                    self.connect_btn.hover_color = '#3D3D45'
                    self.connect_btn.update_colors(self.colors['accent'], '#FFFFFF', '#3D3D45')
        except (tk.TclError, AttributeError, RuntimeError):
            pass
        
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except:
                pass

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.show_mode_selector()
        self.root.after(500, self.update_tray_icon_state)

    def connect(self):
        strategy = self.strategy_var.get()
        if not strategy:
            messagebox.showerror(tr('error_select_strategy'), tr('error_select_strategy'))
            return
        
        self._reset_traffic_history()

        self.update_status(tr('status_starting'), self.colors['accent'])
        self.connect_btn.set_enabled(False)
        self.root.update()
        
        def start_thread():
            success, msg = self.zapret.run_strategy(strategy)
            
            if success:
                self.current_strategy = strategy
                self.is_connected = True
                
                if self.tgws_var.get():
                    self.tg_proxy.start()
                    time.sleep(0.5)
                
                self.stats.start_session()
                self.root.after(0, lambda: self._on_connect_success(strategy, msg))
            else:
                self.root.after(0, lambda: self._on_connect_failed(msg))
        
        threading.Thread(target=start_thread, daemon=True).start()

    def _on_connect_success(self, strategy, msg):
        self.update_status(f"{tr('status_connected')}", 
                        self.colors['accent_green'])
        self.update_ui_state()
        self.save_settings()
        self.start_stats_monitoring()
        self.root.after(100, self.update_stats_display)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)
        self.root.after(500, self.update_tray_icon_state)

    def _on_connect_failed(self, msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_startup'), msg)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def disconnect(self):
        if not self.is_connected and not self.zapret.is_winws_running():
            return
            
        self.update_status(tr('status_disconnecting'), self.colors['accent'])
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(False)
        self.root.update()
        self.stop_rtt_monitoring()
        
        def stop_all():
            try:
                if hasattr(self, 'tg_proxy') and self.tg_proxy:
                    try:
                        self.tg_proxy.stop()
                    except Exception as e:
                        print(f"TGProxy stop error: {e}")
                    time.sleep(1.5)
                
                try:
                    self.zapret.stop_current_strategy()
                except Exception as e:
                    print(f"Zapret stop error: {e}")
                
                time.sleep(0.5)
                
                try:
                    subprocess.run('taskkill /F /IM winws.exe', shell=True, capture_output=True)
                except:
                    pass
                
                try:
                    self._stop_windivert_service()
                except:
                    pass
                
                try:
                    self.stats.end_session()
                except:
                    pass
                
                self.is_connected = False
                self.current_strategy = None
                self.root.after(0, self.finish_disconnect)
                
            except Exception as e:
                print(f"Error in disconnect stop_all: {e}")
                self.is_connected = False
                self.root.after(0, self.finish_disconnect)
        
        threading.Thread(target=stop_all, daemon=True).start()

    def finish_disconnect(self):
        try:
            self._cached_processes = []

            if hasattr(self, 'mode_label') and self.mode_label and self.mode_label.winfo_exists():
                self.mode_label.config(text=tr('mode_not_selected'), fg=self.colors['text_secondary'])
            self.update_status(tr('status_ready'), self.colors['text_secondary'])
            
            def update_button():
                try:
                    if hasattr(self, 'connect_btn') and self.connect_btn:
                        if self.connect_btn.winfo_exists():
                            self.connect_btn.set_enabled(True)
                            self.connect_btn.set_text(tr('button_connect'))
                            self.connect_btn.normal_color = self.colors['accent']
                            self.connect_btn.hover_color = '#3D3D45'
                            self.connect_btn.update_colors(self.colors['accent'], '#FFFFFF', '#3D3D45')
                except:
                    pass
            
            self.root.after(100, update_button)

            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.update_menu()
                except:
                    pass
            
            if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
                try:
                    self.root.after_cancel(self._traffic_update_timer)
                except:
                    pass
                self._traffic_update_timer = None
            
            if hasattr(self, 'rtt_timer_id') and self.rtt_timer_id:
                try:
                    self.root.after_cancel(self.rtt_timer_id)
                except:
                    pass
                self.rtt_timer_id = None
            
            self.stop_shutdown_monitoring()
            self.traffic_history = {}
            self.traffic_history_vpn = {}
            self.traffic_history_direct = {}
            self.traffic_speed_history = {}
            self.traffic_speed_vpn_history = {}
            self.traffic_speed_direct_history = {}
            self.hostname_cache = {}
            self.hostname_cache_time = {}
            self.root.after(500, self.update_tray_icon_state)
        except Exception as e:
            print(f"Error in finish_disconnect: {e}")

    def run_service_command(self, command):
        if not check_zapret_folder():
            return
        success, result = self.zapret.run_service_command(command)
        if success:
            messagebox.showinfo(tr('success'), result)
        else:
            messagebox.showerror(tr('error_occurred'), result)

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
                    #self.current_theme = data.get('theme', 'Dark')
                    self._tg_secret = data.get('tg_secret', None)

                    if not self._tg_secret:
                        self._tg_secret = os.urandom(16).hex()
                        self.save_settings()
                        
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._tg_secret = os.urandom(16).hex()

    def save_settings(self):
        try:
            settings = {
                'current_strategy': self.current_strategy,
                'autostart_enabled': self.check_autostart_status(),
                'update_interval': self.update_interval_index,
                'tg_instruction': getattr(self, '_tg_instruction', False),
                'language': self.languages.get_current_language(),
                #'theme': self.current_theme,
                'tg_secret': getattr(self, '_tg_secret', None),
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except:
            pass

    def show_main_page(self):
        self.pages.show_page_with_animation("main")
        
    def show_service_page(self):
        self.pages.show_page_with_animation("service")
        
    def show_lists_page(self):
        self.pages.show_page_with_animation("lists")

    def show_diagnostic_page(self):
        self.pages.show_page_with_animation("diagnostic")

    def show_settings_page(self):
        self.pages.show_page_with_animation("settings")

    def show_traffic_page(self):
        self.pages.show_page_with_animation("traffic")
        self._cached_processes = []
        if hasattr(self, '_traffic_collecting'):
            self._traffic_collecting = False
        if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
            try:
                self.root.after_cancel(self._traffic_update_timer)
            except:
                pass
        self.update_traffic_table()

    def show_additionally_page(self):
        self.pages.show_page_with_animation("additionally")

    def add_soundcloud_unblock(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            ipset_all_path = ZAPRET_CORE_DIR / "lists" / "ipset-all.txt"
            
            soundcloud_domains = [
                "soundcloud.com",
                "www.soundcloud.com",
                "style.sndcdn.com",
                "a-v2.sndcdn.com",
                "api-v2.soundcloud.com",
                "sb.scorecardresearch.com",
                "secure.quantserve.com",
                "eventlogger.soundcloud.com",
                "api.soundcloud.com",
                "ssl.google-analytics.com",
                "sdk-04.moengage.com",
                "al.sndcdn.com",
                "i1.sndcdn.com",
                "i2.sndcdn.com",
                "i3.sndcdn.com",
                "i4.sndcdn.com",
                "wis.sndcdn.com",
                "va.sndcdn.com",
                "pixel.quantserve.com",
                "assets.web.soundcloud.cloud",
                "*.cloudfront.net",
                ".soundcloud.",
                "playback.media-streaming.soundcloud.cloud",
                "id5-sync.com",
                "cdn.moengage.com",
                "htlbid.com",
                "securepubads.g.doubleclick.net",
                "cdn.cookielaw.org"
            ]
            
            soundcloud_ips = [
                "18.165.122.4/32",
                "18.165.122.6/32",
                "18.165.122.82/32",
                "18.165.122.86/32"
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    existing = f.read()
                
                added = []
                with open(list_general_path, 'a', encoding='utf-8') as f:
                    for domain in soundcloud_domains:
                        if domain not in existing:
                            f.write(f"{domain}\n")
                            added.append(domain)
                
            else:
                return False
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    existing = f.read()
                
                added = []
                with open(ipset_all_path, 'a', encoding='utf-8') as f:
                    for ip in soundcloud_ips:
                        if ip not in existing:
                            f.write(f"{ip}\n")
                            added.append(ip)
                
            else:
                return False
            
            self.show_notification(tr('soundcloud_unblocked'), 3000)
            return True
            
        except Exception:
            return False

    def remove_soundcloud_unblock(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            ipset_all_path = ZAPRET_CORE_DIR / "lists" / "ipset-all.txt"
            
            soundcloud_domains = [
                "soundcloud.com",
                "www.soundcloud.com",
                "style.sndcdn.com",
                "a-v2.sndcdn.com",
                "api-v2.soundcloud.com",
                "sb.scorecardresearch.com",
                "secure.quantserve.com",
                "eventlogger.soundcloud.com",
                "api.soundcloud.com",
                "ssl.google-analytics.com",
                "sdk-04.moengage.com",
                "al.sndcdn.com",
                "i1.sndcdn.com",
                "i2.sndcdn.com",
                "i3.sndcdn.com",
                "i4.sndcdn.com",
                "wis.sndcdn.com",
                "va.sndcdn.com",
                "pixel.quantserve.com",
                "assets.web.soundcloud.cloud",
                "*.cloudfront.net",
                ".soundcloud.",
                "playback.media-streaming.soundcloud.cloud",
                "id5-sync.com",
                "cdn.moengage.com",
                "htlbid.com",
                "securepubads.g.doubleclick.net",
                "cdn.cookielaw.org"
            ]
            
            soundcloud_ips = [
                "18.165.122.4/32",
                "18.165.122.6/32",
                "18.165.122.82/32",
                "18.165.122.86/32"
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                removed = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped not in soundcloud_domains:
                        new_lines.append(line)
                    else:
                        removed.append(line_stripped)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                removed = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped not in soundcloud_ips:
                        new_lines.append(line)
                    else:
                        removed.append(line_stripped)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            self.show_notification(tr('soundcloud_removed'), 3000)
            return True
            
        except Exception:
            return False

    def check_soundcloud_enabled(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            
            if not list_general_path.exists():
                return False
            
            with open(list_general_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return "soundcloud.com" in content
            
        except Exception:
            return False
        
    def add_facebook_instagram_unblock(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            ipset_all_path = ZAPRET_CORE_DIR / "lists" / "ipset-all.txt"
            
            meta_domains = [
                "facebook.com",
                "www.facebook.com",
                "fb.com",
                "www.fb.com",
                "fbcdn.net",
                "www.fbcdn.net",
                "static.xx.fbcdn.net",
                "scontent.xx.fbcdn.net",
                "graph.facebook.com",
                "api.facebook.com",
                "m.facebook.com",
                "business.facebook.com",
                "developers.facebook.com",
                "connect.facebook.net",
                "facebook.net",
                "fbcdn-profile-a.akamaihd.net",
                "fbstatic-a.akamaihd.net",
                "fbexternal-a.akamaihd.net",

                "instagram.com",
                "www.instagram.com",
                "cdninstagram.com",
                "www.cdninstagram.com",
                "scontent.cdninstagram.com",
                "graph.instagram.com",
                "api.instagram.com",
                "i.instagram.com",
                "instagr.am",
                "www.instagr.am",

                "meta.com",
                "www.meta.com",
                "cdn.meta.com",
                "metacdn.com",
                "whatsapp.com",
                "www.whatsapp.com",
            ]
            
            meta_ips = [
                "31.13.24.0/21",
                "31.13.64.0/18",
                "66.220.144.0/20",
                "69.63.176.0/20",
                "69.171.224.0/19",
                "74.119.76.0/22",
                "103.4.96.0/22",
                "129.134.0.0/16",
                "147.75.208.0/20",
                "157.240.0.0/16",
                "173.252.64.0/18",
                "179.60.192.0/22",
                "185.60.216.0/22",
                "185.89.216.0/22",
                "199.96.56.0/21",
                "204.15.20.0/22",
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    existing = f.read()
                
                added = []
                with open(list_general_path, 'a', encoding='utf-8') as f:
                    for domain in meta_domains:
                        if domain not in existing:
                            f.write(f"{domain}\n")
                            added.append(domain)
            else:
                return False
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    existing = f.read()
                
                added = []
                with open(ipset_all_path, 'a', encoding='utf-8') as f:
                    for ip in meta_ips:
                        if ip not in existing:
                            f.write(f"{ip}\n")
                            added.append(ip)
            
            self.show_notification(tr('meta_unblocked'), 3000)
            return True
            
        except Exception as e:
            self.log_to_diagnostic(f"Error adding Meta rules: {e}")
            return False

    def remove_facebook_instagram_unblock(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            ipset_all_path = ZAPRET_CORE_DIR / "lists" / "ipset-all.txt"
            
            meta_domains = [
                "facebook.com", "www.facebook.com", "fb.com", "www.fb.com",
                "fbcdn.net", "www.fbcdn.net", "static.xx.fbcdn.net", "scontent.xx.fbcdn.net",
                "graph.facebook.com", "api.facebook.com", "m.facebook.com", "business.facebook.com",
                "developers.facebook.com", "connect.facebook.net", "facebook.net",
                "fbcdn-profile-a.akamaihd.net", "fbstatic-a.akamaihd.net", "fbexternal-a.akamaihd.net",
                "instagram.com", "www.instagram.com", "cdninstagram.com", "www.cdninstagram.com",
                "scontent.cdninstagram.com", "graph.instagram.com", "api.instagram.com", "i.instagram.com",
                "instagr.am", "www.instagr.am", "meta.com", "www.meta.com", "cdn.meta.com",
                "metacdn.com", "whatsapp.com", "www.whatsapp.com"
            ]
            
            meta_ips = [
                "31.13.24.0/21", "31.13.64.0/18", "66.220.144.0/20", "69.63.176.0/20",
                "69.171.224.0/19", "74.119.76.0/22", "103.4.96.0/22", "129.134.0.0/16",
                "147.75.208.0/20", "157.240.0.0/16", "173.252.64.0/18", "179.60.192.0/22",
                "185.60.216.0/22", "185.89.216.0/22", "199.96.56.0/21", "204.15.20.0/22"
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                removed = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped not in meta_domains:
                        new_lines.append(line)
                    else:
                        removed.append(line_stripped)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                removed = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped not in meta_ips:
                        new_lines.append(line)
                    else:
                        removed.append(line_stripped)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            self.show_notification(tr('meta_removed'), 3000)
            return True
            
        except Exception:
            return False

    def check_meta_enabled(self):
        try:
            list_general_path = ZAPRET_CORE_DIR / "lists" / "list-general.txt"
            
            if not list_general_path.exists():
                return False
            
            with open(list_general_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return "facebook.com" in content or "instagram.com" in content
            
        except Exception:
            return False

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

        if hasattr(self, '_cached_processes') and (current_time - self._last_process_time < 1.5):
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
            processes = processes[:40]
            
        except Exception as e:
            self.log_to_diagnostic(f"{tr('error_traffic_collection')}: {e}")
        
        if not processes:
            processes.append({
                'name': tr('traffic_no_connections'),
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
        
        if len(self.hostname_cache) > self.hostname_cache_maxsize:
            to_remove = len(self.hostname_cache) - self.hostname_cache_maxsize
            oldest = sorted(self.hostname_cache_time.items(), key=lambda x: x[1])[:to_remove + 10]
            for ip_key, _ in oldest:
                self.hostname_cache.pop(ip_key, None)
                self.hostname_cache_time.pop(ip_key, None)
        
        if ip in self.hostname_cache and (current_time - self.hostname_cache_time.get(ip, 0)) < self.dns_cache_ttl:
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

    def is_any_connection_active(self):
        return self.is_connected or self.zapret.is_winws_running() or (hasattr(self, 'tg_proxy') and self.tg_proxy.is_running)

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
        dialog.title(tr('tg_instruction_title'))
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])

        secret = getattr(self, '_tg_secret', None)
        if not secret:
            secret = tr('error_secret_not_found')
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 310
        dialog.geometry(f"+{x}+{y}")
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(20, 5))
        
        title_label = tk.Label(title_frame, text=tr('tg_instruction_title'), 
                            font=("Segoe UI Variable", 20, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text=tr('tg_instruction_subtitle'),
                                font=("Segoe UI Variable", 11),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        subtitle_label.pack(pady=(5, 0))
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=2)
        separator.pack(fill=tk.X, padx=30, pady=10)
        instruction_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        instruction_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        steps = [
            ("1.", tr('tg_step1')),
            ("", tr('tg_step1_desc')),
            ("2.", tr('tg_step2')),
            ("", tr('tg_step2_desc')),
            ("3.", tr('tg_step3')),
            ("", tr('tg_type')),
            ("", tr('tg_host')),
            ("", tr('tg_port')),
        ]
        
        current_step = 0
        
        for i, step in enumerate(steps):
            text, desc = step
            if text:
                step_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                step_frame.pack(fill=tk.X, pady=(10 if current_step > 0 else 0, 2))
                
                step_num = tk.Label(step_frame, text=text, font=("Segoe UI Variable", 13, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                step_num.pack(side=tk.LEFT)
                
                step_text = tk.Label(step_frame, text=desc, font=("Segoe UI Variable", 11),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                step_text.pack(side=tk.LEFT, padx=(5, 0))
                current_step += 1
            else:
                sub_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                sub_frame.pack(fill=tk.X, pady=1)
                
                spacer = tk.Label(sub_frame, text="   ", font=("Segoe UI Variable", 11),
                                fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                spacer.pack(side=tk.LEFT)
                
                bullet = tk.Label(sub_frame, text="▸", font=("Segoe UI Variable", 10),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                bullet.pack(side=tk.LEFT, padx=(10, 5))
                
                sub_text = tk.Label(sub_frame, text=desc, font=("Segoe UI Variable", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
                sub_text.pack(side=tk.LEFT)
        
        link_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
        link_frame.pack(fill=tk.X, pady=(10, 5))
        
        spacer = tk.Label(link_frame, text="   ", font=("Segoe UI Variable", 11),
                        fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        spacer.pack(side=tk.LEFT)
        
        bullet = tk.Label(link_frame, text="▸", font=("Segoe UI Variable", 10),
                        fg=self.colors['accent'], bg=self.colors['bg_light'])
        bullet.pack(side=tk.LEFT, padx=(10, 5))
        
        copy_frame = tk.Frame(link_frame, bg=self.colors['bg_light'], cursor="hand2")
        copy_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        link_text = tr('tg_copy_secret')
        copy_label = tk.Label(copy_frame, text=link_text, font=("Segoe UI Variable", 10),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        copy_label.pack()
        
        def copy_link(event=None):
            secret = getattr(self, '_tg_secret', None)
            if not secret:
                secret = tr('error_secret_not_found')
            self.root.clipboard_clear()
            self.root.clipboard_append(f"{secret}")
            self.root.update()
            copy_label.config(text=tr('tg_copied'), fg=self.colors['accent_green'])
            self.show_notification(tr('notification_copied_secret'), 1500)
        
        copy_label.bind("<Button-1>", copy_link)
        
        def on_enter(event):
            copy_label.config(fg=self.colors['accent_hover'], font=("Segoe UI Variable", 10, "underline"))
            copy_frame.config(cursor="hand2")
        
        def on_leave(event):
            copy_label.config(fg=self.colors['accent'], font=("Segoe UI Variable", 10))
        
        copy_label.bind("<Enter>", on_enter)
        copy_label.bind("<Leave>", on_leave)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=30, pady=15)
        dont_show_var = tk.BooleanVar(value=False)

        dont_show_cb = tk.Checkbutton(
            bottom_frame,
            text=tr('tg_dont_show'),
            variable=dont_show_var,
            bg=self.colors['bg_medium'],
            fg=self.colors['text_secondary'],
            selectcolor=self.colors['bg_medium'],
            activebackground=self.colors['bg_medium'],
            activeforeground=self.colors['text_secondary'],
            highlightthickness=0,
            bd=0,
            padx=0,
            font=("Segoe UI Variable", 10)
        )
        dont_show_cb.pack(side=tk.LEFT)

        close_btn = RoundedButton(
            bottom_frame,
            text=tr('button_close'),
            command=lambda: self._cancel_tg_proxy_mode(dialog, dont_show_var.get()),
            width=100, height=35,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        close_btn.pack(side=tk.RIGHT)
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

    def _start_tg_proxy_mode(self, dialog, dont_show=False):
        if dialog:
            dialog.destroy()
        
        if dont_show:
            self._tg_instruction = True
            self.save_settings()
        
        self._do_start_tg_proxy()

    def _cancel_tg_proxy_mode(self, dialog, dont_show=False):
        if dialog:
            dialog.destroy()
        
        if dont_show:
            self._tg_instruction = True
            self.save_settings()
        
        if not self.is_connected:
            self.update_status(tr('status_ready'), self.colors['text_secondary'])
            if hasattr(self, 'connect_btn') and self.connect_btn:
                self.connect_btn.set_enabled(True)
        else:
            pass
        
    def _on_combined_start_success(self, mode_name):
        if hasattr(self, 'mode_label') and self.mode_label:
            self.mode_label.config(text=mode_name, fg=self.colors['accent_green'])
        self.update_status(f"{tr('status_connected')}", 
                        self.colors['accent_green'])
        self.update_ui_state()
        self.save_settings()
        self.root.after(100, self.update_stats_display)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

        self.root.after(500, self.update_tray_icon_state)

    def _on_combined_start_failed(self, error_msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_startup'), f"{tr('error_startup')}: {error_msg}")
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

        if hasattr(self, 'tg_proxy') and self.tg_proxy:
            self.tg_proxy.stop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretLauncher(root)
    root.mainloop()
