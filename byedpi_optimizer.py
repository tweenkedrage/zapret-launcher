import subprocess
import time
import shutil
import socket
import json
from pathlib import Path
import sys
from typing import Optional, Tuple

class ByeDPIOptimizer:
    def __init__(self, app_data_dir: Path):
        self.app_data_dir = app_data_dir
        self.byedpi_dir = app_data_dir / "byedpi"
        self.bin_dir = self.byedpi_dir / "bin"
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.current_version = "17.3"
        self._binary_path = None
        
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
        if binary and binary.exists() and binary != self.bin_dir / "ciadpi.exe":
            target = self.bin_dir / "ciadpi.exe"
            try:
                shutil.copy2(binary, target)
            except Exception as e:
                print(f"Не удалось скопировать бинарник: {e}")
    
    def set_params(self, params):
        self.rostel_params = params
        self._save_params()

    def _save_params(self):
        try:
            config_file = self.byedpi_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump({'params': self.rostel_params}, f)
        except:
            pass
    
    def get_binary_path(self) -> Optional[Path]:
        if self._binary_path is not None:
            return self._binary_path
        
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            exe_path = base_path / "bin" / "ciadpi.exe"
            if exe_path.exists():
                self._binary_path = exe_path
                return exe_path
        
        local_path = Path(__file__).parent / "bin" / "ciadpi.exe"
        if local_path.exists():
            self._binary_path = local_path
            return local_path
        
        root_path = Path(__file__).parent / "ciadpi.exe"
        if root_path.exists():
            self._binary_path = root_path
            return root_path
        
        self._binary_path = None
        return None
    
    def _is_already_running(self) -> bool:
        try:
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq ciadpi.exe" /FO CSV',
                shell=True, capture_output=True, text=True
            )
            return 'ciadpi.exe' in result.stdout
        except:
            return False
    
    def start(self) -> Tuple[bool, str]:
        if self._is_already_running():
            self.stop()
            
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
            
            for _ in range(10):
                time.sleep(0.3)
                if self.process.poll() is not None:
                    return False, "Процесс завершился сразу"
                
                if self._is_port_open(10801):
                    self.is_running = True
                    return True, "ByeDPI запущен"
            
            return False, "ByeDPI запущен, но порт 10801 не открыт"
                                
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"

    def _is_port_open(self, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
        
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
                        pids.add(parts[-1])
            
            for pid in pids:
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
            
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
