from __future__ import annotations
import argparse
import asyncio
import base64
import logging
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('tg-ws-proxy')

_TCP_NODELAY = True
_RECV_BUF = 262144
_SEND_BUF = 262144
_WS_POOL_SIZE = 16
_WS_POOL_MAX_AGE = 180.0
_MAX_MSG_SIZE = 1024 * 1024
_HEARTBEAT_INTERVAL = 30.0
_CONNECTION_TIMEOUT = 30.0
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0
_DC_FAIL_COOLDOWN = 15.0

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

_dc_opt: Dict[int, Optional[str]] = {}
_ws_blacklist: Set[Tuple[int, bool]] = set()
_dc_fail_until: Dict[Tuple[int, bool], float] = {}

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
_ssl_ctx.set_ciphers('HIGH:!aNULL:!kRSA:!PSK:!SRP:!MD5:!RC4')
_ssl_ctx.options |= ssl.OP_NO_TICKET

def is_port_available(host: str, port: int) -> bool:
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex((host, port))
        return result != 0
    finally:
        sock.close()

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
    except OSError:
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

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self._closed = False
        self._last_heartbeat = time.monotonic()
        self._heartbeat_task = None

    async def _heartbeat(self):
        while not self._closed:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._closed:
                    break
                if time.monotonic() - self._last_heartbeat > _HEARTBEAT_INTERVAL * 2:
                    break
                await self.ping()
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
                      timeout: float = 8.0) -> 'RawWebSocket':
        reader = writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 443, ssl=_ssl_ctx,
                                        server_hostname=domain,
                                        limit=_RECV_BUF),
                timeout=min(timeout, 8))
            _set_sock_opts(writer.transport)

            ws_key = base64.b64encode(os.urandom(16)).decode()
            req = (
                f'GET {path} HTTP/1.1\r\n'
                f'Host: {domain}\r\n'
                f'Upgrade: websocket\r\n'
                f'Connection: Upgrade\r\n'
                f'Sec-WebSocket-Key: {ws_key}\r\n'
                f'Sec-WebSocket-Version: 13\r\n'
                f'Sec-WebSocket-Protocol: binary\r\n'
                f'Origin: https://web.telegram.org\r\n'
                f'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                f'AppleWebKit/537.36 (KHTML, like Gecko) '
                f'Chrome/131.0.0.0 Safari/537.36\r\n'
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
                return ws

            headers: dict[str, str] = {}
            for hl in response_lines[1:]:
                if ':' in hl:
                    k, v = hl.split(':', 1)
                    headers[k.strip().lower()] = v.strip()

            raise WsHandshakeError(status_code, first_line, headers,
                                    location=headers.get('location'))
        except Exception:
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
            raise

    async def send(self, data: bytes):
        if self._closed:
            raise ConnectionError("WebSocket closed")
        frame = self._build_frame(self.OP_BINARY, data, mask=True)
        self.writer.write(frame)
        await self.writer.drain()

    async def send_batch(self, parts: List[bytes]):
        if self._closed:
            raise ConnectionError("WebSocket closed")
        frames = bytearray()
        for part in parts:
            frames.extend(self._build_frame(self.OP_BINARY, part, mask=True))
        self.writer.write(frames)
        await self.writer.drain()

    async def recv(self) -> Optional[bytes]:
        while not self._closed:
            try:
                opcode, payload = await asyncio.wait_for(
                    self._read_frame(), timeout=10.0)
                self._last_heartbeat = time.monotonic()
            except asyncio.TimeoutError:
                self._closed = True
                return None
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
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except:
                pass
        try:
            self.writer.write(self._build_frame(self.OP_CLOSE, b'', mask=True))
            await self.writer.drain()
        except Exception:
            pass
        try:
            self.writer.close()
            await self.writer.wait_closed()
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
    try:
        n = struct.unpack('!I', _socket.inet_aton(ip))[0]
        return any(lo <= n <= hi for lo, hi in _TG_RANGES)
    except OSError:
        return False

def _is_http_transport(data: bytes) -> bool:
    http_methods = [b'POST ', b'GET ', b'HEAD ', b'OPTIONS ', b'PUT ', b'DELETE ']
    if any(data.startswith(m) for m in http_methods):
        if b'Upgrade: websocket' not in data:
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
    def __init__(self, init_data: bytes):
        key_raw = bytes(init_data[8:40])
        iv = bytes(init_data[40:56])
        cipher = Cipher(algorithms.AES(key_raw), modes.CTR(iv))
        self._dec = cipher.encryptor()
        self._dec.update(b'\x00' * 64)

    def split(self, chunk: bytes) -> List[bytes]:
        plain = self._dec.update(chunk)
        boundaries = []
        pos = 0
        while pos < len(plain):
            first = plain[pos]
            if first == 0x7f:
                if pos + 4 > len(plain):
                    break
                msg_len = (struct.unpack_from('<I', plain, pos + 1)[0] & 0xFFFFFF) * 4
                if msg_len > _MAX_MSG_SIZE:
                    msg_len = _MAX_MSG_SIZE
                pos += 4
            else:
                msg_len = first * 4
                pos += 1
            if msg_len == 0 or pos + msg_len > len(plain):
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

def _ws_domains(dc: int, is_media: Optional[bool]) -> List[str]:
    if is_media is None or is_media:
        return [f'kws{dc}-1.web.telegram.org', f'kws{dc}.web.telegram.org', f'kws{dc}-2.web.telegram.org']
    return [f'kws{dc}.web.telegram.org', f'kws{dc}-1.web.telegram.org', f'kws{dc}-2.web.telegram.org']

class Stats:
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
        self.start_time = time.time()

    def summary(self) -> str:
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
                f"up={_human_bytes(self.bytes_up)} "
                f"down={_human_bytes(self.bytes_down)}")

_stats = Stats()

class _WsPool:
    def __init__(self):
        self._idle: Dict[Tuple[int, bool], deque] = {}
        self._refilling: Set[Tuple[int, bool]] = set()
        self._lock = asyncio.Lock()

    async def get(self, dc: int, is_media: bool,
                  target_ip: str, domains: List[str]
                  ) -> Optional[RawWebSocket]:
        key = (dc, is_media)
        now = time.monotonic()

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
            
            tasks = [asyncio.create_task(
                self._connect_one(target_ip, domains)) for _ in range(needed)]
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
    async def _connect_one(target_ip: str, domains: List[str]) -> Optional[RawWebSocket]:
        for domain in domains:
            try:
                ws = await RawWebSocket.connect(target_ip, domain, timeout=5)
                return ws
            except WsHandshakeError as exc:
                if exc.is_redirect:
                    continue
                return None
            except Exception:
                return None
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

_ws_pool = _WsPool()

async def _bridge_ws(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                     ws: RawWebSocket, label: str,
                     dc: Optional[int] = None, dst: Optional[str] = None, 
                     port: Optional[int] = None, is_media: bool = False,
                     splitter: Optional[_MsgSplitter] = None):
    
    _stats.active_connections += 1
    tcp_to_ws_task = None
    ws_to_tcp_task = None
    
    async def tcp_to_ws():
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(_RECV_BUF), timeout=_CONNECTION_TIMEOUT)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                _stats.bytes_up += len(chunk)
                if splitter:
                    parts = splitter.split(chunk)
                    if len(parts) > 1:
                        await ws.send_batch(parts)
                    else:
                        await ws.send(parts[0])
                else:
                    await ws.send(chunk)
        except (asyncio.CancelledError, ConnectionError, OSError):
            pass
        except Exception as e:
            log.debug(f"tcp_to_ws error: {e}")
        finally:
            try:
                await ws.close()
            except:
                pass

    async def ws_to_tcp():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(ws.recv(), timeout=_CONNECTION_TIMEOUT)
                except asyncio.TimeoutError:
                    break
                if data is None:
                    break
                _stats.bytes_down += len(data)
                writer.write(data)
                buf = writer.transport.get_write_buffer_size()
                if buf > _SEND_BUF // 2:
                    await writer.drain()
        except (asyncio.CancelledError, ConnectionError, OSError):
            pass
        except Exception as e:
            log.debug(f"ws_to_tcp error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
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
                    await asyncio.wait_for(task, timeout=1.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
                except Exception:
                    pass
        
        try:
            await ws.close()
        except:
            pass
        
        try:
            writer.close()
            await writer.wait_closed()
        except:
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
                    data = await asyncio.wait_for(src.read(_RECV_BUF), timeout=_CONNECTION_TIMEOUT)
                except asyncio.TimeoutError:
                    break
                if not data:
                    break
                if 'up' in tag:
                    _stats.bytes_up += len(data)
                else:
                    _stats.bytes_down += len(data)
                dst_w.write(data)
                await dst_w.drain()
        except asyncio.CancelledError:
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
            data = await r.read(_RECV_BUF)
            if not data:
                break
            w.write(data)
            await w.drain()
    except asyncio.CancelledError:
        pass
    finally:
        try:
            w.close()
            await w.wait_closed()
        except:
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
    _stats.connections_total += 1
    peer = writer.get_extra_info('peername')
    label = f"{peer[0]}:{peer[1]}" if peer else "?"

    _set_sock_opts(writer.transport)

    try:
        hdr = await asyncio.wait_for(reader.readexactly(2), timeout=5)
        if hdr[0] != 5:
            return
        nmethods = hdr[1]
        await reader.readexactly(nmethods)
        writer.write(b'\x05\x00')
        await writer.drain()

        req = await asyncio.wait_for(reader.readexactly(4), timeout=5)
        _ver, cmd, _rsv, atyp = req
        if cmd != 1:
            writer.write(_socks5_reply(0x07))
            await writer.drain()
            return

        if atyp == 1:
            raw = await reader.readexactly(4)
            dst = _socket.inet_ntoa(raw)
        elif atyp == 3:
            dlen = (await reader.readexactly(1))[0]
            dst = (await reader.readexactly(dlen)).decode()
        else:
            writer.write(_socks5_reply(0x08))
            await writer.drain()
            return

        port = struct.unpack('!H', await reader.readexactly(2))[0]

        if not _is_telegram_ip(dst):
            _stats.connections_passthrough += 1
            try:
                rr, rw = await asyncio.wait_for(
                    asyncio.open_connection(dst, port, limit=_RECV_BUF), timeout=8)
            except Exception:
                writer.write(_socks5_reply(0x05))
                await writer.drain()
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
                        except asyncio.CancelledError:
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

        dc, is_media = _dc_from_init(init)
        init_patched = False
        
        if dc is None and dst and dst in _IP_TO_DC:
            result = _IP_TO_DC.get(dst)
            if result:
                dc, is_media = result
                if dc in _dc_opt:
                    init = _patch_init_dc(init, dc if is_media else -dc)
                    init_patched = True

        if dc is None or dc not in _dc_opt:
            await _tcp_fallback(reader, writer, dst, port, init, label)
            return

        dc_key = (dc, is_media if is_media is not None else True)
        now = time.monotonic()

        if dc_key in _ws_blacklist:
            await _tcp_fallback(reader, writer, dst, port, init,
                                     label, dc=dc, is_media=is_media)
            return

        fail_until = _dc_fail_until.get(dc_key, 0)
        if now < fail_until:
            await _tcp_fallback(reader, writer, dst, port, init,
                                     label, dc=dc, is_media=is_media)
            return

        domains = _ws_domains(dc, is_media)
        target = _dc_opt[dc]
        ws = None
        ws_failed_redirect = False
        all_redirects = True

        ws = await _ws_pool.get(dc, is_media, target, domains)
        if not ws:
            for domain in domains:
                try:
                    ws = await RawWebSocket.connect(target, domain, timeout=6)
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

            await _tcp_fallback(reader, writer, dst, port, init,
                                     label, dc=dc, is_media=is_media)
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
                         dc=dc, dst=dst, port=port, is_media=is_media,
                         splitter=splitter)

    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        pass
    except ConnectionResetError:
        pass
    except Exception as e:
        log.debug(f"Error in _handle_client: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

_server_instance = None
_server_stop_event = None

async def _run(port: int, dc_opt: Dict[int, Optional[str]],
               stop_event: Optional[asyncio.Event] = None,
               host: str = '127.0.0.1'):
    global _dc_opt, _server_instance, _server_stop_event
    
    if not is_port_available(host, port):
        log.error(f"Port {port} is already in use on {host}")
        return
    
    _dc_opt = dc_opt
    _server_stop_event = stop_event

    server = await asyncio.start_server(
        _handle_client, host, port, limit=_RECV_BUF)
    _server_instance = server

    for sock in server.sockets:
        try:
            sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass

    log.info("=" * 60)
    log.info("  Telegram WS Bridge Proxy (Optimized)")
    log.info("  Listening on   %s:%d", host, port)
    log.info("  Target DC IPs:")
    for dc in sorted(dc_opt.keys()):
        ip = dc_opt.get(dc)
        log.info("    DC%d: %s", dc, ip)
    log.info("  Pool size: %d, Cooldown: %.1fs", _WS_POOL_SIZE, _DC_FAIL_COOLDOWN)
    log.info("=" * 60)
    log_stats_task = None
    
    async def log_stats():
        try:
            while True:
                await asyncio.sleep(60)
                log.info("Stats: %s", _stats.summary())
        except asyncio.CancelledError:
            pass
    
    warmup_task = asyncio.create_task(_ws_pool.warmup(dc_opt))
    
    if stop_event:
        await stop_event.wait()
        log.info("Shutting down gracefully...")
        
        if log_stats_task:
            log_stats_task.cancel()
            try:
                await log_stats_task
            except asyncio.CancelledError:
                pass
        
        if not warmup_task.done():
            warmup_task.cancel()
            try:
                await warmup_task
            except asyncio.CancelledError:
                pass
        
        server.close()
        await server.wait_closed()
        await asyncio.sleep(2)
        await _ws_pool.cleanup()
        
        log.info("Final stats: %s", _stats.summary())
    else:
        if warmup_task and not warmup_task.done():
            await warmup_task
        
        log_stats_task = asyncio.create_task(log_stats())
        
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            if log_stats_task and not log_stats_task.done():
                log_stats_task.cancel()
                try:
                    await log_stats_task
                except asyncio.CancelledError:
                    pass
    
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
        description='Telegram Desktop WebSocket Bridge Proxy (Optimized)')
    ap.add_argument('--port', type=int, default=DEFAULT_PORT,
                    help=f'Listen port (default {DEFAULT_PORT})')
    ap.add_argument('--host', type=str, default='127.0.0.1',
                    help='Listen host (default 127.0.0.1)')
    ap.add_argument('--dc-ip', metavar='DC:IP', action='append',
                    default=[
                        '1:149.154.175.50', '1:149.154.175.52', '1:149.154.175.53',
                        '2:149.154.167.220', '2:149.154.167.151', '2:149.154.167.51',
                        '3:149.154.175.100', '3:149.154.175.102',
                        '4:149.154.167.91', '4:149.154.167.118', '4:149.154.167.92',
                        '5:91.108.56.100', '5:91.108.56.102', '5:91.108.56.126'
                    ],
                    help='Target IP for a DC, e.g. --dc-ip 1:149.154.175.205'
                         ' --dc-ip 2:149.154.167.220')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='Debug logging')
    args = ap.parse_args()

    try:
        dc_opt = parse_dc_ip_list(args.dc_ip)
    except ValueError as e:
        log.error(str(e))
        sys.exit(1)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s  %(levelname)-5s  %(message)s',
        datefmt='%H:%M:%S',
    )

    try:
        asyncio.run(_run(args.port, dc_opt, host=args.host))
    except KeyboardInterrupt:
        log.info("Shutting down. Final stats: %s", _stats.summary())

async def _run_async(port: int, dc_opt: Dict[int, Optional[str]],
                      stop_event: Optional[asyncio.Event] = None,
                      host: str = '127.0.0.1'):
    await _run(port, dc_opt, stop_event, host)

def run_proxy_async(port: int, dc_opt: Dict[int, str],
                     stop_event: Optional[asyncio.Event] = None,
                     host: str = '127.0.0.1'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_async(port, dc_opt, stop_event, host))
    except KeyboardInterrupt:
        print("\nShutting down...")
        if stop_event:
            stop_event.set()
        loop.run_until_complete(asyncio.sleep(1))
    except Exception as e:
        print(f"TGProxy error: {e}")
    finally:
        loop.close()

if __name__ == '__main__':
    main()
