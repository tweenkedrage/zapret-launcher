# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import subprocess
import socket
import time
import threading
from typing import Optional, Tuple, List, Dict, Any
import urllib.request
import re
from datetime import datetime
import psutil
import sys

class VPNChecker:
    def __init__(self, callback=None):
        self.callback = callback
        self.is_running = False
        self._check_thread = None
        self._stop_event = None
        self._vpn_detected = False
        self._last_check_time = 0
        self._cache_duration = 5
        
        self.test_hosts = [
            ('8.8.8.8', 53),
            ('1.1.1.1', 53),
            ('208.67.222.222', 53),
        ]
        
        self.test_urls = [
            'https://www.google.com',
            'https://www.cloudflare.com',
            'https://www.microsoft.com',
        ]
        
        self.vpn_process_keywords = [
            'openvpn', 'wireguard', 'protonvpn', 'nordvpn', 
            'expressvpn', 'surfshark', 'cyberghost', 'ipvanish',
            'tunnelbear', 'hotspotshield', 'windscribe', 'vyprvpn',
            'privateinternetaccess', 'pia', 'mullvad', 'ivpn',
            'airvpn', 'perfectprivacy', 'zenmate', 'hidester',
            'slickvpn', 'fastestvpn', 'buffered', 'vpn.ac',
            'torguard', 'vpnunlimited', 'vpngate',
            'softether', 'v2ray', 'shadowsocks',
            'wg-quick', 'ovpn', 'vpn.exe', 'vpnclient',
            'forticlient', 'cisco', 'anyconnect', 'pulse secure',
            'globalprotect', 'openconnect', 'wireguard.exe',
            'protonvpn.exe', 'nordvpn.exe', 'expressvpn.exe'
        ]
        
        self.vpn_interface_keywords = [
            'tun', 'tap', 'utun', 'wg', 'vpn', 'openvpn', 'wireguard'
        ]

    def set_callback(self, callback):
        self.callback = callback

    def _notify(self, status: str, message: str = "", data: Dict = None):
        if self.callback:
            try:
                self.callback(status, message, data)
            except Exception as e:
                print(f"Callback error: {e}")

    def check_internet_connection(self, timeout: int = 2) -> Tuple[bool, str]:
        for host, port in self.test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    return True, f"DNS: {host}"
            except Exception:
                continue

        for url in self.test_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if response.getcode() == 200:
                        return True, f"HTTP: {url}"
            except Exception:
                continue

        try:
            result = subprocess.run(
                ['ping', '-n', '1', '8.8.8.8'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=timeout
            )
            if result.returncode == 0:
                return True, "Ping: 8.8.8.8"
        except Exception:
            pass

        return False, "No internet connection"

    def check_vpn_processes(self) -> Tuple[bool, List[str]]:
        detected = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    proc_cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                    
                    skip_processes = ['svchost.exe', 'textinput.exe', 'explorer.exe', 'taskhost.exe', 'dwm.exe']
                    if any(skip in proc_name for skip in skip_processes):
                        continue
                    
                    for keyword in self.vpn_process_keywords:
                        if keyword in proc_name or keyword in proc_cmdline:
                            if len(keyword) > 3:
                                if proc_name not in detected:
                                    detected.append(proc_name)
                                break
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        return len(detected) > 0, detected

    def check_vpn_interfaces(self) -> Tuple[bool, List[str]]:
        detected = []
        
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    current_adapter = ''
                    
                    for line in lines:
                        if 'Адаптер' in line or 'Adapter' in line:
                            current_adapter = line.strip()
                        elif 'PPP' in line or 'TUN' in line or 'TAP' in line:
                            if current_adapter:
                                for keyword in self.vpn_interface_keywords:
                                    if keyword in current_adapter.lower():
                                        detected.append(current_adapter)
                                        break
            else:
                result = subprocess.run(
                    ['ifconfig'],
                    capture_output=True, text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        for keyword in self.vpn_interface_keywords:
                            if keyword in line.lower():
                                detected.append(line.strip())
                                break
        except Exception:
            pass
        
        return len(detected) > 0, detected

    def check_vpn_routes(self) -> bool:
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['route', 'print'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '0.0.0.0' in line and '255.255.255.255' in line:
                            return True
            return False
        except Exception:
            return False

    def check_external_ip(self) -> Optional[str]:
        try:
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://checkip.amazonaws.com'
            ]
            
            for service in services:
                try:
                    req = urllib.request.Request(
                        service,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    with urllib.request.urlopen(req, timeout=2) as response:
                        ip = response.read().decode('utf-8').strip()
                        if ip and self._is_valid_ip(ip):
                            return ip
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _is_valid_ip(self, ip: str) -> bool:
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        return re.match(pattern, ip) is not None

    def check_dns_changes(self) -> Tuple[bool, str]:
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    dns_servers = []
                    
                    for line in lines:
                        if 'DNS-сервер' in line or 'DNS Servers' in line:
                            parts = line.split(':')
                            if len(parts) > 1:
                                dns = parts[1].strip()
                                if dns:
                                    dns_servers.append(dns)
                    
                    standard_dns = ['8.8.8.8', '1.1.1.1', '208.67.222.222', '192.168']
                    for dns in dns_servers:
                        is_standard = False
                        for std in standard_dns:
                            if dns.startswith(std):
                                is_standard = True
                                break
                        if not is_standard and dns != '0.0.0.0':
                            return True, f"DNS changed to: {dns}"
            return False, ""
        except Exception:
            return False, ""

    def full_check(self) -> Dict[str, Any]:
        result = {
            'timestamp': datetime.now().isoformat(),
            'vpn_detected': False,
            'internet_available': False,
            'vpn_processes': [],
            'vpn_interfaces': [],
            'external_ip': None,
            'dns_changed': False,
            'dns_info': '',
            'details': {}
        }
        
        internet_ok, internet_msg = self.check_internet_connection()
        result['internet_available'] = internet_ok
        result['details']['internet'] = internet_msg
        
        external_ip = self.check_external_ip()
        if external_ip:
            result['external_ip'] = external_ip
        
        dns_changed, dns_info = self.check_dns_changes()
        result['dns_changed'] = dns_changed
        result['dns_info'] = dns_info
        
        has_vpn_proc, vpn_procs = self.check_vpn_processes()
        if has_vpn_proc:
            result['vpn_processes'] = vpn_procs
            result['vpn_detected'] = True
        
        has_vpn_iface, vpn_ifaces = self.check_vpn_interfaces()
        if has_vpn_iface:
            result['vpn_interfaces'] = vpn_ifaces
            result['vpn_detected'] = True
        
        if self.check_vpn_routes() and not result['vpn_detected']:
            result['vpn_detected'] = True
            result['details']['routes'] = 'VPN routes detected'
        
        return result

    def start_monitoring(self, interval: int = 10):
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event = threading.Event()
        
        def monitor_loop():
            while not self._stop_event.is_set():
                try:
                    result = self.full_check()
                    self._vpn_detected = result['vpn_detected']
                    self._last_check_time = time.time()
                    
                    self._notify(
                        'vpn_status',
                        'VPN detected' if result['vpn_detected'] else 'No VPN detected',
                        result
                    )
                except Exception as e:
                    self._notify('error', str(e))
                
                self._stop_event.wait(interval)
        
        self._check_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._check_thread.start()

    def stop_monitoring(self):
        self.is_running = False
        if self._stop_event:
            self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=2)
            self._check_thread = None

    def is_vpn_active(self) -> bool:
        if time.time() - self._last_check_time > self._cache_duration:
            result = self.full_check()
            self._vpn_detected = result['vpn_detected']
            self._last_check_time = time.time()
        
        return self._vpn_detected

    def get_status(self) -> Dict[str, Any]:
        if not self._last_check_time:
            result = self.full_check()
            self._vpn_detected = result['vpn_detected']
            self._last_check_time = time.time()
            return result
        
        return {
            'vpn_detected': self._vpn_detected,
            'last_check': self._last_check_time,
            'cached': True
        }

def check_vpn_status(parent, callback=None):
    checker = VPNChecker(callback)
    result = checker.full_check()
    return checker, result

if __name__ == "__main__":
    def on_status(status, message, data):
        if data:
            print(f"Data: {data}")
    
    checker = VPNChecker(on_status)
    result = checker.full_check()
    checker.start_monitoring(interval=5)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        checker.stop_monitoring()
