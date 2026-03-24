import tkinter as tk
from tkinter import messagebox, scrolledtext
import os

class ListEditor:
    def __init__(self, parent, file_path, title):
        self.parent = parent
        self.file_path = file_path
        self.title = title
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Редактирование {title}")
        self.dialog.geometry("600x500")
        self.dialog.minsize(500, 400)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        main_frame = tk.Frame(self.dialog, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_area = scrolledtext.ScrolledText(main_frame, 
                                                   wrap=tk.WORD,
                                                   font=("Consolas", 10),
                                                   height=20,
                                                   undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_area.bind('<Control-c>', self.copy_text)
        self.text_area.bind('<Control-C>', self.copy_text)
        self.text_area.bind('<Control-v>', self.paste_text)
        self.text_area.bind('<Control-V>', self.paste_text)
        self.text_area.bind('<Control-x>', self.cut_text)
        self.text_area.bind('<Control-X>', self.cut_text)
        self.text_area.bind('<Control-a>', self.select_all)
        self.text_area.bind('<Control-A>', self.select_all)
        
        self.load_content()
        
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="Сохранить", command=self.save_content,
                 bg='#6c5579', fg='white', padx=20, pady=5).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(button_frame, text="Отмена", command=self.dialog.destroy,
                 padx=20, pady=5).pack(side=tk.RIGHT)
        
    def copy_text(self, event=None):
        try:
            self.text_area.event_generate("<<Copy>>")
            return "break"
        except:
            pass
            
    def paste_text(self, event=None):
        try:
            self.text_area.event_generate("<<Paste>>")
            return "break"
        except:
            pass
            
    def cut_text(self, event=None):
        try:
            self.text_area.event_generate("<<Cut>>")
            return "break"
        except:
            pass
            
    def select_all(self, event=None):
        try:
            self.text_area.tag_add("sel", "1.0", "end")
            return "break"
        except:
            pass
        
    def load_content(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_area.insert('1.0', content)
            else:
                self.text_area.insert('1.0', "# Файл не найден. Создайте содержимое и сохраните.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")
    
    def save_content(self):
        try:
            content = self.text_area.get('1.0', tk.END).strip()
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Успех", "Файл успешно сохранен!")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")
