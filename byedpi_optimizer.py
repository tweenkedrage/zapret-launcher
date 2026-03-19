import subprocess
import os
import json
import time
import shutil
from pathlib import Path
import sys
from typing import Optional, Tuple

class ByeDPIOptimizer:
    
    def __init__(self, app_data_dir: Path):
        self.app_data_dir = app_data_dir
        self.byedpi_dir = app_data_dir / "byedpi"
        self.bin_dir = self.byedpi_dir / "bin"
        self.config_file = self.byedpi_dir / "config.json"
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.current_version = "17.3"
        
        # Параметры для Ростелеком
        self.rostel_params = [
            "--split", "1",           # Минимальное разделение
            "-i", "127.0.0.1",        # Локальный адрес
            "-p", "10801",             # Порт
            "--disorder", "-1"         # Изменение порядка пакетов
        ]
        
        self.ensure_directories()
        
        self.copy_binary_if_exists()
        
    def ensure_directories(self):
        self.byedpi_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(exist_ok=True)
    
    def copy_binary_if_exists(self):
        binary = self.get_binary_path()
        if binary and binary.exists():
            target = self.bin_dir / "ciadpi.exe"
            if not target.exists():
                try:
                    shutil.copy2(binary, target)
                    print(f"ByeDPI скопирован в {target}")
                except:
                    pass
    
    def get_binary_path(self) -> Optional[Path]:
        app_binary = self.bin_dir / "ciadpi.exe"
        if app_binary.exists():
            return app_binary
        
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            exe_path = base_path / "bin" / "ciadpi.exe"
            if exe_path.exists():
                return exe_path
        
        local_path = Path(__file__).parent / "bin" / "ciadpi.exe"
        if local_path.exists():
            return local_path
        
        root_path = Path(__file__).parent / "ciadpi.exe"
        if root_path.exists():
            return root_path
        
        return None
    
    def start(self) -> Tuple[bool, str]:
        binary = self.get_binary_path()
        if not binary:
            paths_checked = []
            if getattr(sys, 'frozen', False):
                paths_checked.append(str(Path(sys._MEIPASS) / "bin" / "ciadpi.exe"))
            paths_checked.append(str(Path(__file__).parent / "bin" / "ciadpi.exe"))
            paths_checked.append(str(Path(__file__).parent / "ciadpi.exe"))
            
            return False, f"ByeDPI не найден. Проверены пути: {', '.join(paths_checked)}"
        
        if not binary.exists():
            return False, f"Файл найден но не существует: {binary}"
    
        try:
            self.stop()
            
            print(f"Запуск ByeDPI: {binary}")
            print(f"Параметры: {' '.join(self.rostel_params)}")
            
            args = [str(binary)] + self.rostel_params
            
            self.process = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(1)
            
            if self.process.poll() is None:
                self.is_running = True
                return True, "Оптимизатор запущен"
            else:
                stdout, stderr = self.process.communicate(timeout=1)
                error_msg = stderr.decode('cp1251', errors='ignore') if stderr else "Неизвестная ошибка"
                return False, f"Не удалось запустить ByeDPI: {error_msg}"
                    
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"
    
    def stop(self) -> Tuple[bool, str]:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
                self.process = None
                self.is_running = False
                return True, "Остановлен"
            except:
                try:
                    self.process.kill()
                    self.process = None
                    self.is_running = False
                    return True, "Принудительно остановлен"
                except:
                    pass
        return False, "Не был запущен"
    
    def get_status(self) -> dict:
        binary_exists = self.get_binary_path() is not None
        return {
            'running': self.is_running,
            'version': self.current_version if binary_exists else "0.0",
            'binary_exists': binary_exists,
            'params': ' '.join(self.rostel_params)
        }
