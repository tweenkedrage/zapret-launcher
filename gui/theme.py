def get_theme(theme_name='Dark'):
    themes = {
        'Dark': {
            'accent': '#6c5579',
            'accent_hover': '#e8ccf7',
            'accent_green': '#4ade80',
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
        },
        'Light': { # prerelease
            'accent': '#6c5579',
            'accent_hover': '#e8ccf7',
            'accent_green': '#10b981',
            'accent_red': '#EF4444',
            
            'bg_dark': '#F5F5F7',
            'bg_medium': '#E8E8EC',
            'bg_light': '#FFFFFF',
            'bg_light_hover': '#F0F0F4',
            
            'text_primary': '#1A1A1F',
            'text_secondary': '#6B6B76',
            
            'button_bg': '#E0E0E6',
            'button_hover': '#D0D0D8',
            
            'separator': '#D0D0D8',
        }
    }
    return themes.get(theme_name, themes['Dark'])

def get_theme_names():
    return ['Dark', 'Light']
