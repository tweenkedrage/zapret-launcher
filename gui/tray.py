# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import pystray
from PIL import Image, ImageDraw
import webbrowser
from tkinter import messagebox
import subprocess
from utils.languages import tr
import urllib.request
import threading
import re
import time
from config import BASE_DIR, CURRENT_BUILD

class ModernSystemTray:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.current_rtt = None
        self.last_rtt_update = 0
        self.update_available = False
        self.zapret_update_available = False
        self.update_check_timer_id = None
        self.colors = {
            'bg_dark': '#1E1E24',
            'bg_medium': '#2D2D35',
            'bg_light': '#3D3D45',
            'accent': '#d0a2e9',
            'accent_green': '#4ade80',
            'accent_red': '#f87171',
            'text_primary': '#FFFFFF',
            'text_secondary': '#A0A0B0',
            'button_bg': '#2D2D35',
            'button_hover': '#3D3D45',
        }
        self.create_icon()

    def create_icon(self):
        try:
            icon_paths = [
                BASE_DIR / "resources" / "icon.ico"
            ]
            
            image = None
            for path in icon_paths:
                if path and path.exists():
                    try:
                        image = Image.open(str(path))
                        if image.mode != 'RGBA':
                            image = image.convert('RGBA')
                        image = image.resize((64, 64), Image.Resampling.LANCZOS)
                        break
                    except:
                        continue
            
            if image:
                draw = ImageDraw.Draw(image)
                indicator_size = 16
                indicator_x = 64 - indicator_size - 4
                indicator_y = 64 - indicator_size - 4
                
                if self.app.is_connected:
                    indicator_color = self._hex_to_rgb(self.colors['accent_green'])
                else:
                    indicator_color = self._hex_to_rgb(self.colors['accent_red'])
                
                draw.ellipse(
                    [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                    fill=indicator_color
                )
                
                draw.ellipse(
                    [indicator_x - 1, indicator_y - 1, indicator_x + indicator_size + 1, indicator_y + indicator_size + 1],
                    outline=(255, 255, 255, 255),
                    width=1
                )
            
        except Exception:
            image = Image.new('RGBA', (64, 64), color=self.colors['accent'])
            draw = ImageDraw.Draw(image)
            draw.text((20, 20), "Z", fill='white')

        self.update_menu(image)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def get_tooltip_text(self):
        update_text = ""
        if hasattr(self, 'update_available') and self.update_available:
            update_text = f"\n{tr('update_available')}"
        elif hasattr(self, 'update_available') and self.zapret_update_available:
            update_text = f"\n{tr('update_available')}"
        
        if self.app.is_connected:
            stats = self.app.stats.get_stats_dict()
            mode_text = self.app.mode_label.cget('text') if hasattr(self.app, 'mode_label') and self.app.mode_label else tr('status_connected')
            
            rtt_text = ""
            if hasattr(self.app, 'stats_rtt_label') and self.app.stats_rtt_label:
                rtt_value = self.app.stats_rtt_label.cget('text')
                if rtt_value and rtt_value != "-- ms":
                    rtt_text = f"{rtt_value}"
            
            return (
                f"Zapret Launcher\n"
                f"{tr('mode')} {mode_text}\n"
                f"———————————\n"
                f"{stats['session_time_str']}\n"
                f"{rtt_text}\n"
                f"{stats['speed_down_str']} / {stats['speed_up_str']}\n"
                f"{stats['down_str']} / {stats['up_str']}"
                f"\n{update_text}"
            )
        else:
            return (
                f"Zapret Launcher\n"
                f"{tr('status_ready')}"
            )

    def update_menu(self, image=None):
        help_menu = pystray.Menu(
            pystray.MenuItem(
                tr('menu_help_report'),
                lambda: webbrowser.open("https://t.me/zapret_technical"),
                enabled=True
            ),
            pystray.MenuItem(
                tr('menu_help_release'),
                lambda: webbrowser.open("https://zapret-launcher.ru/changelog"),
                enabled=True
            ),
            pystray.MenuItem(
                tr('menu_help_idea'),
                lambda: webbrowser.open("https://t.me/zapret_technical"),
                enabled=True
            ),
            pystray.MenuItem(
                tr('menu_help_readme'),
                lambda: webbrowser.open("https://github.com/tweenkedrage/zapret-launcher/blob/main/docs/README.md"),
                enabled=True
            ),
            pystray.MenuItem(
                tr('menu_help_logs'),
                lambda: self.open_logs(),
                enabled=True
            )
        )
        settings_menu = pystray.Menu(
            pystray.MenuItem(
                f"{tr('menu_settings_interface')} ({self._get_interval_text()})",
                self._cycle_refresh_interval,
                enabled=True
            ),
            pystray.MenuItem(
                tr('menu_settings_folder'),
                self.app.open_appdata_folder,
                enabled=True
            ),
        )
        
        is_connecting = hasattr(self.app, '_connecting') and self.app._connecting
        is_disconnecting = hasattr(self.app, '_disconnecting') and self.app._disconnecting
        is_busy = is_connecting or is_disconnecting
        
        if is_busy:
            if is_connecting:
                connect_text = tr('status_starting')
            else:
                connect_text = tr('status_disconnecting')
            connect_item = pystray.MenuItem(
                connect_text,
                None,
                enabled=False
            )
        else:
            if self.app.is_connected:
                connect_text = tr('menu_disconnect')
            else:
                connect_text = tr('menu_connect')
            connect_item = pystray.MenuItem(
                connect_text,
                self.toggle_connection,
                enabled=True
            )
        
        menu = pystray.Menu(
            pystray.MenuItem(
                tr('menu_open'),
                self.show_window,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            connect_item,
            pystray.MenuItem(
                tr('menu_settings'),
                settings_menu
            ),
            pystray.MenuItem(
                tr('menu_help'),
                help_menu
            ),
            pystray.MenuItem(
                tr('menu_exit'),
                self.quit_from_tray
            )
        )
        
        if self.icon:
            self.icon.menu = menu
            if image:
                self.icon.icon = image
            self.icon.title = self.get_tooltip_text()
        else:
            if image is None:
                image = Image.new('RGBA', (64, 64), color=self.colors['accent'])
                draw = ImageDraw.Draw(image)
                draw.text((20, 20), "Z", fill='white')
            
            self.icon = pystray.Icon(
                "zapret_launcher",
                image,
                self.get_tooltip_text(),
                menu
            )

    def _get_interval_text(self):
        interval = self.app.update_interval
        if interval == 1:
            return tr('settings_interval_fast_small')
        elif interval == 5:
            return tr('settings_interval_5_small')
        elif interval == 10:
            return tr('settings_interval_10_small')
        elif interval == 30:
            return tr('settings_interval_30_small')
        elif interval == 60:
            return tr('settings_interval_60_small')
        elif interval is None:
            return tr('settings_interval_off_small')
        else:
            return f"{interval} {tr('seconds')}"

    def _cycle_refresh_interval(self):
        intervals = [1, 5, 10, 30, 60, None]
        current = self.app.update_interval
        next_index = (intervals.index(current) + 1) % len(intervals) if current in intervals else 1
        new_interval = intervals[next_index]
        
        if new_interval is None:
            self.app.update_interval_index = 5
            self.app.update_interval = None
        elif new_interval == 1:
            self.app.update_interval_index = 0
            self.app.update_interval = 1
        elif new_interval == 5:
            self.app.update_interval_index = 1
            self.app.update_interval = 5
        elif new_interval == 10:
            self.app.update_interval_index = 2
            self.app.update_interval = 10
        elif new_interval == 30:
            self.app.update_interval_index = 3
            self.app.update_interval = 30
        elif new_interval == 60:
            self.app.update_interval_index = 4
            self.app.update_interval = 60
        
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()

        if hasattr(self.app, 'pages') and hasattr(self.app.pages, 'settings_page_obj'):
            self.app.pages.settings_page_obj.update_interval_display()

        self.update_menu()

    def open_logs(self):
        try:
            self.show_window()
            self.app.root.after(500, lambda: self.app.show_logs_page())
        except Exception:
            pass

    def update_tooltip(self):
        if self.icon:
            try:
                self.icon.title = self.get_tooltip_text()
            except:
                pass

    def check_for_updates(self):
        try:
            buildnumber_url = "https://zapret-launcher.ru/updater/docs/build_number.txt"
            req = urllib.request.Request(
                buildnumber_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                latest_build = response.read().decode('utf-8').strip()
            
            current_build = CURRENT_BUILD
            need_launcher_update = self._compare_builds(current_build, latest_build)
            
            if need_launcher_update:
                if not self.update_available:
                    self.update_available = True
                    self.zapret_update_available = False
                    self.update_icon_state()
                return
            
            try:
                zapret_version_url = "https://zapret-launcher.ru/updater/docs/zapret_version.txt"
                req_zapret = urllib.request.Request(
                    zapret_version_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req_zapret, timeout=10) as response:
                    latest_zapret = response.read().decode('utf-8').strip()
                
                current_zapret = self.app.get_current_zapret_version()
                need_zapret_update = self.app._compare_zapret_versions(current_zapret, latest_zapret)
                
                if need_zapret_update:
                    if not self.zapret_update_available:
                        self.zapret_update_available = True
                        self.update_available = False
                        self.update_icon_state()
                else:
                    if self.zapret_update_available or self.update_available:
                        self.zapret_update_available = False
                        self.update_available = False
                        self.update_icon_state()
            except Exception:
                if self.zapret_update_available or self.update_available:
                    self.zapret_update_available = False
                    self.update_available = False
                    self.update_icon_state()
                    
        except Exception:
            pass

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

    def stop_update_checker(self):
        if self.update_check_timer_id:
            try:
                self.app.root.after_cancel(self.update_check_timer_id)
            except:
                pass
            self.update_check_timer_id = None

    def _schedule_update_check(self):
        if not hasattr(self, '_first_check_done'):
            interval = 5000
            self._first_check_done = True
        else:
            interval = 60 * 60 * 1000
        self.update_check_timer_id = self.app.root.after(interval, self._do_update_check)

    def _do_update_check(self):
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        self._schedule_update_check()

    def update_icon_state(self):
        try:
            if not self.icon:
                self.create_icon()
                return
            
            is_connected = False
            
            if hasattr(self.app, 'zapret') and self.app.zapret:
                if self.app.zapret.is_winws_running():
                    is_connected = True
            
            if hasattr(self.app, 'tg_proxy') and self.app.tg_proxy:
                if self.app.tg_proxy.is_running:
                    is_connected = True
            
            if not is_connected and hasattr(self.app, 'is_connected'):
                is_connected = self.app.is_connected
            
            icon_paths = [
                BASE_DIR / "resources" / "icon.ico"
            ]
            
            image = None
            for path in icon_paths:
                if path and path.exists():
                    try:
                        image = Image.open(str(path))
                        if image.mode != 'RGBA':
                            image = image.convert('RGBA')
                        image = image.resize((64, 64), Image.Resampling.LANCZOS)
                        break
                    except:
                        continue
            
            if image:
                draw = ImageDraw.Draw(image)
                indicator_size = 16
                indicator_x = 64 - indicator_size - 4
                indicator_y = 64 - indicator_size - 4
                
                if hasattr(self, 'update_available') and self.update_available:
                    draw.ellipse(
                        [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                        fill=(30, 144, 255)
                    )
                    draw.ellipse(
                        [indicator_x - 1, indicator_y - 1, indicator_x + indicator_size + 1, indicator_y + indicator_size + 1],
                        outline=(255, 255, 255, 255),
                        width=1
                    )
                elif hasattr(self, 'zapret_update_available') and self.zapret_update_available:
                    draw.ellipse(
                        [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                        fill=(30, 144, 255)
                    )
                    draw.ellipse(
                        [indicator_x - 1, indicator_y - 1, indicator_x + indicator_size + 1, indicator_y + indicator_size + 1],
                        outline=(255, 255, 255, 255),
                        width=1
                    )
                else:
                    if is_connected:
                        indicator_color = self._hex_to_rgb(self.colors['accent_green'])
                    else:
                        indicator_color = self._hex_to_rgb(self.colors['accent_red'])
                    
                    draw.ellipse(
                        [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                        fill=indicator_color
                    )
                    draw.ellipse(
                        [indicator_x - 1, indicator_y - 1, indicator_x + indicator_size + 1, indicator_y + indicator_size + 1],
                        outline=(255, 255, 255, 255),
                        width=1
                    )
                
                self.icon.icon = image
        except Exception:
            pass

    def force_update_menu(self):
        if self.icon:
            try:
                self.update_menu()
                self.icon.update_menu()
            except Exception:
                pass

    def quit_from_tray(self):
        if hasattr(self.app, '_disconnecting') and self.app._disconnecting:
            self.app.root.after(500, self.quit_from_tray)
            return
        
        is_any_running = False
        if hasattr(self.app, 'zapret') and self.app.zapret:
            if self.app.zapret.is_winws_running():
                is_any_running = True
        if hasattr(self.app, 'tg_proxy') and self.app.tg_proxy:
            if self.app.tg_proxy.is_running:
                is_any_running = True
        if hasattr(self.app, 'is_connected') and self.app.is_connected:
            is_any_running = True
        
        if is_any_running:
            result = messagebox.askyesno(
                tr('dialog_exit'),
                tr('dialog_exit_message')
            )
            if result:
                self._prepare_and_quit()
        else:
            self._prepare_and_quit()

    def _prepare_and_quit(self):
        try:
            self.app.save_settings()
        except:
            pass
        
        if self.icon:
            self.icon.stop()

        if hasattr(self.app, 'zapret') and self.app.zapret:
            self.app.zapret.stop_current_strategy()
        if hasattr(self.app, 'tg_proxy') and self.app.tg_proxy:
            self.app.tg_proxy.stop()
        self.app.root.after(500, self.app.quit_from_tray)

    def show_window(self):
        try:
            if not self.app.root.winfo_exists():
                return
            
            if self.app.root.state() == 'normal' and self.app.root.winfo_viewable():
                self.app.root.lift()
                self.app.root.focus_force()
                return
                
            self.app.root.deiconify()
            self.app.root.lift()
            self.app.root.focus_force()
            self.app.root.state('normal')
            
            try:
                self.app.root.attributes('-alpha', 0.0)
                for i in range(0, 101, 10):
                    self.app.root.attributes('-alpha', i / 100)
                    self.app.root.update()
                    time.sleep(0.01)
                self.app.root.attributes('-alpha', 1.0)
            except:
                pass
        except Exception:
            pass

    def toggle_connection(self):
        is_connecting = hasattr(self.app, '_connecting') and self.app._connecting
        is_disconnecting = hasattr(self.app, '_disconnecting') and self.app._disconnecting
        
        if is_connecting or is_disconnecting:
            return
        
        if self.app.is_connected:
            self._do_toggle_connection()
        else:
            self.show_window()
            self.app.root.after(200, self._check_and_connect)
        
        self.update_icon_state()

    def _check_and_connect(self):
        self.app.toggle_connection()

    def _do_toggle_connection(self):
        if self.app.is_connected:
            self.app.disconnect()
        else:
            self.app.show_mode_selector()

    def get_rtt(self):
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '8.8.8.8'],
                capture_output=True, text=True,
                timeout=2
            )
            if result.returncode == 0:
                match = re.search(r'(?:время|time)[=<>]\s*(\d+)', result.stdout, re.IGNORECASE)
                if match:
                    return int(match.group(1))
        except:
            pass
        return None

    def run(self):
        self.start_update_checker()
        self.icon.run()
