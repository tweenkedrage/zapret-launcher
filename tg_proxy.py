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
from typing import Dict, List, Optional, Set, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DEFAULT_PORT = 1080
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('tg-ws-proxy')

_TCP_NODELAY = True
_RECV_BUF = 262144
_SEND_BUF = 262144
_WS_POOL_SIZE = 8
_WS_POOL_MAX_AGE = 180.0

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
    1: ['149.154.175.50', '149.154.175.52', '149.154.175.53'],
    2: ['149.154.167.220', '149.154.167.151', '149.154.167.51'],
    3: ['149.154.175.100', '149.154.175.102'],
    4: ['149.154.167.91', '149.154.167.118', '149.154.167.92'],
    5: ['91.108.56.100', '91.108.56.102', '91.108.56.126'],
}

_dc_opt: Dict[int, Optional[str]] = {}
_ws_blacklist: Set[Tuple[int, bool]] = set()
_dc_fail_until: Dict[Tuple[int, bool], float] = {}
_DC_FAIL_COOLDOWN = 30.0

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
_ssl_ctx.set_ciphers('HIGH:!aNULL:!kRSA:!PSK:!SRP:!MD5:!RC4')
_ssl_ctx.options |= ssl.OP_NO_TICKET

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
        self._mask_cache = os.urandom(4)

    @staticmethod
    async def connect(ip: str, domain: str, path: str = '/apiws',
                      timeout: float = 8.0) -> 'RawWebSocket':
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
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(),
                                              timeout=timeout)
                if line in (b'\r\n', b'\n', b''):
                    break
                response_lines.append(
                    line.decode('utf-8', errors='replace').strip())
        except asyncio.TimeoutError:
            writer.close()
            raise

        if not response_lines:
            writer.close()
            raise WsHandshakeError(0, 'empty response')

        first_line = response_lines[0]
        parts = first_line.split(' ', 2)
        try:
            status_code = int(parts[1]) if len(parts) >= 2 else 0
        except ValueError:
            status_code = 0

        if status_code == 101:
            return RawWebSocket(reader, writer)

        headers: dict[str, str] = {}
        for hl in response_lines[1:]:
            if ':' in hl:
                k, v = hl.split(':', 1)
                headers[k.strip().lower()] = v.strip()

        writer.close()
        raise WsHandshakeError(status_code, first_line, headers,
                                location=headers.get('location'))

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
            opcode, payload = await self._read_frame()

            if opcode == self.OP_CLOSE:
                self._closed = True
                try:
                    reply = self._build_frame(
                        self.OP_CLOSE,
                        payload[:2] if payload else b'',
                        mask=True)
                    self.writer.write(reply)
                    await self.writer.drain()
                except Exception:
                    pass
                return None

            if opcode == self.OP_PING:
                try:
                    pong = self._build_frame(self.OP_PONG, payload,
                                             mask=True)
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
        try:
            self.writer.write(
                self._build_frame(self.OP_CLOSE, b'', mask=True))
            await self.writer.drain()
        except Exception:
            pass
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass

    @staticmethod
    def _build_frame(opcode: int, data: bytes,
                     mask: bool = False) -> bytes:
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
        hdr = await self.reader.readexactly(2)
        opcode = hdr[0] & 0x0F
        is_masked = bool(hdr[1] & 0x80)
        length = hdr[1] & 0x7F

        if length == 126:
            length = struct.unpack('>H',
                                   await self.reader.readexactly(2))[0]
        elif length == 127:
            length = struct.unpack('>Q',
                                   await self.reader.readexactly(8))[0]

        if is_masked:
            mask_key = await self.reader.readexactly(4)
            payload = await self.reader.readexactly(length)
            return opcode, _xor_mask(payload, mask_key)

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
    return (data[:5] == b'POST ' or data[:4] == b'GET ' or
            data[:5] == b'HEAD ' or data[:8] == b'OPTIONS ')

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
                msg_len = (
                    struct.unpack_from('<I', plain, pos + 1)[0] & 0xFFFFFF
                ) * 4
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

def _ws_domains(dc: int, is_media) -> List[str]:
    if is_media is None or is_media:
        return [f'kws{dc}-1.web.telegram.org', f'kws{dc}.web.telegram.org']
    return [f'kws{dc}.web.telegram.org', f'kws{dc}-1.web.telegram.org']

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

    def summary(self) -> str:
        return (f"total={self.connections_total} ws={self.connections_ws} "
                f"tcp_fb={self.connections_tcp_fallback} "
                f"http_skip={self.connections_http_rejected} "
                f"pass={self.connections_passthrough} "
                f"err={self.ws_errors} "
                f"pool={self.pool_hits}/{self.pool_hits+self.pool_misses} "
                f"up={_human_bytes(self.bytes_up)} "
                f"down={_human_bytes(self.bytes_down)}")

_stats = Stats()

class _WsPool:
    def __init__(self):
        self._idle: Dict[Tuple[int, bool], list] = {}
        self._refilling: Set[Tuple[int, bool]] = set()

    async def get(self, dc: int, is_media: bool,
                  target_ip: str, domains: List[str]
                  ) -> Optional[RawWebSocket]:
        key = (dc, is_media)
        now = time.monotonic()

        bucket = self._idle.get(key, [])
        while bucket:
            ws, created = bucket.pop(0)
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

    def _schedule_refill(self, key, target_ip, domains):
        if key in self._refilling:
            return
        self._refilling.add(key)
        asyncio.create_task(self._refill(key, target_ip, domains))

    async def _refill(self, key, target_ip, domains):
        dc, is_media = key
        try:
            bucket = self._idle.setdefault(key, [])
            needed = _WS_POOL_SIZE - len(bucket)
            if needed <= 0:
                return
            tasks = [asyncio.create_task(
                self._connect_one(target_ip, domains)) for _ in range(needed)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for ws in results:
                if isinstance(ws, RawWebSocket):
                    bucket.append((ws, time.monotonic()))
        finally:
            self._refilling.discard(key)

    @staticmethod
    async def _connect_one(target_ip, domains) -> Optional[RawWebSocket]:
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
    async def _quiet_close(ws):
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
                key = (dc, is_media)
                tasks.append(self._refill(key, target_ip, domains))
        await asyncio.gather(*tasks)

_ws_pool = _WsPool()

async def _bridge_ws(reader, writer, ws: RawWebSocket, label,
                     dc=None, dst=None, port=None, is_media=False,
                     splitter: _MsgSplitter = None):
    dc_tag = f"DC{dc}{'m' if is_media else ''}" if dc else "DC?"
    dst_tag = f"{dst}:{port}" if dst else "?"

    up_bytes = 0
    down_bytes = 0
    up_packets = 0
    down_packets = 0
    start_time = asyncio.get_event_loop().time()

    async def tcp_to_ws():
        nonlocal up_bytes, up_packets
        try:
            while True:
                chunk = await reader.read(_RECV_BUF)
                if not chunk:
                    break
                _stats.bytes_up += len(chunk)
                up_bytes += len(chunk)
                up_packets += 1
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

    async def ws_to_tcp():
        nonlocal down_bytes, down_packets
        try:
            while True:
                data = await ws.recv()
                if data is None:
                    break
                _stats.bytes_down += len(data)
                down_bytes += len(data)
                down_packets += 1
                writer.write(data)
                buf = writer.transport.get_write_buffer_size()
                if buf > _SEND_BUF // 2:
                    await writer.drain()
        except (asyncio.CancelledError, ConnectionError, OSError):
            pass

    tasks = [asyncio.create_task(tcp_to_ws()),
             asyncio.create_task(ws_to_tcp())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await ws.close()
        except:
            pass
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def _bridge_tcp(reader, writer, remote_reader, remote_writer,
                      label, dc=None, dst=None, port=None,
                      is_media=False):
    async def forward(src, dst_w, tag):
        try:
            while True:
                data = await src.read(_RECV_BUF)
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

async def _pipe(r, w):
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

def _socks5_reply(status):
    return bytes([0x05, status, 0x00, 0x01]) + b'\x00' * 6

async def _tcp_fallback(reader, writer, dst, port, init, label,
                        dc=None, is_media=False):
    try:
        rr, rw = await asyncio.wait_for(
            asyncio.open_connection(dst, port, limit=_RECV_BUF), timeout=8)
    except Exception as exc:
        return False

    _stats.connections_tcp_fallback += 1
    rw.write(init)
    await rw.drain()
    await _bridge_tcp(reader, writer, rr, rw, label,
                      dc=dc, dst=dst, port=port, is_media=is_media)
    return True

async def _handle_client(reader, writer):
    _stats.connections_total += 1
    peer = writer.get_extra_info('peername')
    label = f"{peer[0]}:{peer[1]}" if peer else "?"

    _set_sock_opts(writer.transport)

    try:
        hdr = await asyncio.wait_for(reader.readexactly(2), timeout=5)
        if hdr[0] != 5:
            writer.close()
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
            writer.close()
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
            writer.close()
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
                writer.close()
                return

            writer.write(_socks5_reply(0x00))
            await writer.drain()
            await _pipe(reader, rw)
            await _pipe(rr, writer)
            return

        writer.write(_socks5_reply(0x00))
        await writer.drain()

        try:
            init = await asyncio.wait_for(reader.readexactly(64), timeout=10)
        except asyncio.IncompleteReadError:
            return

        if _is_http_transport(init):
            _stats.connections_http_rejected += 1
            writer.close()
            return

        dc, is_media = _dc_from_init(init)
        init_patched = False
        
        if dc is None and dst in _IP_TO_DC:
            dc, is_media = _IP_TO_DC.get(dst)
            if dc in _dc_opt:
                init = _patch_init_dc(init, dc if is_media else -dc)
                init_patched = True

        if dc is None or dc not in _dc_opt:
            await _tcp_fallback(reader, writer, dst, port, init, label)
            return

        dc_key = (dc, is_media if is_media is not None else True)
        now = time.monotonic()
        media_tag = (" media" if is_media else (" media?" if is_media is None else ""))

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
            elif ws_failed_redirect:
                _dc_fail_until[dc_key] = now + _DC_FAIL_COOLDOWN
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

    except asyncio.TimeoutError:
        pass
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except:
            pass

_server_instance = None
_server_stop_event = None

async def _run(port: int, dc_opt: Dict[int, Optional[str]],
               stop_event: Optional[asyncio.Event] = None,
               host: str = '127.0.0.1'):
    global _dc_opt, _server_instance, _server_stop_event
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
    for dc in dc_opt.keys():
        ip = dc_opt.get(dc)
        log.info("    DC%d: %s", dc, ip)
    log.info("=" * 60)

    asyncio.create_task(_ws_pool.warmup(dc_opt))

    if stop_event:
        async def wait_stop():
            await stop_event.wait()
            server.close()
            await server.wait_closed()
        asyncio.create_task(wait_stop())

    async with server:
        try:
            await server.serve_forever()
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
                    default=['2:149.154.167.220', '4:149.154.167.220'],
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
    except Exception as e:
        print(f"TGProxy error: {e}")
    finally:
        loop.close()

if __name__ == '__main__':
    main()
