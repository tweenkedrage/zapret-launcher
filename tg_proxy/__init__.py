from .run import run_proxy
from .config import proxy_config
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR / 'tg_proxy'))
else:
    BASE_DIR = Path(__file__).parent.parent

__all__ = ["run_proxy", "proxy_config"]
