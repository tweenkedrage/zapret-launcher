from widgets import RoundedButton

DARK_THEME = {
    'name': 'Темная',
    'bg_dark': '#0F0F12',
    'bg_medium': '#1A1A1F',
    'bg_light': '#25252B',
    'accent': '#4361ee',
    'accent_hover': '#5a7aff',
    'accent_green': '#10b981',
    'accent_red': '#ef4444',
    'text_primary': '#FFFFFF',
    'text_secondary': '#9CA3AF',
    'border': '#2D2D35',
    'button_bg': '#33333D',
    'separator': '#2D2D35',
}

def get_theme(theme_name='dark'):
    return DARK_THEME

def get_theme_names():
    return ['dark']
