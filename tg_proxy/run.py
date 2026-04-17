import asyncio
import logging
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR / 'tg_proxy'))
else:
    BASE_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(BASE_DIR))

from tg_proxy.tg_ws_proxy import _run, proxy_config
from tg_proxy.utils import get_link_host
from tg_proxy.config import parse_dc_ip_list

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('tg-proxy-runner')

def get_tg_link(host: str, port: int, secret: str) -> str:
    link_host = get_link_host(host)
    return f"tg://proxy?server={link_host}&port={port}&secret={secret}"

async def run_with_link(host: str = '127.0.0.1', port: int = 1080, secret: str = None, stop_event: asyncio.Event = None):
    proxy_config.host = host
    proxy_config.port = port
    
    if secret:
        proxy_config.secret = secret
    else:
        proxy_config.secret = os.urandom(16).hex()
    proxy_config.dc_redirects = {
        2: '149.154.167.220',
    }
    proxy_config.buffer_size = 256 * 1024
    proxy_config.pool_size = 4
    proxy_config.fallback_cfproxy = False
    proxy_config.fake_tls_domain = ''
    
    print("\n" + "=" * 60)
    print("  TELEGRAM MTPROTO PROXY")
    print("=" * 60)
    print(f"  Server: {host}:{port}")
    print(f"  Secret: {proxy_config.secret}")
    print("\n  Link start proxy:")
    link = get_tg_link(host, port, proxy_config.secret)
    print(f"\n  {link}")
    print("\n" + "=" * 60)
    print("=" * 60 + "\n")
    await _run(stop_event)

def run_proxy(host: str = '127.0.0.1', port: int = 1080, secret: str = None, stop_event: asyncio.Event = None):
    try:
        asyncio.run(run_with_link(host, port, secret, stop_event))
    except KeyboardInterrupt:
        print("\nProxy stopped")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    run_proxy()
