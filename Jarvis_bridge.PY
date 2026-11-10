"""Jarvis Bridge: website ko aapke laptop se jodta hai.
Isse volume, brightness, screenshot, file search, app kholna aur WhatsApp (sirf naam se) chalta hai.
Sirf aapke apne GitHub link (neeche ALLOWED) se aayi requests maani jaati hain."""
import json
import os
import re
import subprocess
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pyautogui
import pyperclip

pyautogui.FAILSAFE = False
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
ALLOWED = {o.strip() for o in os.environ.get(
    "JARVIS_ORIGINS", "https://ptatiksha.github.io,http://localhost:8000,http://127.0.0.1:8000").split(",") if o.strip()}
LOCK = threading.Lock()
STATE = {"shot": None, "found": None}
HOME = lambda: Path(os.environ.get("JARVIS_HOME") or Path.home())
PROTO = {"calculator": "calculator:", "calc": "calculator:", "settings": "ms-settings:", "setting": "ms-settings:",
         "camera": "microsoft.windows.camera:", "photos": "ms-photos:", "clock": "ms-clock:", "store": "ms-windows-store:",
         "microsoft store": "ms-windows-store:", "maps": "bingmaps:", "weather": "msnweather:", "whatsapp": "whatsapp:",
         "paint": "ms-paint:", "snipping tool": "ms-screenclip:", "spotify": "spotify:", "discord": "discord:", "teams": "msteams:"}


def press(key, times=1):
    for _ in range(times):
        pyautogui.press(key)


def volume(direction):
    press("volumeup" if direction == "up" else "volumedown", 5)


def brightness(value=None, delta=None):
    import screen_brightness_control as sbc
    current = sbc.get_brightness()[0]
    new = max(0, min(100, int(value) if value is not None else current + int(delta)))
    sbc.set_brightness(new)
    return {"value": new}


def screenshot():
    folder = HOME() / "Pictures"
    folder.mkdir(exist_ok=True)
    path = folder / f"jarvis_screenshot_{int(time.time())}.png"
    pyautogui.screenshot().save(str(path))
    STATE["shot"] = str(path)
    return {"path": str(path)}


def find_file(query, open_it=True):
    q = re.sub(r"\b(file|folder|pdf|dhundo|dhoondho|search|wali|wala|open|kholo|ki|ka|ko|karke)\b", " ", query or "", flags=re.I)
    words = q.lower().split()
    if not words:
        raise ValueError("File ka naam samajh nahi aaya.")
    best = None
    for root in [HOME() / d for d in ("Desktop", "Documents", "Downloads", "Pictures")]:
        if not root.exists():
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files + dirs:
                if all(w in name.lower() for w in words):
                    p = Path(base) / name
                    try:
                        m = p.stat().st_mtime
                    except OSError:
                        continue
                    if best is None or m > best[0]:
                        best = (m, p)
    if not best:
        raise ValueError("Is naam ki file nahi mili.")
    STATE["found"] = str(best[1])
    if open_it:
        os.startfile(str(best[1]))
    return {"path": str(best[1]), "name": best[1].name}


def open_folder(name):
    os.startfile(str(HOME() / name))


def open_app(name):
    name = " ".join(re.sub(r"\b(open|kholo|chalao|start|app)\b", " ", name or "", flags=re.I).split()).lower()
    if not name:
        raise ValueError("Kaunsa app kholna hai?")
    if name in PROTO:
        os.startfile(PROTO[name])
        return {"found": True, "name": name}
    roots = [Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
             Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs", HOME() / "Desktop"]
    best = None
    for root in roots:
        if root.exists():
            for p in root.rglob("*"):
                if p.suffix.lower() in (".lnk", ".exe"):
                    stem = p.stem.lower()
                    score = 1.0 if name == stem else 0.9 if name in stem else SequenceMatcher(None, name, stem).ratio()
                    if best is None or score > best[0]:
                        best = (score, p)
    if best and best[0] >= 0.7:
        os.startfile(str(best[1]))
        return {"found": True, "name": best[1].stem}
    return {"found": False}


def open_url(url):
    if not re.match(r"^https?://", url or ""):
        raise ValueError("Sirf http/https link khul sakte hain.")
    webbrowser.open(url)


def youtube_id(query):
    """Pehle video ka id YouTube search se nikalta hai (video filter ke saath)."""
    import urllib.parse
    import urllib.request
    url = "https://www.youtube.com/results?sp=EgIQAQ%3D%3D&search_query=" + urllib.parse.quote(query or "")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    m = re.search(r'"videoId":"([\w-]{11})"', html)
    if not m:
        raise ValueError("Video nahi mila.")
    return m.group(1)


def youtube_play(query):
    webbrowser.open("https://www.youtube.com/watch?v=" + youtube_id(query))


def _wa_open_chat(contact):
    try:
        os.startfile("whatsapp:")
    except Exception:
        subprocess.Popen(["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getWindowsWithTitle("WhatsApp") if w.title]
        if wins:
            if wins[0].isMinimized:
                wins[0].restore()
            wins[0].activate()
            time.sleep(1)
    except Exception:
        pass
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    pyperclip.copy(contact)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2.0)
    pyautogui.press("enter")
    time.sleep(1.5)


def whatsapp_message(contact, message):
    if not contact or not message:
        raise ValueError("Contact ya message khali hai.")
    _wa_open_chat(contact)
    pyperclip.copy(message)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(1.0)


def whatsapp_file(contact, source=None, query=None):
    if source == "screenshot":
        path = STATE["shot"] if STATE["shot"] and Path(STATE["shot"]).exists() else screenshot()["path"]
    elif source == "found":
        path = STATE["found"]
    else:
        path = find_file(query, open_it=False)["path"]
    if not path or not Path(path).exists():
        raise ValueError("Bhejne wali file nahi mili.")
    _wa_open_chat(contact)
    safe = str(Path(path).resolve()).replace("'", "''")
    subprocess.run(["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Path '{safe}'"], check=True, timeout=20)
    time.sleep(0.8)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(3.0)
    pyautogui.press("enter")
    time.sleep(1.0)


def sys_action(name):
    if name == "minimize":
        pyautogui.hotkey("win", "d")
    elif name == "close_window":
        pyautogui.hotkey("alt", "f4")
    elif name == "lock":
        import ctypes
        ctypes.windll.user32.LockWorkStation()
    elif name in ("enter", "backspace"):
        press(name)
    elif name == "playpause":
        press("playpause")
    elif name == "mute":
        press("volumemute")
    else:
        raise ValueError("Ye system action maujood nahi hai.")


def run(d):
    a = d.get("action")
    extra = {}
    if a == "volume":
        volume(d.get("dir"))
    elif a == "brightness":
        extra = brightness(d.get("value"), d.get("delta"))
    elif a == "screenshot":
        extra = screenshot()
    elif a == "find_file":
        extra = find_file(d.get("query"), d.get("open", True))
    elif a == "open_folder":
        open_folder(d.get("name", "Desktop"))
    elif a == "open_app":
        extra = open_app(d.get("name"))
    elif a == "open_url":
        open_url(d.get("url"))
    elif a == "youtube_id":
        extra = {"id": youtube_id(d.get("query"))}
    elif a == "youtube_play":
        youtube_play(d.get("query"))
    elif a == "whatsapp_message":
        whatsapp_message(d.get("contact"), d.get("message"))
    elif a == "whatsapp_file":
        whatsapp_file(d.get("contact"), d.get("source"), d.get("query"))
    elif a == "sys":
        sys_action(d.get("name"))
    elif a == "type":
        pyautogui.write(str(d.get("text", "")), interval=0.04)
    else:
        raise ValueError("Unknown action")
    return {"ok": True, **extra}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _allowed(self):
        return self.headers.get("Origin", "") in ALLOWED

    def _send(self, code, body=None):
        self.send_response(code)
        if self._allowed():
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        data = json.dumps(body or {}).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204 if self._allowed() else 403)

    def do_GET(self):
        if not self._allowed():
            return self._send(403, {"ok": False, "error": "Origin allowed nahi hai."})
        self._send(200, {"ok": True, "name": "Jarvis Bridge"})

    def do_POST(self):
        if not self._allowed():
            return self._send(403, {"ok": False, "error": "Origin allowed nahi hai."})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            with LOCK:
                result = run(body)
            self._send(200, result)
        except ValueError as error:
            self._send(200, {"ok": False, "error": str(error)})
        except Exception as error:
            print("ERROR:", repr(error))
            self._send(200, {"ok": False, "error": "Laptop par ye kaam nahi ho paya."})


if __name__ == "__main__":
    print("=" * 50)
    print(" JARVIS BRIDGE chalu hai (port %d)" % PORT)
    print(" Is window ko band mat karo. Ab website se laptop control hoga.")
    print("=" * 50)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
