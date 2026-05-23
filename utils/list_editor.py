import tkinter as tk
from tkinter import ttk, messagebox
import os
import pywinstyles
from utils.languages import tr

class ListEditor:
    def __init__(self, parent, file_path, title, app=None):
        self.app = app
        self.parent = parent
        self.file_path = file_path
        self.title = title
        self.result = None
        self.current_button_index = -1
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"{tr('editor_title')} {title}")
        self.dialog.geometry("600x500")
        self.dialog.minsize(500, 400)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        if app:
            self.dialog.configure(bg=app.colors['bg_medium'])
            self._set_dialog_header_color(self.dialog)
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        main_frame = tk.Frame(self.dialog, padx=10, pady=10)
        if app:
            main_frame.configure(bg=app.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        text_frame = tk.Frame(main_frame)
        if app:
            text_frame.configure(bg=app.colors['bg_medium'])
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_area = tk.Text(text_frame, 
                                 wrap=tk.WORD,
                                 font=("Consolas", 10),
                                 undo=True,
                                 height=20)
        
        scrollbar = ttk.Scrollbar(text_frame, style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_area.yview)
        
        if app:
            self.text_area.configure(
                bg=app.colors['bg_light'],
                fg=app.colors['text_primary'],
                insertbackground=app.colors['text_primary'],
                selectbackground=app.colors['accent'],
                selectforeground=app.colors['text_primary'],
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=app.colors['accent'],
                highlightbackground=app.colors['bg_medium']
            )
        else:
            self.text_area.configure(relief=tk.SUNKEN)
        
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
        if app:
            button_frame.configure(bg=app.colors['bg_medium'])
        button_frame.pack(fill=tk.X)
        
        button_style = {}
        if app:
            button_style = {
                'bg': app.colors['accent'],
                'fg': app.colors['text_primary'],
                'activebackground': app.colors['button_hover'],
                'activeforeground': app.colors['text_primary'],
                'relief': tk.FLAT,
                'bd': 0,
                'cursor': 'hand2'
            }
        
        self.save_btn = tk.Button(button_frame, text=tr('editor_save'), command=self.save_content,
                                 padx=20, pady=5, takefocus=True, **button_style)
        self.save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_style = {}
        if app:
            cancel_style = {
                'bg': app.colors['button_bg'],
                'fg': app.colors['text_primary'],
                'activebackground': app.colors['accent'],
                'activeforeground': app.colors['text_primary'],
                'relief': tk.FLAT,
                'bd': 0,
                'cursor': 'hand2'
            }
        
        self.cancel_btn = tk.Button(button_frame, text=tr('editor_cancel'), command=self.dialog.destroy,
                                   padx=20, pady=5, takefocus=True, **cancel_style)
        self.cancel_btn.pack(side=tk.RIGHT)
        self.buttons = [self.save_btn, self.cancel_btn]
        
        if app:
            self.save_btn.bind("<Enter>", lambda e: self.save_btn.configure(bg=app.colors['button_hover']))
            self.save_btn.bind("<Leave>", lambda e: self.save_btn.configure(bg=app.colors['accent']))
            self.cancel_btn.bind("<Enter>", lambda e: self.cancel_btn.configure(bg=app.colors['accent']))
            self.cancel_btn.bind("<Leave>", lambda e: self.cancel_btn.configure(bg=app.colors['button_bg']))

    def _set_dialog_header_color(self, dialog):
        try:
            if self.app and hasattr(self.app, 'colors'):
                header_color = self.app.colors['bg_medium']
            else:
                header_color = "#0F0F12"
            
            dialog.after(10, lambda: self._apply_header_color(dialog, header_color))
        except ImportError:
            pass
        except Exception:
            pass

    def _apply_header_color(self, dialog, color):
        try:
            if dialog.winfo_exists():
                pywinstyles.change_header_color(dialog, color)
                dialog.update()
        except Exception:
            pass
        
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
                self.text_area.insert('1.0', "# File not found. Create content and save")
        except Exception as e:
            if self.app:
                self.app.log_event("info", f"Failed to upload file: {os.path.basename(self.file_path)}")
            messagebox.showerror(tr('error_no_connection'), f"{tr('editor_error_load')}: {str(e)}")
    
    def save_content(self):
        try:
            content = self.text_area.get('1.0', tk.END).strip()
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if self.app:
                self.app.log_event("info", f"File has been saved: {os.path.basename(self.file_path)}")
            messagebox.showinfo(tr('success'), tr('editor_success'))
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror(tr('error_no_connection'), f"{tr('editor_error_save')}: {str(e)}")
