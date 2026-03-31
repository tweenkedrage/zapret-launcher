import subprocess
import time
import shutil
import socket
import json
from pathlib import Path
import sys
import re
from typing import Optional, Tuple

class ByeDPIOptimizer:
    def __init__(self, app_data_dir: Path):
        self.app_data_dir = app_data_dir
        self.byedpi_dir = app_data_dir / "byedpi"
        self.bin_dir = self.byedpi_dir / "bin"
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.current_version = "17.3"
        self._binary_path: Optional[Path] = None
        
        self.rostel_params = [
            "--split", "1",
            "-i", "127.0.0.1",
            "-p", "10801",
            "--disorder", "-1"
        ]
        
        self.ensure_directories()
        self.copy_binary_if_exists()
        self._load_params()
        
    def ensure_directories(self):
        self.byedpi_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(exist_ok=True)
    
    def copy_binary_if_exists(self):
        source = None
        if getattr(sys, 'frozen', False):
            source = Path(sys._MEIPASS) / "bin" / "ciadpi.exe"
        else:
            source = Path(__file__).parent / "bin" / "ciadpi.exe"
            if not source.exists():
                source = Path(__file__).parent / "ciadpi.exe"
        
        if source and source.exists():
            target = self.bin_dir / "ciadpi.exe"
            if not target.exists() or source != target:
                try:
                    shutil.copy2(source, target)
                except Exception as e:
                    print(f"Не удалось скопировать бинарник: {e}")
            self._binary_path = target
    
    def set_params(self, params: list):
        self.rostel_params = params
        self._save_params()

    def _save_params(self):
        try:
            config_file = self.byedpi_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({'params': self.rostel_params}, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения параметров: {e}")
    
    def _load_params(self):
        try:
            config_file = self.byedpi_dir / "config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'params' in data:
                        self.rostel_params = data['params']
        except Exception as e:
            print(f"Ошибка загрузки параметров: {e}")
    
    def get_binary_path(self) -> Optional[Path]:
        if self._binary_path is not None and self._binary_path.exists():
            return self._binary_path
        
        cached_path = self.bin_dir / "ciadpi.exe"
        if cached_path.exists():
            self._binary_path = cached_path
            return cached_path
        
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
                shell=True, capture_output=True, text=True, timeout=5
            )
            return 'ciadpi.exe' in result.stdout
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def _is_port_open(self, port: int) -> bool:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
        except Exception:
            return False
        finally:
            if sock:
                sock.close()
    
    def _kill_process_on_port(self, port: int):
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True, timeout=5
            )
            pids = set()
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        pids.add(parts[-1])
            
            for pid in pids:
                try:
                    subprocess.run(
                        f'taskkill /F /PID {pid}',
                        shell=True, capture_output=True, timeout=3
                    )
                except subprocess.TimeoutExpired:
                    pass
            
            if port == 10801:
                subprocess.run(
                    'taskkill /F /IM ciadpi.exe',
                    shell=True, capture_output=True, timeout=3
                )
                
        except subprocess.TimeoutExpired:
            print(f"Таймаут при поиске процессов на порту {port}")
        except Exception as e:
            print(f"Ошибка при очистке порта {port}: {e}")
    
    def _wait_port_release(self, port: int, timeout: float = 3.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self._is_port_open(port):
                return True
            time.sleep(0.2)
        return False
    
    def start(self) -> Tuple[bool, str]:
        ok, msg = self.check_binary()
        if not ok:
            return False, msg
        
        self._kill_process_on_port(10801)
        time.sleep(0.5)
        
        if not self._wait_port_release(10801, 2.0):
            return False, "Порт 10801 занят другим приложением"
        
        binary = self.get_binary_path()
        if not binary:
            return False, "ByeDPI не найден"
        
        if not binary.exists():
            return False, f"Файл не существует: {binary}"

        try:
            args = [str(binary)] + self.rostel_params
            
            print(f"Запуск ByeDPI: {' '.join(args)}")
            self.process = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            for attempt in range(30):
                time.sleep(0.3)
                
                if self.process.poll() is not None:
                    returncode = self.process.returncode
                    if returncode != 0:
                        return False, f"Процесс завершился с кодом {returncode}. Проверьте параметры: {' '.join(self.rostel_params)}"
                    return False, "Процесс завершился сразу после запуска"
                
                if self._is_port_open(10801):
                    self.is_running = True
                    return True, "ByeDPI запущен"
                
                if attempt == 10:
                    print("Ожидание открытия порта 10801...")
                elif attempt == 20:
                    print("ByeDPI всё ещё запускается...")
            
            if self.process.poll() is None:
                self.stop()
                return False, f"Порт 10801 не открылся за 9 секунд. Проверьте параметры: {' '.join(self.rostel_params)}"
            
            return False, "Неизвестная ошибка при запуске"                 
        except FileNotFoundError:
            return False, f"Файл не найден: {binary}"
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"
    
    def stop(self) -> Tuple[bool, str]:
        result = False
        msg = "Не был запущен"
        
        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
                self.process = None
                self.is_running = False
                result = True
                msg = "Остановлен"
            except Exception as e:
                print(f"Ошибка остановки процесса: {e}")
                self.process = None
        
        self._kill_process_on_port(10801)
        self._wait_port_release(10801, 2.0)
        
        return result, msg

    def restart(self) -> Tuple[bool, str]:
        self.stop()
        time.sleep(1)
        return self.start()
    
    def check_binary(self) -> Tuple[bool, str]:
        binary = self.get_binary_path()
        if not binary:
            return False, "ByeDPI не найден"
        
        if not binary.exists():
            return False, f"Файл не существует: {binary}"
        
        try:
            result = subprocess.run(
                [str(binary), "--help"],
                capture_output=True,
                timeout=3
            )
            return True, "Бинарник работает"
        except Exception as e:
            return False, f"Бинарник не отвечает: {e}"

    def get_status(self) -> dict:
        binary_exists = self.get_binary_path() is not None
        port_open = self._is_port_open(10801)
        
        if self.process is not None:
            poll = self.process.poll()
            if poll is not None:
                self.is_running = False
                self.process = None
        else:
            self.is_running = self._is_already_running()
        
        return {
            'running': self.is_running and port_open,
            'version': self.current_version if binary_exists else "0.0",
            'binary_exists': binary_exists,
            'port_open': port_open,
            'params': ' '.join(self.rostel_params)
        }
    
    def get_version(self) -> str:
        binary = self.get_binary_path()
        if not binary or not binary.exists():
            return "0.0"
        
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout or result.stderr
            for line in output.split('\n'):
                if 'version' in line.lower():
                    match = re.search(r'(\d+\.\d+)', line)
                    if match:
                        return match.group(1)
            return self.current_version
        except Exception:
            return self.current_version
