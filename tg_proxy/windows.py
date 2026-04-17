import sys
import socket
import subprocess

IS_FROZEN = getattr(sys, 'frozen', False)

def get_link_host(host: str) -> str:
    if host == '0.0.0.0':
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                return s.getsockname()[0]
        except:
            return '127.0.0.1'
    return host

def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(['clip.exe'], input=text.encode('utf-16le'), check=True)
        return True
    except:
        try:
            import ctypes
            ctypes.windll.user32.OpenClipboard(0)
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.SetClipboardData(13, ctypes.c_wchar_p(text))
            ctypes.windll.user32.CloseClipboard()
            return True
        except:
            return False
