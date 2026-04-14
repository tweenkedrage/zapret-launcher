import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build():
    folders = ['build', 'dist', '__pycache__']
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Удалена папка {folder}")
    
    spec_file = Path('Zapret Launcher.spec')
    if spec_file.exists():
        spec_file.unlink()
        print("Удален spec файл")
    print()

def install_requirements():
    requirements = [
        'pystray',
        'pillow', 
        'cryptography',
        'psutil',
        'pyinstaller'
    ]
    
    print("Установка зависимостей...")
    for req in requirements:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', req])
        print(f"{req}")
    print()

def build_exe():
    print("Сборка Zapret Launcher...")
    print()
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'Zapret Launcher',
        '--icon', 'icon.ico',
        '--clean',
        '--noconfirm',
    ]
    
    hidden_imports = [
        '--hidden-import', 'pystray',
        '--hidden-import', 'PIL',
        '--hidden-import', 'cryptography',
        '--hidden-import', 'cryptography.hazmat.primitives.ciphers',
        '--hidden-import', 'asyncio',
        '--hidden-import', 'psutil',
    ]
    cmd.extend(hidden_imports)
    
    data_files = [
        '--add-data', 'tg_proxy.py;.',
        '--add-data', 'pages.py;.',
        '--add-data', 'theme.py;.',
        '--add-data', 'network_set.py;.',
        '--add-data', 'widgets.py;.',
        '--add-data', 'list_editor.py;.',
        '--add-data', 'icon.ico;.',
        '--add-data', 'icon.png;.',
    ]
    
    if os.path.exists('zapret_resources.zip'):
        data_files.extend(['--add-data', 'zapret_resources.zip;.'])
        print("Найден zapret_resources.zip")
    
    cmd.extend(data_files)
    cmd.append('main.py')
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print("=" * 50)
        print("Сборка завершена успешно!")
        print(f"Файл: {os.path.abspath('dist/ZapretLauncher.exe')}")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("Ошибка сборки!")
        print("=" * 50)
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 50)
    print("Zapret Launcher - Build Script")
    print("=" * 50)
    print()
    
    if not os.path.exists('icon.ico'):
        print("Предупреждение: icon.ico не найден")
        print("  Будут использованы стандартные иконки")
        print()
    
    choice = input("Выберите действие:\n1 - Полная сборка\n2 - Очистка и сборка\n3 - Только очистка\n\nВаш выбор (1-3): ")
    
    if choice == '1':
        install_requirements()
        clean_build()
        build_exe()
    elif choice == '2':
        install_requirements()
        clean_build()
    elif choice == '3':
        clean_build()
        build_exe()
    elif choice == '4':
        clean_build()
        print("Очистка завершена")
    else:
        print("Неверный выбор!")
