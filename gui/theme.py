# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

def get_theme(theme_name='Default'):
    themes = {
        'Default': {
            'accent': '#6c5579',
            'accent_hover': '#e8ccf7',
            'accent_green': '#4ade80',
            'accent_darkgreen': '#348f55',
            'accent_red': '#EF4444',
            
            'bg_dark': '#0F0F12',
            'bg_medium': '#1A1A1F',
            'bg_light': '#25252B',
            'bg_light_hover': '#3a3a44',
            
            'text_primary': '#FFFFFF',
            'text_secondary': '#A1A1AA',
            
            'button_bg': '#2D2D35',
            'button_hover': '#3D3D45',
            
            'separator': "#2D2D35",
        },
        'Pink': {
            'accent': "#D4438C",
            'accent_hover': "#DD72A9",
            'accent_green': '#4ade80',
            'accent_darkgreen': '#348f55',
            'accent_red': '#EF4444',
            
            'bg_dark': '#1E1B2E',
            'bg_medium': '#2D2A3F',
            'bg_light': '#3D3A55',
            'bg_light_hover': '#4D4A6B',
            
            'text_primary': '#FFFFFF',
            'text_secondary': "#B0B0C9",
            
            'button_bg': '#4D4A6B',
            'button_hover': '#5D5A7B',
            
            'separator': "#46435A",
        },
        'Light': { #pre-release
            'accent': '#6c5579',
            'accent_hover': '#8b6b9e',
            'accent_green': '#10B981',
            'accent_darkgreen': '#059669',
            'accent_red': '#EF4444',
            
            'bg_dark': '#F8F9FA',
            'bg_medium': '#F1F3F5',
            'bg_light': '#FFFFFF',
            'bg_light_hover': '#E9ECEF',
            
            'text_primary': '#212529',
            'text_secondary': '#6C757D',
            
            'button_bg': '#E9ECEF',
            'button_hover': '#DEE2E6',
            
            'separator': '#DEE2E6',
        }
    }
    return themes.get(theme_name, themes['Default'])

def get_theme_names():
    return ['Default', 'Pink']
