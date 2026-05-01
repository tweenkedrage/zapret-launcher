from tkinter import messagebox
from utils.languages import tr
import subprocess
import os
import json
import time
import zipfile
import shutil
import tempfile
import urllib.request
import webbrowser
from pathlib import Path

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'Zapret Launcher'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

LAUNCHER_API_URL = "https://api.github.com/repos/tweenkedrage/zapret-launcher/releases/latest"
CURRENT_VERSION = "3.1e"

def log_update_event(message: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    try:
        log_file = APPDATA_DIR / "logs.txt"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error writing update log: {e}")

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
                log_update_event(f"Launcher update found: {CURRENT_VERSION} -> {latest_version}")
                
                if silent:
                    result = messagebox.askyesno(
                        tr('update_launcher_title'),
                        f"{tr('update_launcher_available')}\n"
                        f"{tr('update_launcher_current')} {CURRENT_VERSION}\n"
                        f"{tr('update_launcher_new')} {latest_version}\n\n"
                        f"{tr('update_launcher_question')}"
                    )
                    if result:
                        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher/releases/latest")
                    return True
                else:
                    result = messagebox.askyesno(
                        tr('update_launcher_title'),
                        f"{tr('update_launcher_available')}\n"
                        f"{tr('update_launcher_current')} {CURRENT_VERSION}\n"
                        f"{tr('update_launcher_new')} {latest_version}\n\n"
                        f"{tr('update_launcher_question')}"
                    )
                    if result and download_url:
                        webbrowser.open("https://github.com/tweenkedrage/zapret-launcher/releases/latest")
                    return True
            else:
                if not silent:
                    try:
                        messagebox.showinfo(tr('update_launcher_title'), tr('update_launcher_latest'))
                    except KeyboardInterrupt:
                        pass
                return False
    except KeyboardInterrupt:
        return False
    except Exception as e:
        log_update_event(f"Error checking for launcher updates: {str(e)}")
        if not silent:
            try:
                messagebox.showerror(tr('error_update_check'), f"{tr('error_update_check')}: {str(e)}")
            except KeyboardInterrupt:
                pass
        return False

def check_zapret_updates(parent, silent=False):
    if not silent:
        try:
            messagebox.showinfo(
                tr('update_zapret_title'), 
                "Zapret updates are disabled. Only the initial extraction is performed."
            )
        except KeyboardInterrupt:
            pass
    return False

def update_zapret_core(parent, version):
    try:
        messagebox.showwarning(
            "Update Disabled", 
            "Zapret auto-update is disabled. The core files are fixed and will not be updated."
        )
        parent.update_status(tr('status_ready'))
    except:
        pass
