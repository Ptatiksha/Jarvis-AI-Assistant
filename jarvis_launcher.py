"""Jarvis launcher: pehli baar Groq API key poochta hai (login jaisa), phir Jarvis shuru karta hai.
Key aapke laptop par ~/.jarvis_data/groq_key.txt me save hoti hai. Key badalni ho to wo file delete kar do."""
import os
import runpy
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

KEY_FILE = Path.home() / ".jarvis_data" / "groq_key.txt"


def get_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        if KEY_FILE.exists():
            key = KEY_FILE.read_text(encoding="utf-8").strip()
            if key:
                return key
    except OSError:
        pass

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    while True:
        key = simpledialog.askstring(
            "Jarvis Login",
            "Apni Groq API key paste karo (gsk_ se shuru hoti hai):",
            show="*",
            parent=root,
        )
        if key is None:
            root.destroy()
            sys.exit(0)
        key = key.strip()
        if key.startswith("gsk_") and len(key) > 20:
            break
        messagebox.showerror("Jarvis", "Key sahi nahi lag rahi. gsk_ se shuru hone wali poori key paste karo.", parent=root)
    KEY_FILE.parent.mkdir(exist_ok=True)
    KEY_FILE.write_text(key, encoding="utf-8")
    root.destroy()
    return key


os.environ["GROQ_API_KEY"] = get_key()
runpy.run_module("jarvis_mood_aware_v15", run_name="__main__")
