import tkinter as tk
from tkinter import ttk
from gui.widgets import RoundedButton
from utils.languages import tr

class DiagnosticPage:
    def __init__(self, parent, app):
        self.app = app
        self.colors = app.colors
        self.font_primary = app.font_primary
        self.font_medium = app.font_medium
        self.font_bold = app.font_bold
        
        self.frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        
        title_label = tk.Label(
            self.frame,
            text=tr('diagnostic_title'),
            font=("Inter", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(anchor='w', pady=(30, 5), padx=30)
        
        desc_label = tk.Label(
            self.frame,
            text=tr('diagnostic_desc'),
            font=("Inter", 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 20), padx=30)
        
        main_container = tk.Frame(self.frame, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)
        
        left_panel = tk.Frame(main_container, bg=self.colors['bg_dark'], width=420)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15), anchor='n')
        
        right_panel = tk.Frame(main_container, bg=self.colors['bg_dark'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, anchor='n')
        
        self._create_diagnostic_card(left_panel, "Zapret", [
            (tr('diagnostic_zapret_logs'), self.app.check_zapret_logs),
            (tr('diagnostic_zapret_auto'), self.app.auto_select_strategy),
        ])
        
        self._create_diagnostic_card(left_panel, tr('diagnostic_system'), [
            (tr('diagnostic_system_appdata'), self.app.open_appdata_folder),
            (tr('diagnostic_system_autostart'), self.app.toggle_autostart),
            (tr('diagnostic_system_optimize'), self.app.optimize_network_latency),
            (tr('diagnostic_system_dns_find'), self.app.find_and_set_best_dns),
            (tr('diagnostic_system_dns_flush'), self.app.flush_dns_cache_command),
            (tr('diagnostic_system_restore'), self.app.restore_network_defaults_command),
        ])
        
        self._create_diagnostic_card(left_panel, tr('diagnostic_general'), [
            (tr('diagnostic_general_clear'), self.app.clear_cache),
            (tr('diagnostic_general_report'), self.app.save_diagnostic_report),
        ])
        
        result_frame = tk.Frame(right_panel, bg=self.colors['bg_medium'])
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        result_header = tk.Frame(result_frame, bg=self.colors['bg_medium'], height=35)
        result_header.pack(fill=tk.X)
        result_header.pack_propagate(False)
        
        tk.Label(
            result_header, 
            text=tr('diagnostic_results'), 
            font=("Inter", 12, "bold"),
            fg=self.colors['accent'], 
            bg=self.colors['bg_medium']
        ).pack(side=tk.LEFT, padx=12, pady=6)
        
        sep = tk.Frame(result_frame, bg=self.colors['separator'], height=1)
        sep.pack(fill=tk.X, padx=12)
        
        text_container = tk.Frame(result_frame, bg=self.colors['bg_medium'])
        text_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.app.diagnostic_text = tk.Text(
            text_container, 
            bg=self.colors['bg_dark'],
            fg=self.colors['text_primary'],
            font=("Consolas", 9),
            wrap=tk.WORD,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors['separator'],
            highlightcolor=self.colors['accent'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            padx=8,
            pady=8
        )
        
        scrollbar = ttk.Scrollbar(
            text_container, 
            command=self.app.diagnostic_text.yview, 
            style="Custom.Vertical.TScrollbar"
        )
        self.app.diagnostic_text.configure(yscrollcommand=scrollbar.set)
        
        self.app.diagnostic_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_diagnostic_card(self, parent, title, buttons):
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=4)
        
        inner = tk.Frame(card, bg=self.colors['bg_light'])
        inner.pack(fill=tk.X, padx=10, pady=6)
        
        title_label = tk.Label(
            inner, 
            text=title, 
            font=("Inter", 11, "bold"),
            fg=self.colors['accent'], 
            bg=self.colors['bg_light']
        )
        title_label.pack(anchor='w', pady=(0, 5))
        
        sep = tk.Frame(inner, bg=self.colors['separator'], height=1)
        sep.pack(fill=tk.X, pady=(0, 5))
        
        buttons_container = tk.Frame(inner, bg=self.colors['bg_light'])
        buttons_container.pack(fill=tk.X)
        
        row = None
        for i, (btn_text, btn_cmd) in enumerate(buttons):
            if i % 2 == 0:
                row = tk.Frame(buttons_container, bg=self.colors['bg_light'])
                row.pack(fill=tk.X, pady=2)
            
            btn = RoundedButton(
                row if row else buttons_container,
                text=btn_text,
                command=lambda cmd=btn_cmd: self.app.safe_command(cmd),
                width=130, height=26,
                bg=self.colors['button_bg'],
                fg=self.colors['text_secondary'],
                font=("Inter", 8),
                corner_radius=5
            )
            
            if i % 2 == 0:
                btn.pack(side=tk.LEFT, padx=(0, 6), expand=True, fill=tk.X)
            else:
                btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        if len(buttons) % 2 == 1 and row:
            filler = tk.Frame(row, bg=self.colors['bg_light'])
            filler.pack(side=tk.LEFT, expand=True, fill=tk.X)
    
    def get_frame(self):
        return self.frame