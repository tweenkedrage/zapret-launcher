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
from utils.languages import tr, get_languages
from typing import List, Optional
from gui.theme import get_theme, get_theme_names
from datetime import datetime
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
            
            time.sleep(3.0)
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
                BASE_DIR / "resources" / "icon.ico",
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
                    f.write("# example.com\n")
                
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
                            'traffic_page', 'settings_page', 'additionally_page',
                            'logs_page']:
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
            subprocess.run(
                'sc stop windivert > nul 2>&1',
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(0.5)
        except:
            pass

    def quit_from_tray(self):
        self._stop_windivert_before_restart()
        self.zapret.stop_current_strategy()
        if hasattr(self, 'tg_proxy'):
            self.tg_proxy.stop()
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        sys.exit(0)

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
                BASE_DIR / "resources" / "icon.png",
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
            (tr('additionally_title'), self.show_additionally_page),
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

        beta_label = tk.Label(
            version_frame,
            text="beta",
            font=("Segoe UI Variable", 8),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        )
        beta_label.pack(side=tk.LEFT)
        
        self.credit_label = tk.Label(
            self.credit_frame,
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
            buildnumber_url = "https://zapret-launcher.ru/updater/docs/build_number.txt" # build_number.txt | test/test.txt
            
            req = urllib.request.Request(
                buildnumber_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                latest_build = response.read().decode('utf-8').strip()
            
            current_build = CURRENT_BUILD
            
            if self._compare_builds(current_build, latest_build):
                self.root.after(0, self.show_update_label)
            else:
                self.root.after(0, self.hide_update_label)
        except Exception:
            self.root.after(0, self.hide_update_label)

    def install_update(self):
        try:
            latest_version = None
            latest_build = None
            
            try:
                req_version = urllib.request.Request(
                    "https://zapret-launcher.ru/updater/docs/version_launcher.txt",  # version_launcher.txt
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req_version, timeout=5) as response:
                    latest_version = response.read().decode('utf-8').strip()
            except Exception:
                latest_version = "?"
            
            try:
                req_build = urllib.request.Request(
                    "https://zapret-launcher.ru/updater/docs/build_number.txt",  # build_number.txt
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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

    def show_mode_selector(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('mode_select_title'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

        self.set_dialog_header_color(dialog)
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        
        dialog.geometry(f"500x550+{x}+{y}")
        
        tk.Label(dialog, text=tr('mode_select'), font=("Segoe UI Variable", 16, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.colors['bg_medium'], highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_medium'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=440)
        canvas.configure(yscrollcommand=None)
        canvas.pack(side="left", fill="both", expand=True)
        
        modes = [
            {"name": tr('mode_standard'), "desc": tr('mode_standard_desc'), 
            "zapret": True, "tgproxy": False},
            {"name": "Telegram Proxy", "desc": tr('mode_tgproxy_desc'), 
            "zapret": False, "tgproxy": True},
            {"name": tr('mode_zapret_tgproxy'), "desc": tr('mode_zapret_tgproxy_desc'), 
            "zapret": True, "tgproxy": True},
        ]
        
        selected_index = [0]
        selected_mode = [None]
        selected_widget = [None]
        mode_frames = []
        select_btn = [None]
        
        def update_select_button():
            if select_btn[0]:
                if selected_mode[0]:
                    select_btn[0].set_enabled(True)
                    select_btn[0].normal_color = self.colors['accent']
                    select_btn[0].hover_color = self.colors['accent']
                    select_btn[0].update_colors(
                        self.colors['accent'],
                        self.colors['text_primary'],
                        self.colors['accent']
                    )
                    select_btn[0].config(cursor="hand2")
                else:
                    select_btn[0].set_enabled(False)
                    select_btn[0].normal_color = self.colors['accent']
                    select_btn[0].hover_color = self.colors['accent']
                    select_btn[0].update_colors(
                        self.colors['button_bg'],
                        self.colors['text_secondary'],
                        self.colors['button_bg']
                    )
                    select_btn[0].config(cursor="arrow")
        
        def on_single_click(mode, frame, name_label, desc_label, index):
            if selected_widget[0]:
                prev_frame, prev_name, prev_desc, _ = selected_widget[0]
                prev_frame.configure(bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
                prev_name.configure(fg=self.colors['accent'], bg=self.colors['bg_light'])
                prev_desc.configure(fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
            
            frame.configure(bg=self.colors['accent'], relief=tk.RIDGE, bd=2)
            name_label.configure(fg=self.colors['text_primary'], bg=self.colors['accent'])
            desc_label.configure(fg=self.colors['text_secondary'], bg=self.colors['accent'])
            
            selected_widget[0] = (frame, name_label, desc_label, index)
            selected_mode[0] = mode
            selected_index[0] = index
            update_select_button()
            canvas.yview_moveto(index / len(modes) if len(modes) > 0 else 0)
        
        def on_double_click(mode):
            if mode:
                dialog.destroy()
                self.start_with_mode(mode)
        
        def on_select_click():
            if selected_mode[0]:
                dialog.destroy()
                self.start_with_mode(selected_mode[0])
        
        def move_selection(delta):
            new_index = selected_index[0] + delta
            if 0 <= new_index < len(modes):
                selected_index[0] = new_index
                mode = modes[new_index]
                frame, name_label, desc_label = mode_frames[new_index]
                on_single_click(mode, frame, name_label, desc_label, new_index)
        
        def on_key_press(event):
            if event.keysym == 'Up':
                move_selection(-1)
                return "break"
            elif event.keysym == 'Down':
                move_selection(1)
                return "break"
            elif event.keysym == 'Return':
                if selected_mode[0]:
                    dialog.destroy()
                    self.start_with_mode(selected_mode[0])
                return "break"
            elif event.keysym == 'Escape':
                dialog.destroy()
                return "break"
        
        dialog.bind('<Up>', on_key_press)
        dialog.bind('<Down>', on_key_press)
        dialog.bind('<Return>', on_key_press)
        dialog.bind('<Escape>', on_key_press)
        
        for idx, mode in enumerate(modes):
            mode_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="hand2")
            mode_frame.pack(fill=tk.X, padx=10, pady=5, ipady=8)
            
            original_bg = self.colors['bg_light']
            name_label = tk.Label(mode_frame, text=mode["name"], font=("Segoe UI Variable", 12, "bold"),
                                fg=self.colors['accent'], bg=original_bg)
            name_label.pack(anchor='w', padx=15, pady=(8, 2))
            desc_label = tk.Label(mode_frame, text=mode["desc"], font=("Segoe UI Variable", 9),
                                fg=self.colors['text_secondary'], bg=original_bg)
            desc_label.pack(anchor='w', padx=15, pady=(0, 8))
            
            mode_frames.append((mode_frame, name_label, desc_label))
            
            if idx == 0:
                selected_index[0] = 0
                selected_mode[0] = mode
                selected_widget[0] = (mode_frame, name_label, desc_label, idx)
                mode_frame.configure(bg=self.colors['accent'], relief=tk.RIDGE, bd=2)
                name_label.configure(fg=self.colors['text_primary'], bg=self.colors['accent'])
                desc_label.configure(fg=self.colors['text_secondary'], bg=self.colors['accent'])
                update_select_button()

            def make_on_click(m, f, nl, dl, i):
                return lambda e: on_single_click(m, f, nl, dl, i)
            
            def make_on_double(m):
                return lambda e: on_double_click(m)
            
            click_handler = make_on_click(mode, mode_frame, name_label, desc_label, idx)
            double_handler = make_on_double(mode)
            
            mode_frame.bind("<Button-1>", click_handler)
            mode_frame.bind("<Double-Button-1>", double_handler)
            name_label.bind("<Button-1>", click_handler)
            name_label.bind("<Double-Button-1>", double_handler)
            desc_label.bind("<Button-1>", click_handler)
            desc_label.bind("<Double-Button-1>", double_handler)
            
            def make_on_enter(frame, nl, dl, orig_bg, idx_local):
                def on_enter_func(e):
                    if selected_widget[0] and selected_widget[0][3] == idx_local:
                        return
                    frame.configure(bg=self.colors['bg_light_hover'])
                    nl.configure(bg=self.colors['bg_light_hover'])
                    dl.configure(bg=self.colors['bg_light_hover'])
                return on_enter_func
            
            def make_on_leave(frame, nl, dl, orig_bg, idx_local):
                def on_leave_func(e):
                    if selected_widget[0] and selected_widget[0][3] == idx_local:
                        return
                    frame.configure(bg=orig_bg)
                    nl.configure(bg=orig_bg)
                    dl.configure(bg=orig_bg)
                return on_leave_func
            
            mode_frame.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            mode_frame.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
            name_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            name_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
            desc_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            desc_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=20, pady=15)
        
        select_btn[0] = RoundedButton(
            bottom_frame,
            text=tr('mode_select_button'),
            command=on_select_click,
            width=100, height=35,
            bg=self.colors['accent'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        select_btn[0].normal_color = self.colors['accent']
        select_btn[0].hover_color = self.colors['accent']
        select_btn[0].set_enabled(True)
        select_btn[0].config(cursor="hand2")
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
        
        if mode["name"] == "Telegram Proxy":
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
                self.root.after(500, self.show_tg_proxy_instruction)
        
        self.connect_btn.set_enabled(True)
        self.root.after(500, self.update_tray_icon_state)

    def _on_tg_proxy_failed_direct(self, error_msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_no_connection'), f"{error_msg}")
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def select_strategy_for_mode(self, mode_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('select_strategy_title'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

        self.set_dialog_header_color(dialog)
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 275
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        
        dialog.geometry(f"550x550+{x}+{y}")
        
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
        
        is_processing = False
        
        def on_select(event):
            selection = strategy_listbox.curselection()
            if selection:
                strategy = self.zapret.available_strategies[selection[0]]
                desc_label.config(text=f"{tr('selected')} {strategy}")
        
        strategy_listbox.bind("<<ListboxSelect>>", on_select)
        
        if self.current_strategy:
            try:
                idx = self.zapret.available_strategies.index(self.current_strategy)
                strategy_listbox.selection_set(idx)
                strategy_listbox.see(idx)
                desc_label.config(text=f"{tr('selected')} {self.current_strategy}")
            except ValueError:
                pass
        
        def move_selection(delta):
            nonlocal is_processing
            if is_processing:
                return
            is_processing = True
            
            try:
                current = strategy_listbox.curselection()
                if current:
                    new_idx = current[0] + delta
                else:
                    new_idx = 0 if delta > 0 else len(self.zapret.available_strategies) - 1
                
                if 0 <= new_idx < len(self.zapret.available_strategies):
                    strategy_listbox.selection_clear(0, tk.END)
                    strategy_listbox.selection_set(new_idx)
                    strategy_listbox.see(new_idx)
                    strategy = self.zapret.available_strategies[new_idx]
                    desc_label.config(text=f"{tr('selected')} {strategy}")
            finally:
                dialog.after(100, lambda: setattr(move_selection, 'processing', False))
                is_processing = False
        
        def on_key_press(event):
            if event.keysym == 'Up':
                move_selection(-1)
                return "break"
            elif event.keysym == 'Down':
                move_selection(1)
                return "break"
            elif event.keysym == 'Return':
                start_with_strategy()
                return "break"
            elif event.keysym == 'Escape':
                dialog.destroy()
                return "break"
        
        def on_double_click(event):
            start_with_strategy()
        
        dialog.bind('<Up>', on_key_press)
        dialog.bind('<Down>', on_key_press)
        dialog.bind('<Return>', on_key_press)
        dialog.bind('<Escape>', on_key_press)

        strategy_listbox.bind('<Up>', on_key_press)
        strategy_listbox.bind('<Down>', on_key_press)
        strategy_listbox.bind('<Return>', on_key_press)
        strategy_listbox.bind('<Escape>', on_key_press)
        strategy_listbox.bind('<Double-Button-1>', on_double_click)
        strategy_listbox.focus_set()
        
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
                    self.save_settings()
                    
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
                self.save_settings()
                
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
                                font=("Segoe UI Variable", 10), corner_radius=8,
                                hover_color=self.colors['accent'], theme_name=self.current_theme)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text=tr('mode_cancel'), command=dialog.destroy,
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI Variable", 10), corner_radius=8,
                                hover_color=self.colors['accent'], theme_name=self.current_theme)
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
        except Exception:
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
        except Exception as e:
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

    def open_github(self):
        webbrowser.open("https://zapret-launcher.ru")

    def check_initial_status(self):
        if not check_zapret_folder():
            return
        
        if self.zapret.is_winws_running():
            self.is_connected = True
            self.update_status(tr('status_connected'), self.colors['accent_green'])
            self.update_ui_state()
            if hasattr(self, 'tray_icon'):
                self.tray_icon.update_menu()

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
                self.show_mode_selector()
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

    def _on_connect_failed(self, msg):
        self.update_status(tr('status_error'), self.colors['accent_red'])
        messagebox.showerror(tr('error_startup'), msg)
        if hasattr(self, 'connect_btn') and self.connect_btn:
            self.connect_btn.set_enabled(True)

    def disconnect(self):
        if not self.is_connected and not self.zapret.is_winws_running():
            return
        
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
                self.root.after(0, self.finish_disconnect)
                
            except Exception:
                self.is_connected = False
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
        except Exception:
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

                    saved_theme = data.get('theme', 'Default')
                    if saved_theme in get_theme_names():
                        self.current_theme = saved_theme
                    else:
                        self.current_theme = 'Default'

                    if not self._tg_secret:
                        self._tg_secret = os.urandom(16).hex()
                        self.save_settings()
                        
        except Exception:
            self.log_event("info", "New secret key has been generated (first run)")
            self._tg_secret = os.urandom(16).hex()
            self.current_theme = 'Default'
            self.tg_host = TG_HOST
            self.tg_port = TG_PORT
            self.tg_fake_tls = TG_FAKE_TLS
            self.tg_fake_tls_domain = TG_FAKE_TLS_DOMAIN

    def save_settings(self):
        try:
            settings = {
                'current_strategy': self.current_strategy,
                'autostart_enabled': self.check_autostart_status(),
                'update_interval': self.update_interval_index,
                'tg_instruction': getattr(self, '_tg_instruction', False),
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

    def show_additionally_page(self):
        self.pages.show_page_with_animation("additionally")

    def add_soundcloud_unblock(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            ipset_all_path = LISTS_DIR / "ipset-all.txt"
            
            soundcloud_domains = [
                "soundcloud.com", "www.soundcloud.com", "style.sndcdn.com",
                "a-v2.sndcdn.com", "api-v2.soundcloud.com", "sb.scorecardresearch.com",
                "secure.quantserve.com", "eventlogger.soundcloud.com", "api.soundcloud.com",
                "ssl.google-analytics.com", "sdk-04.moengage.com", "al.sndcdn.com",
                "i1.sndcdn.com", "i2.sndcdn.com", "i3.sndcdn.com", "i4.sndcdn.com",
                "wis.sndcdn.com", "va.sndcdn.com", "pixel.quantserve.com",
                "assets.web.soundcloud.cloud", "*.cloudfront.net", ".soundcloud.",
                "playback.media-streaming.soundcloud.cloud", "id5-sync.com",
                "cdn.moengage.com", "htlbid.com", "securepubads.g.doubleclick.net",
                "cdn.cookielaw.org"
            ]
            
            soundcloud_ips = [
                "18.165.122.4/32", "18.165.122.6/32",
                "18.165.122.82/32", "18.165.122.86/32"
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_domains = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if '.' in line and len(line) > 3:
                        for domain in soundcloud_domains:
                            if domain in line and line != domain:
                                parts = line.split(domain)
                                for part in parts:
                                    part = part.strip()
                                    if part and '.' in part and len(part) > 3:
                                        clean_domains.add(part)
                                clean_domains.add(domain)
                                break
                        else:
                            clean_domains.add(line)
                
                for domain in soundcloud_domains:
                    clean_domains.add(domain)
                
                filtered_domains = set()
                for domain in clean_domains:
                    if domain in ['cloud', 'www.', 'www', '.com', 'com', 'http', 'https']:
                        continue
                    if domain.startswith('/') or domain.endswith('/'):
                        continue
                    if len(domain) < 4:
                        continue
                    filtered_domains.add(domain)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    for domain in sorted(filtered_domains):
                        f.write(f"{domain}\n")
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_ips = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if '/' in line or ('.' in line and any(c.isdigit() for c in line)):
                        if len(line) > 5 and line[0].isdigit():
                            clean_ips.add(line)
                
                for ip in soundcloud_ips:
                    clean_ips.add(ip)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    for ip in sorted(clean_ips):
                        f.write(f"{ip}\n")
            
            self.show_notification(tr('soundcloud_unblocked'), 3000)
            self.log_event("info", "SoundCloud rules added to list-custom.txt and ipset-all.txt")
            return True
        except Exception as e:
            self.log_event("error", f"Error adding SoundCloud rules: {str(e)}")
            return False

    def remove_soundcloud_unblock(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            ipset_all_path = LISTS_DIR / "ipset-all.txt"
            
            soundcloud_domains = [
                "soundcloud.com", "www.soundcloud.com", "style.sndcdn.com",
                "a-v2.sndcdn.com", "api-v2.soundcloud.com", "sb.scorecardresearch.com",
                "secure.quantserve.com", "eventlogger.soundcloud.com", "api.soundcloud.com",
                "ssl.google-analytics.com", "sdk-04.moengage.com", "al.sndcdn.com",
                "i1.sndcdn.com", "i2.sndcdn.com", "i3.sndcdn.com", "i4.sndcdn.com",
                "wis.sndcdn.com", "va.sndcdn.com", "pixel.quantserve.com",
                "assets.web.soundcloud.cloud", "*.cloudfront.net", ".soundcloud.",
                "playback.media-streaming.soundcloud.cloud", "id5-sync.com",
                "cdn.moengage.com", "htlbid.com", "securepubads.g.doubleclick.net",
                "cdn.cookielaw.org"
            ]
            
            soundcloud_ips = [
                "18.165.122.4/32", "18.165.122.6/32",
                "18.165.122.82/32", "18.165.122.86/32"
            ]
            
            if list_general_path.exists():
                with open(list_general_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_domains = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line in ['cloud', 'www.', 'www', '.com', 'com', 'http', 'https']:
                        continue
                    if line.startswith('/') or line.endswith('/'):
                        continue
                    if len(line) < 4:
                        continue
                    
                    is_soundcloud = False
                    for domain in soundcloud_domains:
                        if domain in line:
                            is_soundcloud = True
                            break
                    
                    if not is_soundcloud:
                        clean_domains.add(line)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    for domain in sorted(clean_domains):
                        f.write(f"{domain}\n")
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_ips = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line in soundcloud_ips:
                        continue
                    if '/' in line and len(line) > 5:
                        clean_ips.add(line)
                    elif '.' in line and len(line) > 5 and line[0].isdigit():
                        clean_ips.add(line)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    for ip in sorted(clean_ips):
                        f.write(f"{ip}\n")
            
            self.show_notification(tr('soundcloud_removed'), 3000)
            self.log_event("info", "SoundCloud rules have been removed from list-custom.txt and ipset-all.txt")
            return True
        except Exception as e:
            self.log_event("error", f"Error removing SoundCloud rules: {str(e)}")
            return False

    def check_soundcloud_enabled(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            
            if not list_general_path.exists():
                return False
            
            with open(list_general_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return "soundcloud.com" in content
            
        except Exception:
            return False
        
    def add_facebook_instagram_unblock(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            ipset_all_path = LISTS_DIR / "ipset-all.txt"
            
            meta_domains = [
                "facebook.com", "www.facebook.com", "fb.com", "www.fb.com",
                "fbcdn.net", "www.fbcdn.net", "static.xx.fbcdn.net", "scontent.xx.fbcdn.net",
                "graph.facebook.com", "api.facebook.com", "m.facebook.com", "business.facebook.com",
                "developers.facebook.com", "connect.facebook.net", "facebook.net",
                "fbcdn-profile-a.akamaihd.net", "fbstatic-a.akamaihd.net", "fbexternal-a.akamaihd.net",
                "instagram.com", "www.instagram.com", "cdninstagram.com", "www.cdninstagram.com",
                "scontent.cdninstagram.com", "graph.instagram.com", "api.instagram.com", "i.instagram.com",
                "meta.com", "www.meta.com", "cdn.meta.com", "metacdn.com",
                "whatsapp.com", "www.whatsapp.com"
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
                
                clean_domains = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line in ['cloud', 'www.', 'www', '.com', 'com', 'http', 'https']:
                        continue
                    if line.startswith('/') or line.endswith('/'):
                        continue
                    if len(line) < 4:
                        continue
                    
                    is_merged = False
                    for domain in meta_domains:
                        if domain in line and line != domain:
                            parts = line.split(domain)
                            for part in parts:
                                part = part.strip()
                                if part and '.' in part and len(part) > 3:
                                    if part not in ['cloud', 'www.', 'www', '.com', 'com']:
                                        clean_domains.add(part)
                            clean_domains.add(domain)
                            is_merged = True
                            break
                    
                    if not is_merged:
                        clean_domains.add(line)
                
                for domain in meta_domains:
                    clean_domains.add(domain)
                
                filtered_domains = set()
                for domain in clean_domains:
                    if domain in ['cloud', 'www.', 'www', '.com', 'com', 'http', 'https']:
                        continue
                    if domain.startswith('/') or domain.endswith('/'):
                        continue
                    if len(domain) < 4:
                        continue
                    filtered_domains.add(domain)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    for domain in sorted(filtered_domains):
                        f.write(f"{domain}\n")
            else:
                return False
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_ips = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if '/' in line and len(line) > 5:
                        clean_ips.add(line)
                    elif '.' in line and line.count('.') == 3 and len(line) > 7:
                        clean_ips.add(line)
                
                for ip in meta_ips:
                    clean_ips.add(ip)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    for ip in sorted(clean_ips):
                        f.write(f"{ip}\n")
            
            self.show_notification(tr('meta_unblocked'), 3000)
            self.log_event("info", f"Meta rules added to list-custom.txt and ipset-all.txt")
            return True
        except Exception as e:
            self.log_event("error", f"Error adding Meta rules: {str(e)}")
            return False

    def remove_facebook_instagram_unblock(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            ipset_all_path = LISTS_DIR / "ipset-all.txt"
            
            meta_domains = [
                "facebook.com", "www.facebook.com", "fb.com", "www.fb.com",
                "fbcdn.net", "www.fbcdn.net", "static.xx.fbcdn.net", "scontent.xx.fbcdn.net",
                "graph.facebook.com", "api.facebook.com", "m.facebook.com", "business.facebook.com",
                "developers.facebook.com", "connect.facebook.net", "facebook.net",
                "fbcdn-profile-a.akamaihd.net", "fbstatic-a.akamaihd.net", "fbexternal-a.akamaihd.net",
                "instagram.com", "www.instagram.com", "cdninstagram.com", "www.cdninstagram.com",
                "scontent.cdninstagram.com", "graph.instagram.com", "api.instagram.com", "i.instagram.com",
                "meta.com", "www.meta.com", "cdn.meta.com", "metacdn.com",
                "whatsapp.com", "www.whatsapp.com"
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
                
                clean_domains = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line in ['cloud', 'www.', 'www', '.com', 'com', 'http', 'https']:
                        continue
                    if line.startswith('/') or line.endswith('/'):
                        continue
                    if len(line) < 4:
                        continue
                    
                    is_meta = False
                    for domain in meta_domains:
                        if domain in line:
                            is_meta = True
                            break
                    
                    if not is_meta:
                        clean_domains.add(line)
                
                with open(list_general_path, 'w', encoding='utf-8') as f:
                    for domain in sorted(clean_domains):
                        f.write(f"{domain}\n")
            
            if ipset_all_path.exists():
                with open(ipset_all_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                clean_ips = set()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line in meta_ips:
                        continue
                    
                    if '/' in line and len(line) > 5:
                        clean_ips.add(line)
                    elif '.' in line and line.count('.') == 3 and len(line) > 7:
                        clean_ips.add(line)
                
                with open(ipset_all_path, 'w', encoding='utf-8') as f:
                    for ip in sorted(clean_ips):
                        f.write(f"{ip}\n")
            
            self.show_notification(tr('meta_removed'), 3000)
            self.log_event("info", f"Meta rules have been removed from list-custom.txt and ipset-all.txt")
            return True
        except Exception as e:
            self.log_event("error", f"Error removing Meta rules: {str(e)}")
            return False

    def check_meta_enabled(self):
        try:
            list_general_path = LISTS_DIR / "list-custom.txt"
            
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

    def show_hosts_instruction(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('instruction_title_window'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 300
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 240
        
        dialog.geometry(f"600x480+{x}+{y}")

        dialog.update_idletasks()
        self.set_dialog_header_color(dialog)
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(15, 5))
        
        title_label = tk.Label(title_frame, text=tr('hosts_instruction_title'), 
                            font=("Segoe UI Variable", 18, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text=tr('hosts_instruction_subtitle'),
                                font=("Segoe UI Variable", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        subtitle_label.pack(pady=(3, 0))
        
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=30, pady=8)
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        inner = tk.Frame(main_frame, bg=self.colors['bg_light'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        steps = [
            ("1.", tr('hosts_step1')),
            ("2.", tr('hosts_step2')),
            ("", tr('hosts_step2_desc')),
            ("3.", tr('hosts_step3')),
        ]
        
        current_step = 0
        
        for i, step in enumerate(steps):
            text, desc = step
            if text:
                step_frame = tk.Frame(inner, bg=self.colors['bg_light'])
                step_frame.pack(fill=tk.X, pady=(5 if current_step > 0 else 0, 1))
                
                step_num = tk.Label(step_frame, text=text, font=("Segoe UI Variable", 12, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                step_num.pack(side=tk.LEFT)
                
                step_text = tk.Label(step_frame, text=desc, font=("Segoe UI Variable", 10),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                step_text.pack(side=tk.LEFT, padx=(5, 0))
                current_step += 1
            else:
                sub_frame = tk.Frame(inner, bg=self.colors['bg_light'])
                sub_frame.pack(fill=tk.X, pady=0)
                
                spacer = tk.Label(sub_frame, text="   ", font=("Segoe UI Variable", 10),
                                fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                spacer.pack(side=tk.LEFT)
                
                bullet = tk.Label(sub_frame, text="▸", font=("Segoe UI Variable", 9),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                bullet.pack(side=tk.LEFT, padx=(10, 3))
                
                sub_text = tk.Label(sub_frame, text=desc, font=("Segoe UI Variable", 9),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
                sub_text.pack(side=tk.LEFT)
        
        copy_frame_block = tk.Frame(inner, bg=self.colors['bg_light'])
        copy_frame_block.pack(fill=tk.X, pady=(10, 5))
        
        spacer = tk.Label(copy_frame_block, text="   ", font=("Segoe UI Variable", 10),
                        fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        spacer.pack(side=tk.LEFT)
        
        bullet = tk.Label(copy_frame_block, text="▸", font=("Segoe UI Variable", 9),
                        fg=self.colors['accent'], bg=self.colors['bg_light'])
        bullet.pack(side=tk.LEFT, padx=(10, 3))
        
        copy_label = tk.Label(copy_frame_block, text=tr('hosts_copy_lines'), font=("Segoe UI Variable", 9),
                            fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        copy_label.pack(side=tk.LEFT)
        
        hosts_lines = """149.154.167.220 zws4.web.telegram.org
149.154.167.220 vesta.web.telegram.org
149.154.167.220 vesta-1.web.telegram.org
149.154.167.220 venus-1.web.telegram.org
149.154.167.220 telegram.me
149.154.167.220 telegram.dog
149.154.167.220 telegram.space
149.154.167.220 telesco.pe
149.154.167.220 tg.dev
149.154.167.220 telegram.org
149.154.167.220 my.telegram.org
149.154.167.220 t.me
149.154.167.220 api.telegram.org
149.154.167.220 td.telegram.org
149.154.167.220 venus.web.telegram.org
149.154.167.220 web.telegram.org
149.154.167.220 kws2-1.web.telegram.org
149.154.167.220 kws2.web.telegram.org
149.154.167.220 kws4-1.web.telegram.org
149.154.167.220 kws4.web.telegram.org
149.154.167.220 zws2-1.web.telegram.org
149.154.167.220 zws2.web.telegram.org
149.154.167.220 zws4-1.web.telegram.org"""
        
        def copy_hosts_lines(event=None):
            self.root.clipboard_clear()
            self.root.clipboard_append(hosts_lines)
            self.root.update()
            copy_label.config(text=tr('tg_copied'), fg=self.colors['accent_green'])
            self.show_notification(tr('hosts_copied_notification'), 2000)
            self.root.after(2000, lambda: copy_label.config(text=tr('hosts_copy_lines'), fg=self.colors['accent']))
        
        copy_label.bind("<Button-1>", copy_hosts_lines)
        
        def on_enter_copy(event):
            copy_label.config(fg=self.colors['accent_hover'], font=("Segoe UI Variable", 9, "underline"))
        
        def on_leave_copy(event):
            copy_label.config(fg=self.colors['accent'], font=("Segoe UI Variable", 9))
        
        copy_label.bind("<Enter>", on_enter_copy)
        copy_label.bind("<Leave>", on_leave_copy)
        
        step4_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step4_frame.pack(fill=tk.X, pady=(10, 3))
        
        step_num4 = tk.Label(step4_frame, text="4.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num4.pack(side=tk.LEFT)
        
        step_text4 = tk.Label(step4_frame, text=tr('hosts_step4'), font=("Segoe UI Variable", 10),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text4.pack(side=tk.LEFT, padx=(5, 0))
        
        step5_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step5_frame.pack(fill=tk.X, pady=(3, 5))
        
        step_num5 = tk.Label(step5_frame, text="5.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num5.pack(side=tk.LEFT)
        
        step_text5 = tk.Label(step5_frame, text=tr('hosts_step5'), font=("Segoe UI Variable", 10),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text5.pack(side=tk.LEFT, padx=(5, 0))
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=30, pady=12)
        
        close_btn = RoundedButton(
            bottom_frame,
            text=tr('button_close'),
            command=dialog.destroy,
            width=100, height=32,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.current_theme
        )
        close_btn.pack(side=tk.RIGHT)

    def show_github_instruction(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('instruction_title_window'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 300
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 200
        
        dialog.geometry(f"700x500+{x}+{y}")

        dialog.update_idletasks()
        self.set_dialog_header_color(dialog)
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(15, 5))
        
        title_label = tk.Label(title_frame, text=tr('ghub_instruction_title'), 
                            font=("Segoe UI Variable", 18, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text=tr('ghub_instruction_subtitle'),
                                font=("Segoe UI Variable", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        subtitle_label.pack(pady=(3, 0))
        
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=1)
        separator.pack(fill=tk.X, padx=30, pady=8)
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        inner = tk.Frame(main_frame, bg=self.colors['bg_light'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        step1_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step1_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num1 = tk.Label(step1_frame, text="1.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num1.pack(side=tk.LEFT)
        
        step_text1 = tk.Label(step1_frame, text=tr('ghub_step1'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text1.pack(side=tk.LEFT, padx=(5, 0))
        
        step2_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step2_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num2 = tk.Label(step2_frame, text="2.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num2.pack(side=tk.LEFT)
        
        step_text2 = tk.Label(step2_frame, text=tr('ghub_step2'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text2.pack(side=tk.LEFT, padx=(5, 0))
        
        step3_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step3_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num3 = tk.Label(step3_frame, text="3.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num3.pack(side=tk.LEFT)
        
        step_text3 = tk.Label(step3_frame, text=tr('ghub_step3'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text3.pack(side=tk.LEFT, padx=(5, 0))
        
        step4_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step4_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num4 = tk.Label(step4_frame, text="4.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num4.pack(side=tk.LEFT)
        
        step_text4 = tk.Label(step4_frame, text=tr('ghub_step4'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text4.pack(side=tk.LEFT, padx=(5, 0))

        step5_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step5_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num5 = tk.Label(step5_frame, text="5.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num5.pack(side=tk.LEFT)
        
        step_text5 = tk.Label(step5_frame, text=tr('ghub_step5'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text5.pack(side=tk.LEFT, padx=(5, 0))

        step6_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step6_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num6 = tk.Label(step6_frame, text="6.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num6.pack(side=tk.LEFT)
        
        step_text6 = tk.Label(step6_frame, text=tr('ghub_step6'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text6.pack(side=tk.LEFT, padx=(5, 0))

        step7_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step7_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num7 = tk.Label(step7_frame, text="7.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num7.pack(side=tk.LEFT)
        
        step_text7 = tk.Label(step7_frame, text=tr('ghub_step7'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text7.pack(side=tk.LEFT, padx=(5, 0))

        step8_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        step8_frame.pack(fill=tk.X, pady=(0, 8))
        
        step_num8 = tk.Label(step8_frame, text="8.", font=("Segoe UI Variable", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        step_num8.pack(side=tk.LEFT)
        
        step_text8 = tk.Label(step8_frame, text=tr('ghub_step8'), font=("Segoe UI Variable", 8),
                            fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        step_text8.pack(side=tk.LEFT, padx=(5, 0))

        copy_frame_block = tk.Frame(inner, bg=self.colors['bg_light'])
        copy_frame_block.pack(fill=tk.X, pady=(10, 5))
        
        spacer = tk.Label(copy_frame_block, text="   ", font=("Segoe UI Variable", 10),
                        fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        spacer.pack(side=tk.LEFT)
        
        bullet = tk.Label(copy_frame_block, text="▸", font=("Segoe UI Variable", 9),
                        fg=self.colors['accent'], bg=self.colors['bg_light'])
        bullet.pack(side=tk.LEFT, padx=(10, 3))
        
        copy_label = tk.Label(copy_frame_block, text=tr('ghub_copy_lines'), font=("Segoe UI Variable", 9),
                            fg=self.colors['accent'], bg=self.colors['bg_light'], cursor="hand2")
        copy_label.pack(side=tk.LEFT)
        
        lists_lines = """githubapp.com
dependabot.com
github.com
api.github.com
githubassets.com
githubusercontent.com
gh.io
ghcr.io
github.io
github.new
github.dev
github.blog
github.community"""

        def copy_lists_lines(event=None):
            self.root.clipboard_clear()
            self.root.clipboard_append(lists_lines)
            self.root.update()
            copy_label.config(text=tr('tg_copied'), fg=self.colors['accent_green'])
            self.show_notification(tr('ghub_copied_notification'), 2000)
            self.root.after(2000, lambda: copy_label.config(text=tr('ghub_copy_lines'), fg=self.colors['accent']))
        
        copy_label.bind("<Button-1>", copy_lists_lines)
        
        def on_enter_copy(event):
            copy_label.config(fg=self.colors['accent_hover'], font=("Segoe UI Variable", 9, "underline"))
        
        def on_leave_copy(event):
            copy_label.config(fg=self.colors['accent'], font=("Segoe UI Variable", 9))
        
        copy_label.bind("<Enter>", on_enter_copy)
        copy_label.bind("<Leave>", on_leave_copy)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=30, pady=12)
        
        close_btn = RoundedButton(
            bottom_frame,
            text=tr('button_close'),
            command=dialog.destroy,
            width=100, height=32,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.current_theme
        )
        close_btn.pack(side=tk.RIGHT)

    def show_tg_proxy_instruction(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('instruction_title_window'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

        secret = getattr(self, '_tg_secret', None)
        if not secret:
            secret = tr('error_secret_not_found')
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 310
        
        dialog.geometry(f"500x520+{x}+{y}")
        
        dialog.update_idletasks()
        self.set_dialog_header_color(dialog)
        
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
            
            if self.tg_fake_tls and self.tg_fake_tls_domain:
                domain_hex = self.tg_fake_tls_domain.encode('ascii').hex()
                link = f"ee{secret}{domain_hex}"
                notification = tr('notification_copied_secret')
            else:
                link = f"{secret}"
                notification = tr('notification_copied_secret')
            
            self.root.clipboard_clear()
            self.root.clipboard_append(link)
            self.root.update()
            copy_label.config(text=tr('tg_copied'), fg=self.colors['accent_green'])
            self.show_notification(notification, 1500)
        
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
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.current_theme
        )
        close_btn.pack(side=tk.RIGHT)

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
            self.root.after(500, self.show_tg_proxy_instruction)

        self.root.after(500, self.update_tray_icon_state)
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
                    if len(logs) > 1000:
                        logs = logs[-1000:]
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
    mutex_name = "ZapretLauncher_SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Zapret Launcher")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        sys.exit(0)
    
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
    
    if '--no-splash' not in sys.argv and '--from-splash' not in sys.argv:
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
