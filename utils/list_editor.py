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
        self.search_frame = None
        self.search_var = None
        self.search_start_pos = "1.0"
        self.search_visible = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"{tr('edit_title_window')} {title}")
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

        self.text_area.focus_set()
        
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
        
        self.search_frame = tk.Frame(main_frame)
        if app:
            self.search_frame.configure(bg=app.colors['bg_medium'])
        
        self.search_label = tk.Label(self.search_frame, text=tr('editor_find'), font=("Segoe UI", 9))
        if app:
            self.search_label.configure(bg=app.colors['bg_medium'], fg=app.colors['text_secondary'])
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = tk.Entry(self.search_frame, font=("Segoe UI", 9), width=30)
        if app:
            self.search_entry.configure(
                bg=app.colors['bg_light'],
                fg=app.colors['text_primary'],
                insertbackground=app.colors['text_primary'],
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=app.colors['accent']
            )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', self.search_next)
        
        self.search_next_btn = tk.Button(self.search_frame, text=tr('editor_find_next'), command=self.search_next, width=10)
        if app:
            self.search_next_btn.configure(
                bg=app.colors['accent'],
                fg=app.colors['text_primary'],
                relief=tk.FLAT,
                cursor='hand2',
                activebackground=app.colors['accent']
            )
        self.search_next_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_close_btn = tk.Button(self.search_frame, text=tr('editor_close'), command=self.toggle_search, width=8)
        if app:
            self.search_close_btn.configure(
                bg=app.colors['button_bg'],
                fg=app.colors['text_primary'],
                relief=tk.FLAT,
                cursor='hand2',
                activebackground=app.colors['accent']
            )
        self.search_close_btn.pack(side=tk.LEFT)
        
        self.search_info = tk.Label(self.search_frame, text="", font=("Segoe UI", 8))
        if app:
            self.search_info.configure(bg=app.colors['bg_medium'], fg=app.colors['accent'])
        self.search_info.pack(side=tk.LEFT, padx=(10, 0))
        
        self.text_area.bind('<Control-f>', self.toggle_search)
        self.text_area.bind('<Control-F>', self.toggle_search)
        self.text_area.bind('<Escape>', self.on_escape)
        self.text_area.bind('<Control-c>', self.copy_text)
        self.text_area.bind('<Control-C>', self.copy_text)
        self.text_area.bind('<Control-v>', self.paste_text)
        self.text_area.bind('<Control-V>', self.paste_text)
        self.text_area.bind('<Control-x>', self.cut_text)
        self.text_area.bind('<Control-X>', self.cut_text)
        self.text_area.bind('<Control-a>', self.select_all)
        self.text_area.bind('<Control-A>', self.select_all)

        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self.text_area.bind('<Escape>', lambda e: self.dialog.destroy())
        self.search_entry.bind('<Escape>', lambda e: self.dialog.destroy())
        
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
                'activebackground': app.colors['accent'],
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
        
        info_frame = tk.Frame(button_frame)
        if app:
            info_frame.configure(bg=app.colors['bg_medium'])
        info_frame.pack(side=tk.LEFT)
        
        info_label = tk.Label(info_frame, text=tr('editor_tooltip'),
                             font=("Segoe UI", 8))
        if app:
            info_label.configure(bg=app.colors['bg_medium'], fg=app.colors['text_secondary'])
        info_label.pack(side=tk.LEFT, padx=10)
        
        if app:
            self.save_btn.bind("<Enter>", lambda e: self.save_btn.configure(bg=app.colors['accent']))
            self.save_btn.bind("<Leave>", lambda e: self.save_btn.configure(bg=app.colors['accent']))
            self.cancel_btn.bind("<Enter>", lambda e: self.cancel_btn.configure(bg=app.colors['accent']))
            self.cancel_btn.bind("<Leave>", lambda e: self.cancel_btn.configure(bg=app.colors['button_bg']))

    def toggle_search(self, event=None):
        if self.search_visible:
            self.search_frame.pack_forget()
            self.search_visible = False
            self.text_area.tag_remove("search", "1.0", "end")
            self.text_area.focus()
        else:
            self.search_frame.pack(fill=tk.X, pady=(0, 10), before=self.text_area.master)
            self.search_visible = True
            self.search_entry.focus()
            self.search_entry.select_range(0, tk.END)
            self.text_area.tag_remove("search", "1.0", "end")
            self.search_start_pos = self.text_area.index(tk.INSERT)
            self.search_info.config(text="")

    def on_escape(self, event=None):
        if self.search_visible:
            self.toggle_search()
        return "break"

    def search_next(self, event=None):
        search_text = self.search_entry.get()
        if not search_text:
            self.search_info.config(text=tr('editor_enter_text'))
            return
        
        self.text_area.tag_remove("search", "1.0", "end")
        start_pos = self.search_start_pos
        
        pos = self.text_area.search(search_text, start_pos, "end", nocase=True)
        
        if not pos:
            pos = self.text_area.search(search_text, "1.0", "end", nocase=True)
            if not pos:
                self.search_info.config(text=f"'{search_text}' {tr('editor_not_found')}")
                self.search_start_pos = "1.0"
                return
            self.search_start_pos = self.text_area.index(f"{pos}+{len(search_text)}c")
        else:
            self.search_info.config(text="")
            self.search_start_pos = self.text_area.index(f"{pos}+{len(search_text)}c")
        
        end_pos = self.text_area.index(f"{pos}+{len(search_text)}c")
        self.text_area.tag_add("search", pos, end_pos)
        self.text_area.tag_config("search", background="#A46EBD", foreground="#000000")
        
        self.text_area.see(pos)
        self.text_area.mark_set(tk.INSERT, pos)
        self.text_area.focus()

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
            messagebox.showinfo(tr('success'), f"{tr('editor_success')}\n{tr('restart_zapret')}")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror(tr('error_no_connection'), f"{tr('editor_error_save')}: {str(e)}")
