import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict, Any
from widgets import RoundedButton

class CustomProviderDialog:
    def __init__(self, parent, colors, existing_data: Optional[Dict[str, Any]] = None):
        self.parent = parent
        self.colors = colors
        self.existing_data = existing_data
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Создание кастомного провайдера" if not existing_data else "Редактирование провайдера")
        self.dialog.geometry("580x600")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=self.colors['bg_medium'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
        if existing_data:
            self.name_entry.insert(0, existing_data.get("name", ""))
            if existing_data.get("params"):
                self.params_text.insert("1.0", "\n".join(existing_data["params"]))
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 290
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 300
        self.dialog.geometry(f"+{x}+{y}")
        
    def _create_widgets(self):
        scrollable_frame = tk.Frame(self.dialog, bg=self.colors['bg_medium'])
        scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        title = tk.Label(scrollable_frame, text="Настройка кастомного провайдера", 
                        font=("Segoe UI", 16, "bold"),
                        fg=self.colors['text_primary'], bg=self.colors['bg_medium'])
        title.pack(pady=(20, 15))
        
        name_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_medium'])
        name_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        tk.Label(name_frame, text="Название провайдера (макс. 14 символов):", 
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        self.name_var = tk.StringVar()
        self.name_var.trace('w', self._limit_name_length)
        
        self.name_entry = tk.Entry(name_frame, font=("Segoe UI", 11),
                                   bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                   insertbackground=self.colors['text_primary'],
                                   textvariable=self.name_var)
        self.name_entry.pack(fill=tk.X, pady=(5, 0), ipady=5)
        
        self.char_count_label = tk.Label(name_frame, text="14 символов осталось", 
                                        font=("Segoe UI", 9),
                                        fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        self.char_count_label.pack(anchor='e', pady=(2, 0))
        
        params_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_medium'])
        params_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15), padx=10)
        
        tk.Label(params_frame, text="Параметры запуска (каждый параметр с новой строки):", 
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(anchor='w')
        
        tk.Label(params_frame, text="Пример:\n--split 1\n--disorder -1", 
                font=("Segoe UI", 9),
                fg=self.colors['text_secondary'], bg=self.colors['bg_medium']).pack(anchor='w', pady=(2, 5))
        
        text_frame = tk.Frame(params_frame, bg=self.colors['bg_light'], bd=1, relief=tk.FLAT)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        self.params_text = tk.Text(text_frame, height=12, font=("Consolas", 10),
                                   bg=self.colors['bg_dark'], fg=self.colors['text_primary'],
                                   insertbackground=self.colors['text_primary'],
                                   wrap=tk.WORD, bd=0)
        self.params_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_scrollbar = ttk.Scrollbar(text_frame, command=self.params_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.params_text.configure(yscrollcommand=text_scrollbar.set)
        
        btn_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_medium'])
        btn_frame.pack(fill=tk.X, pady=20, padx=10)
        
        save_btn = RoundedButton(btn_frame, text="Сохранить", command=self._save,
                                width=120, height=35, bg=self.colors['accent'],
                                fg=self.colors['text_primary'],
                                font=("Segoe UI", 10, "bold"), corner_radius=8,
                                hover_color='#3D3D45')
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_btn = RoundedButton(btn_frame, text="Отмена", command=self.dialog.destroy,
                                  width=100, height=35, bg=self.colors['button_bg'],
                                  fg=self.colors['text_secondary'],
                                  font=("Segoe UI", 10), corner_radius=8,
                                  hover_color='#3D3D45')
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        self.name_entry.bind("<Return>", lambda e: self._save())
        self.params_text.bind("<Control-Return>", lambda e: self._save())
        
    def _limit_name_length(self, *args):
        name = self.name_var.get()
        if len(name) > 14:
            self.name_var.set(name[:14])
            name = name[:14]
        
        remaining = 14 - len(name)
        self.char_count_label.config(text=f"{remaining} символов осталось" if remaining > 0 else "Максимум 14 символов")
        if remaining == 0:
            self.char_count_label.config(fg=self.colors['accent_red'])
        else:
            self.char_count_label.config(fg=self.colors['text_secondary'])
        
    def _save(self):
        name = self.name_entry.get().strip()
        params_text = self.params_text.get("1.0", tk.END).strip()
        
        if not name:
            messagebox.showerror("Ошибка", "Введите название провайдера")
            return
        
        if len(name) > 14:
            messagebox.showerror("Ошибка", "Название не должно превышать 14 символов")
            return
        
        if not params_text:
            messagebox.showerror("Ошибка", "Введите параметры запуска")
            return
        
        params = [p.strip() for p in params_text.split('\n') if p.strip()]
        
        self.result = {
            "name": name,
            "params": params
        }
        self.dialog.destroy()

def edit_custom_provider(parent, colors, existing_data: Optional[dict] = None) -> Optional[dict]:
    dialog = CustomProviderDialog(parent, colors, existing_data)
    parent.wait_window(dialog.dialog)
    return dialog.result
