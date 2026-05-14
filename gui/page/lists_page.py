import tkinter as tk
from tkinter import messagebox
from gui.widgets import RoundedButton
from utils.languages import tr
from utils.list_editor import ListEditor
import os
from pathlib import Path

APPDATA_DIR = Path(os.getenv('APPDATA')) / 'Zapret Launcher'
LISTS_DIR = APPDATA_DIR / "zapret_core" / "lists"

def check_zapret_folder():
    zapret_core_dir = APPDATA_DIR / "zapret_core"
    if not zapret_core_dir.exists():
        messagebox.showerror(
            tr('error_zapret_folder'), 
            f"{tr('error_zapret_folder')}\n\n"
            f"Expected folder: {zapret_core_dir}\n\n"
            "Restart the program to extract resources."
        )
        return False
    return True

def open_lists_folder():
    try:
        os.startfile(LISTS_DIR)
    except Exception as e:
        messagebox.showerror(tr('error_occurred'), f"Failed to open folder: {str(e)}")

class ListsPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('lists_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('lists_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        lists_content = tk.Frame(self.frame, bg=self.colors['bg_light'])
        lists_content.pack(fill=tk.X, padx=30, pady=10)
        
        for label, filename in [
            (tr('lists_general'), "list-general.txt"), 
            (tr('lists_general_user'), "list-general-user.txt"),
            (tr('lists_google'), "list-google.txt"), 
            (tr('lists_ipset'), "ipset-all.txt")
        ]:
            
            frame = tk.Frame(lists_content, bg=self.colors['bg_light'])
            frame.pack(fill=tk.X, pady=15, padx=20)
            
            text_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(text_frame, text=label, font=("Inter", 14, "bold"), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w')
            tk.Label(text_frame, text=filename, font=("Inter", 11), 
                    fg=self.colors['text_secondary'], bg=self.colors['bg_light'], anchor='w').pack(anchor='w', pady=(5, 0))
            
            btn_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            btn_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            edit_btn = RoundedButton(btn_frame, text=tr('lists_edit'), 
                                    command=lambda f=filename: self.edit_list_file(f),
                                    width=100, height=35, bg=self.colors['button_bg'], 
                                    font=("Inter", 10), corner_radius=8)
            edit_btn.pack()
        
        folder_frame = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        folder_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        open_folder_btn = RoundedButton(folder_frame, text=tr('lists_open_folder'), 
                                    command=open_lists_folder,
                                    width=300, height=40, bg=self.colors['button_bg'], 
                                    font=("Inter", 11, "bold"), corner_radius=10)
        open_folder_btn.pack()
    
    def edit_list_file(self, filename):
        if not check_zapret_folder():
            return
        lists_path = os.path.join(self.app.zapret.zapret_dir, "lists")
        file_path = os.path.join(lists_path, filename)
        ListEditor(self.app.root, file_path, filename, app=self.app)
    
    def get_frame(self):
        return self.frame