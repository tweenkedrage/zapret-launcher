from pathlib import Path
import os

BASE_DIR = Path(__file__).parent
APPDATA_DIR = Path(os.getenv('APPDATA')) / 'Zapret Launcher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

CURRENT_VERSION = "3.2.1.7"
CURRENT_BUILD = "3218"

ZAPRET_VERSION_URL = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/docs/zapret_version.txt"
ZAPRET_CORE_URL = "https://raw.githubusercontent.com/tweenkedrage/zapret-launcher/main/updater/zapret_core.zip"
