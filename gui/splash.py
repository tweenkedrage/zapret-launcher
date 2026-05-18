import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk
from utils.languages import tr
import urllib.request
import subprocess
import sys
import threading
import re
import ctypes
import time
import zipfile
import shutil
import os

class SplashWindow:
    def __init__(self, theme='Dark', current_version=None, current_build=None):
        self.window = tk.Tk()
        
        self.theme = {
            'bg_dark': '#1E1E1E',
            'bg_light': '#2D2D2D',
            'accent': '#0078D4',
            'accent_hover': '#e8ccf7',
            'text_secondary': '#A0A0A0'
        }
        
        if current_version is None:
            for arg in sys.argv:
                if arg.startswith('--version='):
                    current_version = arg.split('=')[1]
                    break
        self.current_version = current_version if current_version else "0.0"
        
        if current_build is None:
            for arg in sys.argv:
                if arg.startswith('--build='):
                    current_build = arg.split('=')[1]
                    break
        self.current_build = current_build if current_build else "0"

        self.width = 320
        self.height = 260
        self._is_closing = False

        self.build_url = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/docs/build_number.txt"
        self.exe_url = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/updater/Zapret%20Launcher.exe"
        self.zip_url = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/updater/_internal.zip"
        
        self.appdata_path = Path(os.environ.get('APPDATA', '')) / "Zapret Launcher"
        self.internal_path = self.appdata_path / "_internal"

        self.setup_window()
        self.setup_ui()

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def run_as_admin(self):
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()
        
    def after(self, ms, func):
        if not self._is_closing:
            try:
                return self.window.after(ms, func)
            except:
                pass
        return None
        
    def setup_window(self):
        self.window.overrideredirect(True)
        self.window.configure(bg=self.theme['bg_dark'])
        self.window.attributes('-topmost', True)
        self.window.bind("<Button-1>", self.start_move)
        self.window.bind("<B1-Motion>", self.on_move)
        self.center_window()
        
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")
        
    def center_window(self):
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
    def setup_ui(self):
        main_frame = tk.Frame(self.window, bg=self.theme['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        center_container = tk.Frame(main_frame, bg=self.theme['bg_dark'])
        center_container.place(relx=0.5, rely=0.45, anchor="center")
        
        self.logo_label = tk.Label(center_container, bg=self.theme['bg_dark'])
        self.logo_label.pack(pady=(0, 5))
        self.load_logo()
        
        self.status_label = tk.Label(
            center_container,
            text=tr('splash_check_connecting'),
            font=("Segoe UI Variable", 10),
            fg=self.theme['text_secondary'],
            bg=self.theme['bg_dark']
        )
        self.status_label.pack(pady=(0, 8))
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            center_container,
            variable=self.progress_var,
            length=260,
            mode='determinate',
            maximum=100
        )
        self.progress_bar.pack()
        
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            'TProgressbar',
            background=self.theme['accent_hover'],
            troughcolor=self.theme['bg_light'],
            thickness=6
        )
        
    def load_logo(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).parent.parent
            
            icon_paths = [
                base_path / "resources" / "icon.png",
                base_path / "resources" / "icon.ico",
                base_path / "icon.png",
            ]
            
            for path in icon_paths:
                if path.exists():
                    img = Image.open(path)
                    img = img.resize((140, 140), Image.Resampling.LANCZOS)
                    self.logo_image = ImageTk.PhotoImage(img)
                    self.logo_label.config(image=self.logo_image)
                    return
                    
            self.logo_label.config(image='', text='')
        except Exception:
            self.logo_label.config(image='', text='')
    
    def update_status(self, text, progress=None):
        if self._is_closing:
            return
        try:
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.config(text=text)
            if progress is not None and self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_var.set(progress)
        except:
            pass
    
    def start(self):
        if not self.is_admin():
            self.run_as_admin()
            return
        
        threading.Thread(target=self.cleanup_old_internal_folders, daemon=True).start()
    
        self._check_internet()
        self.window.mainloop()

    def _check_internet(self):
        self.update_status(tr('splash_check_connecting'), 10)
        def check():
            try:
                req = urllib.request.Request("http://www.google.com", headers={'User-Agent': 'Mozilla/5.0'})
                urllib.request.urlopen(req, timeout=5)
                self.after(0, self._check_for_update)
            except Exception:
                self.after(0, lambda: self.update_status(tr('splash_check_connect_error'), 20))
                self.after(2000, self._launch_main_app)
        threading.Thread(target=check, daemon=True).start()

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

    def _compare_versions(self, current, latest):
        current_tuple = self._version_to_tuple(current)
        latest_tuple = self._version_to_tuple(latest)
        need_update = latest_tuple > current_tuple
        return need_update
    
    def _compare_builds(self, current, latest):
        try:
            current_int = int(current)
            latest_int = int(latest)
            return latest_int > current_int
        except ValueError:
            return str(latest) > str(current)

    def _check_for_update(self):
        self.update_status(tr('splash_check_updates'), 30)
        
        def check():
            try:
                req = urllib.request.Request(
                    self.build_url,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    latest_build = response.read().decode('utf-8').strip()
                
                current_build  = self.current_build
                need_update = self._compare_builds(current_build, latest_build)
            
                if need_update:
                    self.after(1000, lambda: self._start_update(latest_build))
                else:
                    self.after(0, lambda: self.update_status(tr('splash_starting_exe'), 100))
                    self.after(1500, self._launch_main_app)
                    
            except Exception:
                self.after(0, lambda: self.update_status(tr('splash_starting_exe'), 100))
                self.after(1500, self._launch_main_app)
        
        threading.Thread(target=check, daemon=True).start()

    def _start_update(self, new_build):
        self.update_status(f"{tr('splash_downloading')}", 50)
        self.after(500, self._download_and_update)

    def _download_with_progress(self, url, dest_path, start_progress=0, end_progress=100):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(dest_path, 'wb') as f:
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress_range = end_progress - start_progress
                            progress = start_progress + int((downloaded / total_size) * progress_range)
                            progress = min(end_progress, max(start_progress, progress))
                            
                            def update_prog(p=progress):
                                if not self._is_closing:
                                    try:
                                        self.progress_var.set(p)
                                    except:
                                        pass
                            self.after(0, update_prog)
            return True
        except Exception:
            return False

    def _extract_zip_with_progress(self, zip_path, extract_path, start_progress=0, end_progress=100):
        try:
            self._stop_zapret_processes()
            
            if self.internal_path.exists():
                self.update_status(tr('splash_remove_old'), start_progress)
                
                for root, dirs, files in os.walk(self.internal_path):
                    for file in files:
                        try:
                            file_path = Path(root) / file
                            os.chmod(file_path, 0o666)
                        except:
                            pass
                
                for attempt in range(3):
                    try:
                        shutil.rmtree(self.internal_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            continue
                        else:
                            temp_old = self.internal_path.parent / f"_internal_old_{int(time.time())}"
                            self.internal_path.rename(temp_old)
                            threading.Thread(target=lambda: shutil.rmtree(temp_old, ignore_errors=True)).start()
                            break
            
            self.appdata_path.mkdir(parents=True, exist_ok=True)
            self.update_status(tr('splash_extracting'), start_progress + 5)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                total_files = len(zip_ref.namelist())
                extracted = 0
                
                for file_info in zip_ref.infolist():
                    zip_ref.extract(file_info, self.appdata_path)
                    extracted += 1
                    
                    extracted_path = self.appdata_path / file_info.filename
                    if extracted_path.exists():
                        try:
                            os.chmod(extracted_path, 0o666)
                        except:
                            pass
                    
                    if total_files > 0:
                        progress_range = end_progress - start_progress
                        progress = start_progress + int((extracted / total_files) * progress_range)
                        progress = min(end_progress, max(start_progress, progress))
                        
                        def update_prog(p=progress):
                            if not self._is_closing:
                                try:
                                    self.progress_var.set(p)
                                except:
                                    pass
                        self.after(0, update_prog)
            
            return True
        except Exception:
            return False

    def _download_and_update(self):
        was_admin = self.is_admin()
        
        def update_worker():
            temp_exe = None
            temp_zip = None
            try:
                current_exe = Path(sys.executable)
                temp_exe = current_exe.parent / f"{current_exe.stem}_new.exe"
                temp_zip = current_exe.parent / "_internal_temp.zip"
                
                self.after(0, lambda: self.update_status(tr('splash_downloading_exe'), 0))
                exe_success = self._download_with_progress(self.exe_url, temp_exe, 0, 40)
                
                if not exe_success or not temp_exe.exists() or temp_exe.stat().st_size == 0:
                    raise Exception("Failed to download exe file")
                
                self.after(0, lambda: self.update_status(tr('splash_downloading_zip'), 40))
                zip_success = self._download_with_progress(self.zip_url, temp_zip, 40, 70)
                
                if not zip_success or not temp_zip.exists() or temp_zip.stat().st_size == 0:
                    raise Exception("Failed to download zip file")
                
                self.after(0, lambda: self.update_status(tr('splash_extracting_files'), 70))
                extract_success = self._extract_zip_with_progress(temp_zip, self.appdata_path, 70, 95)
                
                if not extract_success:
                    raise Exception("Failed to extract zip file")
                
                self.after(0, lambda: self.update_status(tr('splash_install_update'), 95))
                self._stop_zapret_processes()
                
                old_exe = current_exe.with_suffix(".exe.old")
                if old_exe.exists():
                    old_exe.unlink()
                
                current_exe.rename(old_exe)
                temp_exe.rename(current_exe)
                
                if temp_zip.exists():
                    temp_zip.unlink()
                
                self.after(0, lambda: self.update_status(tr('splash_starting_exe'), 100))
                
                if was_admin:
                    subprocess.Popen([str(current_exe)])
                else:
                    subprocess.Popen([str(current_exe)])
                
                self.after(500, self.close)
                sys.exit(0)
                
            except Exception:
                self.after(0, lambda: self.update_status(tr('splash_update_error'), 100))
                self.after(2000, self._launch_main_app)
                
                if temp_exe and temp_exe.exists():
                    try:
                        temp_exe.unlink()
                    except:
                        pass
                if temp_zip and temp_zip.exists():
                    try:
                        temp_zip.unlink()
                    except:
                        pass
        
        threading.Thread(target=update_worker, daemon=True).start()
    
    def _stop_zapret_processes(self):
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'winws.exe'], 
                          capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(['sc', 'stop', 'WinDivert'], 
                          capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(['taskkill', '/F', '/IM', 'nfqws.exe'], 
                      capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
        except:
            pass

    def cleanup_old_internal_folders(self):
        try:
            appdata_path = Path(os.environ.get('APPDATA', '')) / "Zapret Launcher"
            if not appdata_path.exists():
                return
            
            deleted_count = 0
            
            for item in appdata_path.iterdir():
                if item.is_dir() and item.name.startswith('_internal_old_'):
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            try:
                                file_path = Path(root) / file
                                os.chmod(file_path, 0o666)
                            except:
                                pass
                    
                    try:
                        shutil.rmtree(item)
                        deleted_count += 1
                    except PermissionError:
                        try:
                            new_name = item.parent / f"_internal_old_del_{int(time.time())}"
                            item.rename(new_name)
                            shutil.rmtree(new_name, ignore_errors=True)
                            deleted_count += 1
                        except:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _launch_main_app(self):
        if self._is_closing:
            return
        self.update_status(tr('splash_starting_exe'), 100)
        time.sleep(0.5)
        self.close()
        
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = sys.argv[0]
            
            subprocess.Popen([exe_path, '--no-splash', '--from-splash'])
        except Exception:
            pass
    
    def close(self):
        self._is_closing = True
        try:
            self.window.destroy()
        except:
            pass
