import tkinter as tk
import sys
import tempfile
import threading
import shutil
import time
import psutil
import zipfile
import subprocess
import urllib.request
from config import APPDATA_DIR, ZAPRET_CORE_URL
from pathlib import Path
from tkinter import ttk, messagebox
from gui.theme import get_theme_names
from gui.widgets import RoundedButton
from utils.languages import tr

class SettingsPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('settings_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('settings_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        main_container = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=4)
        cards_frame = tk.Frame(main_container, bg=self.colors['bg_dark'])
        cards_frame.pack(fill=tk.BOTH, expand=True)
        left_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right_column = tk.Frame(cards_frame, bg=self.colors['bg_dark'])
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        self._create_settings_card(left_column, tr('settings_interface'), [
            (tr('settings_interval_fast'), self._set_update_interval_0),
            (tr('settings_interval_5'), self._set_update_interval_5),
            (tr('settings_interval_10'), self._set_update_interval_10),
            (tr('settings_interval_30'), self._set_update_interval_30),
            (tr('settings_interval_60'), self._set_update_interval_60),
            (tr('settings_interval_off'), self._set_update_interval_none),
        ])

        theme_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        theme_card.pack(fill=tk.X, pady=6)
        theme_inner = tk.Frame(theme_card, bg=self.colors['bg_light'])
        theme_inner.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(theme_inner, text=tr('settings_theme'), font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        theme_names = get_theme_names()
        
        theme_var = tk.StringVar(value=self.app.current_theme)
        theme_combo = ttk.Combobox(theme_inner, textvariable=theme_var, 
                                   values=theme_names,
                                   state='readonly', width=15)
        theme_combo.pack(anchor='w', pady=5)
        
        def on_theme_change(event=None):
            new_theme = theme_var.get()
            current_theme = self.app.current_theme
            
            if new_theme != current_theme:
                restart_msg = tr('restart_manual_message')
                restart_title = tr('restart_manual_title')
                
                result = messagebox.showwarning(
                    restart_title,
                    restart_msg + "\n\n",
                    type=messagebox.OKCANCEL
                )
                
                if result == 'ok':
                    self.app.show_notification(tr('please_wait'), 2000)
                    self.app.log_event("info", f"Theme changed: {current_theme} -> {new_theme}")
                    self.app.current_theme = new_theme
                    self.app.save_settings()
                    self.app.root.after(2500, self._restart_launcher)
                else:
                    theme_var.set(current_theme)
        theme_combo.bind("<<ComboboxSelected>>", on_theme_change)
        
        lang_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        lang_card.pack(fill=tk.X, pady=6)
        lang_inner = tk.Frame(lang_card, bg=self.colors['bg_light'])
        lang_inner.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(lang_inner, text=tr('settings_language'), font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        lang_var = tk.StringVar(value=self.app.languages.get_current_language())
        lang_combo = ttk.Combobox(lang_inner, textvariable=lang_var, 
                                   values=list(self.app.languages.LANGUAGES.keys()),
                                   state='readonly', width=15)
        lang_combo.pack(anchor='w', pady=5)
        
        def on_language_change(event=None):
            new_lang = lang_var.get()
            current_lang = self.app.languages.get_current_language()
            
            if new_lang != current_lang:
                restart_msg = tr('restart_manual_message')
                restart_title = tr('restart_manual_title')
                
                result = messagebox.showwarning(
                    restart_title,
                    restart_msg + "\n\n",
                    type=messagebox.OKCANCEL
                )
                
                if result == 'ok':
                    self.app.show_notification(tr('please_wait'), 2000)
                    self.app.log_event("info", f"Interface language changed: {current_lang} -> {new_lang}")
                    self.app.languages.set_language(new_lang)
                    self.app.save_settings()
                    self.app.root.after(2500, self._restart_launcher)
                else:
                    lang_var.set(current_lang)
        lang_combo.bind("<<ComboboxSelected>>", on_language_change)
        
        tg_card = tk.Frame(right_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        tg_card.pack(fill=tk.X, pady=6)
        tg_inner = tk.Frame(tg_card, bg=self.colors['bg_light'])
        tg_inner.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(tg_inner, text="Telegram Proxy", font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))

        secret_value = getattr(self.app, '_tg_secret', None)
        if secret_value and len(secret_value) > 16:
            secret_text = f"{tr('settings_current_tg_secret')} {secret_value[:16]}..."
        elif secret_value:
            secret_text = f"{tr('settings_current_tg_secret')} {secret_value}"
        else:
            secret_text = tr('settings_current_tg_secret')

        self.secret_label = tk.Label(tg_inner, text=secret_text,
                            font=("Inter", 9), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.secret_label.pack(anchor='w', pady=(0, 5))

        self.secret_value_label = self.secret_label

        regenerate_btn = RoundedButton(
            tg_inner,
            text=tr('tg_generate_secret'),
            command=self._regenerate_secret,
            width=200, height=30,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        regenerate_btn.pack(anchor='w', pady=5)

        def copy_current_link():
            secret = getattr(self.app, '_tg_secret', None)
            if secret:
                if self.app.tg_fake_tls and self.app.tg_fake_tls_domain:
                    domain_hex = self.app.tg_fake_tls_domain.encode('ascii').hex()
                    link = f"ee{secret}{domain_hex}"
                    notification = tr('notification_copied_secret')
                else:
                    link = secret
                    notification = tr('notification_copied_secret')
                
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(link)
                self.app.root.update()
                self.app.show_notification(notification, 2000)
            else:
                messagebox.showwarning(tr('error_secret_not_found'), tr('error_telegram_proxy_start'))

        copy_btn = RoundedButton(
            tg_inner,
            text=tr('tg_copy_secret'),
            command=copy_current_link,
            width=200, height=30,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        copy_btn.pack(anchor='w', pady=5)

        tg_instruction = RoundedButton(
            tg_inner,
            text=tr('tg_instruction_show_hide'),
            command=self._show_instruction,
            width=200, height=30,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        tg_instruction.pack(anchor='w', pady=5)

        info_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        info_card.pack(fill=tk.X, pady=6)
        info_inner = tk.Frame(info_card, bg=self.colors['bg_light'])
        info_inner.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(info_inner, text=tr('settings_current'), font=("Inter", 12, "bold"),
            fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        self.current_interval_label = tk.Label(info_inner, 
            text=f"{tr('settings_current_interval')} {self._get_current_interval_text()}",
            font=("Inter", 10), fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
        self.current_interval_label.pack(anchor='w', pady=2)

        maintenance_card = tk.Frame(left_column, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        maintenance_card.pack(fill=tk.X, pady=6)
        maintenance_inner = tk.Frame(maintenance_card, bg=self.colors['bg_light'])
        maintenance_inner.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(maintenance_inner, text=tr('settings_recovery'), font=("Inter", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))

        buttons_frame = tk.Frame(maintenance_inner, bg=self.colors['bg_light'])
        buttons_frame.pack(fill=tk.X, pady=(0, 3))

        integrity_btn = RoundedButton(
            buttons_frame,
            text=tr('settings_integrity'),
            command=self._show_integrity_placeholder,
            width=180, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 9),
            corner_radius=6,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        integrity_btn.pack(side=tk.LEFT, padx=(0, 10))

        reinstall_btn = RoundedButton(
            buttons_frame,
            text=tr('settings_reinstall'),
            command=self._reinstall_files,
            width=180, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 9),
            corner_radius=6,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        reinstall_btn.pack(side=tk.LEFT)

        buttons_frame2 = tk.Frame(maintenance_inner, bg=self.colors['bg_light'])
        buttons_frame2.pack(fill=tk.X)

        appdata_btn = RoundedButton(
            buttons_frame2,
            text=tr('settings_open_folder'),
            command=self.app.open_appdata_folder,
            width=180, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 9),
            corner_radius=6,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        appdata_btn.pack(side=tk.LEFT, padx=(0, 10))

        autostart_btn = RoundedButton(
            buttons_frame2,
            text=tr('settings_autostart'),
            command=self.app.toggle_autostart,
            width=180, height=32,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Inter", 9),
            corner_radius=6,
            hover_color=self.colors['accent'],
            theme_name=self.app.current_theme
        )
        autostart_btn.pack(side=tk.LEFT, padx=(0, 10))

    def update_interval_display(self):
        if hasattr(self, 'current_interval_label'):
            self.current_interval_label.config(
                text=f"{tr('settings_current_interval')} {self._get_current_interval_text()}"
            )

    def _show_integrity_placeholder(self):
        missing_files = []
        ok_count = 0
        
        checks = [
            ("zapret_core/bin/winws.exe", "winws.exe"),
            ("zapret_core/bin/WinDivert.dll", "WinDivert.dll"),
            ("zapret_core/bin/WinDivert64.sys", "WinDivert64.sys"),
            ("zapret_core/bin/quic_initial_dbankcloud_ru.bin", "quic_initial_dbankcloud_ru.bin"),
            ("zapret_core/bin/quic_initial_www_google_com.bin", "quic_initial_www_google_com.bin"),
            ("zapret_core/bin/stun.bin", "stun.bin"),
            ("zapret_core/bin/tls_clienthello_4pda_to.bin", "tls_clienthello_4pda_to.bin"),
            ("zapret_core/bin/tls_clienthello_max_ru.bin", "tls_clienthello_max_ru.bin"),
            ("zapret_core/bin/tls_clienthello_www_google_com.bin", "tls_clienthello_www_google_com.bin"),
            ("zapret_core/bin/cygwin1.dll", "cygwin1.dll"),

            ("zapret_core/service.bat", "service.bat"),
            ("zapret_core/general.bat", "general.bat"),
            ("zapret_core/general (ALT).bat", "general (ALT).bat"),
            ("zapret_core/general (ALT2).bat", "general (ALT2).bat"),
            ("zapret_core/general (ALT3).bat", "general (ALT3).bat"),
            ("zapret_core/general (ALT4).bat", "general (ALT4).bat"),
            ("zapret_core/general (ALT5).bat", "general (ALT5).bat"),
            ("zapret_core/general (ALT6).bat", "general (ALT6).bat"),
            ("zapret_core/general (ALT7).bat", "general (ALT7).bat"),
            ("zapret_core/general (ALT8).bat", "general (ALT8).bat"),
            ("zapret_core/general (ALT9).bat", "general (ALT9).bat"),
            ("zapret_core/general (ALT10).bat", "general (ALT10).bat"),
            ("zapret_core/general (ALT11).bat", "general (ALT11).bat"),
            ("zapret_core/general (ALT12).bat", "general (ALT12).bat"),
            ("zapret_core/general (FAKE TLS AUTO).bat", "general (FAKE TLS AUTO).bat"),
            ("zapret_core/general (FAKE TLS AUTO ALT).bat", "general (FAKE TLS AUTO ALT).bat"),
            ("zapret_core/general (FAKE TLS AUTO ALT2).bat", "general (FAKE TLS AUTO ALT2).bat"),
            ("zapret_core/general (FAKE TLS AUTO ALT3).bat", "general (FAKE TLS AUTO ALT3).bat"),
            ("zapret_core/general (SIMPLE FAKE).bat", "general (SIMPLE FAKE).bat"),
            ("zapret_core/general (SIMPLE FAKE ALT).bat", "general (SIMPLE FAKE ALT).bat"),
            ("zapret_core/general (SIMPLE FAKE ALT2).bat", "general (SIMPLE FAKE ALT2).bat"),

            ("resources/icon.ico", "icon.ico"),
            ("resources/icon.png", "icon.png"),
            ("config.json", "config.json"),
        ]
        
        for path, name in checks:
            full_path = APPDATA_DIR / path
            if full_path.exists():
                ok_count += 1
            else:
                missing_files.append(name)
        
        lists_dir = APPDATA_DIR / "zapret_core/lists"
        if lists_dir.exists():
            list_files = ["ipset-all.txt", 
                        "ipset-all.txt.backup", 
                        "ipset-exclude.txt",
                        "ipset-exclude-user.txt", 
                        "list-exclude-user.txt", 
                        "list-exclude.txt",
                        "list-custom.txt",
                        "list-general-user.txt", 
                        "list-general.txt", 
                        "list-google.txt"]
            
            for list_file in list_files:
                if (lists_dir / list_file).exists():
                    ok_count += 1
                else:
                    missing_files.append(f"lists/{list_file}")
        else:
            missing_files.append(f"zapret_core/lists ({tr('settings_integrity_folder_missing')})")
        
        utils_dir = APPDATA_DIR / "zapret_core/utils"
        if not utils_dir.exists():
            missing_files.append(f"zapret_core/utils ({tr('settings_integrity_folder_missing')})")
        else:
            ok_count += 1
        
        bin_dir = APPDATA_DIR / "zapret_core/bin"
        if not bin_dir.exists():
            missing_files.append(f"zapret_core/bin ({tr('settings_integrity_folder_missing')})")
        else:
            ok_count += 1
        
        if missing_files:
            result_text = f"{tr('settings_integrity_result')}\n"
            result_text += f"{tr('settings_integrity_missing_count').format(count=len(missing_files))}\n\n"
            for file in missing_files:
                result_text += f"  • {file}\n"
            
            messagebox.showwarning(
                tr('settings_integrity_title'),
                result_text
            )
        else:
            messagebox.showinfo(
                tr('settings_integrity_title'),
                tr('settings_integrity_success')
            )

    def _show_instruction(self):
        self.app._tg_instruction = not self.app._tg_instruction
        self.app.save_settings()
        
        if self.app._tg_instruction:
            self.app.show_notification(tr('tg_instruction_hidden'), 1500)
        else:
            self.app.show_notification(tr('tg_instruction_shown'), 1500)

    def _regenerate_secret(self):
        self.app.regenerate_tg_secret()
        self.update_secret_display()

    def _reinstall_files(self):
        all_files_exist = self._check_all_files_exist()
            
        if all_files_exist:
            result = messagebox.askyesno(
                tr('settings_reinstall_title'),
                tr('settings_reinstall_all_exists')
            )
            if not result:
                return
        else:
            result = messagebox.askyesno(
                tr('settings_reinstall_title'),
                tr('settings_reinstall_missing')
            )
            if not result:
                return
            
        winws_running = False
        for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        winws_running = True
                        break
                except:
                    pass
            
        if winws_running:
            result = messagebox.askyesno(
                tr('settings_reinstall_active'),
                tr('settings_reinstall_disconnect')
            )
            if not result:
                return
            self.app.disconnect()
            time.sleep(1)

        self.app.show_notification(tr('please_wait'), 5000)
        self.app.root.after(500, lambda: threading.Thread(target=self._download_and_install_zapret_core, daemon=True).start())

    def _check_all_files_exist(self):
        missing_files = []
        
        checks = [
            "zapret_core/bin/winws.exe",
            "zapret_core/bin/WinDivert.dll",
            "zapret_core/bin/WinDivert64.sys",
            "zapret_core/bin/quic_initial_dbankcloud_ru.bin",
            "zapret_core/bin/quic_initial_www_google_com.bin",
            "zapret_core/bin/stun.bin",
            "zapret_core/bin/tls_clienthello_4pda_to.bin",
            "zapret_core/bin/tls_clienthello_max_ru.bin",
            "zapret_core/bin/tls_clienthello_www_google_com.bin",
            "zapret_core/bin/cygwin1.dll",
            "zapret_core/service.bat",
            "zapret_core/general.bat",
            "zapret_core/general (ALT).bat",
            "zapret_core/general (ALT2).bat",
            "zapret_core/general (ALT3).bat",
            "zapret_core/general (ALT4).bat",
            "zapret_core/general (ALT5).bat",
            "zapret_core/general (ALT6).bat",
            "zapret_core/general (ALT7).bat",
            "zapret_core/general (ALT8).bat",
            "zapret_core/general (ALT9).bat",
            "zapret_core/general (ALT10).bat",
            "zapret_core/general (ALT11).bat",
            "zapret_core/general (ALT12).bat",
            "zapret_core/general (FAKE TLS AUTO).bat",
            "zapret_core/general (FAKE TLS AUTO ALT).bat",
            "zapret_core/general (FAKE TLS AUTO ALT2).bat",
            "zapret_core/general (FAKE TLS AUTO ALT3).bat",
            "zapret_core/general (SIMPLE FAKE).bat",
            "zapret_core/general (SIMPLE FAKE ALT).bat",
            "zapret_core/general (SIMPLE FAKE ALT2).bat",
            "resources/icon.ico",
            "resources/icon.png",
            "config.json",
        ]
        
        for path in checks:
            full_path = APPDATA_DIR / path
            if not full_path.exists():
                missing_files.append(path)
        
        lists_dir = APPDATA_DIR / "zapret_core/lists"
        if lists_dir.exists():
            list_files = [
                "ipset-all.txt",
                "ipset-all.txt.backup",
                "ipset-exclude.txt",
                "ipset-exclude-user.txt",
                "list-exclude-user.txt",
                "list-exclude.txt",
                "list-custom.txt",
                "list-general-user.txt",
                "list-general.txt",
                "list-google.txt"
            ]
            for list_file in list_files:
                if not (lists_dir / list_file).exists():
                    missing_files.append(f"zapret_core/lists/{list_file}")
        else:
            missing_files.append("zapret_core/lists (папка отсутствует)")
        
        for folder in ["utils", "bin"]:
            folder_path = APPDATA_DIR / f"zapret_core/{folder}"
            if not folder_path.exists():
                missing_files.append(f"zapret_core/{folder} (папка отсутствует)")
        return len(missing_files) == 0

    def _download_and_install_zapret_core(self):
        def install_thread():
            temp_zip = None
            
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'winws.exe'], 
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(['sc', 'stop', 'WinDivert'], 
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1.5)
                
                zapret_dir = APPDATA_DIR / "zapret_core"
                
                req = urllib.request.Request(ZAPRET_CORE_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    temp_zip = tempfile.mktemp(suffix='.zip')
                    with open(temp_zip, 'wb') as f:
                        f.write(response.read())
                
                user_files = []
                lists_dir = zapret_dir / "lists"
                if lists_dir.exists():
                    for file in lists_dir.glob("*-user.txt"):
                        user_files.append(file)
                
                with zipfile.ZipFile(temp_zip, 'r') as zf:
                    temp_extract = tempfile.mkdtemp()
                    zf.extractall(temp_extract)
                    
                    extracted_core = Path(temp_extract) / "zapret_core"
                    if not extracted_core.exists():
                        extracted_core = Path(temp_extract)
                    
                    if zapret_dir.exists():
                        for attempt in range(3):
                            try:
                                shutil.rmtree(zapret_dir)
                                break
                            except PermissionError:
                                time.sleep(1)
                    
                    for item in extracted_core.iterdir():
                        dest = zapret_dir / item.name
                        if item.is_dir():
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                    
                    shutil.rmtree(temp_extract)
                
                for user_file in user_files:
                    dest = zapret_dir / "lists" / user_file.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(user_file, dest)
                
                if temp_zip and Path(temp_zip).exists():
                    Path(temp_zip).unlink()
                
                self.app.root.after_idle(lambda: self._show_success_and_restart())
            
            except Exception as e:
                self.app.root.after_idle(lambda: messagebox.showerror(
                    "Error", 
                    f"Unable to reinstall kernel: {str(e)}"
                ))
        
        threading.Thread(target=install_thread, daemon=True).start()

    def _show_success_and_restart(self):
        self.app.root.after(2500, self._restart_launcher)

    def _restart_launcher(self):
        try:
            winws_running = False
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        winws_running = True
                        break
                except:
                    pass
            
            tg_running = False
            if hasattr(self.app, 'tg_proxy') and self.app.tg_proxy:
                tg_running = self.app.tg_proxy.is_running
            
            if winws_running or tg_running or self.app.is_connected:
                if hasattr(self.app, 'zapret') and self.app.zapret:
                    self.app.zapret.stop_current_strategy()
                
                if tg_running and hasattr(self.app, 'tg_proxy'):
                    self.app.tg_proxy.stop()
                
                try:
                    subprocess.run(['sc', 'stop', 'WinDivert'], 
                                capture_output=True, 
                                creationflags=subprocess.CREATE_NO_WINDOW)
                except:
                    pass
                
                time.sleep(1)
                
                self.app.is_connected = False
                self.app.current_strategy = None
                
                if hasattr(self.app, 'mode_label') and self.app.mode_label:
                    self.app.mode_label.config(text=tr('mode_not_selected'), 
                                            fg=self.app.colors['text_secondary'])
                if hasattr(self.app, 'connect_btn') and self.app.connect_btn:
                    self.app.connect_btn.set_text(tr('button_connect'))
        
        except Exception:
            pass
        
        self.app.save_settings()
        
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = sys.argv[0]
        
        subprocess.Popen([exe_path, '--no-splash', '--from-splash'])
        self.app.root.quit()
        self.app.root.destroy()
        sys.exit(0)
    
    def update_secret_display(self):
        if not hasattr(self, 'secret_label') or not self.secret_label:
            return
        
        try:
            if not self.secret_label.winfo_exists():
                return
        except:
            return

        if hasattr(self, 'secret_label') and self.secret_label:
            new_secret = getattr(self.app, '_tg_secret', None)
            if new_secret and len(new_secret) > 16:
                self.secret_label.config(text=f"{tr('settings_current_tg_secret')} {new_secret[:16]}...")
            elif new_secret:
                self.secret_label.config(text=f"{tr('settings_current_tg_secret')} {new_secret}")
            else:
                self.secret_label.config(text=tr('settings_current_tg_secret'))

        self.secret_label.update_idletasks()
    
    def _get_current_interval_text(self):
        intervals = {
            1: tr('settings_interval_fast_text'),
            5: tr('settings_interval_5'),
            10: tr('settings_interval_10'),
            30: tr('settings_interval_30'),
            60: tr('settings_interval_60'),
            None: tr('settings_interval_off_text')
        }
        return intervals.get(self.app.update_interval, tr('settings_interval_10'))
    
    def _create_settings_card(self, parent, title, options):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'])
        inner.pack(fill=tk.X, padx=8, pady=6)
        
        title_frame = tk.Frame(inner, bg=self.colors['bg_light'])
        title_frame.pack(fill=tk.X, pady=(0, 4))
        
        title_label = tk.Label(title_frame, text=title, font=("Inter", 12, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        title_label.pack(side=tk.LEFT)
        
        title_sep = tk.Frame(inner, bg=self.colors['separator'], height=1)
        title_sep.pack(fill=tk.X, pady=(0, 4))
        
        options_container = tk.Frame(inner, bg=self.colors['bg_light'])
        options_container.pack(fill=tk.X)
        
        for i in range(0, len(options), 2):
            row = tk.Frame(options_container, bg=self.colors['bg_light'])
            row.pack(fill=tk.X, pady=1)
            
            opt1_text, opt1_cmd = options[i]
            if opt1_cmd:
                btn1 = RoundedButton(row, text=opt1_text, command=opt1_cmd,
                                    width=130, height=26,
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=("Inter", 9),
                                    corner_radius=6,
                                    hover_color=self.colors['accent'],
                                    theme_name=self.app.current_theme)
                btn1.pack(side=tk.LEFT, padx=(0, 6))
            
            if i + 1 < len(options):
                opt2_text, opt2_cmd = options[i + 1]
                if opt2_cmd:
                    btn2 = RoundedButton(row, text=opt2_text, command=opt2_cmd,
                                        width=130, height=26,
                                        bg=self.colors['button_bg'],
                                        fg=self.colors['text_secondary'],
                                        font=("Inter", 9),
                                        corner_radius=6,
                                        hover_color=self.colors['accent'],
                                        theme_name=self.app.current_theme)
                    btn2.pack(side=tk.LEFT, padx=(6, 0))
    
    def _set_update_interval_0(self):
        if self.app.update_interval_index == 0:
            return
        self.app.update_interval_index = 0
        self.app.update_interval = 1
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        self.app.show_notification(tr('notification_interval_fast'))
        self.app.log_event("info", "Interface refresh interval is set to fast")
    
    def _set_update_interval_5(self):
        if self.app.update_interval_index == 1:
            return
        self.app.update_interval_index = 1
        self.app.update_interval = self.app.update_intervals[1]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        self.app.show_notification(tr('notification_interval_5'))
        self.app.log_event("info", "Interface refresh interval is set to 5 seconds")
    
    def _set_update_interval_10(self):
        if self.app.update_interval_index == 2:
            return
        self.app.update_interval_index = 2
        self.app.update_interval = self.app.update_intervals[2]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        self.app.show_notification(tr('notification_interval_10'))
        self.app.log_event("info", "Interface refresh interval is set to 10 seconds")
    
    def _set_update_interval_30(self):
        if self.app.update_interval_index == 3:
            return
        self.app.update_interval_index = 3
        self.app.update_interval = self.app.update_intervals[3]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        self.app.show_notification(tr('notification_interval_30'))
        self.app.log_event("info", "Interface refresh interval is set to 30 seconds")
    
    def _set_update_interval_60(self):
        if self.app.update_interval_index == 4:
            return
        self.app.update_interval_index = 4
        self.app.update_interval = self.app.update_intervals[4]
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.start_stats_monitoring()
        self.app.show_notification(tr('notification_interval_60'))
        self.app.log_event("info", "Interface refresh interval is set to 60 seconds")
    
    def _set_update_interval_none(self):
        if self.app.update_interval_index == 5:
            return
        self.app.update_interval_index = 5
        self.app.update_interval = None
        self._update_interval_ui()
        self.app.save_settings()
        self.app.stop_stats_monitoring()
        self.app.show_notification(tr('notification_interval_off'))
        self.app.log_event("info", "Interface refresh interval is set to never")
    
    def _update_interval_ui(self):
        if hasattr(self, 'current_interval_label'):
            self.current_interval_label.config(
                text=f"{tr('settings_current_interval')} {self._get_current_interval_text()}"
            )
    
    def get_frame(self):
        return self.frame
