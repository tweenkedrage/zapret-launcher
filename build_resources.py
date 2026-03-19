import os
import zipfile
import urllib.request
import tempfile
from pathlib import Path

print("Создание zapret_resources.zip...")

ZIP_FILENAME = "zapret_resources.zip"
GITHUB_URL = "https://github.com/Flowseal/zapret-discord-youtube/archive/refs/heads/master.zip"

try:
    print(f"Загрузка Zapret с GitHub...")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        urllib.request.urlretrieve(GITHUB_URL, tmp_file.name)
        temp_zip = tmp_file.name
    
    print(f"Загружено, размер: {os.path.getsize(temp_zip)} байт")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Распаковка Zapret...")
        
        with zipfile.ZipFile(temp_zip, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        extracted_dirs = os.listdir(temp_dir)
        if not extracted_dirs:
            raise Exception("Архив пуст")
        
        source_dir = os.path.join(temp_dir, extracted_dirs[0])
        print(f"Найдена папка: {extracted_dirs[0]}")
        
        print(f"Создание {ZIP_FILENAME}...")
        with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            bin_path = os.path.join(source_dir, "bin")
            if os.path.exists(bin_path):
                for root, dirs, files in os.walk(bin_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
                print("  Добавлена папка bin/")
            
            lists_path = os.path.join(source_dir, "lists")
            if os.path.exists(lists_path):
                for root, dirs, files in os.walk(lists_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
                print("  Добавлена папка lists/")
            
            utils_path = os.path.join(source_dir, "utils")
            if os.path.exists(utils_path):
                for root, dirs, files in os.walk(utils_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
                print("  Добавлена папка utils/")
            
            service_bat = os.path.join(source_dir, "service.bat")
            if os.path.exists(service_bat):
                new_zip.write(service_bat, "service.bat")
                print("  Добавлен service.bat")
            
            for file in os.listdir(source_dir):
                if file.startswith("general") and file.endswith(".bat"):
                    full_path = os.path.join(source_dir, file)
                    new_zip.write(full_path, file)
                    print(f"  Добавлен {file}")
    
    os.unlink(temp_zip)
    
    if os.path.exists(ZIP_FILENAME):
        print(f"\n✅ Готово! Создан файл: {ZIP_FILENAME}")
        print(f"Размер: {os.path.getsize(ZIP_FILENAME)} байт")
        print(f"Путь: {os.path.abspath(ZIP_FILENAME)}")
    else:
        print("\n❌ Ошибка: файл не создан")

except Exception as e:
    print(f"\n❌ Ошибка: {e}")

input("\nНажми Enter для выхода...")
