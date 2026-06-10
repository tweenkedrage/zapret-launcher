# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

from pathlib import Path
import os

BASE_DIR = Path(__file__).parent
APPDATA_DIR = Path(os.getenv('APPDATA')) / 'Zapret Launcher'
CONFIG_FILE = APPDATA_DIR / 'config.json'
LISTS_DIR = APPDATA_DIR / "zapret_core" / "lists"
ZAPRET_CORE_DIR = APPDATA_DIR / "zapret_core"

CURRENT_VERSION = "3.2.1.9"
CURRENT_BUILD = "3373"

TG_HOST = "127.0.0.1"
TG_PORT = 1443
TG_FAKE_TLS = True
TG_FAKE_TLS_DOMAIN = "www.google.com"

ZAPRET_VERSION_URL = "https://zapret-launcher.ru/updater/docs/zapret_version.txt"
ZAPRET_CORE_URL = "https://zapret-launcher.ru/updater/full_zapret_core.zip"
