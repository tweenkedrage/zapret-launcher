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
        
        self.rostel_params = [
            "--split", "1",
            "-i", "127.0.0.1",
            "-p", "10801",
            "--disorder", "-1"
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
                except:
                    pass
    
    def set_params(self, params):
        self.rostel_params = params
    
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
            return False, "ByeDPI не найден"
        
        if not binary.exists():
            return False, f"Файл не существует: {binary}"

        try:
            self.stop()
            self._kill_process_on_port(10801)
            
            args = [str(binary)] + self.rostel_params
            
            print(f"Запуск ByeDPI: {' '.join(args)}")
            
            self.process = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(2)
            
            if self.process.poll() is None:
                time.sleep(1)
                
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 10801))
                sock.close()
                
                if result == 0:
                    self.is_running = True
                    return True, "ByeDPI запущен"
                else:
                    return False, "ByeDPI запущен, но порт 10801 не открыт"
            else:
                return False, "Процесс завершился сразу"
                            
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"
        
    def stop(self) -> Tuple[bool, str]:
        result = False
        msg = "Не был запущен"
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
                self.process = None
                self.is_running = False
                result = True
                msg = "Остановлен"
            except:
                try:
                    self.process.kill()
                    self.process = None
                    self.is_running = False
                    result = True
                    msg = "Принудительно остановлен"
                except:
                    pass
        
        self._kill_process_on_port(10801)
        return result, msg

    def _kill_process_on_port(self, port):
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True
            )
            pids = set()
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        pids.add(pid)
            
            for pid in pids:
                try:
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                except:
                    pass
            
            if port == 10801:
                subprocess.run('taskkill /F /IM ciadpi.exe', shell=True, capture_output=True)
                
        except Exception as e:
            print(f"Ошибка при очистке порта {port}: {e}")
    
    def get_status(self) -> dict:
        binary_exists = self.get_binary_path() is not None
        return {
            'running': self.is_running,
            'version': self.current_version if binary_exists else "0.0",
            'binary_exists': binary_exists,
            'params': ' '.join(self.rostel_params)
        }
