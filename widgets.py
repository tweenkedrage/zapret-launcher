import tkinter as tk

class ModernSwitch(tk.Canvas):
    def __init__(self, parent, width=50, height=24, bg_color='#25252B', 
                 active_color='#4361ee', command=None, initial=False):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent['bg'])
        self.active_color = active_color
        self.inactive_color = bg_color
        self.state = initial
        self.command = command
        self.width = width
        self.height = height
        
        self.bg_rect = self.create_oval(2, 2, width-2, height-2, fill=self.inactive_color, outline='#2D2D35', width=1)
        self.slider = self.create_oval(4, 4, height-4, height-4, fill='#ffffff', outline='', tags=('slider',))
        
        if self.state:
            self.coords(self.slider, width-height+4, 4, width-4, height-4)
            self.itemconfig(self.bg_rect, fill=self.active_color)
        
        self.tag_bind(self.bg_rect, "<Button-1>", self.on_click)
        self.tag_bind("slider", "<Button-1>", self.on_click)

    def on_click(self, event):
        self.state = not self.state
        if self.state:
            self.coords(self.slider, self.width-self.height+4, 4, self.width-4, self.height-4)
            self.itemconfig(self.bg_rect, fill=self.active_color)
        else:
            self.coords(self.slider, 4, 4, self.height-4, self.height-4)
            self.itemconfig(self.bg_rect, fill=self.inactive_color)
        if self.command:
            self.command(self.state)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=200, height=40, 
                 bg='#4361ee', fg='white', font=("Segoe UI", 11, "bold"), corner_radius=8):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent['bg'], cursor="hand2")
        self.command = command
        self.bg = bg
        self.fg = fg
        self.font = font
        self.enabled = True
        self.normal_color = bg
        self.hover_color = "#6c5579"
        self.corner_radius = corner_radius
        
        points = []
        points.extend([corner_radius, 0, width-corner_radius, 0])
        points.extend([width, 0, width, corner_radius, width, height-corner_radius, width, height])
        points.extend([width-corner_radius, height, corner_radius, height])
        points.extend([0, height, 0, height-corner_radius, 0, corner_radius, 0, 0])
        self.rect = self.create_polygon(points, smooth=True, fill=bg, outline='')
        self.text_id = self.create_text(width//2, height//2, text=text, fill=fg, font=font)
        
        for item in [self.rect, self.text_id]:
            self.tag_bind(item, "<Button-1>", self.on_click)
            self.tag_bind(item, "<Enter>", self.on_enter)
            self.tag_bind(item, "<Leave>", self.on_leave)

    def on_click(self, event):
        if self.enabled and self.command:
            self.command()

    def on_enter(self, event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.hover_color)

    def on_leave(self, event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.normal_color)

    def set_text(self, text):
        self.itemconfig(self.text_id, text=text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        color = self.normal_color if enabled else '#666666'
        self.itemconfig(self.rect, fill=color)

    def update_colors(self, bg_color, fg_color, hover_color):
        self.normal_color = bg_color
        self.hover_color = hover_color
        self.itemconfig(self.rect, fill=bg_color)
        self.itemconfig(self.text_id, fill=fg_color)
