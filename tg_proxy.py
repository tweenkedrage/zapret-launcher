from __future__ import annotations
import argparse
import asyncio
import base64
import os
import socket as _socket
import ssl
import struct
import sys
import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DEFAULT_PORT = 1080

TG_MODE_FAST = "fast"
TG_MODE_STABLE = "stable"
CURRENT_MODE = TG_MODE_STABLE

_TCP_KEEPIDLE = 30
_TCP_KEEPINTVL = 5
_TCP_KEEPCNT = 3

if sys.version_info < (3, 11):
    class _TimeoutManager:
        def __init__(self, timeout):
            self.timeout = timeout
            self._task = None
            self._cancel_handle = None
            
        async def __aenter__(self):
            if self.timeout is None:
                return self
            self._task = asyncio.current_task()
            self._cancel_handle = asyncio.get_running_loop().call_later(
                self.timeout, self._cancel_task
            )
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._cancel_handle:
                self._cancel_handle.cancel()
            if exc_type is asyncio.CancelledError and self.timeout is not None:
                raise asyncio.TimeoutError()
            
        def _cancel_task(self):
            if self._task and not self._task.done():
                self._task.cancel()
    
    def timeout(delay):
        return _TimeoutManager(delay)
    
    asyncio.timeout = timeout

TG_CONFIGS = {
    TG_MODE_FAST: {
        "ws_pool_size": 48,
        "ws_pool_max_age": 180.0,
        "max_connections": 400,
        "heartbeat_interval": 15.0,
        "connection_timeout": 120.0,
        "recv_buf": 2097152,
        "send_buf": 2097152,
        "max_reconnect_attempts": 5,
        "reconnect_delay": 0.5,
        "ws_keepalive_interval": 20.0,
        "retry_delay": 0.5,
        "max_retries": 5,
        "dc_fail_cooldown": 15.0,
        "socket_buffer_multiplier": 8,
    },
    TG_MODE_STABLE: {
        "ws_pool_size": 32,
        "ws_pool_max_age": 300.0,
        "max_connections": 250,
        "heartbeat_interval": 25.0,
        "connection_timeout": 150.0,
        "recv_buf": 1048576,
        "send_buf": 1048576,
        "max_reconnect_attempts": 6,
        "reconnect_delay": 1.0,
        "ws_keepalive_interval": 30.0,
        "retry_delay": 0.8,
        "max_retries": 6,
        "dc_fail_cooldown": 30.0,
        "socket_buffer_multiplier": 6,
    }
}

def set_tg_mode(mode: str) -> bool:
    global CURRENT_MODE, _WS_POOL_SIZE, _WS_POOL_MAX_AGE, _MAX_CONNECTIONS
    global _HEARTBEAT_INTERVAL, _CONNECTION_TIMEOUT, _RECV_BUF, _SEND_BUF
    global _MAX_RECONNECT_ATTEMPTS, _RECONNECT_DELAY, _WS_KEEPALIVE_INTERVAL
    global _RETRY_DELAY, _MAX_RETRIES, _DC_FAIL_COOLDOWN, _connection_semaphore
    
    if mode not in TG_CONFIGS:
        return False
    
    CURRENT_MODE = mode
    config = TG_CONFIGS[mode]
    
    _WS_POOL_SIZE = config["ws_pool_size"]
    _WS_POOL_MAX_AGE = config["ws_pool_max_age"]
    _MAX_CONNECTIONS = config["max_connections"]
    _HEARTBEAT_INTERVAL = config["heartbeat_interval"]
    _CONNECTION_TIMEOUT = config["connection_timeout"]
    _RECV_BUF = config["recv_buf"]
    _SEND_BUF = config["send_buf"]
    _MAX_RECONNECT_ATTEMPTS = config["max_reconnect_attempts"]
    _RECONNECT_DELAY = config["reconnect_delay"]
    _WS_KEEPALIVE_INTERVAL = config["ws_keepalive_interval"]
    _RETRY_DELAY = config["retry_delay"]
    _MAX_RETRIES = config["max_retries"]
    _DC_FAIL_COOLDOWN = config["dc_fail_cooldown"]
    
    _connection_semaphore = asyncio.Semaphore(_MAX_CONNECTIONS)
    return True

def get_current_mode() -> str:
    return CURRENT_MODE

def get_mode_config() -> dict:
    return TG_CONFIGS.get(CURRENT_MODE, TG_CONFIGS[TG_MODE_STABLE])

_TCP_NODELAY = True
_RECV_BUF = 1048576
_SEND_BUF = 1048576
_WS_POOL_SIZE = 32
_WS_POOL_MAX_AGE = 300.0
_MAX_MSG_SIZE = 10 * 1024 * 1024
_HEARTBEAT_INTERVAL = 25.0
_CONNECTION_TIMEOUT = 150.0
_MAX_RETRIES = 6
_RETRY_DELAY = 0.8
_DC_FAIL_COOLDOWN = 30.0
_MAX_CONNECTIONS = 250
_SOCKET_BUFFER_MULTIPLIER = 6
_WS_KEEPALIVE_INTERVAL = 30.0
_MAX_RECONNECT_ATTEMPTS = 6
_RECONNECT_DELAY = 1.0

_connection_semaphore = asyncio.Semaphore(_MAX_CONNECTIONS)
_telegram_ip_cache: Dict[str, bool] = {}
_CACHE_MAX_SIZE = 2000

_TG_RANGES = [
    (struct.unpack('!I', _socket.inet_aton('185.76.151.0'))[0],
     struct.unpack('!I', _socket.inet_aton('185.76.151.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('149.154.160.0'))[0],
     struct.unpack('!I', _socket.inet_aton('149.154.175.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('91.105.192.0'))[0],
     struct.unpack('!I', _socket.inet_aton('91.105.193.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('91.108.0.0'))[0],
     struct.unpack('!I', _socket.inet_aton('91.108.255.255'))[0]),
]

_IP_TO_DC: Dict[str, Tuple[int, bool]] = {
    '149.154.175.50': (1, False), '149.154.175.51': (1, False),
    '149.154.175.53': (1, False), '149.154.175.54': (1, False),
    '149.154.175.52': (1, True),
    '149.154.167.41': (2, False), '149.154.167.50': (2, False),
    '149.154.167.51': (2, False), '149.154.167.220': (2, False),
    'web.telegram.org': (2, False),
    '95.161.76.100':  (2, False),
    '149.154.167.151': (2, True), '149.154.167.222': (2, True),
    '149.154.167.223': (2, True), '149.154.162.123': (2, True),
    '149.154.175.100': (3, False), '149.154.175.101': (3, False),
    '149.154.175.102': (3, True),
    '149.154.167.91': (4, False), '149.154.167.92': (4, False),
    '149.154.164.250': (4, True), '149.154.166.120': (4, True),
    '149.154.166.121': (4, True), '149.154.167.118': (4, True),
    '149.154.165.111': (4, True),
    '91.108.56.100': (5, False), '91.108.56.101': (5, False),
    '91.108.56.116': (5, False), '91.108.56.126': (5, False),
    '149.154.171.5':  (5, False),
    '91.108.56.102': (5, True), '91.108.56.128': (5, True),
    '91.108.56.151': (5, True),
}

FULL_DC_OPT = {
    1: ['149.154.175.50', '149.154.175.52', '149.154.175.53', '149.154.175.51', '149.154.175.54'],
    2: ['149.154.167.220', '149.154.167.151', '149.154.167.51', '149.154.167.41', '149.154.167.50', '95.161.76.100'],
    3: ['149.154.175.100', '149.154.175.102', '149.154.175.101'],
    4: ['149.154.167.91', '149.154.167.118', '149.154.167.92', '149.154.164.250', '149.154.166.120', '149.154.166.121'],
    5: ['91.108.56.100', '91.108.56.102', '91.108.56.126', '91.108.56.101', '91.108.56.116', '149.154.171.5'],
}

_TELEGRAM_WEB_DOMAINS = [
    'web.telegram.org',
    'webk.telegram.org',
    'web.telegram.org/z',
    'web.telegram.org/k',
    'web.telegram.org/a',
    'pl.web.telegram.org',
    'pl2.web.telegram.org',
]

_TELEGRAM_WEB_PATHS = [
    '/apiws',
    '/apiwsp',
    '/apiwss',
    '/apiws/v1',
    '/apiws/v2',
]

_MEDIA_DOMAINS = [
    't.me',
    'tdesktop.com',
    'telegram.org',
    'telegram.dog',
    'telegra.ph',
    'cdn-telegram.org',
    'cdn4.telegram-cdn.org',
    'cdn5.telegram-cdn.org',
    'cdn6.telegram-cdn.org',
    'cdn7.telegram-cdn.org',
    'cdn8.telegram-cdn.org',
    'cdn9.telegram-cdn.org',
    'media.telegram.org',
    'video.telegram.org',
    'photos.telegram.org',
    'docs.telegram.org',
    'kws1.web.telegram.org',
    'kws2.web.telegram.org',
    'kws3.web.telegram.org',
    'kws4.web.telegram.org',
    'kws5.web.telegram.org',
    'plweb1.telegram.org',
    'plweb2.telegram.org',
    'plweb3.telegram.org',
    'plweb4.telegram.org',
    'plweb5.telegram.org',
]

_IP_TO_DC.update({
    '149.154.175.52': (1, True),
    '149.154.167.151': (2, True),
    '149.154.175.102': (3, True),
    '149.154.167.118': (4, True),
    '91.108.56.102': (5, True),
    '149.154.167.222': (2, True),
    '149.154.167.223': (2, True),
    '149.154.164.250': (4, True),
    '149.154.166.120': (4, True),
    '149.154.166.121': (4, True),
    '149.154.165.111': (4, True),
    '91.108.56.128': (5, True),
    '91.108.56.151': (5, True),
})

_dc_opt: Dict[int, Optional[str]] = {}
_ws_blacklist: Set[Tuple[int, bool]] = set()
_dc_fail_until: Dict[Tuple[int, bool], float] = {}

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
_ssl_ctx.set_ciphers('DEFAULT@SECLEVEL=1')
_ssl_ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

_dns_cache: Dict[str, Tuple[str, float]] = {}
_dns_cache_lock = asyncio.Lock()

async def _resolve_hostname(hostname: str) -> Optional[str]:
    now = time.time()
    
    async with _dns_cache_lock:
        if hostname in _dns_cache:
            ip, expires = _dns_cache[hostname]
            if now < expires:
                return ip
    
    try:
        loop = asyncio.get_running_loop()
        ip = await loop.getaddrinfo(hostname, 443, 
                                   family=_socket.AF_INET,
                                   type=_socket.SOCK_STREAM)
        if ip:
            ip_addr = ip[0][4][0]
            async with _dns_cache_lock:
                _dns_cache[hostname] = (ip_addr, now + 300)
            return ip_addr
    except Exception:
        pass
    return None

def is_port_available(host: str, port: int) -> bool:
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex((host, port))
        return result != 0
    finally:
        sock.close()

def _is_telegram_web_host(host: str) -> bool:
    if not host:
        return False
    host_lower = host.lower()
    return any(domain in host_lower for domain in _TELEGRAM_WEB_DOMAINS)

def _set_sock_opts(transport):
    sock = transport.get_extra_info('socket')
    if sock is None:
        return
    if _TCP_NODELAY:
        try:
            sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass
    try:
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_RCVBUF, _RECV_BUF)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_SNDBUF, _SEND_BUF)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_KEEPALIVE, 1)
        sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_KEEPIDLE, _TCP_KEEPIDLE)
        sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_KEEPINTVL, _TCP_KEEPINTVL)
        sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_KEEPCNT, _TCP_KEEPCNT)
    except (OSError, AttributeError):
        pass

class WsHandshakeError(Exception):
    def __init__(self, status_code: int, status_line: str,
                 headers: dict = None, location: str = None):
        self.status_code = status_code
        self.status_line = status_line
        self.headers = headers or {}
        self.location = location
        super().__init__(f"HTTP {status_code}: {status_line}")

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

def _xor_mask(data: bytes, mask: bytes) -> bytes:
    if not data:
        return data
    n = len(data)
    mask_rep = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, 'big') ^ int.from_bytes(mask_rep, 'big')).to_bytes(n, 'big')

class RawWebSocket:
    OP_CONTINUATION = 0x0
    OP_TEXT = 0x1
    OP_BINARY = 0x2
    OP_CLOSE = 0x8
    OP_PING = 0x9
    OP_PONG = 0xA

    __slots__ = ('reader', 'writer', '_closed', '_last_heartbeat', '_heartbeat_task', 
                 '_keepalive_task', '_last_activity', '_reconnect_attempts',
                 '_send_buffer', '_send_lock', '_flush_task')

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self._closed = False
        self._last_heartbeat = time.monotonic()
        self._last_activity = time.monotonic()
        self._heartbeat_task = None
        self._keepalive_task = None
        self._reconnect_attempts = 0
        self._send_buffer = bytearray()
        self._send_lock = asyncio.Lock()
        self._flush_task = None

    async def _flush_buffer(self):
        while not self._closed:
            await asyncio.sleep(0.1)
            async with self._send_lock:
                if self._send_buffer:
                    data = bytes(self._send_buffer)
                    self._send_buffer.clear()
                    try:
                        self.writer.write(data)
                        await self.writer.drain()
                    except Exception:
                        self._closed = True
                        break

    async def _heartbeat(self):
        while not self._closed:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._closed:
                    break
                
                now = time.monotonic()
                if now - self._last_activity > _HEARTBEAT_INTERVAL * 2:
                    await self.ping()
                    self._last_heartbeat = now
                
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _keepalive(self):
        while not self._closed:
            try:
                await asyncio.sleep(_WS_KEEPALIVE_INTERVAL)
                if self._closed:
                    break
                
                now = time.monotonic()
                if now - self._last_heartbeat > _HEARTBEAT_INTERVAL * 3:
                    await self.close()
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def ping(self):
        if self._closed:
            return
        try:
            frame = self._build_frame(self.OP_PING, b'', mask=True)
            self.writer.write(frame)
            await self.writer.drain()
        except Exception:
            pass

    @staticmethod
    async def connect(ip: str, domain: str, path: str = '/apiws',
                    timeout: float = 15.0, is_web: bool = False) -> 'RawWebSocket':
        if 'cdn' in domain or 'media' in domain:
            timeout = 45.0
            media_paths = ['/apiws', '/apiwss', '/apiws/v2', '/']
            for media_path in media_paths:
                try:
                    return await RawWebSocket._connect_attempt(ip, domain, media_path, timeout, is_web)
                except Exception:
                    continue
            raise ConnectionError("All media paths failed")
        else:
            return await RawWebSocket._connect_attempt(ip, domain, path, timeout, is_web)

    @staticmethod
    async def _connect_attempt(ip: str, domain: str, path: str, timeout: float, is_web: bool) -> 'RawWebSocket':
        last_error = None
        
        for attempt in range(_MAX_RECONNECT_ATTEMPTS):
            reader = writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, 443, ssl=_ssl_ctx,
                                            server_hostname=domain,
                                            limit=_RECV_BUF),
                    timeout=min(timeout, 10))
                _set_sock_opts(writer.transport)

                ws_key = base64.b64encode(os.urandom(16)).decode()
                
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                origin = 'https://web.telegram.org'
                
                req = (
                    f'GET {path} HTTP/1.1\r\n'
                    f'Host: {domain}\r\n'
                    f'Upgrade: websocket\r\n'
                    f'Connection: Upgrade\r\n'
                    f'Sec-WebSocket-Key: {ws_key}\r\n'
                    f'Sec-WebSocket-Version: 13\r\n'
                    f'Sec-WebSocket-Protocol: binary\r\n'
                    f'Origin: {origin}\r\n'
                    f'User-Agent: {user_agent}\r\n'
                    f'\r\n'
                ).encode()
                writer.write(req)
                await writer.drain()

                response_lines: list[str] = []
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=timeout)
                    if line in (b'\r\n', b'\n', b''):
                        break
                    response_lines.append(line.decode('utf-8', errors='replace').strip())

                if not response_lines:
                    raise WsHandshakeError(0, 'empty response')

                first_line = response_lines[0]
                parts = first_line.split(' ', 2)
                try:
                    status_code = int(parts[1]) if len(parts) >= 2 else 0
                except ValueError:
                    status_code = 0

                if status_code == 101:
                    ws = RawWebSocket(reader, writer)
                    ws._heartbeat_task = asyncio.create_task(ws._heartbeat())
                    ws._keepalive_task = asyncio.create_task(ws._keepalive())
                    ws._flush_task = asyncio.create_task(ws._flush_buffer())
                    return ws

                headers: dict[str, str] = {}
                for hl in response_lines[1:]:
                    if ':' in hl:
                        k, v = hl.split(':', 1)
                        headers[k.strip().lower()] = v.strip()

                raise WsHandshakeError(status_code, first_line, headers,
                                        location=headers.get('location'))
                                            
            except Exception as e:
                last_error = e
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except:
                        pass
                
                if attempt < _MAX_RECONNECT_ATTEMPTS - 1:
                    await asyncio.sleep(_RECONNECT_DELAY)
                    continue
                    
        raise last_error or ConnectionError("Failed to connect after retries")

    async def send(self, data: bytes):
        if self._closed:
            raise ConnectionError("WebSocket closed")
        try:
            frame = self._build_frame(self.OP_BINARY, data, mask=True)
            async with self._send_lock:
                self._send_buffer.extend(frame)
                if len(self._send_buffer) > _SEND_BUF // 2:
                    to_send = bytes(self._send_buffer)
                    self._send_buffer.clear()
                    self.writer.write(to_send)
                    await self.writer.drain()
            self._last_activity = time.monotonic()
        except Exception:
            self._closed = True
            raise

    async def send_batch(self, parts: List[bytes]):
        if self._closed:
            raise ConnectionError("WebSocket closed")
        
        if len(parts) == 1:
            await self.send(parts[0])
            return
        
        async with self._send_lock:
            for part in parts:
                frame = self._build_frame(self.OP_BINARY, part, mask=True)
                self._send_buffer.extend(frame)
            
            if len(self._send_buffer) > _SEND_BUF // 2:
                data = bytes(self._send_buffer)
                self._send_buffer.clear()
                self.writer.write(data)
                await self.writer.drain()
        
        self._last_activity = time.monotonic()

    async def recv(self) -> Optional[bytes]:
        while not self._closed:
            try:
                async with asyncio.timeout(30.0):
                    opcode, payload = await self._read_frame()
                self._last_activity = time.monotonic()
                self._last_heartbeat = time.monotonic()
            except asyncio.TimeoutError:
                continue
            except ConnectionError:
                self._closed = True
                return None
                
            if opcode == self.OP_CLOSE:
                self._closed = True
                try:
                    reply = self._build_frame(self.OP_CLOSE, payload[:2] if payload else b'', mask=True)
                    self.writer.write(reply)
                    await self.writer.drain()
                except Exception:
                    pass
                return None

            if opcode == self.OP_PING:
                try:
                    pong = self._build_frame(self.OP_PONG, payload, mask=True)
                    self.writer.write(pong)
                    await self.writer.drain()
                except Exception:
                    pass
                continue

            if opcode == self.OP_PONG:
                continue

            if opcode in (self.OP_TEXT, self.OP_BINARY):
                return payload
        return None

    async def close(self):
        if self._closed:
            return
        self._closed = True
        
        for task in [self._heartbeat_task, self._keepalive_task, self._flush_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except:
                    pass
        
        try:
            close_frame = self._build_frame(self.OP_CLOSE, b'', mask=True)
            self.writer.write(close_frame)
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass
        
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass

    @staticmethod
    def _build_frame(opcode: int, data: bytes, mask: bool = False) -> bytes:
        header = bytearray()
        header.append(0x80 | opcode)
        length = len(data)
        mask_bit = 0x80 if mask else 0x00

        if length < 126:
            header.append(mask_bit | length)
        elif length < 65536:
            header.append(mask_bit | 126)
            header.extend(struct.pack('>H', length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack('>Q', length))

        if mask:
            mask_key = os.urandom(4)
            header.extend(mask_key)
            return bytes(header) + _xor_mask(data, mask_key)
        return bytes(header) + data

    async def _read_frame(self) -> Tuple[int, bytes]:
        try:
            hdr = await self.reader.readexactly(2)
        except asyncio.IncompleteReadError as e:
            raise ConnectionError("Connection closed") from e
        
        opcode = hdr[0] & 0x0F
        is_masked = bool(hdr[1] & 0x80)
        length = hdr[1] & 0x7F

        if length == 126:
            length = struct.unpack('>H', await self.reader.readexactly(2))[0]
        elif length == 127:
            length = struct.unpack('>Q', await self.reader.readexactly(8))[0]

        if is_masked:
            mask_key = await self.reader.readexactly(4)
            payload = await self.reader.readexactly(length)
            return opcode, _xor_mask(payload, mask_key)
        else:
            payload = await self.reader.readexactly(length)
            return opcode, payload

def _human_bytes(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def _is_telegram_ip(ip: str) -> bool:
    if ip in _telegram_ip_cache:
        return _telegram_ip_cache[ip]
    
    try:
        n = struct.unpack('!I', _socket.inet_aton(ip))[0]
        result = any(lo <= n <= hi for lo, hi in _TG_RANGES)
        
        if len(_telegram_ip_cache) >= _CACHE_MAX_SIZE:
            _telegram_ip_cache.pop(next(iter(_telegram_ip_cache)))
        _telegram_ip_cache[ip] = result
        return result
    except OSError:
        return False

def _is_http_transport(data: bytes) -> bool:
    if len(data) < 4:
        return False
    if data[0:4] == b'POST' or data[0:3] == b'GET' or data[0:4] == b'HEAD':
        if b'Upgrade: websocket' in data or b'Upgrade: WebSocket' in data:
            return False
        if b'web.telegram.org' in data or b'webk.telegram.org' in data:
            return False
        return True
    return False

def _dc_from_init(data: bytes) -> Tuple[Optional[int], bool]:
    try:
        key = bytes(data[8:40])
        iv = bytes(data[40:56])
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        keystream = encryptor.update(b'\x00' * 64) + encryptor.finalize()
        plain = bytes(a ^ b for a, b in zip(data[56:64], keystream[56:64]))
        proto = struct.unpack('<I', plain[0:4])[0]
        dc_raw = struct.unpack('<h', plain[4:6])[0]
        if proto in (0xEFEFEFEF, 0xEEEEEEEE, 0xDDDDDDDD):
            dc = abs(dc_raw)
            if 1 <= dc <= 5:
                return dc, (dc_raw < 0)
    except Exception:
        pass
    return None, False

def _patch_init_dc(data: bytes, dc: int) -> bytes:
    if len(data) < 64:
        return data

    new_dc = struct.pack('<h', dc)
    try:
        key_raw = bytes(data[8:40])
        iv = bytes(data[40:56])
        cipher = Cipher(algorithms.AES(key_raw), modes.CTR(iv))
        enc = cipher.encryptor()
        ks = enc.update(b'\x00' * 64) + enc.finalize()
        patched = bytearray(data[:64])
        patched[60] = ks[60] ^ new_dc[0]
        patched[61] = ks[61] ^ new_dc[1]
        if len(data) > 64:
            return bytes(patched) + data[64:]
        return bytes(patched)
    except Exception:
        return data

class _MsgSplitter:
    __slots__ = ('_dec', '_buffer')
    
    def __init__(self, init_data: bytes):
        key_raw = bytes(init_data[8:40])
        iv = bytes(init_data[40:56])
        cipher = Cipher(algorithms.AES(key_raw), modes.CTR(iv))
        self._dec = cipher.encryptor()
        self._dec.update(b'\x00' * 64)
        self._buffer = b''

    def split(self, chunk: bytes) -> List[bytes]:
        self._buffer += chunk
        plain = self._dec.update(self._buffer)
        self._buffer = b''
        
        boundaries = []
        pos = 0
        plain_len = len(plain)
        while pos < plain_len:
            first = plain[pos]
            if first == 0x7f:
                if pos + 4 > plain_len:
                    self._buffer = chunk[pos:]
                    break
                msg_len = (struct.unpack_from('<I', plain, pos + 1)[0] & 0xFFFFFF) * 4
                if msg_len > _MAX_MSG_SIZE:
                    msg_len = _MAX_MSG_SIZE
                pos += 4
            else:
                msg_len = first * 4
                pos += 1
            if msg_len == 0 or pos + msg_len > plain_len:
                if pos < plain_len:
                    self._buffer = chunk[pos:]
                break
            pos += msg_len
            boundaries.append(pos)
        
        if len(boundaries) <= 1:
            return [chunk]
        
        parts = []
        prev = 0
        for b in boundaries:
            parts.append(chunk[prev:b])
            prev = b
        if prev < len(chunk):
            parts.append(chunk[prev:])
        return parts

def _ws_domains(dc: int, is_media: Optional[bool], is_web: bool = False) -> List[str]:
    if is_web:
        return ['web.telegram.org', 'webk.telegram.org']
    
    domains = [f'kws{dc}.web.telegram.org']
    if is_media:
        domains.append(f'kws{dc}-1.web.telegram.org')
        domains.append(f'plweb{dc}.telegram.org')
        domains.append(f'cdn{dc}.telegram.org')
    
    return domains

class Stats:
    __slots__ = ('connections_total', 'connections_ws', 'connections_tcp_fallback',
                 'connections_http_rejected', 'connections_passthrough', 'ws_errors',
                 'bytes_up', 'bytes_down', 'pool_hits', 'pool_misses', 'active_connections', 
                 'start_time', 'reconnections', '_last_reset')

    def __init__(self):
        self.connections_total = 0
        self.connections_ws = 0
        self.connections_tcp_fallback = 0
        self.connections_http_rejected = 0
        self.connections_passthrough = 0
        self.ws_errors = 0
        self.bytes_up = 0
        self.bytes_down = 0
        self.pool_hits = 0
        self.pool_misses = 0
        self.active_connections = 0
        self.reconnections = 0
        self.start_time = time.time()
        self._last_reset = time.time()

    def reset_if_overflow(self):
        now = time.time()
        if now - self._last_reset > 3600:
            self.connections_total = 0
            self.connections_ws = 0
            self.connections_tcp_fallback = 0
            self.connections_http_rejected = 0
            self.connections_passthrough = 0
            self.ws_errors = 0
            self.pool_hits = 0
            self.pool_misses = 0
            self.reconnections = 0
            self._last_reset = now

    def summary(self) -> str:
        self.reset_if_overflow()
        total_pool = self.pool_hits + self.pool_misses
        if total_pool == 0:
            pool_rate = "n/a"
        else:
            pool_rate = f"{self.pool_hits}/{total_pool}"
        uptime = int(time.time() - self.start_time)
        return (f"uptime={uptime}s total={self.connections_total} ws={self.connections_ws} "
                f"tcp_fb={self.connections_tcp_fallback} "
                f"http_skip={self.connections_http_rejected} "
                f"pass={self.connections_passthrough} "
                f"err={self.ws_errors} "
                f"active={self.active_connections} "
                f"pool={pool_rate} "
                f"reconn={self.reconnections} "
                f"up={_human_bytes(self.bytes_up)} "
                f"down={_human_bytes(self.bytes_down)}")

_stats = Stats()

class _WsPool:
    __slots__ = ('_idle', '_refilling', '_lock', '_recent')
    
    def __init__(self):
        self._idle: Dict[Tuple[int, bool], deque] = {}
        self._refilling: Set[Tuple[int, bool]] = set()
        self._lock = asyncio.Lock()
        self._recent: Dict[Tuple[int, bool], deque] = {}

    async def get(self, dc: int, is_media: bool,
                  target_ip: str, domains: List[str]
                  ) -> Optional[RawWebSocket]:
        key = (dc, is_media)
        now = time.monotonic()
        
        recent = self._recent.get(key)
        if recent:
            while recent:
                ws, created = recent.popleft()
                age = now - created
                if age > _WS_POOL_MAX_AGE * 0.3:
                    asyncio.create_task(self._quiet_close(ws))
                    continue
                if not ws._closed:
                    _stats.pool_hits += 1
                    return ws
                asyncio.create_task(self._quiet_close(ws))
        
        async with self._lock:
            bucket = self._idle.get(key)
            if bucket:
                while bucket:
                    ws, created = bucket.popleft()
                    age = now - created
                    if age > _WS_POOL_MAX_AGE or ws._closed:
                        asyncio.create_task(self._quiet_close(ws))
                        continue
                    _stats.pool_hits += 1
                    if key not in self._recent:
                        self._recent[key] = deque(maxlen=3)
                    self._recent[key].append((ws, now))
                    self._schedule_refill(key, target_ip, domains)
                    return ws
        
        _stats.pool_misses += 1
        self._schedule_refill(key, target_ip, domains)
        return None

    def _schedule_refill(self, key: Tuple[int, bool], target_ip: str, domains: List[str]):
        if key in self._refilling:
            return
        self._refilling.add(key)
        asyncio.create_task(self._refill(key, target_ip, domains))

    async def _refill(self, key: Tuple[int, bool], target_ip: str, domains: List[str]):
        try:
            async with self._lock:
                bucket = self._idle.setdefault(key, deque())
                current_count = len(bucket)
                needed = _WS_POOL_SIZE - current_count
                if needed <= 0:
                    return
            
            tasks = []
            for _ in range(min(needed, 8)):
                task = asyncio.create_task(self._connect_one(target_ip, domains))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            async with self._lock:
                bucket = self._idle.setdefault(key, deque())
                remaining = _WS_POOL_SIZE - len(bucket)
                for ws in results:
                    if isinstance(ws, RawWebSocket) and remaining > 0:
                        bucket.append((ws, time.monotonic()))
                        remaining -= 1
                    elif isinstance(ws, RawWebSocket):
                        await self._quiet_close(ws)
        finally:
            self._refilling.discard(key)

    @staticmethod
    async def _connect_one(target_ip: str, domains: List[str], is_web: bool = False) -> Optional[RawWebSocket]:
        for domain in domains:
            try:
                for path in _TELEGRAM_WEB_PATHS:
                    try:
                        ws = await RawWebSocket.connect(target_ip, domain, path=path, timeout=15, is_web=is_web)
                        return ws
                    except WsHandshakeError:
                        continue
            except Exception:
                continue
        return None

    @staticmethod
    async def _quiet_close(ws: RawWebSocket):
        try:
            await ws.close()
        except Exception:
            pass

    async def warmup(self, dc_opt: Dict[int, Optional[str]]):
        tasks = []
        for dc, target_ip in dc_opt.items():
            if target_ip is None:
                continue
            for is_media in (False, True):
                domains = _ws_domains(dc, is_media)
                tasks.append(self._refill((dc, is_media), target_ip, domains))
        if tasks:
            await asyncio.gather(*tasks)

    async def cleanup(self):
        async with self._lock:
            for key, bucket in list(self._idle.items()):
                for ws, _ in bucket:
                    await self._quiet_close(ws)
                self._idle[key] = deque()
            for key, bucket in list(self._recent.items()):
                for ws, _ in bucket:
                    await self._quiet_close(ws)
                self._recent[key] = deque()

_ws_pool = _WsPool()

async def _bridge_ws(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                     ws: RawWebSocket, label: str,
                     dc: Optional[int] = None, dst: Optional[str] = None, 
                     port: Optional[int] = None, is_media: bool = False,
                     splitter: Optional[_MsgSplitter] = None):
    
    _stats.active_connections += 1
    
    async def tcp_to_ws():
        try:
            while True:
                try:
                    async with asyncio.timeout(_CONNECTION_TIMEOUT):
                        chunk = await reader.read(_RECV_BUF)
                except asyncio.TimeoutError:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
                if not chunk:
                    break
                _stats.bytes_up += len(chunk)
                try:
                    if splitter:
                        parts = splitter.split(chunk)
                        if len(parts) > 1:
                            await ws.send_batch(parts)
                        else:
                            await ws.send(parts[0])
                    else:
                        await ws.send(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            try:
                await ws.close()
            except:
                pass

    async def ws_to_tcp():
        try:
            while True:
                try:
                    async with asyncio.timeout(_CONNECTION_TIMEOUT):
                        data = await ws.recv()
                except asyncio.TimeoutError:
                    continue
                if data is None:
                    break
                _stats.bytes_down += len(data)
                try:
                    writer.write(data)
                    if writer.transport.get_write_buffer_size() > _SEND_BUF // 2:
                        await writer.drain()
                except (ConnectionResetError, BrokenPipeError):
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (ConnectionResetError, OSError):
                pass
            except:
                pass

    tcp_to_ws_task = asyncio.create_task(tcp_to_ws())
    ws_to_tcp_task = asyncio.create_task(ws_to_tcp())
    
    try:
        done, pending = await asyncio.wait(
            [tcp_to_ws_task, ws_to_tcp_task], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
                
    except asyncio.CancelledError:
        if tcp_to_ws_task and not tcp_to_ws_task.done():
            tcp_to_ws_task.cancel()
        if ws_to_tcp_task and not ws_to_tcp_task.done():
            ws_to_tcp_task.cancel()
        await asyncio.gather(tcp_to_ws_task, ws_to_tcp_task, return_exceptions=True)
        raise
        
    finally:
        for task in [tcp_to_ws_task, ws_to_tcp_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=0.5)
                except (TimeoutError, asyncio.CancelledError):
                    pass
                except Exception:
                    pass
        
        try:
            await ws.close()
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            pass
        
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass
        
        _stats.active_connections -= 1

async def _bridge_tcp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                      remote_reader: asyncio.StreamReader, remote_writer: asyncio.StreamWriter,
                      label: str, dc: Optional[int] = None, dst: Optional[str] = None, 
                      port: Optional[int] = None, is_media: bool = False):
    
    _stats.active_connections += 1
    
    async def forward(src: asyncio.StreamReader, dst_w: asyncio.StreamWriter, tag: str):
        try:
            while True:
                try:
                    async with asyncio.timeout(_CONNECTION_TIMEOUT):
                        data = await src.read(_RECV_BUF)
                except asyncio.TimeoutError:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
                if not data:
                    break
                if 'up' in tag:
                    _stats.bytes_up += len(data)
                else:
                    _stats.bytes_down += len(data)
                try:
                    dst_w.write(data)
                    if dst_w.transport.get_write_buffer_size() > _SEND_BUF // 2:
                        await dst_w.drain()
                except (ConnectionResetError, BrokenPipeError):
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    tasks = [
        asyncio.create_task(forward(reader, remote_writer, 'up')),
        asyncio.create_task(forward(remote_reader, writer, 'down')),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for w in (writer, remote_writer):
            try:
                w.close()
                await w.wait_closed()
            except:
                pass
        _stats.active_connections -= 1

async def _pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    try:
        while True:
            try:
                data = await r.read(_RECV_BUF)
                if not data:
                    break
                w.write(data)
                await w.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
            except asyncio.CancelledError:
                raise
    except asyncio.CancelledError:
        raise
    finally:
        try:
            w.close()
            await w.wait_closed()
        except (ConnectionResetError, OSError, asyncio.CancelledError):
            pass
        except Exception:
            pass

def _socks5_reply(status: int) -> bytes:
    return bytes([0x05, status, 0x00, 0x01]) + b'\x00' * 6

async def _tcp_fallback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                        dst: str, port: int, init: bytes, label: str,
                        dc: Optional[int] = None, is_media: bool = False) -> bool:
    for attempt in range(_MAX_RETRIES):
        try:
            rr, rw = await asyncio.wait_for(
                asyncio.open_connection(dst, port, limit=_RECV_BUF), timeout=8)
            break
        except Exception:
            if attempt == _MAX_RETRIES - 1:
                return False
            await asyncio.sleep(_RETRY_DELAY)
            continue

    _stats.connections_tcp_fallback += 1
    rw.write(init)
    await rw.drain()
    await _bridge_tcp(reader, writer, rr, rw, label,
                      dc=dc, dst=dst, port=port, is_media=is_media)
    return True

async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        async with asyncio.timeout(300):
            async with _connection_semaphore:
                _stats.connections_total += 1
                peer = writer.get_extra_info('peername')
                label = f"{peer[0]}:{peer[1]}" if peer else "?"

                _set_sock_opts(writer.transport)

                try:
                    try:
                        hdr = await asyncio.wait_for(reader.readexactly(2), timeout=5)
                    except asyncio.IncompleteReadError:
                        return
                    
                    if hdr[0] != 5:
                        writer.close()
                        return
                    nmethods = hdr[1]
                    try:
                        await asyncio.wait_for(reader.readexactly(nmethods), timeout=5)
                    except asyncio.IncompleteReadError:
                        return
                    
                    writer.write(b'\x05\x00')
                    await writer.drain()

                    try:
                        req = await asyncio.wait_for(reader.readexactly(4), timeout=5)
                    except asyncio.IncompleteReadError:
                        return
                    
                    _ver, cmd, _rsv, atyp = req
                    if cmd != 1:
                        writer.write(_socks5_reply(0x07))
                        await writer.drain()
                        writer.close()
                        return

                    if atyp == 1:
                        raw = await asyncio.wait_for(reader.readexactly(4), timeout=5)
                        dst = _socket.inet_ntoa(raw)
                    elif atyp == 3:
                        dlen = (await asyncio.wait_for(reader.readexactly(1), timeout=5))[0]
                        dst = (await asyncio.wait_for(reader.readexactly(dlen), timeout=5)).decode()
                    else:
                        writer.write(_socks5_reply(0x08))
                        await writer.drain()
                        writer.close()
                        return

                    port = struct.unpack('!H', await asyncio.wait_for(reader.readexactly(2), timeout=5))[0]
                    is_web = _is_telegram_web_host(dst)
                    
                    is_media = False
                    if any(domain in dst for domain in _MEDIA_DOMAINS):
                        is_media = True
                    elif 'cdn' in dst or 'media' in dst or 'video' in dst or 'photo' in dst:
                        is_media = True
                    elif port in [80, 443, 8080, 8443, 9443]:
                        is_media = True

                    if not _is_telegram_ip(dst) and not is_web and not is_media:
                        _stats.connections_passthrough += 1
                        try:
                            rr, rw = await asyncio.wait_for(
                                asyncio.open_connection(dst, port, limit=_RECV_BUF), 
                                timeout=8
                            )
                        except Exception:
                            writer.write(_socks5_reply(0x05))
                            await writer.drain()
                            writer.close()
                            return

                        writer.write(_socks5_reply(0x00))
                        await writer.drain()
                        
                        pipe1 = asyncio.create_task(_pipe(reader, rw))
                        pipe2 = asyncio.create_task(_pipe(rr, writer))
                        
                        try:
                            await asyncio.wait([pipe1, pipe2], return_when=asyncio.FIRST_COMPLETED)
                        finally:
                            for task in [pipe1, pipe2]:
                                if not task.done():
                                    task.cancel()
                                    try:
                                        await task
                                    except:
                                        pass
                        return

                    writer.write(_socks5_reply(0x00))
                    await writer.drain()

                    try:
                        init = await asyncio.wait_for(reader.readexactly(64), timeout=10)
                    except asyncio.IncompleteReadError:
                        return

                    if _is_http_transport(init):
                        _stats.connections_http_rejected += 1
                        return

                    dc, is_media_flag = _dc_from_init(init)
                    init_patched = False

                    if is_media:
                        is_media_flag = True

                    if dc is None and is_web:
                        dc = 2
                        is_media_flag = False

                    if dc is None and dst in _IP_TO_DC:
                        result = _IP_TO_DC.get(dst)
                        if result:
                            dc, is_media_flag = result
                            if dc in _dc_opt:
                                init = _patch_init_dc(init, dc if is_media_flag else -dc)
                                init_patched = True

                    if dc is None or dc not in _dc_opt:
                        await _tcp_fallback(reader, writer, dst, port, init, label)
                        return

                    dc_key = (dc, is_media_flag if is_media_flag is not None else True)
                    now = time.monotonic()

                    if dc_key in _ws_blacklist:
                        await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media_flag)
                        return

                    fail_until = _dc_fail_until.get(dc_key, 0)
                    if now < fail_until:
                        await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media_flag)
                        return

                    domains = _ws_domains(dc, is_media_flag, is_web=is_web)
                    target = _dc_opt[dc]
                    
                    if target is None and dc in FULL_DC_OPT:
                        target = FULL_DC_OPT[dc][0]
                    
                    if target is None:
                        await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media_flag)
                        return
                    
                    ws = None
                    ws_failed_redirect = False
                    all_redirects = True

                    ws = await _ws_pool.get(dc, is_media_flag, target, domains)
                    if not ws:
                        for domain in domains:
                            try:
                                ws = await RawWebSocket.connect(target, domain, timeout=15, is_web=is_web)
                                all_redirects = False
                                break
                            except WsHandshakeError as exc:
                                _stats.ws_errors += 1
                                if exc.is_redirect:
                                    ws_failed_redirect = True
                                    continue
                                else:
                                    all_redirects = False
                            except Exception:
                                _stats.ws_errors += 1
                                all_redirects = False

                    if ws is None:
                        if ws_failed_redirect and all_redirects:
                            _ws_blacklist.add(dc_key)
                        else:
                            _dc_fail_until[dc_key] = now + _DC_FAIL_COOLDOWN
                        await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media_flag)
                        return

                    _dc_fail_until.pop(dc_key, None)
                    _stats.connections_ws += 1

                    splitter = None
                    if init_patched:
                        try:
                            splitter = _MsgSplitter(init)
                        except Exception:
                            pass

                    await ws.send(init)
                    await _bridge_ws(reader, writer, ws, label,
                                     dc=dc, dst=dst, port=port, is_media=is_media_flag,
                                     splitter=splitter)

                except asyncio.IncompleteReadError:
                    return
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    raise
                except (ConnectionResetError, BrokenPipeError):
                    pass
                except Exception:
                    pass
                finally:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except:
                        pass
                        
    except asyncio.TimeoutError:
        pass
    except asyncio.CancelledError:
        raise
    except Exception:
        pass   

_server_instance = None
_server_stop_event = None

async def _run(port: int, dc_opt: Dict[int, Optional[str]],
               stop_event: Optional[asyncio.Event] = None,
               host: str = '127.0.0.1'):
    global _dc_opt, _server_instance, _server_stop_event
    
    if not is_port_available(host, port):
        return
    
    _dc_opt = dc_opt
    _server_stop_event = stop_event

    server = await asyncio.start_server(
        _handle_client, host, port, limit=_RECV_BUF)
    _server_instance = server
    
    warmup_task = asyncio.create_task(_ws_pool.warmup(dc_opt))
    
    if stop_event:
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            if not warmup_task.done():
                warmup_task.cancel()
                try:
                    await asyncio.wait_for(warmup_task, timeout=0.5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except Exception:
                    pass
            
            server.close()
            try:
                await asyncio.wait_for(server.wait_closed(), timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
            
            await asyncio.sleep(0.3)
            
            try:
                await asyncio.wait_for(_ws_pool.cleanup(), timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
    else:
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            server.close()
            await server.wait_closed()
    
    _server_instance = None

def parse_dc_ip_list(dc_ip_list: List[str]) -> Dict[int, str]:
    dc_opt: Dict[int, str] = {}
    for entry in dc_ip_list:
        if ':' not in entry:
            raise ValueError(f"Invalid --dc-ip format {entry!r}, expected DC:IP")
        dc_s, ip_s = entry.split(':', 1)
        try:
            dc_n = int(dc_s)
            _socket.inet_aton(ip_s)
        except (ValueError, OSError):
            raise ValueError(f"Invalid --dc-ip {entry!r}")
        dc_opt[dc_n] = ip_s
    return dc_opt

def run_proxy(port: int, dc_opt: Dict[int, str],
              stop_event: Optional[asyncio.Event] = None,
              host: str = '127.0.0.1'):
    asyncio.run(_run(port, dc_opt, stop_event, host))

def main():
    ap = argparse.ArgumentParser(
        description='Telegram Proxy')
    ap.add_argument('--port', type=int, default=DEFAULT_PORT,
                    help=f'Listen port (default {DEFAULT_PORT})')
    ap.add_argument('--host', type=str, default='127.0.0.1',
                    help='Listen host (default 127.0.0.1)')
    ap.add_argument('--mode', type=str, choices=['fast', 'stable'], default='stable',
                    help='Mode: fast (high CPU/RAM usage) or stable (balanced)')
    ap.add_argument('--dc-ip', metavar='DC:IP', action='append',
                    default=[
                        '1:149.154.175.50', '1:149.154.175.52', '1:149.154.175.53',
                        '2:149.154.167.220', '2:149.154.167.151', '2:149.154.167.51',
                        '3:149.154.175.100', '3:149.154.175.102',
                        '4:149.154.167.91', '4:149.154.167.118', '4:149.154.167.92',
                        '5:91.108.56.100', '5:91.108.56.102', '5:91.108.56.126'
                    ],
                    help='Target IP for a DC, e.g. --dc-ip 1:149.154.175.205')
    args = ap.parse_args()

    try:
        dc_opt = parse_dc_ip_list(args.dc_ip)
    except ValueError:
        sys.exit(1)
    
    set_tg_mode(args.mode)

    try:
        asyncio.run(_run(args.port, dc_opt, host=args.host))
    except Exception:
        sys.exit(1)

async def _run_async(port: int, dc_opt: Dict[int, Optional[str]],
                      stop_event: Optional[asyncio.Event] = None,
                      host: str = '127.0.0.1',
                      mode: str = TG_MODE_STABLE):
    set_tg_mode(mode)
    await _run(port, dc_opt, stop_event, host)

def run_proxy_async(port: int, dc_opt: Dict[int, str],
                     stop_event: Optional[asyncio.Event] = None,
                     host: str = '127.0.0.1',
                     mode: str = TG_MODE_STABLE):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_async(port, dc_opt, stop_event, host, mode))
    except KeyboardInterrupt:
        if stop_event:
            stop_event.set()
        loop.run_until_complete(asyncio.sleep(1))
    finally:
        loop.close()

if __name__ == '__main__':
    main()
