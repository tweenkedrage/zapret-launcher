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
ZAPRET_API_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"
CURRENT_VERSION = "3.1c"

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
                log_update_event(f"Zapret update found: {current_zapret_version} -> {latest_version}")
                
                try:
                    result = messagebox.askyesno(
                        tr('update_zapret_title'),
                        f"{tr('update_zapret_available')}\n"
                        f"{tr('update_zapret_current')} {current_zapret_version}\n"
                        f"{tr('update_zapret_new')} {latest_version}\n\n"
                        f"{tr('update_zapret_question')}"
                    )
                except KeyboardInterrupt:
                    return False
                if result:
                    update_zapret_core(parent, latest_version)
                return True
            else:
                if not silent:
                    try:
                        messagebox.showinfo(tr('update_zapret_title'), tr('update_zapret_latest'))
                    except KeyboardInterrupt:
                        pass
                return False
    except KeyboardInterrupt:
        return False
    except Exception as e:
        log_update_event(f"Error checking for updates Zapret: {str(e)}")
        if not silent:
            try:
                messagebox.showerror(tr('error_update_check'), f"{tr('error_update_check')} Zapret: {str(e)}")
            except KeyboardInterrupt:
                pass
        return False

def update_zapret_core(parent, version):
    try:
        log_update_event(f"Starting Zapret update to version {version}")
        parent.update_status(tr('status_updating_zapret'), parent.colors['accent'])
        parent.root.update()
        
        if parent.zapret.is_winws_running():
            log_update_event("Stop the current Zaprot strategy before updating")
            parent.zapret.stop_current_strategy()
            time.sleep(1)

        user_lists = {}
        lists_dir = ZAPRET_CORE_DIR / "lists"
        if lists_dir.exists():
            user_lists_count = 0
            for file in lists_dir.glob("*-user.txt"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        user_lists[file.name] = f.read()
                        user_lists_count += 1
                except:
                    pass
            if user_lists_count > 0:
                log_update_event(f"{user_lists_count} user lists saved")
        
        download_url = f"https://github.com/flowseal/zapret-discord-youtube/archive/refs/heads/master.zip"
        log_update_event(f"Downloading the Zapret archive from GitHub...")
        
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
                log_update_event("winws.exe processes have stopped")
            except:
                pass

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    if ZAPRET_CORE_DIR.exists():
                        shutil.rmtree(ZAPRET_CORE_DIR)
                    log_update_event(f"Removed old Zapret folder (attempt {attempt + 1})")
                    break
                except Exception as delete_error:
                    if attempt < max_attempts - 1:
                        try:
                            os.system(f'rmdir /s /q "{ZAPRET_CORE_DIR}"')
                            time.sleep(1)
                        except:
                            pass
                        continue
                    else:
                        raise Exception(f"Failed to delete folder after {max_attempts} attempts")
        
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
        if user_lists:
            log_update_event(f"{len(user_lists)} user lists restored")
        
        parent.zapret.load_strategies()
        if hasattr(parent, 'strategy_combo'):
            parent.strategy_combo['values'] = parent.zapret.available_strategies
            if parent.zapret.available_strategies:
                parent.strategy_var.set(parent.zapret.available_strategies[0])
        
        parent.update_status(tr('status_ready'))
        log_update_event(f"Zapret has been successfully updated to version {version}")
        messagebox.showinfo(tr('update_zapret_success'), f"{tr('update_zapret_success')} {version}") 
    except Exception as e:
        error_msg = str(e)
        log_update_event(f"Zapret update error: {error_msg}")
        messagebox.showerror(tr('update_zapret_failed'), f"{tr('update_zapret_failed')}: {error_msg}")
        parent.update_status(tr('status_ready'))
