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
            print(f"Folder {folder} has been deleted")
    
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"Removed: {pycache_path}")
    
    spec_file = Path('Zapret Launcher.spec')
    if spec_file.exists():
        spec_file.unlink()
        print("Spec file removed")
    print()

def install_requirements():
    requirements = [
        'pystray',
        'pillow', 
        'cryptography',
        'psutil',
        'pyinstaller'
    ]
    
    print("Installing dependencies...")
    for req in requirements:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', req])
        print(f"  {req}")
    print()

def build_exe():
    print("Building Zapret Launcher...")
    print()
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'Zapret Launcher',
        '--icon', 'resources/icon.ico',
        '--clean',
        '--noconfirm',
    ]
    
    hidden_imports = [
        '--hidden-import', 'pystray',
        '--hidden-import', 'PIL',
        '--hidden-import', 'cryptography',
        '--hidden-import', 'psutil',
        '--hidden-import', 'tkinter',
    ]
    cmd.extend(hidden_imports)
    
    data_files = [
        '--add-data', f'gui{os.pathsep}gui',
        '--add-data', f'utils{os.pathsep}utils',
        '--add-data', f'resources{os.pathsep}resources',
        '--add-data', f'tg_proxy{os.pathsep}tg_proxy',
    ]
    
    if os.path.exists('zapret_resources.zip'):
        data_files.extend(['--add-data', f'zapret_resources.zip{os.pathsep}.'])
        print("Found zapret_resources.zip")
    
    cmd.extend(data_files)
    cmd.append('main.py')
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print("=" * 50)
        print("Build completed successfully!")
        print(f"File: {os.path.abspath('dist/Zapret Launcher.exe')}")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("Build error!")
        print("=" * 50)
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 50)
    print("Zapret Launcher - Build Script")
    print("=" * 50)
    print()
    
    if not os.path.exists('resources/icon.ico'):
        print("Warning: resources/icon.ico not found")
        print()
    
    print("Choose action:")
    print("1 - Full build")
    print("2 - Clean + build")
    print()
    
    choice = input("Enter choice (1-2): ")
    
    if choice == '1':
        install_requirements()
        clean_build()
        build_exe()
    elif choice == '2':
        clean_build()
        build_exe()
    elif choice == '3':
        build_exe()
    elif choice == '4':
        clean_build()
        print("Cleaning completed")
    else:
        print("Wrong choice!")
