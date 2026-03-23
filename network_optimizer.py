import subprocess
import socket
import time
import threading
from typing import List, Tuple, Optional
import winreg
import ctypes


DNS_SERVERS = [
    {"name": "Cloudflare", "primary": "1.1.1.1", "secondary": "1.0.0.1"},
    {"name": "Google", "primary": "8.8.8.8", "secondary": "8.8.4.4"},
    {"name": "OpenDNS", "primary": "208.67.222.222", "secondary": "208.67.220.220"},
    {"name": "Quad9", "primary": "9.9.9.9", "secondary": "149.112.112.112"},
    {"name": "Comss", "primary": "77.88.8.8", "secondary": "77.88.8.1"},
]

def list_network_adapters() -> List[str]:
    adapters = []
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'ip', 'show', 'interfaces'],
            capture_output=True, text=True, encoding='cp866'
        )
        
        lines = result.stdout.split('\n')
        for line in lines:
            if 'подключено' in line.lower() or 'connected' in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    name = ' '.join(parts[3:]).strip('*').strip()
                    if name and 'Loopback' not in name and 'lo' not in name.lower():
                        adapters.append(name)
    except:
        pass
    
    if not adapters:
        try:
            result = subprocess.run(
                ['wmic', 'nic', 'where', 'NetEnabled=True', 'get', 'Name'],
                capture_output=True, text=True, encoding='cp866'
            )
            lines = result.stdout.split('\n')
            for line in lines[1:]:
                name = line.strip()
                if name and 'Loopback' not in name and 'lo' not in name.lower():
                    adapters.append(name)
        except:
            pass
    
    if not adapters:
        try:
            result = subprocess.run(
                ['ipconfig'],
                capture_output=True, text=True, encoding='cp866'
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if 'адаптер' in line.lower() or 'adapter' in line.lower():
                    import re
                    match = re.search(r'[а-яА-Яa-zA-Z0-9\s\-]+(?=:)', line)
                    if match:
                        name = match.group().strip()
                        if name and 'Loopback' not in name and 'lo' not in name.lower():
                            adapters.append(name)
        except:
            pass
    
    return adapters


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def ping_dns_server(dns_ip: str, timeout: float = 2.0) -> Tuple[bool, float]:
    try:
        start = time.time()
        subprocess.run(['ping', '-n', '1', '-w', str(int(timeout * 1000)), dns_ip],
                      capture_output=True, timeout=timeout)
        end = time.time()
        return True, (end - start) * 1000
    except:
        return False, float('inf')


def find_best_dns() -> Tuple[str, str, float, str]:
    results = []
    
    for dns in DNS_SERVERS:
        success, latency = ping_dns_server(dns["primary"])
        if success:
            results.append({
                "name": dns["name"],
                "primary": dns["primary"],
                "secondary": dns["secondary"],
                "latency": latency
            })
    
    if not results:
        return "8.8.8.8", "8.8.4.4", 9999, "Google (fallback)"
    
    results.sort(key=lambda x: x["latency"])
    best = results[0]
    
    return best["primary"], best["secondary"], best["latency"], best["name"]


def set_dns_windows(primary: str, secondary: str) -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'ip', 'show', 'interfaces'],
            capture_output=True, text=True, encoding='cp866'
        )
        
        lines = result.stdout.split('\n')
        adapters = []
        
        for line in lines:
            if ('подключено' in line.lower() or 'connected' in line.lower()) and 'loopback' not in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    adapter_name = ' '.join(parts[3:]) if len(parts) > 4 else parts[3]
                    adapter_name = adapter_name.strip('*').strip()
                    if adapter_name and adapter_name != 'Loopback':
                        adapters.append(adapter_name)
        
        if not adapters:
            result = subprocess.run(
                ['wmic', 'nic', 'where', 'NetEnabled=True', 'get', 'Name'],
                capture_output=True, text=True, encoding='cp866'
            )
            lines = result.stdout.split('\n')
            for line in lines[1:]:
                name = line.strip()
                if name and 'Loopback' not in name:
                    adapters.append(name)
        
        if not adapters:
            return False, "Не найдены активные сетевые адаптеры"
        
        for adapter in adapters:
            try:
                subprocess.run(
                    ['netsh', 'interface', 'ip', 'set', 'dns',
                     f'name={adapter}', 'source=static', f'addr={primary}'],
                    capture_output=True, check=True, timeout=10
                )
                subprocess.run(
                    ['netsh', 'interface', 'ip', 'add', 'dns',
                     f'name={adapter}', f'addr={secondary}', 'index=2'],
                    capture_output=True, check=True, timeout=10
                )
            except subprocess.TimeoutExpired:
                continue
            except:
                continue
        
        return True, f"DNS установлен: {primary}, {secondary} (на {len(adapters)} адаптеров)"
        
    except Exception as e:
        return False, f"Ошибка: {str(e)}"


def flush_dns_cache() -> Tuple[bool, str]:
    try:
        subprocess.run(['ipconfig', '/flushdns'], capture_output=True, check=True)
        return True, "DNS кэш очищен"
    except Exception as e:
        return False, f"Ошибка очистки DNS: {str(e)}"


def optimize_network_latency() -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    changes = []
    errors = []
    
    try:
        key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                        f"{key_path}\\{subkey_name}", 
                                        0, winreg.KEY_SET_VALUE)
                try:
                    winreg.SetValueEx(subkey, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(subkey, "TCPNoDelay", 0, winreg.REG_DWORD, 1)
                    changes.append(f"Интерфейс {subkey_name}: TCP оптимизирован")
                except:
                    pass
                winreg.CloseKey(subkey)
                i += 1
            except WindowsError:
                break
        
        winreg.CloseKey(key)
    except Exception as e:
        errors.append(f"TCP оптимизация: {str(e)}")
    
    tcp_params = [
        ("TcpWindowSize", 65535),
        ("GlobalMaxTcpWindowSize", 65535),
        ("Tcp1323Opts", 3),
        ("DefaultTTL", 64),
        ("EnablePMTUDiscovery", 1),
        ("EnableTCPChimney", 1),
        ("EnableRSS", 1),
        ("EnableTCPA", 1),
    ]
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                            0, winreg.KEY_SET_VALUE)
        
        for param, value in tcp_params:
            try:
                winreg.SetValueEx(key, param, 0, winreg.REG_DWORD, value)
                changes.append(f"{param} = {value}")
            except:
                pass
        
        winreg.CloseKey(key)
    except Exception as e:
        errors.append(f"Глобальные TCP параметры: {str(e)}")
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=disabled'],
                      capture_output=True, check=True)
        changes.append("TCP автонастройка отключена")
    except:
        errors.append("Не удалось отключить автонастройку TCP")
    
    try:
        power_cfg = subprocess.run(['powercfg', '/query', 'SCHEME_CURRENT', 'SUB_NONE', '2a737441-1930-4402-8d77-b2bebba308a3'],
                                   capture_output=True, text=True)
        changes.append("Проверка настроек энергосбережения")
    except:
        pass
    
    result_msg = "Оптимизация выполнена:\n" + "\n".join(changes[:10])
    if errors:
        result_msg += f"\n\nОшибки:\n" + "\n".join(errors)
    
    return True, result_msg


def restore_network_defaults() -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=normal'],
                      capture_output=True, check=True)
        
        subprocess.run(['netsh', 'interface', 'ip', 'set', 'dns', 'name="Ethernet"', 'source=dhcp'],
                      capture_output=True)
        
        return True, "Стандартные настройки сети восстановлены"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def set_dns_manual(primary: str, secondary: str, adapter_name: str) -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    try:
        subprocess.run(
            ['netsh', 'interface', 'ip', 'set', 'dns',
             f'name={adapter_name}', 'source=static', f'addr={primary}'],
            capture_output=True, check=True
        )
        subprocess.run(
            ['netsh', 'interface', 'ip', 'add', 'dns',
             f'name={adapter_name}', f'addr={secondary}', 'index=2'],
            capture_output=True, check=True
        )
        return True, f"DNS установлен для адаптера {adapter_name}"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def get_current_dns() -> Tuple[str, str]:
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'ip', 'show', 'dns'],
            capture_output=True, text=True, encoding='cp866'
        )
        lines = result.stdout.split('\n')
        dns_servers = []
        for line in lines:
            if 'DNS-сервер' in line:
                import re
                ip = re.findall(r'\d+\.\d+\.\d+\.\d+', line)
                if ip:
                    dns_servers.append(ip[0])
        
        if dns_servers:
            return dns_servers[0], dns_servers[1] if len(dns_servers) > 1 else ""
        return "", ""
    except:
        return "", ""
