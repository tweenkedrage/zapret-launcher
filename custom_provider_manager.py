import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / 'ZapretLauncher'
CUSTOM_PROVIDER_FILE = APPDATA_DIR / "custom_provider.json"

def load_custom_provider() -> Optional[Dict[str, Any]]:
    try:
        if CUSTOM_PROVIDER_FILE.exists():
            with open(CUSTOM_PROVIDER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_custom_provider(name: str, params: List[str]) -> bool:
    try:
        data = {
            "name": name,
            "params": params,
            "created": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(CUSTOM_PROVIDER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        pass
        return False

def delete_custom_provider() -> bool:
    try:
        if CUSTOM_PROVIDER_FILE.exists():
            CUSTOM_PROVIDER_FILE.unlink()
            return True
    except Exception:
        pass
    return False
