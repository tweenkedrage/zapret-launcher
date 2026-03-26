import subprocess
import time
from typing import List, Tuple, Optional
import winreg
import re
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
            capture_output=True, text=True, encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        lines = result.stdout.split('\n')
        for line in lines:
            line = line.strip()
            if line and ('connected' in line.lower() or 'подключено' in line.lower()):
                parts = line.split()
                if len(parts) >= 5:
                    name = parts[-1].strip()
                    if name and 'Loopback' not in name and 'lo' not in name.lower():
                        if name not in adapters:
                            adapters.append(name)
                elif len(parts) >= 4:
                    name = parts[-1].strip()
                    if name and 'Loopback' not in name:
                        if name not in adapters:
                            adapters.append(name)
    except Exception as e:
        print(f"Ошибка получения адаптеров: {e}")
    
    if not adapters:
        try:
            result = subprocess.run(
                ['wmic', 'nic', 'where', 'NetEnabled=True', 'get', 'Name'],
                capture_output=True, text=True, encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = result.stdout.split('\n')
            for line in lines[1:]:
                name = line.strip()
                if name and 'Loopback' not in name:
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
    primary_ok, _ = ping_dns_server(primary, timeout=1.0)
    if not primary_ok:
        return False, f"DNS сервер {primary} не отвечает"
    if not is_admin():
        return False, "Требуются права администратора!"
    
    try:
        adapters = list_network_adapters()
        if not adapters:
            return False, "Не найдены активные сетевые адаптеры"
        
        success_count = 0
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
                success_count += 1
            except:
                continue
        
        if success_count == 0:
            return False, "Не удалось установить DNS ни на один адаптер"
        
        return True, f"DNS установлен на {success_count} адаптер(ов)"
        
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def flush_dns_cache() -> Tuple[bool, str]:
    try:
        subprocess.run(['ipconfig', '/flushdns'], capture_output=True, check=True)
        
        try:
            subprocess.run(['dnscmd', '/clearcache'], capture_output=True, check=True)
        except:
            pass
        
        return True, "DNS кеш очищен"
    except Exception as e:
        return False, f"Ошибка очистки DNS: {str(e)}"

def optimize_network_latency() -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    changes = []
    errors = []
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'chimney=disabled'],
                      capture_output=True, check=True)
        changes.append("TCP Chimney отключен")
    except:
        errors.append("Не удалось отключить TCP Chimney")
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'rss=disabled'],
                      capture_output=True, check=True)
        changes.append("RSS отключен")
    except:
        errors.append("Не удалось отключить RSS")
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=normal'],
                      capture_output=True, check=True)
        changes.append("TCP автонастройка установлена в normal")
    except:
        errors.append("Не удалось настроить TCP автонастройку")
    
    try:
        key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        
        winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, 65535)
        changes.append("TCP Window Size увеличен")
        
        winreg.SetValueEx(key, "Tcp1323Opts", 0, winreg.REG_DWORD, 3)
        changes.append("TCP 1323 опции включены")
        
        winreg.CloseKey(key)
    except Exception as e:
        errors.append(f"Ошибка реестра: {str(e)}")
    
    result_msg = "Оптимизация выполнена:\n" + "\n".join(changes)
    if errors:
        result_msg += f"\n\nОшибки:\n" + "\n".join(errors)
    
    return True, result_msg

def restore_network_defaults() -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    changes = []
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=normal'],
                      capture_output=True, check=True)
        changes.append("TCP автонастройка восстановлена (normal)")
    except:
        pass
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'chimney=enabled'],
                      capture_output=True, check=True)
        changes.append("TCP Chimney включен")
    except:
        pass
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'rss=enabled'],
                      capture_output=True, check=True)
        changes.append("RSS включен")
    except:
        pass
    
    try:
        adapters = list_network_adapters()
        for adapter in adapters:
            try:
                subprocess.run(
                    ['netsh', 'interface', 'ip', 'set', 'dns', f'name={adapter}', 'source=dhcp'],
                    capture_output=True, timeout=10
                )
                changes.append(f"DNS восстановлен для {adapter}")
            except:
                continue
    except:
        pass
    
    return True, f"Стандартные настройки восстановлены:\n" + "\n".join(changes[:10])

def set_dns_manual(primary: str, secondary: str, adapter_name: str) -> Tuple[bool, str]:
    if not is_admin():
        return False, "Требуются права администратора!"
    
    try:
        if ' ' in adapter_name:
            adapter_name = f'"{adapter_name}"'
        
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

def get_current_dns() -> dict:
    result_dict = {}
    try:
        adapters = list_network_adapters()
        for adapter in adapters:
            result = subprocess.run(
                ['netsh', 'interface', 'ip', 'show', 'dns', f'name={adapter}'],
                capture_output=True, text=True, encoding='cp866'
            )
            dns_servers = []
            for line in result.stdout.split('\n'):
                if 'DNS сервер' in line:
                    ip = re.findall(r'\d+\.\d+\.\d+\.\d+', line)
                    if ip:
                        dns_servers.append(ip[0])
            
            if dns_servers:
                result_dict[adapter] = {
                    'primary': dns_servers[0],
                    'secondary': dns_servers[1] if len(dns_servers) > 1 else None
                }
        return result_dict
    except:
        return {}
