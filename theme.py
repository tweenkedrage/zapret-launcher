def get_theme(theme_name='dark'):
    themes = {
        'dark': {
            'accent': '#6c5579',
            'accent_hover': '#e8ccf7',
            'accent_green': "#e8ccf7",
            'accent_red': '#EF4444',
            
            'bg_dark': '#0F0F12',
            'bg_medium': '#1A1A1F',
            'bg_light': '#25252B',
            'bg_light_hover': '#3a3a44',
            
            'text_primary': '#FFFFFF',
            'text_secondary': '#A1A1AA',
            
            'button_bg': '#2D2D35',
            'button_hover': '#3D3D45',
            
            'separator': '#2D2D35',
        }
    }
    return themes.get(theme_name, themes['dark'])

def get_theme_names():
    return ['dark']
