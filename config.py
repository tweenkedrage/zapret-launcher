from pathlib import Path
import os

BASE_DIR = Path(__file__).parent
APPDATA_DIR = Path(os.getenv('APPDATA')) / 'Zapret Launcher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
LISTS_DIR = APPDATA_DIR / "zapret_core" / "lists"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

CURRENT_VERSION = "3.2.1.9"
CURRENT_BUILD = "3223"

ZAPRET_VERSION_URL = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/docs/zapret_version.txt"
ZAPRET_CORE_URL = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/updater/full_zapret_core.zip"
