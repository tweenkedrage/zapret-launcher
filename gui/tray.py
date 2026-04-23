import pystray
from PIL import Image, ImageDraw
from utils.updater import check_launcher_updates
import time
import ctypes
from pathlib import Path
from tkinter import messagebox
import subprocess
from utils.languages import tr
import re

BASE_DIR = Path(__file__).parent.parent

class ModernSystemTray:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.current_rtt = None
        self.last_rtt_update = 0
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
                BASE_DIR / "resources" / "icon.ico",
                BASE_DIR / "resources" / "icon.png",
                Path("resources/icon.ico"),
                Path("icon.ico"),
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
                indicator_size = 12
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
                f"\n"
                f"{stats['session_time_str']}\n"
                f"{rtt_text}\n"
                f"{stats['speed_down_str']} / {stats['speed_up_str']}\n"
                f"{stats['down_str']} / {stats['up_str']}"
            )
        else:
            return (
                f"Zapret Launcher\n"
                f"{tr('status_ready')}"
            )

    def update_menu(self, image=None):
        menu = pystray.Menu(
            pystray.MenuItem(
                tr('menu_open'),
                self.show_window,
                default=True
            ),
            pystray.MenuItem(
                tr('menu_connect') if not self.app.is_connected else tr('menu_disconnect'),
                self.toggle_connection
            ),
            pystray.MenuItem(
                tr('menu_check_updates'),
                self.check_launcher_updates
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

    def update_tooltip(self):
        if self.icon:
            try:
                self.icon.title = self.get_tooltip_text()
            except:
                pass

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
                BASE_DIR / "resources" / "icon.ico",
                BASE_DIR / "resources" / "icon.png",
                Path("resources/icon.ico"),
                Path("icon.ico"),
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
                indicator_size = 12
                indicator_x = 64 - indicator_size - 4
                indicator_y = 64 - indicator_size - 4
                
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

    def quit_from_tray(self):
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
                if self.icon:
                    self.icon.stop()
                self.app.quit_from_tray()
        else:
            if self.icon:
                self.icon.stop()
            self.app.quit_from_tray()

    def show_window(self):
        try:
            if not self.app.root.winfo_exists():
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
            
            try:
                hwnd = ctypes.windll.user32.GetParent(self.app.root.winfo_id())
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        except Exception:
            pass

    def check_launcher_updates(self):
        check_launcher_updates(self.app, silent=False)

    def toggle_connection(self):
        if self.app.is_connected:
            self.app.disconnect()
        else:
            self.app.show_mode_selector()
        self.update_icon_state()

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
        self.icon.run()
