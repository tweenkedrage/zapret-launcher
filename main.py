# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
import pywinstyles
from tkinter import messagebox, ttk
from gui.pages import Pages
from tg_proxy.config import proxy_config
from gui.page.lists_page import check_zapret_folder
from gui.tray import ModernSystemTray
from typing import Optional, Tuple, List, Dict
from utils.languages import tr, get_languages
from typing import List, Optional
from gui.dialogs import Dialogs
from gui.theme import get_theme, get_theme_names
from datetime import datetime
from utils.check_lists import check_lists_for_duplicates
from gui.splash import SplashWindow
from gui.widgets import RoundedButton
try:
    from tg_proxy import run_proxy, run
    TG_PROXY_AVAILABLE = True
except ImportError:
    TG_PROXY_AVAILABLE = False
import subprocess
import os
import json
import time
import shutil
import threading
import webbrowser
import getpass
import tempfile
import asyncio
import psutil
import socket
import winreg
from pathlib import Path
import sys
import re
import ctypes
import urllib.request
from ctypes import windll, byref, c_int
from typing import Optional, List, Tuple
from config import CURRENT_VERSION, CURRENT_BUILD, BASE_DIR, APPDATA_DIR, CONFIG_FILE, ZAPRET_CORE_DIR, LISTS_DIR, TG_HOST, TG_PORT, TG_FAKE_TLS, TG_FAKE_TLS_DOMAIN

def check_single_instance():
    mutex_name = "ZapretLauncher_SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:
        return False, None
    return True, mutex

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
        self._cache_duration = 1.0
        self._cached_stats = (0, 0)
        self._cached_time = 0
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
        self.total_up_bytes = 0
        self.total_down_bytes = 0
        self.current_speed_up = 0
        self.current_speed_down = 0
        self.last_up, self.last_down = self._get_network_stats()
        self.last_update_time = time.time()
        
    def end_session(self):
        self.is_monitoring = False
        self.disconnection_count += 1
        
    def _get_network_stats(self):
        current_time = time.time()
        if hasattr(self, '_cached_stats') and hasattr(self, '_cached_time'):
            if current_time - self._cached_time < self._cache_duration:
                return self._cached_stats
        
        try:
            counters = psutil.net_io_counters()
            recv = counters.bytes_recv
            sent = counters.bytes_sent
            self._cached_stats = (recv, sent)
            self._cached_time = current_time
            return recv, sent
        except Exception:
            return 0, 0
    
    def update_speed(self):
        if not self.is_monitoring:
            return
        try:
            current_up, current_down = self._get_network_stats()
            now = time.time()
            time_diff = now - self.last_update_time
            
            if current_up > self.last_up:
                self.total_up_bytes += (current_up - self.last_up)
            if current_down > self.last_down:
                self.total_down_bytes += (current_down - self.last_down)
            
            if time_diff >= 0.5:
                up_diff = max(0, current_up - self.last_up)
                down_diff = max(0, current_down - self.last_down)
                
                raw_speed_up = up_diff / time_diff if time_diff > 0 else 0
                raw_speed_down = down_diff / time_diff if time_diff > 0 else 0
                
                self.current_speed_up = self.current_speed_up * 0.7 + raw_speed_up * 0.3
                self.current_speed_down = self.current_speed_down * 0.7 + raw_speed_down * 0.3
                
                self.last_update_time = now
            
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
    def __init__(self, host=None, port=None, fake_tls_domain=None):
        self._thread = None
        self._running = False
        self._port = port if port is not None else 1443
        self._host = host if host is not None else '127.0.0.1'
        self._fake_tls_domain = fake_tls_domain if fake_tls_domain is not None else ''
        self._secret = None
        self._stop_event = None
        self._log_callback = None

    def set_log_callback(self, callback):
        self._log_callback = callback
        run.set_log_callback(callback)
    
    def _log(self, message):
        if self._log_callback:
            self._log_callback("info", message)

    def set_secret(self, secret):
        self._secret = secret
        if self._running:
            self.stop()
            time.sleep(1)
            self.start()
    
    def update_config(self, host, port):
        was_running = self._running
        if was_running:
            self.stop()
            time.sleep(1)
        
        self._host = host
        self._port = port
        
        if was_running:
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
            if self._is_port_open(self._port):
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
                
                proxy_config.fake_tls_domain = self._fake_tls_domain if hasattr(self, '_fake_tls_domain') else ''
                run_proxy(self._host, self._port, self._secret, self._stop_event)
            except Exception:
                pass

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
            except Exception:
                pass
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

    @property
    def is_running(self):
        return self._running and self._is_port_open(self._port)
    
    @property
    def host(self):
        return self._host
    
    @property
    def port(self):
        return self._port
    
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
        
    def get_resource_path(self, relative_path):
        exe_dir = Path(sys.executable).parent
        local_path = exe_dir / relative_path
        
        if local_path.exists():
            return local_path
        
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            return base_path / relative_path
        else:
            return Path(__file__).parent / relative_path
        
    def ensure_resources(self):
        required_version = self.get_resource_core_version()
        
        if required_version == "0.0":
            messagebox.showerror(
                "Error",
                "File version.txt was not found in the launcher resources\n"
                "Reinstall the launcher"
            )
            sys.exit(1)
        
        version_file = self.zapret_dir / "version.txt"
        
        if version_file.exists():
            current_version = version_file.read_text(encoding='utf-8').strip()
            
            if current_version == required_version and self.bin_dir.exists():
                return
        
        self._copy_zapret_core_from_resources()

    def _copy_zapret_core_from_resources(self):
        try:
            source_dir = self.get_resource_path("zapret_core")
            
            if not source_dir.exists():
                raise Exception(f"Source directory not found: {source_dir}")
            
            if self.zapret_dir.exists():
                shutil.rmtree(self.zapret_dir)
            
            self.zapret_dir.mkdir(parents=True, exist_ok=True)
            
            for item in source_dir.iterdir():
                dest_item = self.zapret_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
            
            version_file = self.zapret_dir / "version.txt"
            if not version_file.exists():
                required_version = self.get_resource_core_version()
                version_file.write_text(required_version, encoding='utf-8')
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to install zapret_core:\n{str(e)}"
            )
            sys.exit(1)

    def get_resource_core_version(self):
        resource_version_file = self.get_resource_path("zapret_core/version.txt")
        if resource_version_file.exists():
            try:
                return resource_version_file.read_text(encoding='utf-8').strip()
            except Exception:
                pass
        return "0.0"
            
    def load_strategies(self):
        if not self.zapret_dir.exists():
            return
            
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
        
        subprocess.run(['sc', 'stop', 'WinDivert'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.5)
        subprocess.run(['sc', 'start', 'WinDivert'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.5)
            
        if not check_zapret_folder():
            return False, tr('error_zapret_folder')

        strategy_path = self.zapret_dir / strategy_name
        if not strategy_path.exists():
            return False, f"{tr('error_strategy_not_found')} {strategy_name}"
            
        try:
            self.stop_current_strategy()
            if hasattr(self, 'parent') and self.parent:
                self.parent.log_event("winws", f"Starting winws.exe with strategy {strategy_name}")

            self.current_process = subprocess.Popen(
                ["cmd.exe", "/c", str(strategy_path)],
                cwd=str(self.zapret_dir),
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(1.0)
            for _ in range(10):
                if self.is_winws_running():
                    return True, f"{tr('status_strategy_started')} {self.get_strategy_display_name(strategy_name)}"
                time.sleep(0.5)
            return False, tr('error_winws_not_found')
        except Exception as e:
            if hasattr(self, 'parent') and self.parent:
                self.parent.log_event("error", f"Error starting strategy {strategy_name} {str(e)}")
            return False, f"{tr('error_startup')} {str(e)}"
            
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
            return True, f"Game Filter: {tr('status_enabled') if self.game_filter_enabled else tr('status_disabled')}\n{tr('restart_zapret')}"
            
        elif command == "ipset_filter":
            modes = ["none", "loaded", "any"]
            current_idx = modes.index(self.ipset_filter_mode)
            self.ipset_filter_mode = modes[(current_idx + 1) % 3]
            return True, f"IPSet Filter: {self.ipset_filter_mode}\n{tr('restart_zapret')}"
        return False, f"{tr('error_unknown_command')} {command}"

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
        self._connecting = False
        self.main_status = None
        self.stats_frame = None
        self.stats_time_label = None
        self.stats_traffic_label = None
        self.stats_total_label = None
        self.stats_speed_up_label = None
        self.stats_speed_down_label = None
        self.stats_rtt_label = None

        self.tg_host = TG_HOST
        self.tg_port = TG_PORT
        self.tg_fake_tls = TG_FAKE_TLS
        self.tg_fake_tls_domain = TG_FAKE_TLS_DOMAIN

        self._shutdown_update_timer = None
        self._shutdown_first_update_done = False

        self.strategy_var = tk.StringVar()
        self.tgws_var = tk.BooleanVar(value=False)

        self._tg_instruction = False
        self._tg_secret = None

        self._show_vpn_detection = False
        self._hide_duplicates_warning = False

        self._notification_queue = []
        self._notification_active = False
        self._current_notification = None

        self.update_intervals = [1, 5, 10, 30, 60, None]
        self.update_interval_index = 1
        self.update_interval = self.update_intervals[self.update_interval_index]
        self.update_timer_id = None

        self.rtt_timer_id = None
        self.rtt_update_interval = 30000

        self.last_selected_index = -1

        self._cached_rtt = -1
        self._cached_rtt_time = 0
        self.rtt_cache_duration = 30

        self.MAX_HISTORY_SIZE = 100
        self.MAX_HISTORY_AGE = 3600

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
                BASE_DIR / "resources" / "icon.ico"
            ]
            
            icon_loaded = False
            for path in icon_paths:
                if path and path.exists():
                    try:
                        if path.suffix.lower() == '.ico':
                            self.root.iconbitmap(default=str(path))
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
                "Zapret Launcher",
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
        self.tg_proxy = TGProxyServer(host=self.tg_host, port=self.tg_port, fake_tls_domain=self.tg_fake_tls_domain if self.tg_fake_tls else '')
        self.tg_proxy.set_log_callback(self.log_event)
        
        self.ensure_appdata_dir()
        self.ensure_custom_list_file()
        self.languages = get_languages()
        self.current_theme = 'Default'
        self.load_settings()
        self.root.after(100, self.check_lists_for_duplicates)
        self.apply_theme()

        if not self._tg_secret:
            self._tg_secret = os.urandom(16).hex()
            self.save_settings()

        self.tg_proxy.set_secret(getattr(self, '_tg_secret', None))
        
        self.setup_ui()
        self.update_check_timer_id = None
        self.start_update_checker()
        self.root.after(100, self.check_initial_status)
        self.show_main_page()
        self.dialogs = Dialogs(self)
                
        self.tray_icon = ModernSystemTray(self)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def ensure_custom_list_file(self):
        try:
            lists_dir = LISTS_DIR
            custom_list_path = lists_dir / "list-custom.txt"
            
            if not lists_dir.exists():
                lists_dir.mkdir(parents=True, exist_ok=True)
            
            if not custom_list_path.exists():
                custom_list_path.touch()
                
                with open(custom_list_path, 'w', encoding='utf-8') as f:
                    f.write("zapret-launcher.ru\n")
                
        except Exception:
            pass

    def update_tray_icon_state(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_icon_state()
            except Exception:
                pass

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
        except Exception:
            pass

    def _force_exit(self):
        try:
            self._stop_windivert_before_restart()
            self.zapret.stop_current_strategy()
            if hasattr(self, 'tg_proxy'):
                self.tg_proxy.stop()
            if hasattr(self, 'tray_icon') and self.tray_icon and hasattr(self.tray_icon, 'icon'):
                try:
                    self.tray_icon.icon.stop()
                except:
                    pass
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
                        if hasattr(btn, 'update_theme'):
                            btn.update_theme(self.current_theme)
                        if hasattr(btn, 'update_colors'):
                            btn.update_colors(
                                self.colors['bg_light'], 
                                self.colors['text_secondary'], 
                                self.colors['accent']
                            )

    def apply_theme(self):
        self.colors = get_theme(self.current_theme)
        self.root.configure(bg=self.colors['bg_dark'])
        self.setup_scrollbar_style()
        self.update_ui_colors()
        self._update_window_title_color()
        
        if hasattr(self, 'pages') and self.pages:
            self.pages.colors = self.colors
            
            for page_name in ['main_page', 'service_page', 'lists_page', 
                            'traffic_page', 'settings_page', 'logs_page']:
                if hasattr(self.pages, page_name):
                    page = getattr(self.pages, page_name)
                    if page:
                        page.configure(bg=self.colors['bg_dark'])
                        
            if hasattr(self, 'left_panel') and self.left_panel:
                self.left_panel.configure(bg=self.colors['bg_medium'])
                
            self.update_nav_buttons_colors()

        if hasattr(self, 'pages'):
            self.pages.update_animation_color()

    def set_dialog_header_color(self, dialog):
        try:
            header_color = self.colors['bg_medium'] if hasattr(self, 'colors') else "#1A1A1F"
            pywinstyles.change_header_color(dialog, header_color)
        except ImportError:
            pass
        except Exception:
            pass

    def _update_window_title_color(self):
        try:
            if self.current_theme == 'Default':
                header_color = "#0F0F12"
            elif self.current_theme == 'Pink':
                header_color = "#1E1B2E"
            else:
                header_color = self.colors['bg_dark']
            
            pywinstyles.change_header_color(self.root, header_color)
            
        except ImportError:
            pass
        except Exception:
            pass

    def _stop_windivert_before_restart(self):
        try:
            subprocess.run(['sc', 'stop', 'WinDivert'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.5)
        except:
            pass

    def quit_from_tray(self):
        self.save_settings()
        self.zapret.stop_current_strategy()
        self._stop_windivert_before_restart()
        if hasattr(self, 'tg_proxy'):
            self.tg_proxy.stop()

        self.stop_update_checker()
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        sys.exit(0)

    def force_tray_menu_update(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.force_update_menu()
            except Exception:
                pass

    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_left_panel()
        self.content_panel = tk.Frame(self.main_container, bg=self.colors['bg_dark'])
        self.content_panel.place(x=250, y=0, width=950, height=800)
        self.pages = Pages(self)

    def log_event(self, event_type: str, message: str, mode_name: str = None):
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d.%m.%Y")
        
        if event_type == "connect" and mode_name:
            log_entry = f"[{date_str} {timestamp}] Mode {mode_name} is connected"
        
        elif event_type == "disconnect" and mode_name:
            log_entry = f"[{date_str} {timestamp}] Disconnected from mode {mode_name}"
        
        elif event_type == "error":
            log_entry = f"[{date_str} {timestamp}] Error: {message}"
        
        elif event_type == "winws":
            log_entry = f"[{date_str} {timestamp}] {message}"
        
        elif event_type == "info":
            log_entry = f"[{date_str} {timestamp}] {message}"

        elif event_type == "success":
            log_entry = f"[{date_str} {timestamp}] {message}"

        else:
            log_entry = f"[{date_str} {timestamp}] {message}"
        
        try:
            log_file = APPDATA_DIR / "logs.txt"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception:
            pass
        
        if hasattr(self, 'pages') and hasattr(self.pages, 'logs_page_obj'):
            if hasattr(self.pages, 'current_page') and self.pages.current_page == "logs":
                if not hasattr(self, '_log_update_scheduled') or not self._log_update_scheduled:
                    self._log_update_scheduled = True
                    self.root.after(300, self._scheduled_log_update)

    def _scheduled_log_update(self):
        self._log_update_scheduled = False
        if hasattr(self, 'pages') and hasattr(self.pages, 'logs_page_obj'):
            self.pages.logs_page_obj.update_logs_display()

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
                BASE_DIR / "resources" / "icon.png"
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
        except Exception:
            pass

        nav_buttons = [
            (tr('main_title'), self.show_main_page),
            (tr('service_title'), self.show_service_page),
            (tr('lists_title'), self.show_lists_page),
            (tr('traffic_title'), self.show_traffic_page),
            (tr('logs_title'), self.show_logs_page),
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
                theme_name=self.current_theme
            )

            btn._command = command
            btn.hover_color = self.colors['accent']
            btn.normal_color = self.colors['bg_light']
            btn.update_colors(self.colors['bg_light'], self.colors['text_secondary'], self.colors['accent'])
            btn.pack()
            
            btn.bind("<Enter>", lambda e: btn.config(cursor="hand2"))
            btn.bind("<Leave>", lambda e: btn.config(cursor=""))
        
        separator = tk.Frame(left_panel, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=20)
        
        self.credit_frame = tk.Frame(left_panel, bg=self.colors['bg_medium'])
        self.credit_frame.pack(side=tk.BOTTOM, pady=(0, 30), fill=tk.X)

        self.left_status = tk.Label(
            self.credit_frame,
            text="●",
            font=("Segoe UI Variable", 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        self.left_status.pack()
        
        version_frame = tk.Frame(self.credit_frame, bg=self.colors['bg_medium'])
        version_frame.pack()

        tk.Label(
            version_frame,
            text=f"v{CURRENT_VERSION} ({CURRENT_BUILD})",
            font=("Segoe UI Variable", 8),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        ).pack(side=tk.LEFT)
        
        self.credit_label = tk.Label(
            self.credit_frame,
            text="zapret-launcher.ru",
            font=("Segoe UI Variable", 8),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium'],
            cursor="hand2"
        )
        self.credit_label.pack(pady=(2, 0))

        self.credit_label.bind("<Enter>", lambda e: self.credit_label.config(fg=self.colors['accent']))
        self.credit_label.bind("<Leave>", lambda e: self.credit_label.config(fg=self.colors['text_secondary']))
        self.credit_label.bind("<Button-1>", lambda e: self.open_website())

    def show_update_label(self):
        try:
            if not hasattr(self, 'foundupdates_frame'):
                if hasattr(self, 'credit_frame'):
                    self.foundupdates_frame = tk.Frame(self.credit_frame, bg=self.colors['bg_medium'])
                    
                    self.foundupdates_label = tk.Label(
                        self.foundupdates_frame,
                        text=tr('update_available'),
                        font=("Segoe UI Variable", 8),
                        fg=self.colors['accent_green'],
                        bg=self.colors['bg_medium'],
                        cursor="hand2"
                    )
                    self.foundupdates_label.pack(pady=(2, 0))
                    
                    self.foundupdates_label.bind("<Enter>", lambda e: self.foundupdates_label.config(fg=self.colors['accent_darkgreen']))
                    self.foundupdates_label.bind("<Leave>", lambda e: self.foundupdates_label.config(fg=self.colors['accent_green']))
                    self.foundupdates_label.bind("<Button-1>", lambda e: self.root.after(500, self.install_update))
            else:
                pass
            
            if hasattr(self, 'foundupdates_frame'):
                self.foundupdates_frame.pack(pady=(5, 0))
        except Exception:
            pass

    def hide_update_label(self):
        try:
            if hasattr(self, 'foundupdates_frame'):
                self.foundupdates_frame.pack_forget()
        except Exception:
            pass

    def check_for_updates(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/plain',
                'Connection': 'close'
            }
            
            buildnumber_url = "https://zapret-launcher.ru/updater/docs/build_number.txt"
            req = urllib.request.Request(buildnumber_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                latest_build = response.read().decode('utf-8').strip()
            
            current_build = CURRENT_BUILD
            need_launcher_update = self._compare_builds(current_build, latest_build)
            
            if need_launcher_update:
                self.root.after(0, self.show_update_label)
                return
            
            current_zapret_version = self.get_current_zapret_version()
            latest_zapret_version = None
            
            try:
                zapret_version_url = "https://zapret-launcher.ru/updater/docs/zapret_version.txt"
                req_zapret = urllib.request.Request(zapret_version_url, headers=headers)
                with urllib.request.urlopen(req_zapret, timeout=10) as response:
                    latest_zapret_version = response.read().decode('utf-8').strip()
            except Exception:
                self.root.after(0, self.hide_update_label)
                return
            
            need_zapret_update = False
            if latest_zapret_version and current_zapret_version:
                need_zapret_update = self._compare_zapret_versions(current_zapret_version, latest_zapret_version)
            
            if need_zapret_update:
                self.root.after(0, self.show_update_label_zapret)
            else:
                self.root.after(0, self.hide_update_label)
                
        except Exception as e:
            self.root.after(0, self.hide_update_label)

    def show_update_label_zapret(self):
        try:
            if not hasattr(self, 'foundupdates_frame_zapret'):
                if hasattr(self, 'credit_frame'):
                    self.foundupdates_frame_zapret = tk.Frame(self.credit_frame, bg=self.colors['bg_medium'])
                    
                    self.foundupdates_label_zapret = tk.Label(
                        self.foundupdates_frame_zapret,
                        text=tr('update_available'),
                        font=("Segoe UI Variable", 8),
                        fg=self.colors['accent_green'],
                        bg=self.colors['bg_medium'],
                        cursor="hand2"
                    )
                    self.foundupdates_label_zapret.pack(pady=(2, 0))
                    
                    self.foundupdates_label_zapret.bind("<Enter>", lambda e: self.foundupdates_label_zapret.config(fg=self.colors['accent_darkgreen']))
                    self.foundupdates_label_zapret.bind("<Leave>", lambda e: self.foundupdates_label_zapret.config(fg=self.colors['accent_green']))
                    self.foundupdates_label_zapret.bind("<Button-1>", lambda e: self.root.after(500, self.install_zapret_update))
            else:
                pass
            
            if hasattr(self, 'foundupdates_frame_zapret'):
                self.foundupdates_frame_zapret.pack(pady=(5, 0))
        except Exception:
            pass

    def install_zapret_update(self):
        try:
            latest_zapret_version = None
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/plain',
                'Connection': 'close'
            }
            
            try:
                req_zapret = urllib.request.Request(
                    "https://zapret-launcher.ru/updater/docs/zapret_version.txt",
                    headers=headers
                )
                with urllib.request.urlopen(req_zapret, timeout=5) as response:
                    latest_zapret_version = response.read().decode('utf-8').strip()
            except Exception:
                latest_zapret_version = "?"
            
            if latest_zapret_version != "?":
                version_text = f"v{latest_zapret_version}"
            else:
                version_text = tr('update_available')
            
            message = f"{tr('update_available_question')}: {version_text}\n{tr('update_ask_now')}"
            
            result = messagebox.askyesno(
                tr('update_zapret_title'),
                message
            )
            
            if result:
                self.save_settings()
                
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = sys.argv[0]
                
                args = [exe_path, '--update-zapret-only']
                for arg in sys.argv[1:]:
                    if arg not in ['--no-splash', '--from-splash']:
                        args.append(arg)
                
                subprocess.Popen(args)
                self.root.quit()
                self.root.destroy()
                sys.exit(0)
                
        except Exception:
            pass

    def install_update(self):
        try:
            latest_version = None
            latest_build = None
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/plain',
                'Connection': 'close'
            }
            
            try:
                req_version = urllib.request.Request(
                    "https://zapret-launcher.ru/updater/docs/version_launcher.txt",
                    headers=headers
                )
                with urllib.request.urlopen(req_version, timeout=5) as response:
                    latest_version = response.read().decode('utf-8').strip()
            except Exception:
                latest_version = "?"
            
            try:
                req_build = urllib.request.Request(
                    "https://zapret-launcher.ru/updater/docs/build_number.txt",
                    headers=headers
                )
                with urllib.request.urlopen(req_build, timeout=5) as response:
                    latest_build = response.read().decode('utf-8').strip()
            except Exception:
                latest_build = "?"
            
            if latest_version != "?" and latest_build != "?":
                version_text = f"v{latest_version} (build {latest_build})"
            elif latest_version != "?":
                version_text = f"v{latest_version}"
            else:
                version_text = tr('update_available')
            
            message = f"{tr('update_available_question')}: {version_text}\n{tr('update_ask_now')}"
            
            result = messagebox.askyesno(
                tr('update_title'),
                message
            )
            
            if result:
                self.save_settings()
                
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = sys.argv[0]
                
                args = [exe_path]
                for arg in sys.argv[1:]:
                    if arg not in ['--no-splash', '--from-splash']:
                        args.append(arg)
                
                subprocess.Popen(args)
                self.root.quit()
                self.root.destroy()
                sys.exit(0)
                
        except Exception:
            pass

    def start_with_mode(self, mode):
        if self.is_connected:
            return
        
        self._connecting = True
        self.force_tray_menu_update()
        
        try:
            if mode["name"] == tr('mode_zapret_tgproxy'):
                if not self.zapret.available_strategies:
                    messagebox.showerror(tr('error_no_strategies'), tr('error_no_strategies'))
                    self._connecting = False
                    self.force_tray_menu_update()
                    return
                
                self._pending_mode = mode
                self.dialogs.show_strategy_selector(mode["name"])
                return
            
            if mode["name"] == "Telegram Proxy":
                self._start_tg_proxy_direct()
                return
            
            if mode["name"] == tr('mode_standard'):
                if not self.zapret.available_strategies:
                    messagebox.showerror(tr('error_no_strategies'), tr('error_no_strategies'))
                    self._connecting = False
                    self.force_tray_menu_update()
                    return
                
                self._pending_mode = mode
                self.dialogs.show_strategy_selector(mode["name"])
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
            
            self._connecting = False
            self.force_tray_menu_update()
            
        except Exception:
            self._connecting = False
            self.force_tray_menu_update()
            raise

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
        
        self.log_event("info", f"New secret-key has been generated: {self._tg_secret[:8]}...")
        self.tg_proxy.set_secret(self._tg_secret)

        if hasattr(self, 'pages') and hasattr(self.pages, 'settings_page_obj'):
            self.pages.settings_page_obj.update_secret_display()
        
        if self.tg_fake_tls and self.tg_fake_tls_domain:
            domain_hex = self.tg_fake_tls_domain.encode('ascii').hex()
            link = f"ee{self._tg_secret}{domain_hex}"
            notification_text = tr('notification_updated_secret')
        else:
            link = self._tg_secret
            notification_text = tr('notification_updated_secret')
        
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        self.root.update()
        self.show_notification(notification_text, 3000)
        
    def _do_start_tg_proxy(self):
        self._reset_traffic_history()
        self.update_status(tr('status_starting'), self.colors['accent'])
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
                self.root.after(0, lambda: self._on_tg_proxy_failed_direct(str(e)))
            finally:
                if not self.is_connected:
                    self._connecting = False
                    self.force_tray_menu_update()
        
        threading.Thread(target=start_thread, daemon=True).start()

    def _on_tg_proxy_started_direct(self):
        if not self.is_connected:
            self.is_connected = True
            self.stats.start_session()
            self.start_stats_monitoring()
            
            self.mode_label.config(text="Telegram Proxy", fg=self.colors['accent_green'])
            self.update_status(tr('status_connected'), self.colors['accent_green'])
            self.update_ui_state()
            self.save_settings()
            self.root.after(100, self.update_stats_display)
            self.log_event("connect", "", "Telegram Proxy")

            if self.tg_fake_tls:
                self.root.after(1000, self.copy_tg_link_to_clipboard)

            if not self._tg_instruction:
                self.root.after(500, self.dialogs.show_tg_proxy_instruction)

            self._connecting = False
            self.force_tray_menu_update()
        
        self.connect_btn.set_enabled(True)
        self.root.after(500, self.update_tray_icon_state)

    def _on_tg_proxy_failed_direct(self, error_msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_no_connection'), f"{error_msg}")
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def _cancel_strategy_selection(self, dialog):
        dialog.destroy()
        self._connecting = False
        self.force_tray_menu_update()

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

        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_icon_state()
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
        current_time = time.time()

        if hasattr(self, '_cached_rtt_time') and self._cached_rtt > 0:
            if (current_time - self._cached_rtt_time) < self.rtt_cache_duration:
                return self._cached_rtt

        try:
            result = subprocess.run(
                ['ping', '-n', '1', '8.8.8.8'],
                capture_output=True, text=True, encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3
            )

            rtt = -1
            
            if result.returncode == 0:
                output = result.stdout
                
                match = re.search(r'(?:время|time)[=<>]\s*(\d+)\s*мс', output, re.IGNORECASE)
                if match:
                    rtt = float(match.group(1))
                else:
                    match = re.search(r'time[=<>](\d+)ms', output, re.IGNORECASE)
                    if match:
                        rtt = float(match.group(1))
                    else:
                        match = re.search(r'(\d+)\s*мс', output, re.IGNORECASE)
                        if match:
                            rtt = float(match.group(1))
            
            if rtt > 0:
                self._cached_rtt = rtt
                self._cached_rtt_time = current_time
            return rtt
            
        except Exception:
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
                interval = 1000
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
            interval = 1000
        elif self.update_interval > 0:
            interval = max(500, int(self.update_interval * 1000))
        else:
            interval = 1000
        
        self.update_timer_id = self.root.after(interval, self._schedule_stats_update)

    def show_notification(self, message, duration=2000):
        try:
            if not self.root.winfo_viewable():
                return
            
            if hasattr(self, '_current_notification') and self._current_notification:
                try:
                    self._current_notification.destroy()
                except:
                    pass
            
            notification = tk.Toplevel(self.root)
            notification.overrideredirect(True)
            notification.configure(bg=self.colors['bg_medium'])
            notification._is_alive = True

            self._current_notification = notification

            try:
                notification.attributes('-topmost', True)
            except:
                pass
            
            def update_notification_position():
                if notification and notification.winfo_exists() and notification._is_alive:
                    try:
                        x = self.root.winfo_x() + self.root.winfo_width() - 310
                        y = self.root.winfo_y() + 50
                        notification.geometry(f"280x40+{x}+{y}")
                    except:
                        pass
            
            def on_root_configure(event=None):
                update_notification_position()
            
            self.root.bind('<Configure>', on_root_configure)
            
            def cleanup():
                try:
                    if notification and notification.winfo_exists():
                        notification._is_alive = False
                        notification.destroy()
                except:
                    pass
                try:
                    self.root.unbind('<Configure>', on_root_configure)
                except:
                    pass
                if self._current_notification == notification:
                    self._current_notification = None
            
            def on_iconify():
                if notification and notification.winfo_exists():
                    try:
                        notification.withdraw()
                    except:
                        pass

            def on_deiconify():
                if notification and notification.winfo_exists() and notification._is_alive:
                    try:
                        notification.deiconify()
                        update_notification_position()
                    except:
                        pass
            
            self.root.bind('<Unmap>', lambda e: on_iconify())
            self.root.bind('<Map>', lambda e: on_deiconify())
            
            def check_window_state():
                if notification and notification.winfo_exists() and notification._is_alive:
                    try:
                        is_active = self.root.focus_displayof() is not None
                        is_visible = self.root.winfo_viewable()
                        is_iconic = self.root.state() == 'iconic'
                        
                        if not is_visible or is_iconic or (not is_active and is_visible):
                            if notification.winfo_viewable():
                                notification.withdraw()
                        else:
                            if not notification.winfo_viewable():
                                notification.deiconify()
                                update_notification_position()
                                notification.lift()
                    except:
                        pass
                    notification.after(10, check_window_state)
            
            try:
                notification.attributes('-alpha', 0.95)
            except:
                pass
            
            x = self.root.winfo_x() + self.root.winfo_width() - 310
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
            
            check_window_state()
            
            def fade_in(alpha=0.0):
                if not self.root.winfo_viewable():
                    cleanup()
                    return
                if alpha < 0.95:
                    alpha += 0.1
                    try:
                        if notification and notification.winfo_exists() and notification._is_alive:
                            notification.attributes('-alpha', alpha)
                            notification.after(30, lambda: fade_in(alpha))
                    except:
                        cleanup()
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
                        cleanup()
                else:
                    cleanup()
            
            fade_in()
            
            def on_notification_click(event=None):
                cleanup()
            
            notification.bind("<Button-1>", on_notification_click)
            
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

    def set_autostart(self, enabled):
        try:
            if enabled:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
                
                xml_template = '''<?xml version="1.0" encoding="UTF-16"?>
                <Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
                <RegistrationInfo>
                    <Date>2024-01-01T00:00:00</Date>
                    <Author>Zapret Launcher</Author>
                    <Description>Auto Start</Description>
                </RegistrationInfo>
                <Triggers>
                    <LogonTrigger>
                    <Enabled>true</Enabled>
                    </LogonTrigger>
                </Triggers>
                <Principals>
                    <Principal id="Author">
                    <RunLevel>HighestAvailable</RunLevel>
                    <UserId>{user_id}</UserId>
                    <LogonType>InteractiveToken</LogonType>
                    </Principal>
                </Principals>
                <Settings>
                    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
                    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
                    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
                    <AllowHardTerminate>true</AllowHardTerminate>
                    <StartWhenAvailable>true</StartWhenAvailable>
                    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
                    <IdleSettings>
                    <StopOnIdleEnd>true</StopOnIdleEnd>
                    <RestartOnIdle>false</RestartOnIdle>
                    </IdleSettings>
                    <AllowStartOnDemand>true</AllowStartOnDemand>
                    <Enabled>true</Enabled>
                    <Hidden>false</Hidden>
                    <RunOnlyIfIdle>false</RunOnlyIfIdle>
                    <WakeToRun>false</WakeToRun>
                    <ExecutionTimeLimit>PT72H</ExecutionTimeLimit>
                    <Priority>7</Priority>
                    <RestartOnFailure>
                    <Interval>PT1M</Interval>
                    <Count>3</Count>
                    </RestartOnFailure>
                </Settings>
                <Actions Context="Author">
                    <Exec>
                    <Command>"{exe_path}"</Command>
                    <Arguments>--from-splash</Arguments>
                    </Exec>
                </Actions>
                </Task>'''
                
                user_id = getpass.getuser()
                xml = xml_template.format(exe_path=exe_path, user_id=user_id)

                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                    f.write(xml)
                    temp_xml = f.name
                
                subprocess.run(
                    ['schtasks', '/create', '/tn', 'ZapretLauncher', '/xml', temp_xml, '/f'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                try:
                    os.unlink(temp_xml)
                except:
                    pass
                
                self.log_event("info", f"Task scheduled for auto-start: {exe_path}")
                return True
            else:
                subprocess.run(
                    ['schtasks', '/delete', '/tn', 'ZapretLauncher', '/f'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.log_event("info", "Auto-start task removed")
                return True
        except Exception as e:
            self.log_event("error", f"Error setting auto-start: {e}")
            return False

    def check_autostart_status(self):
        try:
            result = subprocess.run(
                ['schtasks', '/query', '/tn', 'ZapretLauncher'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return 'ZapretLauncher' in result.stdout
        except:
            return False

    def safe_command(self, command):
        try:
            command()
        except Exception:
            pass

    def open_appdata_folder(self):
        try:
            os.startfile(APPDATA_DIR)
        except Exception:
            pass

    def refresh_page(self, page_name):
        page = getattr(self, f"{page_name}_page")
        page.configure(bg=self.colors['bg_dark'])
        
        for widget in page.winfo_children():
            self.update_widget_colors(widget)

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
        except Exception:
            pass

    def toggle_autostart(self):
        current = self.check_autostart_status()
        new_state = not current
        
        if self.set_autostart(new_state):
            if new_state:
                messagebox.showinfo(tr('success'), tr('autostart_enabled'))
            else:
                messagebox.showinfo(tr('success'), tr('autostart_disabled'))
        else:
            messagebox.showerror(tr('error_occurred'), tr('autostart_error'))

    def open_website(self):
        webbrowser.open("https://zapret-launcher.ru")

    def check_initial_status(self):
        if not check_zapret_folder():
            return
        
        if self.zapret.is_winws_running():
            self.is_connected = True

            if hasattr(self, 'mode_label') and self.mode_label:
                self.mode_label.config(text=tr('mode_standard'), fg=self.colors['accent_green'])

            self.update_status(tr('status_connected'), self.colors['accent_green'])
            self.update_ui_state()
            if hasattr(self, 'tray_icon'):
                self.tray_icon.update_menu()
            
            if self.is_connected and not self.stats.is_monitoring:
                self.stats.start_session()
                self.start_stats_monitoring()
                self.root.after(100, self.update_stats_display)

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
                    self.connect_btn.normal_color = '#3D3D45'
                    self.connect_btn.hover_color = self.colors['accent']
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
        if self._connecting:
            return
        
        if self.is_connected:
            self.disconnect()
        else:
            self._connecting = True
            try:
                if self.check_vpn_before_connect():
                    self.dialogs.show_mode_selector()
            finally:
                self.root.after(500, lambda: setattr(self, '_connecting', False))
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

        mode_name = strategy.replace(".bat", "").replace("general", "").strip() or "Стандартный"
        self.log_event("connect", "", mode_name)

        self._connecting = False
        self.force_tray_menu_update()

    def _on_connect_failed(self, msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_startup'), msg)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

        self._connecting = False
        self.force_tray_menu_update()

    def disconnect(self):
        if not self.is_connected and not self.zapret.is_winws_running():
            return
        
        self._disconnecting = True
        self.force_tray_menu_update()
        
        if self.mode_label and hasattr(self.mode_label, 'cget'):
            current_mode = self.mode_label.cget('text')
            if current_mode and current_mode != tr('mode_not_selected'):
                self.log_event("disconnect", "", current_mode)
            
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
                    except Exception:
                        pass
                    time.sleep(1.5)
                
                try:
                    self.zapret.stop_current_strategy()
                except Exception:
                    pass
                
                time.sleep(0.5)
                
                try:
                    subprocess.run(
                        ['taskkill', '/F', '/IM', 'winws.exe'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
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
                self._disconnecting = False
                self.root.after(0, self.finish_disconnect)
                
            except Exception:
                self.is_connected = False
                self._disconnecting = False
                self.root.after(0, self.finish_disconnect)
        
        threading.Thread(target=stop_all, daemon=True).start()

    def finish_disconnect(self):
        try:
            self._cached_processes = []

            if hasattr(self, 'mode_label') and self.mode_label and self.mode_label.winfo_exists():
                self.mode_label.config(text=tr('mode_not_selected'), fg=self.colors['text_secondary'])
            self.update_status(tr('status_ready'), self.colors['text_secondary'])

            self.stats = StatsMonitor()
            self.stats_update_id = None

            if hasattr(self, 'stats_time_label') and self.stats_time_label:
                self.stats_time_label.config(text="00:00:00")
            if hasattr(self, 'stats_traffic_label') and self.stats_traffic_label:
                self.stats_traffic_label.config(text="⬇ 0 B  |  ⬆ 0 B")
            if hasattr(self, 'stats_total_label') and self.stats_total_label:
                self.stats_total_label.config(text="0 B")
            if hasattr(self, 'stats_speed_up_label') and self.stats_speed_up_label:
                self.stats_speed_up_label.config(text="⬆ 0 B/s")
            if hasattr(self, 'stats_speed_down_label') and self.stats_speed_down_label:
                self.stats_speed_down_label.config(text="⬇ 0 B/s")
            if hasattr(self, 'stats_rtt_label') and self.stats_rtt_label:
                self.stats_rtt_label.config(text="-- ms", fg=self.colors['text_secondary'])

            self.stop_stats_monitoring()
            self._cached_processes = []
            self._last_process_time = 0
            self._traffic_collecting = False
            self._traffic_collecting_start = 0

            if hasattr(self, '_traffic_update_timer') and self._traffic_update_timer:
                try:
                    self.root.after_cancel(self._traffic_update_timer)
                except:
                    pass
                self._traffic_update_timer = None
            
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

            self.traffic_history = {}
            self.traffic_history_vpn = {}
            self.traffic_history_direct = {}
            self.traffic_speed_history = {}
            self.traffic_speed_vpn_history = {}
            self.traffic_speed_direct_history = {}
            self.hostname_cache = {}
            self.hostname_cache_time = {}
            
            if hasattr(self, 'pages') and hasattr(self.pages, 'current_page'):
                if self.pages.current_page == "traffic":
                    if hasattr(self.pages, 'traffic_page_obj'):
                        tree = self.pages.traffic_page_obj.traffic_tree
                        if tree and tree.winfo_exists():
                            for item in tree.get_children():
                                tree.delete(item)
                        self.root.after(500, self.update_traffic_table)
            
            self.root.after(500, self.update_tray_icon_state)
            self._disconnecting = False
            self.force_tray_menu_update()
        except Exception:
            self._disconnecting = False
            pass

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

    def toggle_vpn_detection(self):
        current = getattr(self, '_show_vpn_detection', False)
        new_state = not current
        self._show_vpn_detection = new_state
        self.save_settings()
        
        if new_state:
            self.show_notification(tr('dialog_enabled'), 2000)
            self.log_event("info", "VPN detection enabled")
        else:
            self.show_notification(tr('dialog_disabled'), 2000)
            self.log_event("info", "VPN detection disabled")

    def toggle_hide_duplicates_warning(self):
        current = getattr(self, '_hide_duplicates_warning', False)
        new_state = not current
        self._hide_duplicates_warning = new_state
        self.save_settings()
        
        if new_state:
            self.show_notification(tr('dialog_disabled'), 2000)
            self.log_event("info", "Duplicates warning hidden")
        else:
            self.show_notification(tr('dialog_enabled'), 2000)
            self.log_event("info", "Duplicates warning shown")

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
                        self.strategy_var.set(saved_strategy)
                    
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
                    self._tg_secret = data.get('tg_secret', None)

                    self.tg_host = data.get('tg_host', TG_HOST)
                    self.tg_port = data.get('tg_port', TG_PORT)
                    self.tg_fake_tls = data.get('tg_fake_tls', TG_FAKE_TLS)
                    self.tg_fake_tls_domain = data.get('tg_fake_tls_domain', TG_FAKE_TLS_DOMAIN)

                    self._show_vpn_detection = data.get('show_vpn_detection', False)
                    self._hide_duplicates_warning = data.get('hide_duplicates_warning', False)

                    saved_theme = data.get('theme', 'Default')
                    if saved_theme in get_theme_names():
                        self.current_theme = saved_theme
                    else:
                        self.current_theme = 'Default'

                    if not self._tg_secret:
                        self._tg_secret = os.urandom(16).hex()
                        self.save_settings()
                        
        except Exception as e:
            self.log_event("error", f"Failed to load settings: {e}")
            self.log_event("info", "New secret key has been generated (first run)")
            self._tg_secret = os.urandom(16).hex()
            self.current_theme = 'Default'
            self.tg_host = TG_HOST
            self.tg_port = TG_PORT
            self.tg_fake_tls = TG_FAKE_TLS
            self.tg_fake_tls_domain = TG_FAKE_TLS_DOMAIN
            self._show_vpn_detection = True
            self._hide_duplicates_warning = False

    def save_settings(self):
        try:
            settings = {
                'current_strategy': self.current_strategy,
                'autostart_enabled': self.check_autostart_status(),
                'update_interval': self.update_interval_index,
                'tg_instruction': getattr(self, '_tg_instruction', False),
                'show_vpn_detection': getattr(self, '_show_vpn_detection', False),
                'hide_duplicates_warning': getattr(self, '_hide_duplicates_warning', False),
                'language': self.languages.get_current_language(),
                'tg_secret': getattr(self, '_tg_secret', None),
                'theme': self.current_theme,
                'tg_host': getattr(self, 'tg_host', TG_HOST),
                'tg_port': getattr(self, 'tg_port', TG_PORT),
                'tg_fake_tls': getattr(self, 'tg_fake_tls', TG_FAKE_TLS),
                'tg_fake_tls_domain': getattr(self, 'tg_fake_tls_domain', TG_FAKE_TLS_DOMAIN),
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
        self.root.after(100, self.update_traffic_table)

    def show_logs_page(self):
        self.pages.show_page_with_animation("logs")
        self.pages.update_logs_display()

    def _reset_traffic_history(self):
        self.traffic_history = {}
        self.traffic_history_vpn = {}
        self.traffic_history_direct = {}
        self.traffic_speed_history = {}
        self.traffic_speed_vpn_history = {}
        self.traffic_speed_direct_history = {}
        self.traffic_last_update = time.time()

    def check_lists_for_duplicates(self):
        if getattr(self, '_hide_duplicates_warning', False):
            return
        
        try:
            lists_dir = ZAPRET_CORE_DIR / "lists"
            has_duplicates, summary = check_lists_for_duplicates(lists_dir)
            
            if has_duplicates:
                self.root.after(200, lambda: self.dialogs.show_duplicates_dialog(summary))
        except Exception as e:
            self.log_event("error", f"Failed to check lists for duplicates: {e}")

    def copy_tg_link_to_clipboard(self):
        secret = getattr(self, '_tg_secret', '')
        fake_tls = getattr(self, 'tg_fake_tls', False)
        fake_tls_domain = getattr(self, 'tg_fake_tls_domain', '')
        
        if not secret:
            return
        
        if fake_tls and fake_tls_domain:
            domain_hex = fake_tls_domain.encode('ascii').hex()
            link = f"ee{secret}{domain_hex}"
        else:
            link = f"{secret}"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        self.root.update()
        
        self.show_notification(tr('notification_copied_secret'), 3000)
        self.log_event("info", f"TG secret-key with fake tls copied to clipboard")
    
    def get_process_traffic(self):
        self._cleanup_traffic_history()
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
        
        connections = []
        try:
            connections = psutil.net_connections(kind='inet')
        except psutil.AccessDenied:
            self.log_event("error", "Administrator rights required to view network connections")
            self._cached_processes = [{
                'name': tr('error_admin_required'),
                'speed': '-',
                'vpn': '-',
                'direct': '-',
                'connections': 0,
                'host': '',
                'total': '-'
            }]
            self._last_process_time = current_time
            return self._cached_processes
        except Exception as e:
            self.log_event("error", f"Failed to get network connections: {str(e)}")
            self._cached_processes = [{
                'name': tr('error_traffic_collection'),
                'speed': '-',
                'vpn': '-',
                'direct': '-',
                'connections': 0,
                'host': '',
                'total': '-'
            }]
            self._last_process_time = current_time
            return self._cached_processes
        
        try:
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
            
            vpn_ports = {1443}
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
            self.log_event("error", f"Error collecting traffic: {str(e)}")
            processes = [{
                'name': tr('error_traffic_collection'),
                'speed': '-',
                'vpn': '-',
                'direct': '-',
                'connections': 0,
                'host': '',
                'total': '-'
            }]
        
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
        
        current_page = None
        if hasattr(self, 'pages'):
            current_page = getattr(self.pages, 'current_page', None)
        
        if current_page != "traffic":
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
            except Exception as e:
                self.log_event("error", f"Error collecting traffic data: {str(e)}")
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
        try:
            if hasattr(self, 'pages') and hasattr(self.pages, 'traffic_page_obj'):
                tree = self.pages.traffic_page_obj.traffic_tree
                if tree and tree.winfo_exists():
                    for item in tree.get_children():
                        tree.delete(item)
                    
                    for proc in processes:
                        speed_display = proc['speed'] if proc['speed'] != '-' else '-'
                        
                        tree.insert("", "end", values=(
                            proc['name'],
                            speed_display,
                            proc['vpn'],
                            proc['direct'],
                            str(proc['connections']) if proc['connections'] > 0 else '-',
                            proc['host'],
                            proc['total']
                        ))
        except Exception as e:
            self.log_event("error", f"Error updating traffic table: {str(e)}")

    def is_any_connection_active(self):
        return self.is_connected or self.zapret.is_winws_running() or (hasattr(self, 'tg_proxy') and self.tg_proxy.is_running)

    def _cleanup_traffic_history(self):
        current_time = time.time()
        
        if len(self.traffic_history) > self.MAX_HISTORY_SIZE:
            to_remove = len(self.traffic_history) - self.MAX_HISTORY_SIZE
            oldest_keys = list(self.traffic_history.keys())[:to_remove]
            for key in oldest_keys:
                self.traffic_history.pop(key, None)
                self.traffic_history_vpn.pop(key, None)
                self.traffic_history_direct.pop(key, None)
                self.traffic_speed_history.pop(key, None)
                self.traffic_speed_vpn_history.pop(key, None)
                self.traffic_speed_direct_history.pop(key, None)

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

    def check_vpn_before_connect(self):
        if not getattr(self, '_show_vpn_detection', False):
            return True
        
        try:
            vpn_keywords = [
                'openvpn', 'wireguard', 'protonvpn', 'nordvpn', 
                'expressvpn', 'surfshark', 'cyberghost', 'ipvanish',
                'tunnelbear', 'hotspotshield', 'windscribe', 'vyprvpn',
                'privateinternetaccess', 'pia', 'mullvad', 'ivpn',
                'airvpn', 'perfectprivacy', 'zenmate', 'hidester',
                'slickvpn', 'fastestvpn', 'buffered', 'vpn.ac',
                'torguard', 'vpnunlimited', 'vpngate',
                'softether', 'v2ray', 'shadowsocks', 'trojan',
                'wg-quick', 'ovpn', 'vpn.exe', 'vpnclient',
                'forticlient', 'cisco', 'anyconnect', 'pulse secure',
                'globalprotect', 'openconnect', 'wireguard.exe',
                'protonvpn.exe', 'nordvpn.exe', 'expressvpn.exe',
                'planetvpn', 'planetvpn.exe', 'vpn', 'itopvpn', 
                'itopvpn.exe', 'bebra.exe', 'bebravpn.exe',
                'xray', 'amneziawg', 'surfshark', 'surfsharkvpn'
            ]
            
            has_vpn = False
            detected_processes = []
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    
                    skip_processes = ['svchost.exe', 'textinput.exe', 'explorer.exe', 
                                    'taskhost.exe', 'dwm.exe', 'csrss.exe', 'winlogon.exe',
                                    'services.exe', 'lsass.exe', 'wininit.exe', 'spoolsv.exe',
                                    'searchindexer.exe', 'wmpnetwk.exe', 'system', 'system idle process']
                    
                    if any(skip in proc_name for skip in skip_processes):
                        continue
                    
                    for keyword in vpn_keywords:
                        if keyword in proc_name:
                            has_vpn = True
                            detected_processes.append(proc_name)
                            break
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if has_vpn:
                vpn_data = {
                    'vpn_detected': True,
                    'vpn_processes': detected_processes,
                    'vpn_interfaces': []
                }
                self.dialogs.show_vpn_detected_dialog(vpn_data)
                return False
            return True
            
        except Exception as e:
            self.log_event("error", f"VPN check error: {e}")
            return True

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

        if self.tg_fake_tls:
            self.root.after(1000, self.copy_tg_link_to_clipboard)

        if not self._tg_instruction:
            self.root.after(500, self.dialogs.show_tg_proxy_instruction)

        self.root.after(500, self.update_tray_icon_state)
        self._connecting = False
        self.force_tray_menu_update()
        self.log_event("connect", "", mode_name)

    def _on_combined_start_failed(self, error_msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_startup'), f"{tr('error_startup')}: {error_msg}")
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

        if hasattr(self, 'tg_proxy') and self.tg_proxy:
            self.tg_proxy.stop()

    def _version_to_tuple(self, ver_str):
        ver_str = str(ver_str).strip().lower()
        
        if ver_str.startswith('v'):
            ver_str = ver_str[1:]
        
        match = re.match(r'^(\d+(?:\.\d+)*)([a-z]*)$', ver_str)
        
        if not match:
            numbers = re.findall(r'\d+', ver_str)
            nums = [int(n) for n in numbers]
            while len(nums) < 4:
                nums.append(0)
            return tuple(nums[:4] + [0])
        
        num_part, suffix = match.groups()
        
        if '.' in num_part:
            nums = [int(n) for n in num_part.split('.')]
        else:
            nums = [int(num_part)]
        
        while len(nums) < 4:
            nums.append(0)
        
        suffix_value = 0
        if suffix:
            for i, ch in enumerate(suffix):
                suffix_value = suffix_value * 27 + (ord(ch) - ord('a') + 1)
        
        return tuple(nums[:4] + [suffix_value])

    def _compare_builds(self, current, latest):
        try:
            current_int = int(current)
            latest_int = int(latest)
            return latest_int > current_int
        except ValueError:
            return str(latest) > str(current)

    def _compare_zapret_versions(self, current, latest):
        if not current or current == "0.0":
            return True
        
        def version_to_parts(ver):
            ver = ver.strip().lower()
            match = re.match(r'^(\d+(?:\.\d+)*)([a-z]?)$', ver)
            if not match:
                return [0, 0, 0], 0
            
            num_part, letter = match.groups()
            nums = [int(x) for x in num_part.split('.')]
            while len(nums) < 3:
                nums.append(0)
            
            letter_val = ord(letter) - ord('a') + 1 if letter else 0
            
            return nums, letter_val
        
        current_nums, current_letter = version_to_parts(current)
        latest_nums, latest_letter = version_to_parts(latest)
        
        for i in range(3):
            if latest_nums[i] > current_nums[i]:
                return True
            elif latest_nums[i] < current_nums[i]:
                return False
        
        return latest_letter > current_letter

    def get_current_zapret_version(self):
        try:
            version_file = APPDATA_DIR / "zapret_core" / "version.txt"
            if version_file.exists():
                version = version_file.read_text(encoding='utf-8').strip()
                return version
        except Exception:
            pass
        return "0.0"
    
    def start_update_checker(self):
        self.stop_update_checker()
        self._schedule_update_check()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.start_update_checker()

    def stop_update_checker(self):
        if hasattr(self, 'update_check_timer_id') and self.update_check_timer_id:
            try:
                self.root.after_cancel(self.update_check_timer_id)
            except:
                pass
            self.update_check_timer_id = None

    def _schedule_update_check(self):
        if not hasattr(self, '_first_check_done'):
            interval = 5000
            self._first_check_done = True
        else:
            interval = 60 * 60 * 1000
        
        self.update_check_timer_id = self.root.after(interval, self._do_update_check)

    def _do_update_check(self):
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        self._schedule_update_check()

    def load_logs(self) -> list:
        logs = []
        log_file = APPDATA_DIR / "logs.txt"
        
        try:
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = f.readlines()
        except Exception:
            pass
        return logs
    
    def clear_logs(self):
        log_file = APPDATA_DIR / "logs.txt"
        try:
            if log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            if hasattr(self, 'pages') and self.pages.current_page == "logs":
                self.pages.update_logs_display()
        except Exception:
            pass

if __name__ == "__main__":
    mutex_name = "ZapretLauncher41241_SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Zapret Launcher")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        sys.exit(0)

    auto_start = '--auto-start' in sys.argv
    
    if auto_start:
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, "Zapret Launcher")
                if not value:
                    sys.exit(0)
        except:
            sys.exit(0)
    
    if not is_admin():
        if auto_start:
            run_as_admin()
            sys.exit(0)
        else:
            result = messagebox.askyesno(
                "Zapret Launcher",
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

    zapret_version = "0.0"
    try:
        version_file = APPDATA_DIR / "zapret_core" / "version.txt"
        if version_file.exists():
            zapret_version = version_file.read_text(encoding='utf-8').strip()
    except Exception:
        pass

    current_theme = 'Default'
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_theme = data.get('theme', 'Default')
    except Exception:
        pass
    
    show_splash = '--no-splash' not in sys.argv and '--from-splash' not in sys.argv and not auto_start
    
    if show_splash:
        splash = SplashWindow(theme=current_theme, 
                            current_version=CURRENT_VERSION, 
                            current_build=CURRENT_BUILD,
                            zapret_version=zapret_version)
        splash.start()
    else:
        root = tk.Tk()
        app = ZapretLauncher(root)
        root.mainloop()
        
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)
