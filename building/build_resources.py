import os
import zipfile
import urllib.request
import tempfile
import json

ZIP_FILENAME = "zapret_resources.zip"
GITHUB_URL = "https://github.com/Flowseal/zapret-discord-youtube/archive/refs/heads/master.zip"
VERSION_URL = "https://api.github.com/repos/flowseal/zapret-discord-youtube/releases/latest"

def get_latest_version():
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('tag_name', 'unknown').replace('v', '')
    except:
        return "1.9.7b"

try:
    current_version = get_latest_version()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        urllib.request.urlretrieve(GITHUB_URL, tmp_file.name)
        temp_zip = tmp_file.name
        file_size = os.path.getsize(temp_zip)
        
        if file_size < 100000:
            raise Exception(f"File too small ({file_size} byte)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        
        with zipfile.ZipFile(temp_zip, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        extracted_dirs = os.listdir(temp_dir)
        if not extracted_dirs:
            raise Exception("Archive is empty")
        
        source_dir = os.path.join(temp_dir, extracted_dirs[0])
        
        with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            bin_path = os.path.join(source_dir, "bin")
            if os.path.exists(bin_path):
                for root, dirs, files in os.walk(bin_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
            
            lists_path = os.path.join(source_dir, "lists")
            if os.path.exists(lists_path):
                for root, dirs, files in os.walk(lists_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
            
            utils_path = os.path.join(source_dir, "utils")
            if os.path.exists(utils_path):
                for root, dirs, files in os.walk(utils_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        new_zip.write(full_path, rel_path)
            
            service_bat = os.path.join(source_dir, "service.bat")
            if os.path.exists(service_bat):
                new_zip.write(service_bat, "service.bat")
            
            for file in os.listdir(source_dir):
                if file.startswith("general") and file.endswith(".bat"):
                    full_path = os.path.join(source_dir, file)
                    new_zip.write(full_path, file)
    os.unlink(temp_zip)

    if os.path.exists(ZIP_FILENAME):
        print(f"File created: {ZIP_FILENAME}")
        print(f"Size: {os.path.getsize(ZIP_FILENAME)} byte")
    else:
        print("Error: file is not created!")
        
except Exception as e:
    print(f"Error: {e}")
input("Press Enter...")
