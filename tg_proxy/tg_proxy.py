from __future__ import annotations
import asyncio
import base64
import os
import socket as _socket
import ssl
import struct
import time
import logging
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DEFAULT_PORT = 1080
_TCP_KEEPIDLE = 30
_TCP_KEEPINTVL = 5
_TCP_KEEPCNT = 3

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('tg-proxy')

TG_CONFIG = {
    "ws_pool_size": 32,
    "ws_pool_max_age": 120.0,
    "max_connections": 400,
    "heartbeat_interval": 15.0,
    "connection_timeout": 300.0,
    "recv_buf": 16 * 1024 * 1024,
    "send_buf": 16 * 1024 * 1024,
    "max_reconnect_attempts": 3,
    "max_consecutive_errors": 5,
    "error_cooldown": 30.0,
    "file_timeout": 60.0,
    "reconnect_delay": 1.0,
    "ws_keepalive_interval": 20.0,
    "retry_delay": 1.0,
    "max_retries": 3,
    "dc_fail_cooldown": 30.0,
    "socket_buffer_multiplier": 4,
    "preconnect": True,
    "health_check_interval": 15.0,
    "large_file_chunk_size": 64 * 1024,
    "read_timeout": 60,
    "write_timeout": 60,
}

_TCP_NODELAY = True
_RECV_BUF = TG_CONFIG["recv_buf"]
_SEND_BUF = TG_CONFIG["send_buf"]
_WS_POOL_SIZE = TG_CONFIG["ws_pool_size"]
_WS_POOL_MAX_AGE = TG_CONFIG["ws_pool_max_age"]
_MAX_MSG_SIZE = 10 * 1024 * 1024
_HEARTBEAT_INTERVAL = TG_CONFIG["heartbeat_interval"]
_CONNECTION_TIMEOUT = TG_CONFIG["connection_timeout"]
_MAX_RETRIES = TG_CONFIG["max_retries"]
_RETRY_DELAY = TG_CONFIG["retry_delay"]
_DC_FAIL_COOLDOWN = TG_CONFIG["dc_fail_cooldown"]
_MAX_CONNECTIONS = TG_CONFIG["max_connections"]
_SOCKET_BUFFER_MULTIPLIER = TG_CONFIG["socket_buffer_multiplier"]
_WS_KEEPALIVE_INTERVAL = TG_CONFIG["ws_keepalive_interval"]
_MAX_RECONNECT_ATTEMPTS = TG_CONFIG["max_reconnect_attempts"]
_RECONNECT_DELAY = TG_CONFIG["reconnect_delay"]

_connection_semaphore = asyncio.Semaphore(_MAX_CONNECTIONS)
_telegram_ip_cache: Dict[str, bool] = {}

_consecutive_errors = 0
_last_error_time = 0

_CACHE_MAX_SIZE = 2000

PROTO_ABRIDGED_INT = 0xEFEFEFEF
PROTO_INTERMEDIATE_INT = 0xEEEEEEEE
PROTO_PADDED_INTERMEDIATE_INT = 0xDDDDDDDD

ZERO_64 = b'\x00' * 64
HANDSHAKE_LEN = 64
SKIP_LEN = 8
PREKEY_LEN = 32
KEY_LEN = 32
IV_LEN = 16
PROTO_TAG_POS = 56
DC_IDX_POS = 60

_st_I_le = struct.Struct('<I')

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
    '95.161.76.100': (2, False),
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
    '149.154.171.5': (5, False),
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
    'web.telegram.org', 'webk.telegram.org', 'web.telegram.org/z',
    'web.telegram.org/k', 'web.telegram.org/a', 'pl.web.telegram.org', 'pl2.web.telegram.org',
]

_TELEGRAM_WEB_PATHS = ['/apiws', '/apiwsp', '/apiwss', '/apiws/v1', '/apiws/v2']

_MEDIA_DOMAINS = [
    't.me', 'tdesktop.com', 'telegram.org', 'telegram.dog', 'telegra.ph',
    'cdn-telegram.org', 'cdn4.telegram-cdn.org', 'cdn5.telegram-cdn.org',
    'cdn6.telegram-cdn.org', 'cdn7.telegram-cdn.org', 'cdn8.telegram-cdn.org',
    'cdn9.telegram-cdn.org', 'media.telegram.org', 'video.telegram.org',
    'photos.telegram.org', 'docs.telegram.org',
]

_dc_opt: Dict[int, Optional[str]] = {}
_ws_blacklist: Set[Tuple[int, bool]] = set()
_dc_fail_until: Dict[Tuple[int, bool], float] = {}

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
_ssl_ctx.set_ciphers('DEFAULT@SECLEVEL=1')

_dns_cache: Dict[str, Tuple[str, float]] = {}
_dns_cache_lock = asyncio.Lock()

def set_tg_mode(mode: str) -> bool:
    return True

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

_stats = Stats()

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
    if len(data) < 64:
        return None, False
    
    try:
        key = bytes(data[8:40])
        iv = bytes(data[40:56])
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        keystream = encryptor.update(b'\x00' * 64) + encryptor.finalize()
        plain = bytes(a ^ b for a, b in zip(data[56:64], keystream[56:64]))
        proto = struct.unpack('<I', plain[0:4])[0]
        dc_raw = struct.unpack('<h', plain[4:6])[0]
        if proto in (PROTO_ABRIDGED_INT, PROTO_INTERMEDIATE_INT, PROTO_PADDED_INTERMEDIATE_INT):
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

def _xor_mask(data: bytes, mask: bytes) -> bytes:
    if not data:
        return data
    n = len(data)
    mask_rep = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, 'big') ^ int.from_bytes(mask_rep, 'big')).to_bytes(n, 'big')

class MsgSplitter:
    __slots__ = ('_dec', '_proto', '_cipher_buf', '_plain_buf', '_disabled')
    
    def __init__(self, init_data: bytes, proto_int: int):
        self._proto = proto_int
        self._cipher_buf = bytearray()
        self._plain_buf = bytearray()
        self._disabled = False
        
        try:
            key_raw = bytes(init_data[8:40])
            iv = bytes(init_data[40:56])
            cipher = Cipher(algorithms.AES(key_raw), modes.CTR(iv))
            self._dec = cipher.encryptor()
            self._dec.update(ZERO_64)
        except Exception:
            self._disabled = True

    def split(self, chunk: bytes) -> List[bytes]:
        if not chunk or self._disabled:
            return [chunk] if chunk else []
        
        self._cipher_buf.extend(chunk)
        self._plain_buf.extend(self._dec.update(chunk))
        
        parts = []
        while self._cipher_buf:
            packet_len = self._next_packet_len()
            if packet_len is None:
                break
            if packet_len <= 0:
                parts.append(bytes(self._cipher_buf))
                self._cipher_buf.clear()
                self._plain_buf.clear()
                self._disabled = True
                break
            parts.append(bytes(self._cipher_buf[:packet_len]))
            del self._cipher_buf[:packet_len]
            del self._plain_buf[:packet_len]
        return parts

    def flush(self) -> List[bytes]:
        if not self._cipher_buf:
            return []
        tail = bytes(self._cipher_buf)
        self._cipher_buf.clear()
        self._plain_buf.clear()
        return [tail]

    def _next_packet_len(self) -> Optional[int]:
        if not self._plain_buf:
            return None
        if self._proto == PROTO_ABRIDGED_INT:
            return self._next_abridged_len()
        if self._proto in (PROTO_INTERMEDIATE_INT, PROTO_PADDED_INTERMEDIATE_INT):
            return self._next_intermediate_len()
        return 0

    def _next_abridged_len(self) -> Optional[int]:
        first = self._plain_buf[0]
        if first in (0x7F, 0xFF):
            if len(self._plain_buf) < 4:
                return None
            payload_len = int.from_bytes(self._plain_buf[1:4], 'little') * 4
            header_len = 4
        else:
            payload_len = (first & 0x7F) * 4
            header_len = 1
        if payload_len <= 0:
            return 0
        packet_len = header_len + payload_len
        if len(self._plain_buf) < packet_len:
            return None
        return packet_len

    def _next_intermediate_len(self) -> Optional[int]:
        if len(self._plain_buf) < 4:
            return None
        payload_len = _st_I_le.unpack_from(self._plain_buf, 0)[0] & 0x7FFFFFFF
        if payload_len <= 0:
            return 0
        packet_len = 4 + payload_len
        if len(self._plain_buf) < packet_len:
            return None
        return packet_len

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

class RawWebSocket:
    OP_CONTINUATION = 0x0
    OP_TEXT = 0x1
    OP_BINARY = 0x2
    OP_CLOSE = 0x8
    OP_PING = 0x9
    OP_PONG = 0xA

    __slots__ = ('reader', 'writer', '_closed', '_last_heartbeat', '_heartbeat_task', 
                 '_keepalive_task', '_last_activity', '_reconnect_attempts',
                 '_send_buffer', '_send_lock', '_flush_task', '_read_lock', '_recv_buffer')

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
        self._read_lock = asyncio.Lock()
        self._recv_buffer = bytearray()

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
    async def connect(ip: str, domain: str, path: str = '/apiws', timeout: float = 15.0, is_web: bool = False) -> 'RawWebSocket':
        global _consecutive_errors, _last_error_time
        
        now = time.time()
        if now - _last_error_time < 1.0:
            await asyncio.sleep(0.5)
        
        last_error = None
        for attempt in range(_MAX_RECONNECT_ATTEMPTS):
            reader = writer = None
            try:
                conn_timeout = timeout if not is_web else timeout * 2
                
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, 443, ssl=_ssl_ctx, server_hostname=domain, limit=_RECV_BUF),
                    timeout=conn_timeout)
                _set_sock_opts(writer.transport)

                ws_key = base64.b64encode(os.urandom(16)).decode()
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
                    f'Connection: keep-alive\r\n'
                    f'\r\n'
                ).encode()
                writer.write(req)
                await writer.drain()

                response_lines = []
                read_timeout = timeout if not is_web else timeout * 2
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=read_timeout)
                    if line in (b'\r\n', b'\n', b''):
                        break
                    response_lines.append(line.decode('utf-8', errors='replace').strip())

                if not response_lines:
                    raise ConnectionError("Empty response")

                first_line = response_lines[0]
                parts = first_line.split(' ', 2)
                status_code = int(parts[1]) if len(parts) >= 2 else 0

                if status_code == 101:
                    _consecutive_errors = 0
                    _last_error_time = 0
                    
                    ws = RawWebSocket(reader, writer)
                    ws._heartbeat_task = asyncio.create_task(ws._heartbeat())
                    ws._keepalive_task = asyncio.create_task(ws._keepalive())
                    ws._flush_task = asyncio.create_task(ws._flush_buffer())
                    return ws
                else:
                    raise ConnectionError(f"WebSocket handshake failed: {status_code}")
                    
            except Exception as e:
                last_error = e
                _consecutive_errors += 1
                _last_error_time = time.time()
                
                if _consecutive_errors > 5:
                    await asyncio.sleep(5)
                    _consecutive_errors = 0
                
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except:
                        pass
                
                if attempt < _MAX_RECONNECT_ATTEMPTS - 1:
                    await asyncio.sleep(_RECONNECT_DELAY * (attempt + 1))
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
        async with self._read_lock:
            while not self._closed:
                try:
                    if self._recv_buffer:
                        data = bytes(self._recv_buffer)
                        self._recv_buffer.clear()
                        return data
                    
                    async with asyncio.timeout(_CONNECTION_TIMEOUT):
                        opcode, payload = await self._read_frame()
                    
                    self._last_activity = time.monotonic()
                    self._last_heartbeat = time.monotonic()
                    
                    if opcode == self.OP_CLOSE:
                        self._closed = True
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
                        self._recv_buffer.extend(payload)
                        if len(self._recv_buffer) > 1024 * 1024:
                            data = bytes(self._recv_buffer)
                            self._recv_buffer.clear()
                            return data
                        continue
                        
                except asyncio.TimeoutError:
                    continue
                except (ConnectionResetError, BrokenPipeError, OSError):
                    self._closed = True
                    return None
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self._closed = True
                    return None
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
        except:
            pass
        
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except:
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

class _WsPool:
    __slots__ = ('_idle', '_refilling', '_lock', '_recent')
    
    def __init__(self):
        self._idle: Dict[Tuple[int, bool], deque] = {}
        self._refilling: Set[Tuple[int, bool]] = set()
        self._lock = asyncio.Lock()
        self._recent: Dict[Tuple[int, bool], deque] = {}

    async def get(self, dc: int, is_media: bool, target_ip: str, domains: List[str]) -> Optional[RawWebSocket]:
        global _consecutive_errors
        
        if _consecutive_errors > 10:
            await asyncio.sleep(2)
            return None
        
        key = (dc, is_media)
        
        async with self._lock:
            bucket = self._idle.get(key)
            if bucket:
                while bucket:
                    ws, created = bucket.popleft()
                    age = time.monotonic() - created
                    if age > _WS_POOL_MAX_AGE or ws._closed:
                        asyncio.create_task(self._quiet_close(ws))
                        continue
                    return ws
        
        return await self._connect_one(target_ip, domains)

    async def _connect_one(self, target_ip: str, domains: List[str]) -> Optional[RawWebSocket]:
        for domain in domains:
            try:
                ws = await RawWebSocket.connect(target_ip, domain, timeout=15)
                return ws
            except Exception:
                continue
        return None

    @staticmethod
    async def _quiet_close(ws: RawWebSocket):
        try:
            await ws.close()
        except Exception:
            pass

    async def cleanup(self):
        async with self._lock:
            for key, bucket in list(self._idle.items()):
                for ws, _ in bucket:
                    await self._quiet_close(ws)
                self._idle[key] = deque()


_ws_pool = _WsPool()

def _ws_domains(dc: int, is_media: Optional[bool], is_web: bool = False) -> List[str]:
    if is_web:
        return ['web.telegram.org', 'webk.telegram.org']
    
    domains = [f'kws{dc}.web.telegram.org']
    if is_media:
        domains.append(f'kws{dc}-1.web.telegram.org')
    return domains

async def _bridge_ws(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                     ws: RawWebSocket, label: str, dc: Optional[int] = None, 
                     dst: Optional[str] = None, port: Optional[int] = None, 
                     is_media: bool = False, splitter: Optional[MsgSplitter] = None):
    
    global _consecutive_errors, _last_error_time
    
    _stats.active_connections += 1
    running = True
    
    media_timeout = 120 if is_media else _CONNECTION_TIMEOUT
    
    async def tcp_to_ws():
        nonlocal running
        consecutive_read_errors = 0
        try:
            while running:
                try:
                    async with asyncio.timeout(media_timeout):
                        chunk = await reader.read(_RECV_BUF)
                except asyncio.TimeoutError:
                    consecutive_read_errors += 1
                    if consecutive_read_errors > 3:
                        break
                    continue
                except (ConnectionResetError, BrokenPipeError, OSError, asyncio.CancelledError):
                    break
                    
                if not chunk:
                    break
                    
                consecutive_read_errors = 0
                _stats.bytes_up += len(chunk)
                
                max_chunk = 256 * 1024
                if len(chunk) > max_chunk:
                    for i in range(0, len(chunk), max_chunk):
                        part = chunk[i:i+max_chunk]
                        try:
                            await ws.send(part)
                            await asyncio.sleep(0)
                        except Exception:
                            break
                else:
                    try:
                        await ws.send(chunk)
                    except Exception:
                        break
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.debug(f"tcp_to_ws error: {e}")
        finally:
            running = False

    async def ws_to_tcp():
        nonlocal running
        try:
            while running:
                try:
                    async with asyncio.timeout(media_timeout):
                        data = await ws.recv()
                except asyncio.TimeoutError:
                    continue
                    
                if data is None:
                    break
                    
                _stats.bytes_down += len(data)
                
                max_write = 512 * 1024
                if len(data) > max_write:
                    for i in range(0, len(data), max_write):
                        part = data[i:i+max_write]
                        try:
                            writer.write(part)
                            await asyncio.sleep(0)
                        except Exception:
                            break
                else:
                    try:
                        writer.write(data)
                        if writer.transport.get_write_buffer_size() > _SEND_BUF // 4:
                            await writer.drain()
                    except Exception:
                        break
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.debug(f"ws_to_tcp error: {e}")
        finally:
            running = False
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    tcp_to_ws_task = asyncio.create_task(tcp_to_ws())
    ws_to_tcp_task = asyncio.create_task(ws_to_tcp())
    
    try:
        await asyncio.wait([tcp_to_ws_task, ws_to_tcp_task], return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        pass
    finally:
        for task in [tcp_to_ws_task, ws_to_tcp_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except:
                    pass
        
        try:
            await ws.close()
        except:
            pass
        
        _stats.active_connections -= 1

def _socks5_reply(status: int) -> bytes:
    return bytes([0x05, status, 0x00, 0x01]) + b'\x00' * 6

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
                    
                    writer.write(_socks5_reply(0x00))
                    await writer.drain()

                    try:
                        init = await asyncio.wait_for(reader.readexactly(64), timeout=15)
                    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                        return

                    dc, is_media_flag = _dc_from_init(init)
                    
                    if dc is None or dc not in _dc_opt:
                        try:
                            rr, rw = await asyncio.wait_for(asyncio.open_connection(dst, port, limit=_RECV_BUF), timeout=8)
                            rw.write(init)
                            await rw.drain()
                            
                            async def forward(src, dst_w):
                                try:
                                    while True:
                                        data = await src.read(_RECV_BUF)
                                        if not data:
                                            break
                                        dst_w.write(data)
                                        await dst_w.drain()
                                except:
                                    pass
                            
                            task1 = asyncio.create_task(forward(reader, rw))
                            task2 = asyncio.create_task(forward(rr, writer))
                            
                            await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
                            task1.cancel()
                            task2.cancel()
                        except Exception:
                            pass
                        return

                    target = _dc_opt[dc]
                    if target is None:
                        return
                    
                    domains = _ws_domains(dc, is_media_flag)
                    ws = await _ws_pool.get(dc, is_media_flag, target, domains)
                    
                    if ws is None:
                        return
                    
                    _stats.connections_ws += 1
                    await ws.send(init)
                    await _bridge_ws(reader, writer, ws, label, dc=dc, dst=dst, port=port, is_media=is_media_flag)

                except asyncio.TimeoutError:
                    pass
                except (ConnectionResetError, BrokenPipeError, OSError):
                    pass
                except Exception as e:
                    log.debug(f"Error in _handle_client: {e}")
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

async def _run(port: int, dc_opt_input: Dict[int, Optional[str]],
               stop_event: Optional[asyncio.Event] = None,
               host: str = '127.0.0.1'):
    global _dc_opt, _server_instance, _server_stop_event
    
    _dc_opt = dc_opt_input
    _server_stop_event = stop_event

    server = await asyncio.start_server(_handle_client, host, port, limit=_RECV_BUF)
    _server_instance = server
    
    addr = server.sockets[0].getsockname()
    log.info(f'TG Proxy listening on {addr}')
    
    if stop_event:
        await stop_event.wait()
    else:
        async with server:
            await server.serve_forever()
    
    server.close()
    await server.wait_closed()
    await _ws_pool.cleanup()
    _server_instance = None

def run_proxy(port: int, dc_opt: Dict[int, str],
              stop_event: Optional[asyncio.Event] = None,
              host: str = '127.0.0.1'):
    try:
        asyncio.run(_run(port, dc_opt, stop_event, host))
    except KeyboardInterrupt:
        if stop_event:
            stop_event.set()
    except Exception as e:
        log.error(f"Proxy error: {e}")
        raise

if __name__ == '__main__':
    dc_opt = {
        1: '149.154.175.50',
        2: '149.154.167.220',
        3: '149.154.175.100',
        4: '149.154.167.91',
        5: '91.108.56.100',
    }
    run_proxy(1080, dc_opt)
