# Zapret Launcher - GUI for zapret
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk
from utils.languages import tr
from gui.theme import get_theme
from config import BASE_DIR, APPDATA_DIR
import urllib.request
import subprocess
import sys
import pywinstyles
import webbrowser
import threading
import re
import ctypes
import time
import zipfile
import shutil
import os

class SplashWindow:
    def __init__(self, theme='Default', current_version=None, current_build=None, zapret_version=None):
        self.window = tk.Tk()
        self.colors_name = theme
        self.colors = get_theme(theme)
        
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

        if zapret_version is None:
            for arg in sys.argv:
                if arg.startswith('--zapret-version='):
                    zapret_version = arg.split('=')[1]
                    break
        self.current_zapret_version = zapret_version if zapret_version else "0.0"

        self.width = 320
        self.height = 260
        self._is_closing = False

        self.zapret_version_url = "https://zapret-launcher.ru/updater/docs/zapret_version.txt"
        self.build_url = "https://zapret-launcher.ru/updater/docs/build_number.txt" # build_number.txt | test/test.txt
        self.exe_url = "https://zapret-launcher.ru/updater/Zapret%20Launcher.exe" # Zapret%20Launcher.exe
        self.zip_url = "https://zapret-launcher.ru/updater/_internal.zip"
        self.zapret_url = "https://zapret-launcher.ru/updater/zapret_core.zip"
        
        self.appdata_path = APPDATA_DIR
        self.internal_path = self.appdata_path / "_internal"

        self._target_progress = 0
        self._animation_id = None

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
        self.window.overrideredirect(False)
        self.window.title("Zapret Launcher")
        self.window.configure(bg=self.colors['bg_dark'])
        self.window.resizable(False, False)

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
                            self.window.iconbitmap(default=str(path))
                            icon_loaded = True
                            break
                    except:
                        continue
        except Exception:
            pass

        self._update_window_title_color()
        self.center_window()

    def _update_window_title_color(self):
        try:
            if self.colors_name == 'Default':
                header_color = "#0F0F12"
            elif self.colors_name == 'Pink':
                header_color = "#1E1B2E"
            else:
                header_color = self.colors['bg_dark']
            pywinstyles.change_header_color(self.window, header_color)
            
        except ImportError:
            pass
        except Exception:
            pass
        
    def center_window(self):
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
    def setup_ui(self):
        main_frame = tk.Frame(self.window, bg=self.colors['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        center_container = tk.Frame(main_frame, bg=self.colors['bg_dark'])
        center_container.place(relx=0.5, rely=0.45, anchor="center")
        
        self.logo_label = tk.Label(center_container, bg=self.colors['bg_dark'])
        self.logo_label.pack(pady=(0, 5))
        self.load_logo()
        
        self.status_label = tk.Label(
            center_container,
            text=tr('splash_check_connecting'),
            font=("Segoe UI Variable", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
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
            background=self.colors['accent_hover'],
            troughcolor=self.colors['bg_light'],
            thickness=6
        )
        
        bottom_frame = tk.Frame(center_container, bg=self.colors['bg_dark'])
        bottom_frame.pack(fill=tk.X, pady=(15, 0))
        
        manual_label = tk.Label(
            bottom_frame,
            text=tr('splash_help_update'),
            font=("Segoe UI Variable", 8),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark'],
            cursor="hand2"
        )
        manual_label.pack()
        
        def on_enter_manual(event):
            manual_label.config(fg=self.colors['accent'])
        
        def on_leave_manual(event):
            manual_label.config(fg=self.colors['text_secondary'])
        
        def on_click_manual(event):
            webbrowser.open("https://zapret-launcher.ru/updater/zapret-launcher-installer.exe")
        
        manual_label.bind("<Enter>", on_enter_manual)
        manual_label.bind("<Leave>", on_leave_manual)
        manual_label.bind("<Button-1>", on_click_manual)
        
    def load_logo(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).parent.parent
            
            icon_paths = [
                base_path / "resources" / "icon.ico",
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
                if text is not None:
                    self.status_label.config(text=text)
            if progress is not None:
                self._target_progress = progress
                if self._animation_id:
                    try:
                        self.window.after_cancel(self._animation_id)
                    except:
                        pass
                    self._animation_id = None
                self._animate_progress()
        except:
            pass
    
    def _animate_progress(self):
        if self._is_closing:
            return
        
        current = self.progress_var.get()
        target = self._target_progress
        
        if abs(current - target) <= 1:
            if current != target:
                self.progress_var.set(target)
            return
        
        if current < target:
            diff = target - current
            step = max(1, diff // 8)
            new_value = min(current + step, target)
        else:
            diff = current - target
            step = max(1, diff // 8)
            new_value = max(current - step, target)
        
        self.progress_var.set(new_value)
        self._animation_id = self.window.after(16, self._animate_progress)
    
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
        
    def get_current_zapret_version(self):
        try:
            version_file = self.appdata_path / "zapret_core" / "version.txt"
            if version_file.exists():
                version = version_file.read_text(encoding='utf-8').strip()
                version = re.sub(r'[^\d\.a-z]', '', version.lower())
                return version
        except Exception:
            pass
        return "0.0"
    
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
                    latest_build = re.sub(r'[^\d]', '', latest_build)
                
                current_build = self.current_build
                need_launcher_update = self._compare_builds(current_build, latest_build)
                need_zapret_update, latest_zapret = self._check_zapret_core_update()
                
                if need_launcher_update:
                    self.after(1000, lambda: self._start_update(latest_build))
                elif need_zapret_update:
                    self.after(1000, lambda: self._update_zapret_core_only(latest_zapret))
                else:
                    self.after(0, lambda: self.update_status(tr('splash_starting_exe'), 100))
                    self.after(1500, self._launch_main_app)
                    
            except Exception:
                self.after(0, lambda: self.update_status(tr('splash_starting_exe'), 100))
                self.after(1500, self._launch_main_app)
        
        threading.Thread(target=check, daemon=True).start()

    def _check_zapret_core_update(self):
        try:
            req = urllib.request.Request(
                self.zapret_version_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                latest_version = response.read().decode('utf-8').strip()
            
            current_version = self.get_current_zapret_version()
            need_update = self._compare_zapret_versions(current_version, latest_version)
            return need_update, latest_version
        except Exception:
            return False, None

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
                    last_update = 0
                    
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = start_progress + int((downloaded / total_size) * (end_progress - start_progress))
                            progress = min(end_progress, max(start_progress, progress))
                            
                            now = time.time() * 1000
                            if now - last_update > 50:
                                last_update = now
                                if not self._is_closing:
                                    self._target_progress = progress
                                    self._animate_progress()
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
                last_update = 0
                
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
                        progress = start_progress + int((extracted / total_files) * (end_progress - start_progress))
                        
                        now = time.time() * 1000
                        if now - last_update > 30:
                            last_update = now
                            if not self._is_closing:
                                self._target_progress = progress
                                self._animate_progress()
            
            return True
        except Exception:
            return False
        
    def _update_zapret_core_only(self, new_version):
        self.update_status(tr('splash_updating_zapret'), 80)
        
        def update_zapret_thread():
            try:
                self._stop_zapret_processes()
                success = self._download_zapret_core()
                
                if success:
                    version_file = self.appdata_path / "zapret_core" / "version.txt"
                    version_file.write_text(new_version, encoding='utf-8')
                    
                    self.after(0, lambda: self.update_status(None, 100))
                    self.after(1000, self._launch_main_app)
                else:
                    self.after(0, lambda: self.update_status(tr('splash_update_error'), 100))
                    self.after(2000, self._launch_main_app)
                    
            except Exception:
                self.after(0, lambda: self.update_status(tr('splash_update_error'), 100))
                self.after(2000, self._launch_main_app)
        
        threading.Thread(target=update_zapret_thread, daemon=True).start()
        
    def _download_zapret_core(self):
        temp_zip = None
        try:
            zapret_dir = self.appdata_path / "zapret_core"
            temp_zip = self.appdata_path / "zapret_core_temp.zip"
            
            self.update_status(tr('splash_downloading_zapret'), 80)
            success = self._download_with_progress(self.zapret_url, temp_zip, 80, 88)
            
            if not success:
                raise Exception("Failed to download zapret_core.zip")
            
            self.update_status(tr('splash_extracting_zapret'), 88)
            
            self._stop_zapret_processes()
            time.sleep(1)
            
            temp_extract = self.appdata_path / "zapret_core_temp_extract"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            temp_extract.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                total_files = len(zf.namelist())
                extracted = 0
                
                for file_info in zf.infolist():
                    zf.extract(file_info, temp_extract)
                    extracted += 1
                    
                    if total_files > 0:
                        progress = 88 + int((extracted / total_files) * 10)
                        progress = min(98, progress)
                        self.update_status(None, progress)
            
            source_core = temp_extract / "zapret_core"
            
            if source_core.exists():
                for item in source_core.iterdir():
                    dest = zapret_dir / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            if temp_zip.exists():
                temp_zip.unlink()
            
            self.update_status(None, 98)
            return True
            
        except Exception:
            return False
        finally:
            if temp_zip and temp_zip.exists():
                try:
                    temp_zip.unlink()
                except:
                    pass

    def _remove_readonly_dir(self, path):
        if not path.exists():
            return
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                try:
                    os.chmod(file_path, 0o666)
                except:
                    pass
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    os.chmod(dir_path, 0o666)
                except:
                    pass
        
        shutil.rmtree(path, ignore_errors=True)

    def _download_and_update(self):
        def update_worker():
            temp_exe = None
            temp_zip = None
            update_script = None
            try:
                current_exe = Path(sys.executable)
                temp_exe = current_exe.parent / f"{current_exe.stem}_new.exe"
                temp_zip = current_exe.parent / "_internal_temp.zip"
                update_script = current_exe.parent / "update_temp.bat"
                
                self.after(0, lambda: self.update_status(tr('splash_downloading_exe'), 0))
                exe_success = self._download_with_progress(self.exe_url, temp_exe, 0, 30)
                
                if not exe_success:
                    raise Exception("Failed to download exe file")
                
                self.after(0, lambda: self.update_status(tr('splash_downloading_zip'), 30))
                zip_success = self._download_with_progress(self.zip_url, temp_zip, 30, 60)
                
                if not zip_success:
                    raise Exception("Failed to download zip file")
                
                self.after(0, lambda: self.update_status(tr('splash_extracting_files'), 60))
                extract_success = self._extract_zip_with_progress(temp_zip, self.appdata_path, 60, 80)
                
                if not extract_success:
                    raise Exception("Failed to extract zip file")
                
                self.after(0, lambda: self.update_status(tr('splash_install_update'), 90))
                self._stop_zapret_processes()
                time.sleep(2)
                
                bat_content = f'''@echo off
    timeout /t 2 /nobreak > nul
    copy /y "{temp_exe}" "{current_exe}" > nul
    if errorlevel 1 (
        echo Failed to copy file
    ) else (
        del /f /q "{temp_exe}" 2>nul
        del /f /q "{temp_zip}" 2>nul
        start "" "{current_exe}" --no-splash --from-splash
    )
    del /f /q "%~f0" 2>nul
    '''
                
                with open(update_script, 'w', encoding='utf-8') as f:
                    f.write(bat_content)
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                subprocess.Popen(
                    ['cmd.exe', '/c', str(update_script)],
                    startupinfo=startupinfo,
                    creationflags=subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                self.after(100, self.close)
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
                if update_script and update_script.exists():
                    try:
                        update_script.unlink()
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
            appdata_path = APPDATA_DIR
            if not appdata_path.exists():
                return
            
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
                    except PermissionError:
                        try:
                            new_name = item.parent / f"_internal_old_del_{int(time.time())}"
                            item.rename(new_name)
                            shutil.rmtree(new_name, ignore_errors=True)
                        except:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _launch_main_app(self):
        if self._is_closing:
            return
        
        zapret_dir = self.appdata_path / "zapret_core"
        if not zapret_dir.exists() or not (zapret_dir / "bin" / "winws.exe").exists():
            self.update_status(tr('splash_downloading_zapret'), 50)
            self._download_zapret_core()
        
        self.update_status(tr('splash_starting_exe'), 100)
        time.sleep(1)
        self.close()
        
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = sys.argv[0]
            
            subprocess.Popen(
                [exe_path, '--no-splash', '--from-splash'],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        except Exception:
            pass
    
    def close(self):
        if self._animation_id:
            try:
                self.window.after_cancel(self._animation_id)
            except:
                pass
            self._animation_id = None
        
        self._is_closing = True
        try:
            self.window.destroy()
        except:
            pass
