# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional, List, Tuple
from gui.widgets import RoundedButton
from utils.languages import tr
import psutil
import threading

class Dialogs:
    def __init__(self, app):
        self.app = app
        self.colors = app.colors
        self.current_theme = app.current_theme
        
    def show_mode_selector(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title(tr('mode_select_title'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 250
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 275
        
        dialog.geometry(f"500x550+{x}+{y}")
        dialog.update_idletasks()
        self.app.set_dialog_header_color(dialog)
        
        tk.Label(dialog, text=tr('mode_select'), font=("Segoe UI Variable", 16, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(20, 10))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.colors['bg_medium'], highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_medium'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=440)
        canvas.configure(yscrollcommand=None)
        canvas.pack(side="left", fill="both", expand=True)
        
        modes = [
            {"name": tr('mode_standard'), "desc": tr('mode_standard_desc'), 
            "zapret": True, "tgproxy": False},
            {"name": "Telegram Proxy", "desc": tr('mode_tgproxy_desc'), 
            "zapret": False, "tgproxy": True},
            {"name": tr('mode_zapret_tgproxy'), "desc": tr('mode_zapret_tgproxy_desc'), 
            "zapret": True, "tgproxy": True},
        ]
        
        selected_index = [0]
        selected_mode = [None]
        selected_widget = [None]
        mode_frames = []
        select_btn = [None]
        
        def update_select_button():
            if select_btn[0]:
                if selected_mode[0]:
                    select_btn[0].set_enabled(True)
                    select_btn[0].normal_color = self.colors['accent']
                    select_btn[0].hover_color = self.colors['accent']
                    select_btn[0].update_colors(
                        self.colors['accent'],
                        self.colors['text_primary'],
                        self.colors['accent']
                    )
                    select_btn[0].config(cursor="hand2")
                else:
                    select_btn[0].set_enabled(False)
                    select_btn[0].normal_color = self.colors['accent']
                    select_btn[0].hover_color = self.colors['accent']
                    select_btn[0].update_colors(
                        self.colors['button_bg'],
                        self.colors['text_secondary'],
                        self.colors['button_bg']
                    )
                    select_btn[0].config(cursor="arrow")
        
        def on_single_click(mode, frame, name_label, desc_label, index):
            if selected_widget[0]:
                prev_frame, prev_name, prev_desc, _ = selected_widget[0]
                prev_frame.configure(bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
                prev_name.configure(fg=self.colors['accent'], bg=self.colors['bg_light'])
                prev_desc.configure(fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
            
            frame.configure(bg=self.colors['accent'], relief=tk.RIDGE, bd=2)
            name_label.configure(fg=self.colors['text_primary'], bg=self.colors['accent'])
            desc_label.configure(fg=self.colors['text_secondary'], bg=self.colors['accent'])
            
            selected_widget[0] = (frame, name_label, desc_label, index)
            selected_mode[0] = mode
            selected_index[0] = index
            update_select_button()
            canvas.yview_moveto(index / len(modes) if len(modes) > 0 else 0)
        
        def on_double_click(mode):
            if mode:
                dialog.destroy()
                self.app.start_with_mode(mode)
        
        def on_select_click():
            if selected_mode[0]:
                dialog.destroy()
                self.app.start_with_mode(selected_mode[0])
        
        def move_selection(delta):
            new_index = selected_index[0] + delta
            if 0 <= new_index < len(modes):
                selected_index[0] = new_index
                mode = modes[new_index]
                frame, name_label, desc_label = mode_frames[new_index]
                on_single_click(mode, frame, name_label, desc_label, new_index)
        
        def on_key_press(event):
            if event.keysym == 'Up':
                move_selection(-1)
                return "break"
            elif event.keysym == 'Down':
                move_selection(1)
                return "break"
            elif event.keysym == 'Return':
                if selected_mode[0]:
                    dialog.destroy()
                    self.app.start_with_mode(selected_mode[0])
                return "break"
            elif event.keysym == 'Escape':
                dialog.destroy()
                return "break"
        
        dialog.bind('<Up>', on_key_press)
        dialog.bind('<Down>', on_key_press)
        dialog.bind('<Return>', on_key_press)
        dialog.bind('<Escape>', on_key_press)
        
        for idx, mode in enumerate(modes):
            mode_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0, cursor="hand2")
            mode_frame.pack(fill=tk.X, padx=10, pady=5, ipady=8)
            
            original_bg = self.colors['bg_light']
            name_label = tk.Label(mode_frame, text=mode["name"], font=("Segoe UI Variable", 12, "bold"),
                                fg=self.colors['accent'], bg=original_bg)
            name_label.pack(anchor='w', padx=15, pady=(8, 2))
            desc_label = tk.Label(mode_frame, text=mode["desc"], font=("Segoe UI Variable", 9),
                                fg=self.colors['text_secondary'], bg=original_bg)
            desc_label.pack(anchor='w', padx=15, pady=(0, 8))
            
            mode_frames.append((mode_frame, name_label, desc_label))
            
            if idx == 0:
                selected_index[0] = 0
                selected_mode[0] = mode
                selected_widget[0] = (mode_frame, name_label, desc_label, idx)
                mode_frame.configure(bg=self.colors['accent'], relief=tk.RIDGE, bd=2)
                name_label.configure(fg=self.colors['text_primary'], bg=self.colors['accent'])
                desc_label.configure(fg=self.colors['text_secondary'], bg=self.colors['accent'])
                update_select_button()

            def make_on_click(m, f, nl, dl, i):
                return lambda e: on_single_click(m, f, nl, dl, i)
            
            def make_on_double(m):
                return lambda e: on_double_click(m)
            
            click_handler = make_on_click(mode, mode_frame, name_label, desc_label, idx)
            double_handler = make_on_double(mode)
            
            mode_frame.bind("<Button-1>", click_handler)
            mode_frame.bind("<Double-Button-1>", double_handler)
            name_label.bind("<Button-1>", click_handler)
            name_label.bind("<Double-Button-1>", double_handler)
            desc_label.bind("<Button-1>", click_handler)
            desc_label.bind("<Double-Button-1>", double_handler)
            
            def make_on_enter(frame, nl, dl, orig_bg, idx_local):
                def on_enter_func(e):
                    if selected_widget[0] and selected_widget[0][3] == idx_local:
                        return
                    frame.configure(bg=self.colors['bg_light_hover'])
                    nl.configure(bg=self.colors['bg_light_hover'])
                    dl.configure(bg=self.colors['bg_light_hover'])
                return on_enter_func
            
            def make_on_leave(frame, nl, dl, orig_bg, idx_local):
                def on_leave_func(e):
                    if selected_widget[0] and selected_widget[0][3] == idx_local:
                        return
                    frame.configure(bg=orig_bg)
                    nl.configure(bg=orig_bg)
                    dl.configure(bg=orig_bg)
                return on_leave_func
            
            mode_frame.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            mode_frame.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
            name_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            name_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
            desc_label.bind("<Enter>", make_on_enter(mode_frame, name_label, desc_label, original_bg, idx))
            desc_label.bind("<Leave>", make_on_leave(mode_frame, name_label, desc_label, original_bg, idx))
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=20, pady=15)
        
        select_btn[0] = RoundedButton(
            bottom_frame,
            text=tr('mode_select_button'),
            command=on_select_click,
            width=100, height=35,
            bg=self.colors['accent'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        select_btn[0].normal_color = self.colors['accent']
        select_btn[0].hover_color = self.colors['accent']
        select_btn[0].set_enabled(True)
        select_btn[0].config(cursor="hand2")
        select_btn[0].pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = RoundedButton(
            bottom_frame,
            text=tr('mode_cancel'),
            command=dialog.destroy,
            width=100, height=35,
            bg=self.colors['button_bg'],
            font=("Segoe UI Variable", 10),
            corner_radius=8
        )
        cancel_btn.normal_color = self.colors['button_bg']
        cancel_btn.hover_color = self.colors['accent']
        cancel_btn.config(cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)
        
    def show_strategy_selector(self, mode_name):
        dialog = tk.Toplevel(self.app.root)
        dialog.title(tr('select_strategy_title'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 275
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 275
        
        dialog.geometry(f"550x550+{x}+{y}")
        dialog.update_idletasks()
        self.app.set_dialog_header_color(dialog)
        
        if mode_name == tr('mode_zapret_tgproxy'):
            title_text = f"{tr('select_strategy')}"
            desc_text = ""
        else:
            title_text = tr('select_strategy')
            desc_text = ""
        
        tk.Label(dialog, text=title_text, font=("Segoe UI Variable", 18, "bold"),
                fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(pady=(25, 15))
        
        if desc_text:
            tk.Label(dialog, text=desc_text, font=("Segoe UI Variable", 10),
                    fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                    wraplength=450).pack(pady=(0, 15))
        
        main_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=5)
        
        list_card = tk.Frame(main_frame, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        list_card.pack(fill=tk.BOTH, expand=True)
        
        list_inner = tk.Frame(list_card, bg=self.colors['bg_light'])
        list_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        tk.Label(list_inner, text=tr('available_strategies'), font=("Segoe UI Variable", 12, "bold"),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        list_frame = tk.Frame(list_inner, bg=self.colors['bg_light'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        strategy_listbox = tk.Listbox(list_frame, height=10, font=("Segoe UI Variable", 10),
                                    bg=self.colors['bg_light'], fg=self.colors['text_primary'],
                                    selectbackground=self.colors['accent'],
                                    yscrollcommand=scrollbar.set)
        strategy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=strategy_listbox.yview)
        
        for s in self.app.zapret.available_strategies:
            strategy_listbox.insert(tk.END, s)
        
        desc_label = tk.Label(dialog, text="", font=("Segoe UI Variable", 9),
                            fg=self.colors['text_secondary'], bg=self.colors['bg_medium'],
                            wraplength=400, justify=tk.LEFT)
        desc_label.pack(pady=5, padx=20)
        
        is_processing = False
        
        def on_select(event):
            selection = strategy_listbox.curselection()
            if selection:
                strategy = self.app.zapret.available_strategies[selection[0]]
                desc_label.config(text=f"{tr('selected')} {strategy}")
        
        strategy_listbox.bind("<<ListboxSelect>>", on_select)
        
        if self.app.current_strategy:
            try:
                idx = self.app.zapret.available_strategies.index(self.app.current_strategy)
                strategy_listbox.selection_set(idx)
                strategy_listbox.see(idx)
                desc_label.config(text=f"{tr('selected')} {self.app.current_strategy}")
            except ValueError:
                pass
        
        def move_selection(delta):
            nonlocal is_processing
            if is_processing:
                return
            is_processing = True
            
            try:
                current = strategy_listbox.curselection()
                if current:
                    new_idx = current[0] + delta
                else:
                    new_idx = 0 if delta > 0 else len(self.app.zapret.available_strategies) - 1
                
                if 0 <= new_idx < len(self.app.zapret.available_strategies):
                    strategy_listbox.selection_clear(0, tk.END)
                    strategy_listbox.selection_set(new_idx)
                    strategy_listbox.see(new_idx)
                    strategy = self.app.zapret.available_strategies[new_idx]
                    desc_label.config(text=f"{tr('selected')} {strategy}")
            finally:
                dialog.after(100, lambda: setattr(move_selection, 'processing', False))
                is_processing = False
        
        def on_key_press(event):
            if event.keysym == 'Up':
                move_selection(-1)
                return "break"
            elif event.keysym == 'Down':
                move_selection(1)
                return "break"
            elif event.keysym == 'Return':
                start_with_strategy()
                return "break"
            elif event.keysym == 'Escape':
                dialog.destroy()
                return "break"
        
        def on_double_click(event):
            start_with_strategy()
        
        dialog.bind('<Up>', on_key_press)
        dialog.bind('<Down>', on_key_press)
        dialog.bind('<Return>', on_key_press)
        dialog.bind('<Escape>', on_key_press)

        strategy_listbox.bind('<Up>', on_key_press)
        strategy_listbox.bind('<Down>', on_key_press)
        strategy_listbox.bind('<Return>', on_key_press)
        strategy_listbox.bind('<Escape>', on_key_press)
        strategy_listbox.bind('<Double-Button-1>', on_double_click)
        strategy_listbox.focus_set()
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)
        
        def start_with_strategy():
            selection = strategy_listbox.curselection()
            if not selection:
                messagebox.showerror(tr('error_select_strategy'), tr('error_select_strategy'))
                self.app._connecting = False
                self.app.force_tray_menu_update()
                return
            selected_strategy = self.app.zapret.available_strategies[selection[0]]
            self.app.strategy_var.set(selected_strategy)
            dialog.destroy()
            
            mode = self.app._pending_mode
            self.app.update_status(f"{tr('status_starting')}", self.colors['accent'])
            if hasattr(self.app, 'connect_btn') and self.app.connect_btn:
                self.app.connect_btn.set_enabled(False)
            self.app.root.update()
            
            if mode["name"] == tr('mode_zapret_tgproxy'):
                def start_combined():
                    success, msg = self.app.zapret.run_strategy(selected_strategy)
                    if not success:
                        self.app.root.after(0, lambda: self.app._on_combined_start_failed(msg))
                        return
                    
                    self.app.current_strategy = selected_strategy
                    self.app.save_settings()
                    
                    tg_success = self.app.tg_proxy.start()
                    if not tg_success:
                        self.app.zapret.stop_current_strategy()
                        self.app.root.after(0, lambda: self.app._on_combined_start_failed(tr('error_tgproxy_start')))
                        return
                    
                    if not self.app.tg_proxy.wait_for_start(8):
                        self.app.zapret.stop_current_strategy()
                        self.app.tg_proxy.stop()
                        self.app.root.after(0, lambda: self.app._on_combined_start_failed(tr('error_tgproxy_timeout')))
                        return
                    
                    self.app.is_connected = True
                    self.app.stats.start_session()
                    self.app.start_stats_monitoring()
                    
                    self.app.root.after(0, lambda: self.app._on_combined_start_success(mode["name"]))
                
                threading.Thread(target=start_combined, daemon=True).start()
            else:
                success, msg = self.app.zapret.run_strategy(selected_strategy)
                if not success:
                    self.app.update_status(tr('status_error'), self.colors['accent_red'])
                    messagebox.showerror(tr('error_startup'), msg)
                    if hasattr(self.app, 'connect_btn') and self.app.connect_btn:
                        self.app.connect_btn.set_enabled(True)
                    self.app._connecting = False
                    self.app.force_tray_menu_update()
                    return
                
                self.app.current_strategy = selected_strategy
                self.app.save_settings()
                
                if mode.get("tgproxy", False):
                    self.app.tg_proxy.start()
                
                self.app.is_connected = True
                self.app.stats.start_session()
                self.app.start_stats_monitoring()
                
                if hasattr(self.app, 'mode_label') and self.app.mode_label:
                    self.app.mode_label.config(text=mode["name"], fg=self.colors['accent_green'])
                self.app.update_status(f"{tr('status_connected')}", self.colors['accent_green'])
                self.app.update_ui_state()
                self.app.save_settings()
                self.app.root.after(500, self.app.update_tray_icon_state)
                if hasattr(self.app, 'connect_btn') and self.app.connect_btn:
                    self.app.connect_btn.set_enabled(True)

                self.app._connecting = False
                self.app.force_tray_menu_update()
        
        start_btn = RoundedButton(btn_frame, text=tr('button_start'), command=start_with_strategy,
                                width=120, height=35, bg=self.colors['accent'],
                                font=("Segoe UI Variable", 10), corner_radius=8,
                                hover_color=self.colors['accent'], theme_name=self.current_theme)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = RoundedButton(btn_frame, text=tr('mode_cancel'), command=lambda: self.app._cancel_strategy_selection(dialog),
                                width=80, height=35, bg=self.colors['button_bg'],
                                font=("Segoe UI Variable", 10), corner_radius=8,
                                hover_color=self.colors['accent'], theme_name=self.current_theme)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def show_tg_proxy_instruction(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title(tr('instruction_title_window'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 250
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 310
        
        dialog.geometry(f"500x520+{x}+{y}")
        dialog.update_idletasks()
        self.app.set_dialog_header_color(dialog)

        secret = getattr(self.app, '_tg_secret', None)
        if not secret:
            secret = tr('error_secret_not_found')
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(20, 5))
        
        title_label = tk.Label(title_frame, text=tr('tg_instruction_title'), 
                            font=("Segoe UI Variable", 20, "bold"),
                            fg=self.colors['accent'], bg=self.colors['bg_medium'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text=tr('tg_instruction_subtitle'),
                                font=("Segoe UI Variable", 11),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_medium'])
        subtitle_label.pack(pady=(5, 0))
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=2)
        separator.pack(fill=tk.X, padx=30, pady=10)
        instruction_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        instruction_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        steps = [
            ("1.", tr('tg_step1')),
            ("", tr('tg_step1_desc')),
            ("2.", tr('tg_step2')),
            ("", tr('tg_step2_desc')),
            ("3.", tr('tg_step3')),
            ("", tr('tg_type')),
            ("", tr('tg_host')),
            ("", tr('tg_port')),
        ]
        
        current_step = 0
        
        for i, step in enumerate(steps):
            text, desc = step
            if text:
                step_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                step_frame.pack(fill=tk.X, pady=(10 if current_step > 0 else 0, 2))
                
                step_num = tk.Label(step_frame, text=text, font=("Segoe UI Variable", 13, "bold"),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                step_num.pack(side=tk.LEFT)
                
                step_text = tk.Label(step_frame, text=desc, font=("Segoe UI Variable", 11),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                step_text.pack(side=tk.LEFT, padx=(5, 0))
                current_step += 1
            else:
                sub_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
                sub_frame.pack(fill=tk.X, pady=1)
                
                spacer = tk.Label(sub_frame, text="   ", font=("Segoe UI Variable", 11),
                                fg=self.colors['text_primary'], bg=self.colors['bg_light'])
                spacer.pack(side=tk.LEFT)
                
                bullet = tk.Label(sub_frame, text="▸", font=("Segoe UI Variable", 10),
                                fg=self.colors['accent'], bg=self.colors['bg_light'])
                bullet.pack(side=tk.LEFT, padx=(10, 5))
                
                sub_text = tk.Label(sub_frame, text=desc, font=("Segoe UI Variable", 10),
                                fg=self.colors['text_secondary'], bg=self.colors['bg_light'])
                sub_text.pack(side=tk.LEFT)
        
        link_frame = tk.Frame(instruction_frame, bg=self.colors['bg_light'])
        link_frame.pack(fill=tk.X, pady=(10, 5))
        
        spacer = tk.Label(link_frame, text="   ", font=("Segoe UI Variable", 11),
                        fg=self.colors['text_primary'], bg=self.colors['bg_light'])
        spacer.pack(side=tk.LEFT)
        
        bullet = tk.Label(link_frame, text="▸", font=("Segoe UI Variable", 10),
                        fg=self.colors['accent'], bg=self.colors['bg_light'])
        bullet.pack(side=tk.LEFT, padx=(10, 5))
        
        copy_frame = tk.Frame(link_frame, bg=self.colors['bg_light'], cursor="hand2")
        copy_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        link_text = tr('tg_copy_secret')
        copy_label = tk.Label(copy_frame, text=link_text, font=("Segoe UI Variable", 10),
                            fg=self.colors['accent'], bg=self.colors['bg_light'])
        copy_label.pack()
        
        def copy_link(event=None):
            secret = getattr(self.app, '_tg_secret', None)
            if not secret:
                secret = tr('error_secret_not_found')
            
            if self.app.tg_fake_tls and self.app.tg_fake_tls_domain:
                domain_hex = self.app.tg_fake_tls_domain.encode('ascii').hex()
                link = f"ee{secret}{domain_hex}"
                notification = tr('notification_copied_secret')
            else:
                link = f"{secret}"
                notification = tr('notification_copied_secret')
            
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(link)
            self.app.root.update()
            copy_label.config(text=tr('tg_copied'), fg=self.colors['accent_green'])
            self.app.show_notification(notification, 1500)
        
        copy_label.bind("<Button-1>", copy_link)
        
        def on_enter(event):
            copy_label.config(fg=self.colors['accent_hover'], font=("Segoe UI Variable", 10, "underline"))
            copy_frame.config(cursor="hand2")
        
        def on_leave(event):
            copy_label.config(fg=self.colors['accent'], font=("Segoe UI Variable", 10))
        
        copy_label.bind("<Enter>", on_enter)
        copy_label.bind("<Leave>", on_leave)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        bottom_frame.pack(fill=tk.X, padx=30, pady=15)
        dont_show_var = tk.BooleanVar(value=False)

        dont_show_cb = tk.Checkbutton(
            bottom_frame,
            text=tr('tg_dont_show'),
            variable=dont_show_var,
            bg=self.colors['bg_medium'],
            fg=self.colors['text_secondary'],
            selectcolor=self.colors['bg_medium'],
            activebackground=self.colors['bg_medium'],
            activeforeground=self.colors['text_secondary'],
            highlightthickness=0,
            bd=0,
            padx=0,
            font=("Segoe UI Variable", 10)
        )
        dont_show_cb.pack(side=tk.LEFT)

        close_btn = RoundedButton(
            bottom_frame,
            text=tr('button_close'),
            command=lambda: self.app._cancel_tg_proxy_mode(dialog, dont_show_var.get()),
            width=100, height=35,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'], 
            theme_name=self.current_theme
        )
        close_btn.pack(side=tk.RIGHT)

    def show_duplicates_dialog(self, duplicates_text: str):
        dialog = tk.Toplevel(self.app.root)
        dialog.title(tr('error_warning'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_force()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 350
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 250
        
        dialog.geometry(f"700x550+{x}+{y}")
        dialog.update_idletasks()
        self.app.set_dialog_header_color(dialog)
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(20, 5))
        
        title_label = tk.Label(
            title_frame,
            text=tr('duplicates_title'),
            font=("Segoe UI Variable", 20, "bold"),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text=tr('duplicates_subtitle'),
            font=("Segoe UI Variable", 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_medium']
        )
        subtitle_label.pack(pady=(5, 0))
        
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=2)
        separator.pack(fill=tk.X, padx=30, pady=10)
        
        message_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        message_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=3)
        
        text_frame = tk.Frame(message_frame, bg=self.colors['bg_light'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        text_widget = tk.Text(
            text_frame,
            font=("Consolas", 9),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark'],
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(
            text_frame,
            orient=tk.VERTICAL,
            command=text_widget.yview,
            style="Custom.Vertical.TScrollbar"
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.insert(tk.END, duplicates_text)
        text_widget.config(state=tk.DISABLED)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'], height=70)
        bottom_frame.pack(fill=tk.X, padx=30, pady=(10, 15))
        bottom_frame.pack_propagate(False)
        
        def on_close():
            dialog.destroy()
        
        button_frame = tk.Frame(bottom_frame, bg=self.colors['bg_medium'])
        button_frame.place(relx=1.0, y=17, anchor='ne')
        
        ignore_btn = RoundedButton(
            button_frame,
            text=tr('vpn_ignore'),
            command=on_close,
            width=120, height=35,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.current_theme
        )
        ignore_btn.pack(side=tk.RIGHT, padx=(0, 5))

    def show_vpn_detected_dialog(self, vpn_data: Dict = None):
        dialog = tk.Toplevel(self.app.root)
        dialog.title(tr('error_warning'))
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_force()

        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 250
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 180
        
        dialog.geometry(f"500x350+{x}+{y}")
        dialog.update_idletasks()
        self.app.set_dialog_header_color(dialog)
        
        title_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        title_frame.pack(fill=tk.X, pady=(20, 5))
        
        title_label = tk.Label(
            title_frame, 
            text=tr('vpn_detected_title'), 
            font=("Segoe UI Variable", 20, "bold"),
            fg=self.colors['accent'], 
            bg=self.colors['bg_medium']
        )
        title_label.pack()
        
        separator = tk.Frame(dialog, bg=self.colors['separator'], height=2)
        separator.pack(fill=tk.X, padx=30, pady=10)
        
        message_frame = tk.Frame(dialog, bg=self.colors['bg_light'])
        message_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        inner = tk.Frame(message_frame, bg=self.colors['bg_light'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        message_text = tr('vpn_detected_message')
        
        if vpn_data and vpn_data.get('vpn_processes'):
            procs = ', '.join(vpn_data['vpn_processes'][:3])
            message_text += f"\n\n{tr('vpn_detected_processes')}: {procs}"
        
        if vpn_data and vpn_data.get('vpn_interfaces'):
            ifaces = ', '.join(vpn_data['vpn_interfaces'][:3])
            message_text += f"\n{tr('vpn_detected_interfaces')}: {ifaces}"
        
        message_label = tk.Label(
            inner,
            text=message_text,
            font=("Segoe UI Variable", 10),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_light'],
            wraplength=400,
            justify=tk.LEFT
        )
        message_label.pack(pady=10)
        
        bottom_frame = tk.Frame(dialog, bg=self.colors['bg_medium'], height=70)
        bottom_frame.pack(fill=tk.X, padx=30, pady=(10, 15))
        bottom_frame.pack_propagate(False)
        
        def on_ignore():
            dialog.destroy()
            self.app.dialogs.show_mode_selector()

        def on_disable():
            dialog.destroy()
            
            if vpn_data and vpn_data.get('vpn_processes'):
                killed_count = 0
                for proc_name in vpn_data['vpn_processes']:
                    try:
                        for proc in psutil.process_iter(['name', 'pid']):
                            try:
                                if proc.info['name'] and proc_name.lower() in proc.info['name'].lower():
                                    proc.kill()
                                    killed_count += 1
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    except Exception:
                        pass

            self.app.dialogs.show_mode_selector()

        button_frame = tk.Frame(bottom_frame, bg=self.colors['bg_medium'])
        button_frame.place(relx=1.0, y=17, anchor='ne')

        disable_btn = RoundedButton(
            button_frame,
            text=tr('vpn_disable'),
            command=on_disable,
            width=120, height=35,
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.current_theme
        )
        disable_btn.pack(side=tk.RIGHT, padx=(0, 5))

        ignore_btn = RoundedButton(
            button_frame,
            text=tr('vpn_ignore'),
            command=on_ignore,
            width=120, height=35,
            bg=self.colors['button_bg'],
            fg=self.colors['text_secondary'],
            font=("Segoe UI Variable", 10),
            corner_radius=8,
            hover_color=self.colors['accent'],
            theme_name=self.current_theme
        )
        ignore_btn.pack(side=tk.RIGHT, padx=(0, 5))
