import subprocess
import time
from typing import List, Tuple
import winreg
import re
import ctypes
from utils.languages import tr
import os
import json
from datetime import datetime

DNS_SERVERS = [
    {"name": "Cloudflare Malware", "primary": "1.1.1.2", "secondary": "1.0.0.2"},
    {"name": "Cloudflare", "primary": "1.1.1.1", "secondary": "1.0.0.1"},
    {"name": "Google", "primary": "8.8.8.8", "secondary": "8.8.4.4"},
    {"name": "OpenDNS", "primary": "208.67.222.222", "secondary": "208.67.220.220"},
    {"name": "Quad9", "primary": "9.9.9.9", "secondary": "149.112.112.112"},
    {"name": "Comss", "primary": "77.88.8.8", "secondary": "77.88.8.1"},
]

_logger = None

def set_logger(app):
    global _logger
    _logger = app

def _log(event_type, message):
    if _logger:
        _logger.log_event(event_type, message)
        
def _cleanup_old_backups(backup_dir=None, max_backups=5):
    if backup_dir is None:
        backup_dir = os.path.join(os.environ['TEMP'], 'zapret_backup')
    
    if not os.path.exists(backup_dir):
        return
    
    try:
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith('registry_backup_')],
            key=lambda x: os.path.getctime(os.path.join(backup_dir, x))
        )
        
        while len(backups) > max_backups:
            old_backup = backups.pop(0)
            old_path = os.path.join(backup_dir, old_backup)
            os.remove(old_path)
            _log("info", f"Removed old backup: {old_backup}")
    except Exception as e:
        _log("error", f"Failed to cleanup old backups: {str(e)}")
        
def _backup_registry_key(key_path, backup_dir=None):
    if backup_dir is None:
        backup_dir = os.path.join(os.environ['TEMP'], 'zapret_backup')
    
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f"registry_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        
        backup_data = {}
        i = 0
        while True:
            try:
                name, value, type = winreg.EnumValue(key, i)
                backup_data[name] = {'value': value, 'type': type}
                i += 1
            except OSError:
                break
        
        winreg.CloseKey(key)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        _log("info", f"Registry backup created: {backup_file}")
        return backup_file
    except Exception as e:
        _log("error", f"Failed to backup registry: {str(e)}")
        return None

def _restore_registry_from_backup(backup_file, key_path):
    if not backup_file or not os.path.exists(backup_file):
        return False
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        
        for name, data in backup_data.items():
            try:
                winreg.SetValueEx(key, name, 0, data['type'], data['value'])
            except:
                pass
        
        winreg.CloseKey(key)
        _log("info", f"Registry restored from backup: {backup_file}")
        return True
    except Exception as e:
        _log("error", f"Failed to restore registry: {str(e)}")
        return False

def list_network_adapters() -> List[str]:
    _log("info", "Getting list of network adapters...")
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
    except Exception:
        pass
    
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
    
    _log("success", f"Found {len(adapters)} network adapters")
    return adapters

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ping_dns_server(dns_ip: str, timeout: float = 2.0) -> Tuple[bool, float]:
    _log("info", f"Pinging DNS server: {dns_ip}")
    try:
        start = time.time()
        subprocess.run(['ping', '-n', '1', '-w', str(int(timeout * 1000)), dns_ip],
                      capture_output=True, timeout=timeout)
        end = time.time()
        latency = (end - start) * 1000
        _log("success", f"DNS {dns_ip} responded in {latency:.1f}ms")
        return True, latency
    except:
        _log("error", f"DNS {dns_ip} no response")
        return False, float('inf')

def find_best_dns() -> Tuple[str, str, float, str]:
    _log("info", "Searching for best DNS server...")
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
        _log("error", "No responding DNS servers found")
        return "8.8.8.8", "8.8.4.4", 9999, "Google (fallback)"
    
    results.sort(key=lambda x: x["latency"])
    best = results[0]
    _log("success", f"Best DNS found: {best['name']} (latency: {best['latency']:.1f} ms)")
    return best["primary"], best["secondary"], best["latency"], best["name"]

def set_dns_windows(primary: str, secondary: str) -> Tuple[bool, str]:
    _log("info", f"Setting DNS: {primary}, {secondary}")
    
    primary_ok, _ = ping_dns_server(primary, timeout=1.0)
    if not primary_ok:
        _log("error", f"DNS server not responding: {primary}")
        return False, f"{tr('dns_server_not_responding')} {primary}"
    
    if not is_admin():
        _log("error", "Administrator rights required")
        return False, tr('error_admin_required')
    
    try:
        adapters = list_network_adapters()
        if not adapters:
            _log("error", "No active network adapters found")
            return False, tr('dns_no_adapters')
        
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
                _log("info", f"DNS set on adapter: {adapter}")
            except:
                _log("error", f"Failed to set DNS on adapter: {adapter}")
                continue
        
        if success_count == 0:
            _log("error", "Failed to set DNS on any adapter")
            return False, tr('dns_set_failed')
        
        _log("success", f"DNS set on {success_count} adapters")
        return True, f"{tr('dns_set_success')} {success_count} {tr('dns_adapters_count')}"
    except Exception as e:
        _log("error", f"Failed to set DNS: {str(e)}")
        return False, f"{tr('error_occurred')}: {str(e)}"

def flush_dns_cache() -> Tuple[bool, str]:
    _log("info", "Flushing DNS cache...")
    try:
        subprocess.run(['ipconfig', '/flushdns'], capture_output=True, check=True)
        
        try:
            subprocess.run(['dnscmd', '/clearcache'], capture_output=True, check=True)
        except:
            pass
        
        _log("success", "DNS cache flushed successfully")
        return True, tr('dns_flush_success')
    except Exception as e:
        _log("error", f"Failed to flush DNS cache: {str(e)}")
        return False, f"{tr('error_occurred')}: {str(e)}"

def optimize_network_latency() -> Tuple[bool, str]:
    _log("info", "Starting network optimization...")
    
    if not is_admin():
        _log("error", "Administrator rights required for optimization")
        return False, tr('error_admin_required')
    
    key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
    backup_file = _backup_registry_key(key_path)
    
    changes = []
    errors = []
    
    try:
        result = subprocess.run(
            ['netsh', 'int', 'tcp', 'set', 'global', 'chimney=disabled'],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        changes.append(tr('dns_chimney_disabled'))
        _log("info", "TCP Chimney disabled")
    except subprocess.CalledProcessError as e:
        errors.append(f"{tr('dns_chimney_error')}: {e.stderr.strip() if e.stderr else 'Unknown error'}")
        _log("error", f"Failed to disable TCP Chimney: {e}")
    except Exception as e:
        errors.append(f"{tr('dns_chimney_error')}: {str(e)}")
        _log("error", f"Failed to disable TCP Chimney: {str(e)}")
    
    try:
        result = subprocess.run(
            ['netsh', 'int', 'tcp', 'set', 'global', 'rss=disabled'],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        changes.append(tr('dns_rss_disabled'))
        _log("info", "RSS disabled")
    except subprocess.CalledProcessError as e:
        errors.append(f"{tr('dns_rss_error')}: {e.stderr.strip() if e.stderr else 'Unknown error'}")
        _log("error", f"Failed to disable RSS: {e}")
    except Exception as e:
        errors.append(f"{tr('dns_rss_error')}: {str(e)}")
        _log("error", f"Failed to disable RSS: {str(e)}")
    
    try:
        result = subprocess.run(
            ['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=normal'],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        changes.append(tr('dns_autotuning_set'))
        _log("info", "TCP autotuning set to normal")
    except subprocess.CalledProcessError as e:
        errors.append(f"{tr('dns_autotuning_error')}: {e.stderr.strip() if e.stderr else 'Unknown error'}")
        _log("error", f"Failed to set TCP autotuning: {e}")
    except Exception as e:
        errors.append(f"{tr('dns_autotuning_error')}: {str(e)}")
        _log("error", f"Failed to set TCP autotuning: {str(e)}")
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        
        old_values = {}
        try:
            old_tcp_window, _ = winreg.QueryValueEx(key, "TcpWindowSize")
            old_values['TcpWindowSize'] = old_tcp_window
        except:
            pass
        
        try:
            old_tcp1323, _ = winreg.QueryValueEx(key, "Tcp1323Opts")
            old_values['Tcp1323Opts'] = old_tcp1323
        except:
            pass
        
        winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, 65535)
        changes.append(f"{tr('dns_window_size_increased')} (from {old_values.get('TcpWindowSize', 'default')} to 65535)")
        _log("info", f"TCP Window Size increased to 65535 (was: {old_values.get('TcpWindowSize', 'default')})")
        
        winreg.SetValueEx(key, "Tcp1323Opts", 0, winreg.REG_DWORD, 3)
        changes.append(f"{tr('dns_1323_enabled')} (set to 3)")
        _log("info", f"TCP 1323 options enabled (was: {old_values.get('Tcp1323Opts', 'default')})")
        
        winreg.CloseKey(key)
        
    except PermissionError:
        errors.append(f"{tr('dns_registry_error')}: Access denied to registry")
        _log("error", "Access denied to registry key")
    except Exception as e:
        errors.append(f"{tr('dns_registry_error')}: {str(e)}")
        _log("error", f"Registry error: {str(e)}")
    
    try:
        key_path_nagle = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path_nagle, 0, winreg.KEY_SET_VALUE)
        
        i = 0
        nagle_changes = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey_path = f"{key_path_nagle}\\{subkey_name}"
                subkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path, 0, winreg.KEY_SET_VALUE)
                
                try:
                    winreg.SetValueEx(subkey, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
                    nagle_changes += 1
                except:
                    pass
                
                try:
                    winreg.SetValueEx(subkey, "TCPNoDelay", 0, winreg.REG_DWORD, 1)
                    nagle_changes += 1
                except:
                    pass
                
                winreg.CloseKey(subkey)
                i += 1
            except OSError:
                break
        
        winreg.CloseKey(key)
        
        if nagle_changes > 0:
            changes.append(f"TCP optimization applied to {nagle_changes} interfaces")
            _log("info", f"TCP optimization (Nagle's algorithm) applied to {nagle_changes} interfaces")
            
    except Exception as e:
        _log("warning", f"Could not apply Nagle optimization: {str(e)}")
    
    result_msg = f"{tr('dns_optimize_complete')}:\n" + "\n".join(changes)
    if errors:
        result_msg += f"\n\n{tr('dns_errors')}:\n" + "\n".join(errors)
    
    if backup_file:
        result_msg += f"\n\nRegistry backup saved to:\n{backup_file}"
    
    _cleanup_old_backups()
    
    if errors:
        _log("warning", f"Network optimization completed with {len(errors)} errors: {len(changes)} changes applied")
    else:
        _log("success", f"Network optimization completed successfully: {len(changes)} changes applied")
    
    return True, result_msg

def restore_network_defaults() -> Tuple[bool, str]:
    _log("info", "Restoring network defaults...")
    
    if not is_admin():
        _log("error", "Administrator rights required")
        return False, tr('error_admin_required')
    
    changes = []
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'autotuninglevel=normal'],
                      capture_output=True, check=True)
        changes.append(tr('dns_autotuning_restored'))
        _log("info", "TCP autotuning restored to normal")
    except:
        _log("error", "Failed to restore TCP autotuning")
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'chimney=enabled'],
                      capture_output=True, check=True)
        changes.append(tr('dns_chimney_enabled'))
        _log("info", "TCP Chimney enabled")
    except:
        _log("error", "Failed to enable TCP Chimney")
    
    try:
        subprocess.run(['netsh', 'int', 'tcp', 'set', 'global', 'rss=enabled'],
                      capture_output=True, check=True)
        changes.append(tr('dns_rss_enabled'))
        _log("info", "RSS enabled")
    except:
        _log("error", "Failed to enable RSS")
    
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'ip', 'show', 'interfaces'],
            capture_output=True, text=True, encoding='cp866',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        all_adapters = []
        lines = result.stdout.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('---'):
                parts = line.split()
                if len(parts) >= 4:
                    if parts[0].replace('-', '').isdigit() and 'Loopback' not in line:
                        adapter_name = ' '.join(parts[3:]) if len(parts) > 4 else parts[-1]
                        if adapter_name and adapter_name not in all_adapters:
                            all_adapters.append(adapter_name)
        
        if not all_adapters:
            all_adapters = list_network_adapters()
        
        success_count = 0
        for adapter in all_adapters:
            try:
                subprocess.run(
                    ['netsh', 'interface', 'ip', 'delete', 'dns', f'name={adapter}', 'all'],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ['netsh', 'interface', 'ip', 'set', 'dns', f'name={adapter}', 'source=dhcp'],
                    capture_output=True, timeout=10
                )
                changes.append(f"{tr('dns_restored_for')} {adapter}")
                _log("info", f"DNS restored to DHCP for adapter: {adapter}")
                success_count += 1
            except:
                _log("error", f"Failed to restore DNS for adapter: {adapter}")
                continue
        
        if success_count == 0:
            _log("error", "No adapters were restored")
        
    except Exception as e:
        _log("error", f"Failed to restore DNS: {str(e)}")
    
    if success_count > 0:
        changes.insert(0, f"DNS restored on {success_count} adapters")
    
    _log("success", f"Network defaults restored: {len(changes)} changes")
    return True, f"{tr('dns_restore_success')}:\n" + "\n".join(changes[:15])

def set_dns_manual(primary: str, secondary: str, adapter_name: str) -> Tuple[bool, str]:
    _log("info", f"Setting manual DNS on adapter: {adapter_name}")
    
    if not is_admin():
        _log("error", "Administrator rights required")
        return False, tr('error_admin_required')
    
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
        _log("success", f"DNS set on adapter: {adapter_name}")
        return True, f"{tr('dns_set_for_adapter')} {adapter_name}"
    except Exception as e:
        _log("error", f"Failed to set DNS on {adapter_name}: {str(e)}")
        return False, f"{tr('error_occurred')}: {str(e)}"

def get_current_dns() -> dict:
    _log("info", "Getting current DNS configuration...")
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
                _log("info", f"Adapter {adapter}: DNS {dns_servers[0]}")
        
        _log("success", f"Found DNS config for {len(result_dict)} adapters")
        return result_dict
    except Exception as e:
        _log("error", f"Failed to get DNS config: {str(e)}")
        return {}
