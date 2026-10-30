import asyncio
import os
import re
import tempfile
import datetime
import time
import threading
import webbrowser
import urllib.parse
import requests
import ctypes
import hashlib
import math
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
    GUI_AVAILABLE = True
except ImportError:
    ctk = None
    GUI_AVAILABLE = False

import edge_tts
import pygame
import speech_recognition as sr
import pyautogui
import pyperclip
import psutil
import pywhatkit

from fpdf import FPDF
from openai import OpenAI

# Browser automation for REAL WhatsApp Web / Gmail interaction.
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False



# ============================================================
# JARVIS CONFIGURATION
# ============================================================

pyautogui.FAILSAFE = False

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = "openai/gpt-oss-120b"

client = OpenAI(
    api_key=GROQ_API_KEY or "missing-api-key",
    base_url="https://api.groq.com/openai/v1"
)


# ============================================================
# JARVIS AI PERSONALITY + MEMORY
# ============================================================

messages = [
    {
        "role": "system",
        "content": (
            "Tumhara naam Jarvis hai. "
            "Tum ek smart, calm, friendly aur natural AI voice assistant ho. "
            "Robotic ya template jaisa mat bolo; context ke hisab se natural conversational phrasing use karo. "
            "Har reply ko greeting se start mat karo aur user ki baat ko unnecessarily repeat mat karo. "
            "Agar simple acknowledgement enough ho to seedha short acknowledgement do. "
            "User confused ho to simple step-by-step explain karo. "
            "User se natural human assistant ki tarah baat karo. "
            "Reply user ki language ke according karo. "
            "English question ka English mein answer do. "
            "Hindi question ka Hindi mein answer do. "
            "Hinglish question ka natural Hinglish mein answer do. "
            "Marathi question ka Marathi mein answer do. "
            "Normal answers short, clear and conversational rakho. "
            "Usually 2 se 4 sentences mein answer do. "
            "Study ya programming question mein zarurat ho to properly explain karo. "
            "Calculations ka exact answer do. "
            "Response voice mein bola jayega, isliye natural spoken sentences use karo. "
            "Unnecessary markdown, stars, hashes aur headings mat use karo. "
            "Agar user follow-up question pooche to recent conversation context ka use karo. "
            "Agar context insufficient ho to guess karne ke bajay clarification maango. "
            "Sensitive actions kabhi user confirmation ke bina execute karne ko mat kaho. "
            "MOOD-AWARE CONVERSATION: User ke words aur context se unka possible mood samjho, lekin certainty ka claim mat karo. "
            "Agar user gusse mein lage, calmly acknowledge karo, argue ya lecture mat karo, aur poochho kya hua ya kis tarah help karun. "
            "Agar user sad, lonely, disappointed ya upset lage, pehle empathy dikhao, unki feeling ko dismiss mat karo, aur gently poochho woh share karna chahte hain ya distraction chahte hain. "
            "Agar user happy ya excited ho, unki energy ko naturally match karo aur poochho kya achha hua; overdo mat karo. "
            "Agar user bimar ya pain mein hone ki baat kare, caring response do, simple safe suggestion do, diagnosis ya medicine prescribe mat karo; severe/unusual symptoms mein trusted adult/medical professional ko batane ko kaho. "
            "Agar user tired/stressed/confused ho, short supportive reply aur ek manageable next step do. "
            "Agar mood clear na ho, assume mat karo; normal friendly response do. "
            "Agar user apne mood ke saath koi task bhi bole, dono ka dhyan rakho: pehle brief caring acknowledgement, phir task ko handle karo. "
            "Mood ko user ke against use mat karo, unki feeling ka mazaak mat banao, aur baar-baar mood label mat karo."
        )
    }
]


# ============================================================
# SPEECH RECOGNITION
# ============================================================

recognizer = sr.Recognizer()

recognizer.pause_threshold = 0.8
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

speech_lock = threading.Lock()


# ============================================================
# EDGE TTS VOICES
# ============================================================

HINDI_VOICE = "hi-IN-MadhurNeural"

ENGLISH_VOICE = "en-IN-PrabhatNeural"


# ============================================================
# EDGE TTS AUDIO GENERATOR
# ============================================================

async def generate_speech(text, output_file, voice):

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+12%",
        pitch="+0Hz"
    )

    await communicate.save(output_file)


# ============================================================
# VOICE SELECTION
# ============================================================

def select_voice(text):

    # Hindi / Marathi Devanagari
    if re.search(r"[\u0900-\u097F]", text):
        return HINDI_VOICE

    # English / Roman Hinglish
    return ENGLISH_VOICE


# ============================================================
# PROFESSIONAL GUI HOOKS
# ============================================================

GUI_APP = None

def gui_status(state, detail=None):
    app = globals().get("GUI_APP")
    if app is not None:
        try:
            app.set_state(state, detail)
        except Exception:
            pass

def gui_log(role, text):
    app = globals().get("GUI_APP")
    if app is not None:
        try:
            app.add_message(role, str(text))
        except Exception:
            pass

# ============================================================
# SPEAK
# ============================================================

def speak(text):

    if text is None:
        return

    clean_text = str(text).strip()

    if not clean_text:
        return

    # Remove markdown
    clean_text = clean_text.replace("*", "")
    clean_text = clean_text.replace("#", "")
    clean_text = clean_text.replace("`", "")
    clean_text = clean_text.replace("_", " ")

    # Make maths sound natural
    clean_text = clean_text.replace("+", " plus ")
    clean_text = clean_text.replace("=", " equals ")
    clean_text = clean_text.replace("×", " multiplied by ")
    clean_text = clean_text.replace("÷", " divided by ")
    clean_text = clean_text.replace("%", " percent ")

    print("\nJarvis:", clean_text)
    gui_log("JARVIS", clean_text)
    gui_status("SPEAKING", clean_text[:90])

    voice = select_voice(clean_text)

    # Unique temp file
    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"jarvis_{threading.get_ident()}.mp3"
    )

    with speech_lock:

        try:

            if pygame.mixer.get_init():

                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

            asyncio.run(
                generate_speech(
                    clean_text,
                    temp_path,
                    voice
                )
            )

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(temp_path)

            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)

            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

        except Exception as error:

            print("\nVOICE ERROR:", error)

        finally:

            if os.path.exists(temp_path):

                try:
                    os.remove(temp_path)

                except OSError:
                    pass

    time.sleep(0.3)


# ============================================================
# AI FUNCTION
# ============================================================

def ask_ai(question):

    try:

        if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":

            return (
                "Groq API key set nahi hai. Windows CMD mein GROQ_API_KEY environment variable set karke Jarvis dobara run karo."
            )

        print("\nJarvis soch raha hai...")

        messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.45,
            max_tokens=240
        )

        reply = response.choices[0].message.content

        if not reply:
            return "Mujhe iska answer nahi mila."

        reply = reply.strip()

        messages.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        # Keep recent conversation memory
        if len(messages) > 17:

            system_message = messages[0]

            recent_messages = messages[-14:]

            messages.clear()

            messages.append(system_message)

            messages.extend(recent_messages)

        return reply

    except Exception as error:

        print("\nAI ERROR:", error)

        return (
            "AI se connect karne mein problem aa rahi hai."
        )


def local_mood_response(user_text):
    """Small offline fallback for emotional messages when no AI API key is configured."""
    t = clean_command(user_text).lower()
    if not t:
        return None

    anger = ["gussa", "gusse", "angry", "furious", "irritate", "irritated", "bahut gussa", "dimag kharab"]
    sad = ["sad", "dukhi", "udaas", "bura lag", "rona", "ro rahi", "ro raha", "lonely", "akela", "akeli", "upset", "dil kharab", "mood kharab", "depressed"]
    happy = ["happy", "khush", "excited", "maza aa", "bahut achha", "good news", "i am great", "mast mood"]
    sick = ["bimar", "beemar", "tabiyat kharab", "sar dukh", "sir dukh", "headache", "bukhar", "fever", "pain ho", "dard ho", "nausea", "ulti"]
    tired = ["thak gayi", "thak gaya", "tired", "exhausted", "stress", "stressed", "tension", "overwhelmed"]
    confused = ["confused", "samajh nahi aa", "kya karun", "pata nahi kya karun", "pareshan"]

    if any(x in t for x in anger):
        return "Lagta hai kuch tumhe bahut irritate kar raha hai. Main calmly sun sakta hoon—kya hua, ya abhi tumhe kis tarah ki help chahiye?"
    if any(x in t for x in sad):
        return "Mujhe afsos hai ki tum aisa feel kar rahi ho. Agar tum chaho toh bata sakti ho kya hua; ya hum kisi light topic ya music se thoda mind divert kar sakte hain."
    if any(x in t for x in happy):
        return "Arey wah, ye sunkar achha laga! Kya special hua? Batao, main sun raha hoon."
    if any(x in t for x in sick):
        return "Oh, apna dhyan rakho. Kya symptoms ya takleef ho rahi hai? Agar dard bahut tez ya achanak shuru hua hai, ya saath mein vision problem, confusion, fever ya vomiting hai, toh kisi trusted adult ko abhi batao aur medical help lo."
    if any(x in t for x in tired):
        return "Lagta hai tum kaafi thak ya stress feel kar rahi ho. Agar possible ho toh thoda break aur paani le lo. Chaho toh hum ek chhota sa next step saath mein decide kar sakte hain."
    if any(x in t for x in confused):
        return "Koi baat nahi, ek-ek step karke dekhte hain. Tum mujhe situation thodi si batao; main options simple karke samjha dunga."
    return None


# ============================================================
# AI INTENT ROUTER + MULTI-STEP PLANNER (V12 ADDITION)
# ============================================================

PLANNER_ACTIONS = {"web_search", "youtube_search", "open_app", "find_file"}


def _recent_command_context(current_text="", limit=7):
    """Return recent non-sensitive commands for follow-up interpretation."""
    try:
        rows = _load_json(HISTORY_FILE, [])
    except Exception:
        rows = []
    cleaned = []
    for row in rows:
        command = str(row.get("command", "")).strip()
        if not command or command == current_text:
            continue
        # Security logs/history already redact private-looking values; never send passwords/OTPs.
        if contains_private_information(command):
            continue
        cleaned.append(command[:180])
    return cleaned[-limit:]


def classify_and_plan_command(user_text):
    """Use the LLM only for commands that did not match existing explicit handlers.

    The model can propose only a small allowlist of actions. It cannot directly execute
    arbitrary shell commands, send messages, or bypass confirmation gates.
    """
    if not GROQ_API_KEY:
        return None
    recent = _recent_command_context(user_text)
    prompt = {
        "current_user_request": user_text,
        "recent_conversation_commands": recent,
        "allowed_actions": sorted(PLANNER_ACTIONS),
        "output_schema": {
            "intent": "plan | answer | clarify",
            "reply": "short response in user's language, or clarification question",
            "steps": [
                {"action": "one allowed action", "query": "specific target or search query"}
            ]
        }
    }
    system = (
        "You are Jarvis's intent router and task planner. Interpret English, Hindi and Hinglish naturally. "
        "Use recent commands to resolve follow-ups such as 'ab beginner wala', but do not invent facts or targets. "
        "Return ONLY valid JSON matching the supplied schema. Choose intent='plan' only when the request clearly asks "
        "for one or more supported actions. Allowed actions are web_search, youtube_search, open_app, find_file. "
        "Use at most 3 steps, in order, with non-empty queries. Do not route sending messages/emails, deleting files, "
        "shell commands, purchases, or other unsupported/high-impact actions; choose clarify or answer instead. "
        "If the request is an ordinary question/conversation, use intent='answer'. If the target is ambiguous, use intent='clarify'. "
        "Never claim an action was already executed. The program will ask for user confirmation before every step. "
        "Reply in the user's language and keep it concise."
    )
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}
            ],
            temperature=0.1,
            max_tokens=350
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
        data = json.loads(raw)
        intent = data.get("intent")
        if intent not in {"plan", "answer", "clarify"}:
            return None
        if intent == "plan":
            steps = data.get("steps", [])
            if not isinstance(steps, list) or not steps or len(steps) > 3:
                return None
            valid = []
            for step in steps:
                if not isinstance(step, dict):
                    return None
                action = str(step.get("action", "")).strip().lower()
                query = str(step.get("query", "")).strip()
                if action not in PLANNER_ACTIONS or not query:
                    return None
                valid.append({"action": action, "query": query[:250]})
            data["steps"] = valid
        data["reply"] = str(data.get("reply", "")).strip()[:500]
        return data
    except Exception as error:
        print("AI INTENT ROUTER ERROR:", type(error).__name__, str(error)[:300])
        return None


def execute_ai_plan(plan):
    """Execute only allowlisted actions, asking the user before each action."""
    action_names = {
        "web_search": "Google par search karna",
        "youtube_search": "YouTube par search karna",
        "open_app": "application open karna",
        "find_file": "local file search karna aur open karna"
    }
    steps = plan.get("steps", [])
    for index, step in enumerate(steps, start=1):
        action = step["action"]
        query = step["query"]
        description = f"step {index} of {len(steps)}: {action_names[action]} — {query}"
        if not confirm_action(description):
            speak("Plan yahin cancel kar diya. Baaki steps execute nahi honge.")
            return False
        try:
            if action == "web_search":
                google_search(query)
            elif action == "youtube_search":
                play_youtube_anything(query)
            elif action == "open_app":
                dynamic_open_app(query)
            elif action == "find_file":
                search_local_file(query, open_result=True)
        except Exception as error:
            print("AI PLAN STEP ERROR:", action, repr(error))
            speak(f"Step {index} complete nahi ho paya. Baaki plan rok raha hoon.")
            return False
    return True


def reset_user_controlled_memory():
    """Clear saved notes and conversational context only after explicit confirmation."""
    global messages
    try:
        _save_json(NOTES_FILE, [])
        history = _load_json(HISTORY_FILE, [])
        _save_json(HISTORY_FILE, history[-1:] if history else [])
        messages = [messages[0]]
        speak("Saved notes aur conversational context clear kar diya.")
        security_log("MEMORY_CLEARED", "user confirmed")
    except Exception as error:
        print("MEMORY CLEAR ERROR:", repr(error))
        speak("Memory clear nahi ho payi. Terminal error check karo.")


# ============================================================
# FAST / STABLE MICROPHONE ENGINE
# ============================================================

MIC_DEVICE_INDEX = None  # None = Windows default microphone
MIC_SAMPLE_RATE = 16000
MIC_CHUNK_SIZE = 1024
MIC_CALIBRATED = False
MIC_ERROR_COUNT = 0


def _new_microphone():
    """Create a fresh microphone object. A fresh object helps PyAudio recover after device glitches."""
    return sr.Microphone(
        device_index=MIC_DEVICE_INDEX,
        sample_rate=MIC_SAMPLE_RATE,
        chunk_size=MIC_CHUNK_SIZE,
    )


def calibrate_microphone_once():
    """Calibrate only once. Recalibrating every loop makes wake-up slower and can trigger PyAudio assertions."""
    global MIC_CALIBRATED
    if MIC_CALIBRATED:
        return True
    try:
        with _new_microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.65)
        recognizer.energy_threshold = max(180, min(recognizer.energy_threshold, 1800))
        MIC_CALIBRATED = True
        print(f"MIC READY | energy threshold: {int(recognizer.energy_threshold)}")
        return True
    except Exception as error:
        print("MIC CALIBRATION SKIPPED:", type(error).__name__, str(error))
        # Recognition can still work with a conservative fixed threshold.
        recognizer.energy_threshold = 300
        MIC_CALIBRATED = True
        return False


def capture_voice(timeout=4, phrase_time_limit=9):
    """Fast capture with recovery from intermittent PyAudio AssertionError."""
    global MIC_ERROR_COUNT
    try:
        with _new_microphone() as source:
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
        MIC_ERROR_COUNT = 0
        return audio
    except AssertionError as error:
        MIC_ERROR_COUNT += 1
        print(f"MIC DEVICE RETRY {MIC_ERROR_COUNT}: {type(error).__name__}")
        time.sleep(min(1.5, 0.25 * MIC_ERROR_COUNT))
        raise sr.WaitTimeoutError("microphone backend retry") from error
    except OSError as error:
        MIC_ERROR_COUNT += 1
        print(f"MIC OS RETRY {MIC_ERROR_COUNT}: {error}")
        time.sleep(min(1.5, 0.25 * MIC_ERROR_COUNT))
        raise sr.WaitTimeoutError("microphone device retry") from error


def recognize_voice(audio):
    """Google recognizer with Indian English; it also handles common Hinglish wake phrases well."""
    return recognizer.recognize_google(audio, language="en-IN").strip()

# ============================================================
# TIMER
# ============================================================

def background_timer(seconds, label):

    time.sleep(seconds)

    for _ in range(3):

        speak(
            f"{label} complete ho gaya hai."
        )

        time.sleep(1)


# ============================================================
# ALARM
# ============================================================

def background_alarm(hour, minute):

    speak(
        f"{hour}:{minute:02d} ka alarm set ho gaya hai."
    )

    while True:

        now = datetime.datetime.now()

        if now.hour == hour and now.minute == minute:

            for _ in range(4):

                speak(
                    "Alarm ka time ho gaya hai."
                )

                time.sleep(1)

            break

        time.sleep(10)


# ============================================================
# SET TIMER
# ============================================================

def set_timer_from_text(text):

    numbers = re.findall(r"\d+", text)

    if not numbers:

        speak(
            "Kitne minute ya second ka timer lagana hai?"
        )

        return

    value = int(numbers[0])

    if "second" in text:

        seconds = value

        label = f"{value} second ka timer"

    else:

        seconds = value * 60

        label = f"{value} minute ka timer"

    speak(
        f"{label} start kar diya hai."
    )

    threading.Thread(
        target=background_timer,
        args=(seconds, label),
        daemon=True
    ).start()


# ============================================================
# SET ALARM
# ============================================================

def set_alarm_from_text(text):

    # 7:30 / 07:30
    match = re.search(
        r"\b(\d{1,2})[:.](\d{1,2})\b",
        text
    )

    hour = None
    minute = 0

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2))

    else:

        numbers = re.findall(r"\d+", text)

        if numbers:
            hour = int(numbers[0])

    if hour is None:

        speak(
            "Kitne baje ka alarm lagana hai?"
        )

        return

    # AM / PM support
    if "pm" in text and hour < 12:
        hour += 12

    if "am" in text and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:

        speak(
            "Alarm ka time sahi nahi hai."
        )

        return

    threading.Thread(
        target=background_alarm,
        args=(hour, minute),
        daemon=True
    ).start()


# ============================================================
# AI IMAGE
# ============================================================

def create_ai_image(prompt_text):

    try:

        speak(
            f"{prompt_text} ki image bana raha hoon."
        )

        # AI converts Hinglish/Hindi description to image prompt
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Convert the following description into "
                        "a concise detailed English image generation prompt. "
                        "Return only the prompt.\n\n"
                        + prompt_text
                    )
                }
            ],
            temperature=0.5,
            max_tokens=250
        )

        english_prompt = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        encoded_prompt = urllib.parse.quote(
            english_prompt
        )

        image_url = (
            "https://image.pollinations.ai/prompt/"
            + encoded_prompt
            + "?width=1024&height=1024&nologo=true"
        )

        response = requests.get(
            image_url,
            timeout=45
        )

        if response.status_code != 200:

            speak(
                "Image server se image nahi mili."
            )

            return

        filename = os.path.abspath(
            f"jarvis_image_{int(time.time())}.jpg"
        )

        with open(filename, "wb") as file:
            file.write(response.content)

        speak("Image ready hai aur save ho gayi hai.")
        if confirm_action("generated image file open karunga"):
            os.startfile(filename)
        else:
            speak("Image save hai, lekin open nahi ki.")

    except Exception as error:

        print("\nIMAGE ERROR:", error)

        speak(
            "Image banane mein problem aayi."
        )


# ============================================================
# AI PDF
# ============================================================

def create_pdf_file(topic):

    try:

        speak(
            f"{topic} par PDF bana raha hoon."
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create clear detailed study notes on {topic}. "
                        "Use simple English. "
                        "Use headings and short paragraphs. "
                        "Do not use markdown symbols."
                    )
                }
            ],
            temperature=0.5,
            max_tokens=1500
        )

        content = response.choices[0].message.content

        if not content:

            speak(
                "PDF ke liye content nahi mila."
            )

            return

        # FPDF built-in fonts are limited to Latin-1
        clean_content = (
            content
            .encode("latin-1", "ignore")
            .decode("latin-1")
        )

        clean_topic = (
            topic
            .encode("latin-1", "ignore")
            .decode("latin-1")
        )

        pdf = FPDF()

        pdf.set_auto_page_break(
            auto=True,
            margin=15
        )

        pdf.add_page()

        pdf.set_font(
            "Arial",
            "B",
            16
        )

        pdf.multi_cell(
            0,
            10,
            clean_topic.title(),
            align="C"
        )

        pdf.ln(5)

        pdf.set_font(
            "Arial",
            size=11
        )

        pdf.multi_cell(
            0,
            7,
            clean_content
        )

        safe_name = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            topic
        ).strip("_")

        if not safe_name:
            safe_name = "Jarvis_Notes"

        filename = os.path.abspath(
            safe_name[:40] + ".pdf"
        )

        pdf.output(filename)

        speak("PDF ready hai aur save ho gayi hai.")
        if confirm_action("generated PDF file open karunga"):
            os.startfile(filename)
        else:
            speak("PDF save hai, lekin open nahi ki.")

    except Exception as error:

        print("\nPDF ERROR:", error)

        speak(
            "PDF banane mein problem aayi."
        )


# ============================================================
# SCREENSHOT
# ============================================================

def take_screenshot():

    try:

        filename = os.path.abspath(
            f"screenshot_{int(time.time())}.png"
        )

        screenshot = pyautogui.screenshot()

        screenshot.save(filename)

        speak(
            "Screenshot save ho gaya hai."
        )

        os.startfile(filename)

    except Exception as error:

        print("\nSCREENSHOT ERROR:", error)

        speak(
            "Screenshot lene mein problem aayi."
        )


# ============================================================
# BATTERY / CPU STATUS
# ============================================================

def system_status():

    try:

        cpu = psutil.cpu_percent(
            interval=0.5
        )

        battery = psutil.sensors_battery()

        if battery:

            percentage = round(
                battery.percent
            )

            if battery.power_plugged:
                charging = "charging par laga hai"
            else:
                charging = "charging par nahi hai"

            speak(
                f"Battery {percentage} percent hai. "
                f"Laptop {charging}. "
                f"CPU usage {cpu} percent hai."
            )

        else:

            speak(
                f"CPU usage {cpu} percent hai."
            )

    except Exception as error:

        print("\nSYSTEM STATUS ERROR:", error)

        speak(
            "System status check nahi ho paya."
        )


# ============================================================
# GOOGLE SEARCH
# ============================================================

def google_search(text):

    query = text

    remove_words = [
        "jarvis",
        "google par",
        "google pe",
        "google mein",
        "google me",
        "google",
        "search karo",
        "search kar",
        "search",
        "dhoondho",
        "dhundo",
        "find"
    ]

    for word in remove_words:

        query = query.replace(
            word,
            " "
        )

    query = re.sub(
        r"\s+",
        " ",
        query
    ).strip()

    if not query:

        speak(
            "Google par kya search karna hai?"
        )

        return

    speak(
        f"{query} search kar raha hoon."
    )

    url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote(query)
    )

    webbrowser.open(url)


# ============================================================
# YOUTUBE SONG
# ============================================================

def listen_once(prompt=None):

    if prompt:
        speak(prompt)

    try:
        print("\nListening for your answer...")
        audio = capture_voice(timeout=8, phrase_time_limit=12)

        answer = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        print("Aapne kaha:", answer)
        return answer.strip()

    except sr.WaitTimeoutError:
        speak("Mujhe koi answer sunai nahi diya.")
        return None

    except sr.UnknownValueError:
        speak("Mujhe aapki baat samajh nahi aayi.")
        return None

    except sr.RequestError as error:
        print("\nSPEECH RECOGNITION ERROR:", error)
        speak("Speech recognition service se connect nahi ho raha.")
        return None

    except Exception as error:
        print("\nLISTEN ERROR:", error)
        return None


def play_youtube_anything(query=None):

    try:
        if not query:
            query = listen_once(
                "YouTube par kya search ya play karna hai?"
            )

        if not query:
            return

        query = query.strip()

        print("\nYouTube par search:", query)

        speak(
            f"YouTube par {query} search karke play kar raha hoon."
        )

        pywhatkit.playonyt(query)

    except Exception as error:
        print("\nYOUTUBE ERROR:", error)

        try:
            if query:
                search_url = (
                    "https://www.youtube.com/results?search_query="
                    + urllib.parse.quote(query)
                )
                webbrowser.open(search_url)
                speak("YouTube search results khol diye hain.")
        except Exception as second_error:
            print("\nYOUTUBE SEARCH ERROR:", second_error)
            speak("YouTube par search karne mein problem aa rahi hai.")


# ============================================================
# COMMAND CLEANER
# ============================================================

def clean_command(text):

    text = text.lower().strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Remove Jarvis from beginning
    text = re.sub(
        r"^jarvis[\s,]*",
        "",
        text
    )

    return text.strip()


# ============================================================
# APP OPENING FUNCTIONS
# ============================================================

def open_notepad():

    speak(
        "Notepad khol raha hoon."
    )

    os.system(
        "start notepad"
    )


def open_calculator():

    speak(
        "Calculator khol raha hoon."
    )

    os.system(
        "start calc"
    )


def open_paint():

    speak(
        "Paint khol raha hoon."
    )

    os.system(
        "start mspaint"
    )


def open_camera():

    speak(
        "Camera khol raha hoon."
    )

    os.system(
        "start microsoft.windows.camera:"
    )


def open_settings():

    speak(
        "Settings khol raha hoon."
    )

    os.system(
        "start ms-settings:"
    )


def open_explorer():

    speak(
        "File Explorer khol raha hoon."
    )

    os.system(
        "start explorer"
    )


def open_cmd():

    speak(
        "Command Prompt khol raha hoon."
    )

    os.system(
        "start cmd"
    )


def open_chrome():

    # Kept function name so old command routing does not break.
    speak("Microsoft Edge khol raha hoon.")
    try:
        os.system("start msedge")
    except Exception:
        webbrowser.open("https://www.google.com")


def open_youtube():

    speak(
        "YouTube khol raha hoon."
    )

    webbrowser.open(
        "https://www.youtube.com"
    )


def open_whatsapp():

    speak(
        "WhatsApp Microsoft Edge mein khol raha hoon."
    )
    try:
        subprocess.Popen(["msedge", "https://web.whatsapp.com"])
    except Exception:
        os.system('start msedge "https://web.whatsapp.com"')


def open_instagram():

    speak(
        "Instagram khol raha hoon."
    )

    webbrowser.open(
        "https://www.instagram.com"
    )


# ============================================================
# ADVANCED JARVIS FEATURES
# ============================================================
import json
import base64
import shutil
import subprocess
import smtplib
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from pathlib import Path
from difflib import SequenceMatcher

DATA_DIR = Path.home() / ".jarvis_data"
DATA_DIR.mkdir(exist_ok=True)
TODO_FILE = DATA_DIR / "todos.json"
NOTES_FILE = DATA_DIR / "notes.json"
CONTACTS_FILE = DATA_DIR / "contacts.json"
CUSTOM_FILE = DATA_DIR / "custom_commands.json"
HISTORY_FILE = DATA_DIR / "command_history.json"
VISION_MODEL = "qwen/qwen3.8-27b"


def _load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


INTERACTION_LOCK = threading.RLock()
DIALOG_ACTIVE = False


def listen_answer(prompt, timeout=8, phrase_time_limit=12):
    global DIALOG_ACTIVE
    with INTERACTION_LOCK:
        DIALOG_ACTIVE = True
        try:
            speak(prompt)
            time.sleep(0.25)
            gui_status("LISTENING", "Aapka answer sun raha hoon...")
            audio = capture_voice(timeout=timeout, phrase_time_limit=phrase_time_limit)
            answer = recognize_voice(audio).strip()
            print("DIALOG ANSWER:", answer)
            gui_log("YOU", answer)
            return answer
        except sr.WaitTimeoutError:
            print("DIALOG: answer timeout")
            return ""
        except sr.UnknownValueError:
            print("DIALOG: answer samajh nahi aaya")
            return ""
        except Exception as error:
            print("ANSWER LISTEN ERROR:", type(error).__name__, error)
            return ""
        finally:
            DIALOG_ACTIVE = False


def confirm_action(description):
    """Reliable voice confirmation before sensitive actions.

    Gives two chances to answer. Negative phrases are checked first so phrases
    such as "mat bhejo" never become an accidental approval.
    """
    no_phrases = [
        "no", "nope", "nah", "nahi", "nahin", "nhi",
        "cancel", "cancel karo", "mat karo", "mat bhejo",
        "send mat karo", "rehne do", "chhodo", "chod do",
        "नहीं", "मत भेजो", "कैंसल"
    ]
    yes_phrases = [
        "yes", "yeah", "yup", "haan", "ha", "haa", "han",
        "yes send karo", "haan bhejo", "send karo", "confirm",
        "okay", "ok", "sure", "kar do", "bhejo",
        "हाँ", "हा", "भेजो", "कन्फर्म"
    ]

    # Speak the sensitive action once, then listen up to two times.
    speak(f"Main {description}. Kya main ye karu? Yes ya No bolo.")

    for attempt in range(1, 3):
        answer = ""
        try:
            # Small pause lets TTS/audio output fully release before mic capture.
            time.sleep(0.45)
            print(f"Confirmation listening... attempt {attempt}/2")
            audio = capture_voice(timeout=12, phrase_time_limit=7)
            answer = recognize_voice(audio)
        except sr.WaitTimeoutError:
            print("Confirmation listen: timeout - koi jawab nahi mila")
        except sr.UnknownValueError:
            print("Confirmation listen: awaaz mili, words clear nahi the")
        except sr.RequestError as error:
            print("Confirmation recognition service error:", error)
        except Exception as error:
            print("Confirmation listen error:", repr(error))

        a = (answer or "").lower().strip()
        a = re.sub(r"[^a-z0-9\u0900-\u097f\s]", " ", a)
        a = re.sub(r"\s+", " ", a).strip()
        print(f"Confirmation heard: {a if a else '[nothing recognized]'}")

        # Negative intent always wins.
        if any(phrase == a or phrase in a for phrase in no_phrases):
            print("Confirmation result: NO")
            speak("Theek hai, action cancel kar diya.")
            security_log("CANCELLED_ACTION", description)
            return False

        if any(phrase == a or phrase in a for phrase in yes_phrases):
            print("Confirmation result: YES")
            speak("Okay.")
            security_log("CONFIRMED_ACTION", description)
            return True

        if attempt == 1:
            print("Confirmation result: UNCLEAR - retrying once")
            speak("Mujhe jawab clear nahi mila. Sirf Yes ya No bolo.")

    print("Confirmation result: UNCLEAR")
    speak("Confirmation clear nahi tha. Safety ke liye action cancel kar diya.")
    security_log("UNCLEAR_CONFIRMATION", description)
    return False


def add_history(command):
    data = _load_json(HISTORY_FILE, [])
    data.append({"time": datetime.datetime.now().isoformat(timespec="seconds"), "command": safe_log_text(command)})
    _save_json(HISTORY_FILE, data[-100:])


def last_command():
    data = _load_json(HISTORY_FILE, [])
    if len(data) < 2:
        speak("Abhi koi previous command nahi hai.")
    else:
        speak(f"Aapki pichhli command thi: {data[-2]['command']}")


def dynamic_open_app(name):
    name = re.sub(r"\b(open|kholo|chalao|start|app)\b", " ", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        speak("Kaunsa app open karna hai?")
        return
    roots = [
        Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
    ]
    candidates = []
    for root in roots:
        if root.exists():
            try:
                for p in root.rglob("*"):
                    if p.suffix.lower() in (".lnk", ".exe"):
                        score = SequenceMatcher(None, name.lower(), p.stem.lower()).ratio()
                        if name.lower() in p.stem.lower(): score += 0.5
                        candidates.append((score, p))
            except Exception:
                pass
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        os.startfile(str(candidates[0][1]))
        speak(f"{name} open kar diya.")
    else:
        speak(f"{name} laptop mein installed app ke roop mein nahi mila.")
        if confirm_action(f"{name} ko Microsoft Edge mein web par search karke open karunga"):
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(name))
            speak(f"{name} ka web search Edge mein open kar diya.")


def search_local_file(query, open_result=True):
    q = re.sub(r"\b(file|folder|pdf|dhundo|dhoondho|search|wali|wala|open|kholo)\b", " ", query, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip().lower()
    if not q:
        speak("Kya file ya folder dhoondhna hai?")
        return
    roots = [Path.home()/"Desktop", Path.home()/"Documents", Path.home()/"Downloads"]
    matches = []
    for root in roots:
        if root.exists():
            for base, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if not d.startswith(".")][:80]
                for n in dirs + files:
                    if all(word in n.lower() for word in q.split()):
                        matches.append(Path(base)/n)
                        if len(matches) >= 20: break
                if len(matches) >= 20: break
        if len(matches) >= 20: break
    if not matches:
        speak(f"{q} naam ki file ya folder nahi mila.")
        return
    print("\nMatches:")
    for i,p in enumerate(matches[:10],1): print(i, p)
    speak(f"Mujhe {len(matches)} result mile. Pehla result {matches[0].name} hai.")
    if open_result:
        if confirm_action(f"{matches[0].name} file ya folder open karunga"):
            os.startfile(str(matches[0]))
            speak(f"{matches[0].name} open kar diya.")


def save_contact(name, number):
    contacts=_load_json(CONTACTS_FILE,{})
    contacts[name.lower().strip()]=number.strip()
    _save_json(CONTACTS_FILE,contacts)
    speak(f"{name} contact local Jarvis contacts mein save ho gaya.")


def _paste_text(value):
    """Paste Unicode text safely into the currently focused Windows app."""
    pyperclip.copy(str(value))
    pyautogui.hotkey("ctrl", "v")


def _jarvis_edge_driver():
    """
    Start a dedicated persistent Microsoft Edge session for Jarvis.
    This does NOT use or lock the user's normal Edge Default profile.
    """
    import os
    import shutil
    import time
    from pathlib import Path

    profile_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "JarvisAI" / "EdgeAutomationProfile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("Using Jarvis persistent Edge profile:", profile_dir)

    # Chromium can leave these lock markers behind after a crash.
    # Remove only Jarvis' dedicated profile markers, never the normal Edge profile.
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "DevToolsActivePort"):
        p = profile_dir / name
        try:
            if p.exists() or p.is_symlink():
                p.unlink()
                print("Removed stale Jarvis Edge marker:", name)
        except Exception as cleanup_error:
            print("Could not remove", name, ":", cleanup_error)

    options = webdriver.EdgeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-background-mode")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--remote-debugging-port=0")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(45)
        print("Jarvis Edge automation started successfully.")
        return driver

    except Exception as e:
        print("\n========== FULL EDGE ERROR ==========")
        print("Exception type:", type(e).__name__)
        print("Exception message:")
        print(str(e))
        print("Exception repr:")
        print(repr(e))
        print("=====================================\n")

        # If the persistent profile itself became corrupted, preserve it as backup
        # and retry once with a clean Jarvis-only profile. Normal Edge is untouched.
        try:
            stamp = str(int(time.time()))
            backup = profile_dir.parent / ("EdgeAutomationProfile_Broken_" + stamp)
            if profile_dir.exists():
                try:
                    profile_dir.rename(backup)
                    print("Old Jarvis Edge profile backed up to:", backup)
                except Exception:
                    shutil.rmtree(profile_dir, ignore_errors=True)

            profile_dir.mkdir(parents=True, exist_ok=True)
            retry_options = webdriver.EdgeOptions()
            retry_options.add_argument(f"--user-data-dir={profile_dir}")
            retry_options.add_argument("--profile-directory=Default")
            retry_options.add_argument("--no-first-run")
            retry_options.add_argument("--no-default-browser-check")
            retry_options.add_argument("--disable-background-mode")
            retry_options.add_argument("--disable-extensions")
            retry_options.add_argument("--disable-popup-blocking")
            retry_options.add_argument("--disable-notifications")
            retry_options.add_argument("--start-maximized")
            retry_options.add_argument("--remote-debugging-port=0")

            print("Retrying Edge once with a clean Jarvis automation profile...")
            driver = webdriver.Edge(options=retry_options)
            driver.set_page_load_timeout(45)
            print("Jarvis Edge automation started successfully on clean profile.")
            return driver
        except Exception as retry_error:
            print("\n========== EDGE RETRY ERROR ==========")
            print(type(retry_error).__name__)
            print(str(retry_error))
            print(repr(retry_error))
            print("======================================\n")
            raise RuntimeError(
                "Jarvis Edge automation start nahi ho paya. "
                "Normal Edge ko close karna zaroori nahi hai. "
                "CMD ka EDGE RETRY ERROR output bhejo."
            ) from retry_error


def _wa_find_search_box(driver, timeout=60):
    """Find WhatsApp Web's contact search box using several resilient selectors."""
    wait = WebDriverWait(driver, timeout)
    selectors = [
        (By.XPATH, "//div[@contenteditable='true' and @role='textbox' and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
        (By.XPATH, "//div[@contenteditable='true' and contains(translate(@aria-placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search')]"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"),
    ]
    last = None
    for by, selector in selectors:
        try:
            return WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
        except Exception as e:
            last = e
    # Fallback: visible contenteditable textbox outside footer.
    boxes = wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"))
    for box in boxes:
        try:
            if box.is_displayed() and not box.find_elements(By.XPATH, "ancestor::footer"):
                return box
        except Exception:
            pass
    raise TimeoutException(f"WhatsApp search box nahi mila: {last}")


def _wa_open_contact(driver, contact_name):
    search = _wa_find_search_box(driver)
    search.click()
    search.send_keys(Keys.CONTROL, "a")
    search.send_keys(Keys.BACKSPACE)
    search.send_keys(contact_name)

    # Prefer exact visible saved-contact title.
    safe_name = contact_name.replace("'", "’")
    candidates = [
        (By.XPATH, f"//span[@title={repr(contact_name)}]"),
        (By.XPATH, "//div[@role='listitem']//span[@title]"),
    ]
    try:
        exact = WebDriverWait(driver, 12).until(
            EC.element_to_be_clickable((By.XPATH, f"//span[@title={_xpath_literal(contact_name)}]"))
        )
        exact.click()
        return
    except Exception:
        pass

    # Fallback: first visible search result; user already supplied the intended name.
    results = WebDriverWait(driver, 12).until(
        lambda d: [e for e in d.find_elements(By.XPATH, "//div[@role='listitem']") if e.is_displayed()]
    )
    if not results:
        raise TimeoutException(f"{contact_name} contact search result nahi mila.")
    results[0].click()


def _xpath_literal(value):
    """Quote arbitrary text safely for an XPath string literal."""
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join("'" + p + "'" for p in parts) + ")"


def _wa_find_message_box(driver):
    selectors = [
        (By.XPATH, "//footer//div[@contenteditable='true' and @role='textbox']"),
        (By.XPATH, "//footer//div[@contenteditable='true']"),
    ]
    for by, selector in selectors:
        try:
            return WebDriverWait(driver, 12).until(EC.element_to_be_clickable((by, selector)))
        except Exception:
            pass
    raise TimeoutException("WhatsApp message box nahi mila.")


def whatsapp_message(contact, message):
    """Send using the already logged-in WhatsApp Desktop app on Windows."""
    contact = str(contact).strip()
    message = str(message).strip()
    if not contact or not message:
        speak("Contact ya message empty hai.")
        return False

    if not confirm_action(f"{contact} ko WhatsApp par ye message send karunga: {message}"):
        print("WHATSAPP DESKTOP | Cancelled by user before send.")
        return False

    try:
        speak(f"WhatsApp app mein {contact} ko message bhej raha hoon.")
        print("WHATSAPP DESKTOP | Contact:", contact)
        print("WHATSAPP DESKTOP | Message:", message)

        # Open the installed WhatsApp Desktop app; no browser/Selenium login.
        try:
            os.startfile("whatsapp:")
        except Exception:
            subprocess.Popen(
                ["explorer.exe", r"shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        time.sleep(5)

        # Try to focus the WhatsApp window.
        try:
            import pygetwindow as gw
            wins = [w for w in gw.getWindowsWithTitle("WhatsApp") if w.title]
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(1)
        except Exception as focus_error:
            print("WhatsApp focus note:", repr(focus_error))

        # Search the contact, open first match, paste exact message, send.
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.8)
        pyperclip.copy(contact)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2.0)
        pyautogui.press("enter")
        time.sleep(1.5)

        pyperclip.copy(message)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(1.0)

        print("WHATSAPP DESKTOP | Send action completed.")
        speak(f"{contact} ko WhatsApp message bhej diya.")
        return True

    except Exception as e:
        print("\n========== WHATSAPP DESKTOP ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print(repr(e))
        print("============================================\n")
        speak("WhatsApp Desktop se message send nahi ho paya. Terminal mein error check karo.")
        return False


def email_message_saved_recipient(recipient_name, subject, body):
    """Compose and send Gmail through Selenium; final click only after confirmation."""
    driver = None
    try:
        speak(f"Gmail mein {recipient_name} ke liye email compose kar raha hoon.")
        driver = _jarvis_edge_driver()
        driver.get("https://mail.google.com/mail/u/0/#inbox")
        wait = WebDriverWait(driver, 90)

        compose = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button'][gh='cm']")))
        compose.click()

        to_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[role='combobox'], textarea[name='to']")))
        to_box.send_keys(recipient_name)
        time.sleep(2)
        to_box.send_keys(Keys.ENTER)

        subject_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='subjectbox']")))
        subject_box.send_keys(subject)

        body_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']")))
        body_box.send_keys(body)

        if not confirm_action(f"{recipient_name} ko email send karu"):
            speak("Email send cancel kar diya. Draft Gmail mein rehne diya hai.")
            return

        # Click Gmail's Send button inside the compose dialog; do not type into IDLE.
        send_buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button'][data-tooltip^='Send'], div[role='button'][aria-label^='Send']")
        visible = [b for b in send_buttons if b.is_displayed() and b.is_enabled()]
        if not visible:
            raise TimeoutException("Gmail Send button nahi mila.")
        visible[0].click()
        time.sleep(1)
        security_log("EMAIL_SEND", f"recipient={recipient_name}")
        print(f"REAL GMAIL SEND: {recipient_name}")
        speak("Email send kar diya.")

    except Exception as e:
        print("GMAIL SELENIUM ERROR:", repr(e))
        if "Selenium installed nahi" in str(e):
            speak("Selenium install karna hai. Terminal mein pip install selenium command chalao.")
        else:
            speak("Email send nahi ho paya. Gmail login aur terminal error check karo.")
    finally:
        pass


def instagram_message(username, message):
    """Open Instagram in the same Edge environment and prepare a DM.
    Instagram changes its DOM frequently, so several selectors are tried.
    The final Send/Enter happens only after voice confirmation.
    """
    driver = None
    try:
        speak(f"Instagram par {username} ko dhoondh raha hoon.")
        driver = _jarvis_edge_driver()
        driver.get("https://www.instagram.com/direct/inbox/")
        wait = WebDriverWait(driver, 60)
        # New message button; selectors intentionally broad because Instagram UI changes often.
        buttons = driver.find_elements(By.XPATH, "//button//*[name()='svg']/ancestor::button | //div[@role='button']")
        new_btn = None
        for b in buttons:
            try:
                label = ((b.get_attribute('aria-label') or '') + ' ' + (b.text or '')).lower()
                if 'new message' in label or 'message' == label.strip():
                    new_btn = b; break
            except Exception:
                pass
        if new_btn is None:
            # Direct compose route often opens the recipient picker.
            driver.get("https://www.instagram.com/direct/new/")
        else:
            new_btn.click()
        time.sleep(1.2)
        search = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search...' or @placeholder='Search']")))
        search.send_keys(username)
        time.sleep(2)
        result = wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {_xpath_literal(username.lower())})]")))
        result.click()
        # Some versions require a Next/Chat button after selecting a person.
        for label in ['Next', 'Chat']:
            try:
                btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, f"//button[normalize-space()='{label}'] | //div[@role='button' and normalize-space()='{label}']")))
                btn.click(); break
            except Exception:
                pass
        box = wait.until(EC.element_to_be_clickable((By.XPATH, "//textarea[@placeholder='Message...'] | //div[@contenteditable='true' and @role='textbox']")))
        if not confirm_action(f"{username} ko Instagram message send karu"):
            speak("Instagram message cancel kar diya.")
            return
        box.click(); box.send_keys(message); box.send_keys(Keys.ENTER)
        security_log("INSTAGRAM_SEND", f"recipient={username}")
        speak("Instagram message send kar diya.")
    except Exception as e:
        print("INSTAGRAM SELENIUM ERROR:", repr(e))
        speak("Instagram message send nahi ho paya. Edge login ya Instagram layout check karo.")


def send_email_smtp(to_address, subject, body):
    sender=os.environ.get("JARVIS_EMAIL","").strip()
    password=os.environ.get("JARVIS_EMAIL_APP_PASSWORD","").strip()
    if not sender or not password:
        speak("Email sending ke liye JARVIS_EMAIL aur JARVIS_EMAIL_APP_PASSWORD environment variables set nahi hain.")
        return
    try:
        msg=EmailMessage(); msg["From"]=sender; msg["To"]=to_address; msg["Subject"]=subject; msg.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=20) as smtp:
            smtp.login(sender,password); smtp.send_message(msg)
        speak("Email send ho gaya.")
    except Exception as e:
        print("EMAIL ERROR:",e); speak("Email send nahi ho paya.")


def get_weather(query):
    place = re.sub(r"\b(aaj|kal|weather|mausam|kaisa|kaisi|hai|batao|tomorrow|today|in)\b", " ", query, flags=re.I)
    place = re.sub(r"\s+", " ", place).strip()
    if not place:
        place = listen_answer("Kis city ka weather chahiye?")
    if not place: return
    try:
        url = "https://wttr.in/" + urllib.parse.quote(place) + "?format=j1"
        data = requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0"}).json()
        day_index = 1 if any(x in query.lower() for x in ["kal", "tomorrow"]) else 0
        day = data["weather"][day_index]
        current = data["current_condition"][0]
        if day_index == 0:
            desc = current["weatherDesc"][0]["value"]
            speak(f"{place} mein abhi {current['temp_C']} degree Celsius hai, {desc}. Aaj maximum {day['maxtempC']} aur minimum {day['mintempC']} degree rahega.")
        else:
            desc = day["hourly"][4]["weatherDesc"][0]["value"]
            speak(f"Kal {place} mein maximum {day['maxtempC']} aur minimum {day['mintempC']} degree rahega. Mausam {desc} rehne ka forecast hai.")
    except Exception as e:
        print("WEATHER ERROR:", e); speak("Weather check nahi ho paya.")


def get_news(topic="technology"):
    try:
        q = urllib.parse.quote(topic)
        xml = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en", timeout=12).content
        root = ET.fromstring(xml)
        items = root.findall(".//item")[:5]
        if not items: speak("News nahi mili."); return
        speak(f"{topic} ki top news bata raha hoon.")
        for item in items:
            speak(item.findtext("title", ""))
    except Exception as e:
        print("NEWS ERROR:", e); speak("News fetch nahi ho payi.")


def add_todo(task):
    data = _load_json(TODO_FILE, [])
    data.append({"task": task, "done": False, "created": datetime.datetime.now().isoformat(timespec="seconds")})
    _save_json(TODO_FILE, data); speak("Task to-do list mein add ho gaya.")


def read_todos():
    data = [x for x in _load_json(TODO_FILE, []) if not x.get("done")]
    if not data: speak("To-do list empty hai."); return
    speak("Aapke tasks hain: " + "; ".join(x["task"] for x in data[:10]))


def remember_note(note):
    data = _load_json(NOTES_FILE, [])
    data.append({"note": note, "time": datetime.datetime.now().isoformat(timespec="seconds")})
    _save_json(NOTES_FILE, data); speak("Yaad rakh liya.")


def recall_notes():
    data = _load_json(NOTES_FILE, [])
    if not data: speak("Aapne abhi mujhe kuch yaad rakhne nahi bola."); return
    speak("Aapne mujhe yaad rakhne bola tha: " + "; ".join(x["note"] for x in data[-5:]))


def clipboard_action(action):
    if action == "copy": pyautogui.hotkey("ctrl","c"); speak("Copy kar diya.")
    elif action == "paste": pyautogui.hotkey("ctrl","v"); speak("Paste kar diya.")
    else:
        try:
            import tkinter as tk
            r=tk.Tk(); r.withdraw(); value=r.clipboard_get(); r.destroy(); speak("Clipboard mein hai: " + str(value)[:500])
        except Exception: speak("Clipboard text read nahi ho paya.")


def set_brightness(value):
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(max(0,min(100,int(value))))
        speak(f"Brightness {value} percent kar di.")
    except Exception as e:
        print("BRIGHTNESS ERROR:",e); speak("Brightness control ke liye screen-brightness-control package install hona chahiye.")


def pc_details():
    vm=psutil.virtual_memory(); disk=psutil.disk_usage(str(Path.home().anchor)); bat=psutil.sensors_battery()
    parts=[f"RAM {vm.percent} percent use ho rahi hai", f"Disk {disk.percent} percent full hai", f"CPU {psutil.cpu_percent(0.5)} percent use ho raha hai"]
    if bat: parts.append(f"Battery {round(bat.percent)} percent hai")
    speak(". ".join(parts)+".")


def create_text_file(topic, python_file=False):
    ext=".py" if python_file else ".txt"
    prompt = f"Write {'Python code' if python_file else 'clear notes'} for: {topic}. Return only the file content."
    content=ask_ai(prompt)
    safe=re.sub(r"[^A-Za-z0-9_-]+","_",topic).strip("_")[:40] or "jarvis_file"
    path=Path.cwd()/(safe+ext); path.write_text(content,encoding="utf-8"); os.startfile(str(path)); speak(f"{path.name} bana di.")


def analyze_image_file(path, question):
    try:
        mime="image/png" if str(path).lower().endswith(".png") else "image/jpeg"
        b64=base64.b64encode(Path(path).read_bytes()).decode()
        response=client.chat.completions.create(model=VISION_MODEL,messages=[{"role":"user","content":[{"type":"text","text":question},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}]}],max_completion_tokens=500)
        speak(response.choices[0].message.content)
    except Exception as e:
        print("VISION ERROR:",e); speak("Image analyze nahi ho payi.")


def screenshot_understand():
    path=Path(tempfile.gettempdir())/f"jarvis_screen_{int(time.time())}.png"
    pyautogui.screenshot().save(path)
    analyze_image_file(path,"Explain what is visible on this computer screen. If there is an error, explain it simply and suggest safe troubleshooting steps.")


def camera_understand():
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = True
    print_security_indicator("active")
    try:
        import cv2
        cap=cv2.VideoCapture(0); ok,frame=cap.read(); cap.release()
        if not ok: speak("Camera image capture nahi hui."); return
        path=Path(tempfile.gettempdir())/f"jarvis_camera_{int(time.time())}.jpg"; cv2.imwrite(str(path),frame)
        analyze_image_file(path,"Describe the visible scene and objects briefly. Do not identify people.")
    except Exception as e:
        print("CAMERA ERROR:",e); speak("Camera understanding ke liye opencv-python install hona chahiye.")


def translate_with_ai(text, language):
    speak(ask_ai(f"Translate this into {language}. Return only the translation: {text}"))


def study_mode(topic):
    speak(ask_ai(f"Teach me {topic} as a student in simple Hinglish, step by step, with one small example."))


def quiz_mode(topic):
    q=ask_ai(f"Ask exactly one short viva/quiz question about {topic}. Do not give the answer yet.")
    answer=listen_answer(q)
    if answer: speak(ask_ai(f"Question: {q}\nStudent answer: {answer}\nCheck it briefly, correct mistakes, then give the ideal answer."))


def coding_mode(request):
    result=ask_ai("Give a correct beginner-friendly solution for this programming request. Explain briefly, then provide code: "+request)
    print("\nCODING RESULT:\n",result); speak("Code aur explanation terminal mein de diya hai.")


def calculate_with_ai(expr):
    speak(ask_ai("Calculate this carefully. Give the final answer first and a very short explanation: "+expr))


def enable_startup():
    startup=Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/Startup"
    script=Path(__file__).resolve()
    bat=startup/"Jarvis_AutoStart.bat"
    bat.write_text(f'@echo off\nstart "" /min py -3.13 "{script}"\n',encoding="utf-8")
    speak("Windows startup mein Jarvis enable kar diya. Agli login par automatically start hoga.")


def disable_startup():
    p=Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/Startup/Jarvis_AutoStart.bat"
    if p.exists(): p.unlink()
    speak("Jarvis startup disable kar diya.")


def set_reminder_simple(text):
    now=datetime.datetime.now(); nums=[int(x) for x in re.findall(r"\d+",text)]
    target=None
    if "minute" in text and nums: target=now+datetime.timedelta(minutes=nums[0])
    elif "second" in text and nums: target=now+datetime.timedelta(seconds=nums[0])
    else:
        m=re.search(r"(\d{1,2})(?::(\d{2}))?",text)
        if m:
            h=int(m.group(1)); minute=int(m.group(2) or 0)
            if "pm" in text and h<12: h+=12
            if "am" in text and h==12: h=0
            target=now.replace(hour=h,minute=minute,second=0,microsecond=0)
            if "kal" in text or "tomorrow" in text: target+=datetime.timedelta(days=1)
            elif target<=now: target+=datetime.timedelta(days=1)
    task=re.sub(r"\b(remind|reminder|yaad dilana|yaad dila dena|kal|tomorrow|aaj|today|baje|at|am|pm|minute|minutes|second|seconds)\b"," ",text,flags=re.I)
    task=re.sub(r"\d{1,2}(?::\d{2})?"," ",task); task=re.sub(r"\s+"," ",task).strip() or "aapka reminder"
    if not target: speak("Reminder ka time samajh nahi aaya."); return
    delay=max(0,(target-now).total_seconds())
    def worker(): time.sleep(delay); speak(f"Reminder: {task}")
    threading.Thread(target=worker,daemon=True).start(); speak(f"Reminder {target.strftime('%d %B %I:%M %p')} ke liye set ho gaya.")


def save_custom_command(text):
    # Example: jab main college mode bolu to chrome aur vs code kholo
    m=re.search(r"jab main (.+?) bolu to (.+)",text,re.I)
    if not m: speak("Custom command format samajh nahi aaya."); return
    trigger=m.group(1).strip().lower(); action=m.group(2).strip()
    data=_load_json(CUSTOM_FILE,{ }); data[trigger]=action; _save_json(CUSTOM_FILE,data)
    speak(f"Custom command {trigger} save ho gaya.")


def run_custom_command(text):
    data=_load_json(CUSTOM_FILE,{})
    if text not in data: return False
    action=data[text]
    speak(f"Custom command mila: {action}")
    # Safe simple app-opening custom actions only
    for part in re.split(r"\s+aur\s+|\s+and\s+",action,flags=re.I):
        dynamic_open_app(part)
    return True


# ============================================================
# SECURITY / PRIVACY LAYER
# ============================================================

PRIVACY_MODE = False
SESSION_LOCKED = False
CAMERA_ACTIVE = False
AUTO_SLEEP_SECONDS = 180  # 3 minutes; change to 120-300 if you prefer
LAST_ACTIVITY_TIME = time.time()
SECURITY_LOG_FILE = Path.home() / "jarvis_security_log.txt"

SENSITIVE_WORDS = [
    "password", "passcode", "otp", "one time password", "api key", "apikey",
    "secret key", "token", "pin", "cvv"
]

# Common trusted apps. Unknown apps still require confirmation before search/open.
APP_ALLOW_LIST = {
    "chrome", "google chrome", "notepad", "calculator", "calc", "paint",
    "camera", "settings", "file explorer", "explorer", "cmd", "command prompt",
    "youtube", "whatsapp", "instagram", "vs code", "visual studio code",
    "android studio", "word", "microsoft word", "spotify"
}

# Important folders should never be modified silently.
PROTECTED_PATHS = [
    Path.home(),
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Pictures",
]

DANGEROUS_COMMAND_PATTERNS = [
    r"\bformat\b", r"\bdel\s+/[sqf]", r"\brmdir\s+/s", r"\brd\s+/s",
    r"\bshutdown\s+/[sr]", r"\bdiskpart\b", r"\breg\s+delete\b",
    r"remove-item\s+.+-recurse", r"clear-disk", r"format-volume",
    r"invoke-expression", r"iex\b"
]


def contains_private_information(text):
    t = (text or "").lower()
    return any(word in t for word in SENSITIVE_WORDS)


def safe_log_text(text):
    if contains_private_information(text):
        return "[SENSITIVE COMMAND REDACTED]"
    # Do not store long message/email bodies in the security log.
    t = re.sub(r"\s+", " ", str(text)).strip()
    return t[:160]


def security_log(event, detail=""):
    try:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(SECURITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {event}: {safe_log_text(detail)}\n")
    except Exception:
        pass


def print_security_indicator(state=None):
    if state == "privacy" or PRIVACY_MODE:
        mic = "OFF"
    elif state == "active":
        mic = "ACTIVE"
    else:
        mic = "WAKE ONLY"
    cam = "ON" if CAMERA_ACTIVE else "OFF"
    lock = "LOCKED" if SESSION_LOCKED else "UNLOCKED"
    print(f"[SECURITY] MIC: {mic} | CAMERA: {cam} | SESSION: {lock}")


def ctrl_alt_j_pressed():
    """Windows-only global key-state check. Does not use the microphone."""
    if os.name != "nt":
        return False
    try:
        get_key = ctypes.windll.user32.GetAsyncKeyState
        ctrl = bool(get_key(0x11) & 0x8000)   # VK_CONTROL
        alt = bool(get_key(0x12) & 0x8000)    # VK_MENU
        j = bool(get_key(0x4A) & 0x8000)      # J
        return ctrl and alt and j
    except Exception:
        return False


def wait_in_true_privacy_mode():
    """No microphone is opened here. Only Ctrl+Alt+J is polled locally."""
    global PRIVACY_MODE, LAST_ACTIVITY_TIME
    print_security_indicator("privacy")
    print("PRIVACY MODE: microphone processing completely stopped.")
    print("Press Ctrl + Alt + J to return to WAKE ONLY mode.")
    while PRIVACY_MODE:
        if ctrl_alt_j_pressed():
            PRIVACY_MODE = False
            LAST_ACTIVITY_TIME = time.time()
            security_log("PRIVACY_OFF", "Ctrl+Alt+J")
            print("\nPrivacy mode OFF. MIC remains WAKE ONLY until a wake phrase is heard.")
            print_security_indicator("wake")
            # Debounce keys so one press is handled once.
            time.sleep(0.8)
            return
        time.sleep(0.08)


def is_dangerous_shell_command(command):
    c = (command or "").lower().strip()
    return any(re.search(pattern, c, flags=re.I) for pattern in DANGEROUS_COMMAND_PATTERNS)


def is_protected_path(path):
    try:
        target = Path(path).resolve()
        for protected in PROTECTED_PATHS:
            base = protected.resolve()
            if target == base:
                return True
        return False
    except Exception:
        return True


def update_activity():
    global LAST_ACTIVITY_TIME
    LAST_ACTIVITY_TIME = time.time()

def run_whatsapp_dialog(prefilled_contact=""):
    """Own the complete WhatsApp conversation so follow-up speech cannot become normal commands."""
    contact = (prefilled_contact or "").strip()
    if not contact:
        contact = listen_answer("Kisko WhatsApp message bhejna hai? Contact ka naam bolo.", timeout=8, phrase_time_limit=6)
    if not contact:
        speak("Contact naam sunai nahi diya. WhatsApp message cancel kar diya.")
        return True

    message = listen_answer(f"{contact} ko kya message bhejna hai?", timeout=10, phrase_time_limit=12)
    if not message:
        speak("Message sunai nahi diya. WhatsApp message cancel kar diya.")
        return True

    speak(f"Theek hai. {contact} ko message hai: {message}")
    whatsapp_message(contact, message)
    return True


# ============================================================
# COMMAND PROCESSOR
# ============================================================

def process_command(original_text):

    text = clean_command(
        original_text
    )

    add_history(original_text)
    update_activity()

    global PRIVACY_MODE, SESSION_LOCKED

    # True privacy mode: after this reply the main loop stops opening the microphone.
    if text in ["privacy mode", "privacy mode on", "privacy on", "mic off", "microphone off"]:
        speak("Privacy mode on. Microphone listening ab completely disabled hai. Wapas wake mode mein aane ke liye Control Alt J press kijiye.")
        PRIVACY_MODE = True
        security_log("PRIVACY_ON", "voice command")
        return "privacy"

    # Session lock protects sensitive features. This is a Jarvis feature lock, not Windows authentication.
    if text in ["jarvis lock", "lock jarvis", "session lock", "lock session"]:
        SESSION_LOCKED = True
        security_log("SESSION_LOCK", "enabled")
        speak("Jarvis sensitive features lock kar diye gaye hain. Unlock locally karne ke liye Control Alt J press karke unlock command use kijiye.")
        return True

    if text in ["jarvis unlock", "unlock jarvis", "session unlock", "unlock session"]:
        speak("Security ke liye session voice se unlock nahi hoga. Control Alt J locally press kijiye.")
        return True

    # Never repeat or intentionally store secrets spoken as commands.
    if contains_private_information(original_text):
        security_log("PRIVATE_INPUT", "redacted")
        speak("Security ke liye password, OTP, PIN ya API key ko main repeat ya memory mein save nahi karunga.")
        return True

    if SESSION_LOCKED:
        safe_while_locked = ["time", "date", "battery", "who are you", "tum kaun ho"]
        if not any(x in text for x in safe_while_locked):
            speak("Jarvis session locked hai. Sensitive commands abhi disabled hain.")
            security_log("BLOCKED_LOCKED_ACTION", text)
            return True

    # Custom learned commands
    if run_custom_command(text):
        return True



    # ========================================================
    # SLEEP JARVIS
    # ========================================================

    if text in [
        "bye",
        "bye bye",
        "goodbye",
        "good night",
        "stop",
        "stop jarvis",
        "so jao",
        "so ja",
        "jarvis so jao",
        "sleep",
        "sleep jarvis",
        "band ho jao",
        "jarvis band karo"
    ]:

        speak(
            "Okay, main sleep mode mein ja raha hoon. Hello Jarvis ya uth jao bolkar mujhe wapas jaga sakte ho."
        )

        return "sleep"

    # Complete exit remains available separately
    if text in [
        "exit",
        "exit jarvis",
        "close jarvis",
        "quit jarvis"
    ]:

        speak(
            "Okay, Jarvis completely band kar raha hoon. Bye."
        )

        return False


    # ========================================================
    # NAME / CREATOR
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "who are you",
            "tum kaun ho",
            "aap kaun ho"
        ]
    ):

        speak(
            "Main Jarvis hoon, aapka AI voice assistant."
        )

        return True


    if any(
        phrase in text
        for phrase in [
            "kisne banaya",
            "who made you",
            "who created you",
            "creator kaun"
        ]
    ):

        speak(
            "Mujhe Pratiksha Naik ne banaya hai."
        )

        return True


    # ========================================================
    # ADVANCED FEATURES
    # ========================================================
    if "last command" in text or "pichhli command" in text or "last kya bola" in text:
        last_command(); return True

    if text.startswith("save contact") or text.startswith("contact save"):
        rest=re.sub(r"^(save contact|contact save)\s*","",original_text,flags=re.I).strip()
        name=rest or listen_answer("Contact ka naam bolo.")
        number=listen_answer("Country code ke saath phone number bolo.") if name else ""
        number=re.sub(r"[^+\d]","",number)
        if name and number and confirm_action(f"{name} ka contact number local file mein save karunga"): save_contact(name,number)
        return True

    # NATURAL WHATSAPP COMMANDS - dedicated dialog owns all follow-up speech.
    whatsapp_intent = (
        "whatsapp" in text and any(k in text for k in ["message", "msg", "bhejo", "bhejna", "send", "karo"])
    )
    if whatsapp_intent:
        contact = ""
        patterns = [
            r"whatsapp\s+(?:par|per|pe)\s+(.+?)\s+ko\s+(?:message|msg)",
            r"(.+?)\s+ko\s+whatsapp\s+(?:par|per|pe)?\s*(?:message|msg)?",
            r"whatsapp\s+(?:message|msg)\s+(.+?)\s+ko",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                candidate = m.group(1).strip()
                # Don't mistake generic words for a contact name.
                if candidate not in ("message", "msg", "kisi", "isko", "usko"):
                    contact = candidate
                    break
        return run_whatsapp_dialog(contact)

    # NATURAL INSTAGRAM DM COMMANDS
    instagram_intent = (
        "instagram" in text and any(k in text for k in ["message", "msg", "dm", "bhejo", "send", "karo"])
    )
    if instagram_intent:
        recipient = ""
        patterns = [
            r"instagram\s+(?:par|per|pe)\s+(.+?)\s+ko\s+(?:message|msg|dm)\s*(?:bhejo|send karo|karo)?$",
            r"(.+?)\s+ko\s+instagram\s+(?:par|per|pe)?\s*(?:message|msg|dm)?\s*(?:bhejo|send karo|karo)?$",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                recipient = m.group(1).strip(); break
        if not recipient:
            recipient = listen_answer("Instagram par kisko message bhejna hai? Username bolo.")
        message = listen_answer("Kya message bhejna hai?") if recipient else ""
        if recipient and message:
            if confirm_action(f"{recipient} ko Instagram par ye message send karunga: {message}"):
                instagram_message(recipient, message)
        return True

    # NATURAL EMAIL COMMANDS - recipient may be a saved Gmail contact name.
    email_intent = (
        "email" in text and any(k in text for k in ["bhejo", "send", "message", "mail karo"])
    )
    if email_intent:
        recipient=""
        patterns=[
            r"email\s+(?:par|per|pe)?\s*(.+?)\s+ko\s+(?:email|message)?\s*(?:bhejo|send karo|karo)?$",
            r"(.+?)\s+ko\s+email\s*(?:bhejo|send karo|karo)?$",
        ]
        for pat in patterns:
            m=re.search(pat,text,re.I)
            if m:
                recipient=m.group(1).strip()
                break
        if not recipient:
            recipient=listen_answer("Kisko email bhejna hai? Naam ya email address bolo.")
        subject=listen_answer("Email ka subject bolo.") if recipient else ""
        body=listen_answer("Email mein kya likhna hai?") if subject else ""
        if recipient and subject and body:
            if "@" in recipient:
                if confirm_action(f"{recipient} ko email send karu"):
                    send_email_smtp(recipient,subject,body)
            else:
                email_message_saved_recipient(recipient,subject,body)
        return True

    if "weather" in text or "mausam" in text:
        get_weather(text); return True

    if "news" in text or "khabar" in text:
        topic=re.sub(r"\b(aaj|ki|news|khabar|batao|latest|today)\b"," ",text,flags=re.I); topic=re.sub(r"\s+"," ",topic).strip() or "technology"
        get_news(topic); return True

    if "reminder" in text or "yaad dilana" in text or "yaad dila dena" in text:
        if confirm_action(f"reminder set karunga: {original_text}"): set_reminder_simple(text)
        return True

    if text.startswith("mera task add karo") or text.startswith("task add karo") or text.startswith("todo add"):
        task=re.sub(r"^(mera )?task add karo[: ]*|^todo add[: ]*","",text).strip()
        if not task: task=listen_answer("Kaunsa task add karna hai?")
        if task and confirm_action(f"to-do list mein {task} add karunga"): add_todo(task)
        return True

    if "todo" in text or "to-do" in text or "mere task" in text:
        read_todos(); return True

    if text in ["forget all memory", "forget my memory", "jarvis memory clear", "sab memory bhool jao", "meri memory delete karo"]:
        if confirm_action("saved notes aur conversational context clear karunga"):
            reset_user_controlled_memory()
        return True

    if text.startswith("yaad rakho") or text.startswith("remember this"):
        note=re.sub(r"^(yaad rakho|remember this)[: ]*","",original_text,flags=re.I).strip()
        if note and confirm_action(f"note memory mein save karunga: {note}"): remember_note(note)
        return True

    if "maine kya yaad" in text or "notes memory" in text or "kya yaad rakhne" in text:
        recall_notes(); return True

    if text in ["copy","copy karo"]:
        if confirm_action("selected content copy karunga"): clipboard_action("copy")
        return True
    if text in ["paste","paste karo"]:
        if confirm_action("clipboard paste karunga"): clipboard_action("paste")
        return True
    if "clipboard" in text:
        if confirm_action("clipboard ka text padhunga"): clipboard_action("read")
        return True

    if "brightness" in text:
        nums=re.findall(r"\d+",text)
        if nums and confirm_action(f"brightness {nums[0]} percent karunga"): set_brightness(nums[0])
        elif not nums: speak("Brightness kitne percent karni hai?")
        return True

    if "wifi" in text or "wi-fi" in text:
        if "status" in text:
            os.system("netsh wlan show interfaces") ; speak("Wi-Fi status terminal mein dikha diya hai.")
        elif confirm_action("Wi-Fi settings open karunga"): os.system("start ms-settings:network-wifi")
        return True

    if "bluetooth" in text:
        if confirm_action("Bluetooth settings open karunga"): os.system("start ms-settings:bluetooth")
        return True

    if any(x in text for x in ["ram","storage","disk usage","pc information","pc info","running apps"]):
        pc_details()
        if "running apps" in text:
            names=sorted({p.info['name'] for p in psutil.process_iter(['name']) if p.info.get('name')})[:30]
            print("\nRunning processes:\n"+"\n".join(names))
            speak("Running apps terminal mein dikha diye hain.")
        return True

    if "screenshot samjho" in text or "screen samjho" in text or "screen error" in text:
        if confirm_action("screen ka screenshot lekar AI se analyze karunga"): screenshot_understand()
        return True

    if "camera se dekho" in text or "camera analyze" in text or "camera se batao" in text:
        if confirm_action("camera se ek image capture karke analyze karunga"): camera_understand()
        return True

    if text.startswith("translate ") or "translate karo" in text:
        lang="English"
        for l in ["Marathi","Hindi","English"]:
            if l.lower() in text: lang=l
        content=re.sub(r"\b(translate|karo|into|in|marathi|hindi|english)\b"," ",original_text,flags=re.I); content=re.sub(r"\s+"," ",content).strip()
        if content: translate_with_ai(content,lang)
        return True

    if text.startswith("mujhe ") and any(x in text for x in ["padha","padhai","teach"]):
        topic=re.sub(r"\b(mujhe|padha|padhai|teach|karo)\b"," ",text); study_mode(re.sub(r"\s+"," ",topic).strip()); return True

    if "quiz" in text or "viva start" in text:
        topic=re.sub(r"\b(quiz|viva|start|karo|lo|mera|mujhe)\b"," ",text); topic=re.sub(r"\s+"," ",topic).strip() or "computer engineering"
        quiz_mode(topic); return True

    if any(x in text for x in ["code banao","program banao","coding mode"]):
        coding_mode(original_text); return True

    if any(x in text for x in ["calculate","calculate karo","percent of","percentage","convert "]):
        calculate_with_ai(original_text); return True

    if text.startswith("jab main ") and " bolu to " in text:
        if confirm_action("ye custom command save karunga"): save_custom_command(original_text)
        return True

    if "startup enable" in text or "windows ke sath start" in text or "auto start jarvis" in text:
        if confirm_action("Windows login ke saath Jarvis auto-start enable karunga"): enable_startup()
        return True
    if "startup disable" in text:
        if confirm_action("Jarvis auto-start disable karunga"): disable_startup()
        return True

    if any(x in text for x in ["file dhundo","folder dhundo","pdf dhundo","file search","folder search"]):
        if confirm_action(f"local files mein {original_text} search karunga"): search_local_file(text,open_result=True)
        return True

    if any(x in text for x in ["downloads kholo","documents kholo","desktop kholo"]):
        target=Path.home()/("Downloads" if "downloads" in text else "Documents" if "documents" in text else "Desktop")
        if confirm_action(f"{target.name} folder open karunga"): os.startfile(str(target))
        return True

    if text.endswith(".py kholo") or text.endswith(".pdf kholo") or text.endswith(".txt kholo"):
        if confirm_action(f"{original_text} search karke open karunga"): search_local_file(text,open_result=True)
        return True

    if "text file banao" in text or "python file banao" in text:
        topic=re.sub(r"\b(text|python|file|banao|bana do|ki|ka)\b"," ",text); topic=re.sub(r"\s+"," ",topic).strip() or "Jarvis notes"
        if confirm_action(f"{topic} ki file banaunga"): create_text_file(topic,"python" in text)
        return True

    # Generic installed app opener: "VS Code kholo", "Word kholo", etc.
    if text.endswith(" kholo") or text.startswith("open "):
        protected=["youtube","whatsapp","instagram","chrome","notepad","calculator","paint","camera","settings","file explorer","cmd"]
        if not any(p in text for p in protected):
            if confirm_action(f"{original_text} open karne ki koshish karunga"): dynamic_open_app(text)
            return True

    # ========================================================
    # NOTEPAD
    # Short commands:
    # note
    # notepad
    # notepad kholo
    # open notepad
    # ========================================================

    if (
        text in [
            "note",
            "notes",
            "notepad",
            "notepad kholo",
            "note kholo",
            "open notepad"
        ]
        or "notepad open" in text
    ):

        if confirm_action("Notepad open karunga"):
            open_notepad()

        return True


    # ========================================================
    # CALCULATOR
    # ========================================================

    if text in [
        "calculator",
        "calculator kholo",
        "calc",
        "calc kholo",
        "open calculator",
        "open calc"
    ]:

        if confirm_action("Calculator open karunga"):
            open_calculator()

        return True


    # ========================================================
    # PAINT
    # ========================================================

    if text in [
        "paint",
        "paint kholo",
        "open paint"
    ]:

        if confirm_action("Paint open karunga"):
            open_paint()

        return True


    # ========================================================
    # CAMERA
    # ========================================================

    if text in [
        "camera",
        "camera kholo",
        "open camera",
        "selfie",
        "selfie camera"
    ]:

        if confirm_action("Camera app open karunga"):
            open_camera()

        return True


    # ========================================================
    # SETTINGS
    # ========================================================

    if text in [
        "settings",
        "setting",
        "settings kholo",
        "setting kholo",
        "open settings",
        "open setting"
    ]:

        if confirm_action("Windows Settings open karunga"):
            open_settings()

        return True


    # ========================================================
    # FILE EXPLORER
    # ========================================================

    if text in [
        "files",
        "file",
        "file explorer",
        "file explorer kholo",
        "files kholo",
        "folder kholo",
        "folders",
        "my computer",
        "this pc",
        "open file explorer",
        "open files"
    ]:

        if confirm_action("File Explorer open karunga"):
            open_explorer()

        return True


    # ========================================================
    # CMD
    # ========================================================

    if text in [
        "cmd",
        "cmd kholo",
        "command prompt",
        "command prompt kholo",
        "open cmd",
        "open command prompt"
    ]:

        if confirm_action("Command Prompt open karunga"):
            open_cmd()

        return True


    # ========================================================
    # CHROME
    # ========================================================

    if text in [
        "chrome",
        "chrome kholo",
        "open chrome",
        "browser",
        "browser kholo"
    ]:

        if confirm_action("Microsoft Edge open karunga"):
            open_chrome()

        return True


    # ========================================================
    # YOUTUBE - OPEN ENDED USER INPUT
    # ========================================================

    if text in [
        "youtube",
        "youtube kholo",
        "open youtube",
        "youtube par play karo",
        "youtube pe play karo",
        "youtube par kuch play karo",
        "youtube pe kuch play karo",
        "kuch play karo"
    ]:

        if confirm_action("YouTube open karunga"):
            play_youtube_anything()

        return True


    # ========================================================
    # WHATSAPP
    # ========================================================

    if text in [
        "whatsapp",
        "whatsapp kholo",
        "open whatsapp",
        "whatsapp web"
    ]:

        if confirm_action("WhatsApp open karunga"):
            try:
                os.startfile("whatsapp:")
            except Exception:
                open_whatsapp()

        return True


    # ========================================================
    # INSTAGRAM
    # ========================================================

    if text in [
        "instagram",
        "instagram kholo",
        "open instagram",
        "insta",
        "insta kholo"
    ]:

        if confirm_action("Instagram open karunga"):
            open_instagram()

        return True


    # ========================================================
    # GOOGLE SEARCH
    # ========================================================

    if (
        "google par" in text
        or "google pe" in text
        or "google mein" in text
        or "google me" in text
        or text.startswith("search ")
        or text.startswith("google ")
        or "search karo" in text
        or "dhoondho" in text
        or "dhundo" in text
    ):

        if confirm_action(f"web par search karunga: {original_text}"):
            google_search(text)

        return True


    # ========================================================
    # YOUTUBE DIRECT SEARCH / PLAY
    # Examples: Play Believer, Play Python tutorial, Play anything
    # ========================================================

    if text.startswith("play "):

        query = text[5:].strip()

        if confirm_action(f"YouTube par {query} search ya play karunga"):
            play_youtube_anything(query)

        return True


    if (
        text.endswith(" bajao")
        or text.endswith(" baja do")
        or text.endswith(" chalao")
        or text.endswith(" chala do")
        or "song bajao" in text
        or "song chalao" in text
        or "gaana bajao" in text
        or "gana bajao" in text
        or "gaana chalao" in text
        or "gana chalao" in text
    ):

        query = text

        for ending in [
            " song bajao",
            " song chalao",
            " gaana bajao",
            " gana bajao",
            " gaana chalao",
            " gana chalao",
            " baja do",
            " chala do",
            " bajao",
            " chalao"
        ]:
            if query.endswith(ending):
                query = query[:-len(ending)].strip()
                break

        if confirm_action(f"YouTube par {query if query else 'requested media'} search ya play karunga"):
            play_youtube_anything(query if query else None)

        return True


    # ========================================================
    # VOLUME UP
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "volume up",
            "volume badhao",
            "volume badao",
            "aawaz badhao",
            "awaz badhao",
            "sound badhao"
        ]
    ):

        for _ in range(5):
            pyautogui.press("volumeup")

        speak(
            "Volume badha diya hai."
        )

        return True


    # ========================================================
    # VOLUME DOWN
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "volume down",
            "volume kam",
            "volume kam karo",
            "aawaz kam",
            "awaz kam",
            "sound kam"
        ]
    ):

        for _ in range(5):
            pyautogui.press("volumedown")

        speak(
            "Volume kam kar diya hai."
        )

        return True


    # ========================================================
    # MUTE
    # ========================================================

    if text in [
        "mute",
        "mute karo",
        "sound mute",
        "volume mute"
    ]:

        pyautogui.press(
            "volumemute"
        )

        speak(
            "Mute toggle kar diya hai."
        )

        return True


    # ========================================================
    # MEDIA PLAY / PAUSE
    # ========================================================

    if text in [
        "pause",
        "pause karo",
        "media pause",
        "resume",
        "resume karo",
        "play pause",
        "music pause"
    ]:

        pyautogui.press(
            "playpause"
        )

        speak(
            "Media play pause kar diya hai."
        )

        return True


    # ========================================================
    # MINIMIZE ALL WINDOWS
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "sab minimize",
            "minimize all",
            "sab window minimize",
            "desktop dikhao",
            "show desktop",
            "sab chhupao"
        ]
    ):

        pyautogui.hotkey(
            "win",
            "d"
        )

        speak(
            "Saari windows minimize kar di hain."
        )

        return True


    # ========================================================
    # CLOSE CURRENT WINDOW
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "window band karo",
            "window close karo",
            "close window",
            "current window close",
            "app close karo",
            "app band karo"
        ]
    ):

        speak(
            "Current window close kar raha hoon."
        )

        pyautogui.hotkey(
            "alt",
            "f4"
        )

        return True


    # ========================================================
    # LOCK LAPTOP
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "laptop lock",
            "lock laptop",
            "lock screen",
            "computer lock",
            "pc lock"
        ]
    ):

        speak(
            "Laptop lock kar raha hoon."
        )

        os.system(
            "rundll32.exe user32.dll,LockWorkStation"
        )

        return True


    # ========================================================
    # VOICE TYPING
    # ========================================================

    if (
        text.startswith("type karo ")
        or text.startswith("type ")
        or text.startswith("likho ")
        or text.startswith("write ")
    ):

        typing_text = text

        prefixes = [
            "type karo ",
            "type ",
            "likho ",
            "write "
        ]

        for prefix in prefixes:

            if typing_text.startswith(prefix):

                typing_text = typing_text[
                    len(prefix):
                ]

                break

        typing_text = typing_text.strip()

        if typing_text:

            speak(
                "Type kar raha hoon."
            )

            time.sleep(0.5)

            pyautogui.write(
                typing_text,
                interval=0.04
            )

        else:

            speak(
                "Kya type karna hai?"
            )

        return True


    # ========================================================
    # ENTER KEY
    # ========================================================

    if text in [
        "enter",
        "enter dabao",
        "press enter",
        "enter press karo"
    ]:

        pyautogui.press(
            "enter"
        )

        speak(
            "Enter press kar diya hai."
        )

        return True


    # ========================================================
    # BACKSPACE
    # ========================================================

    if text in [
        "backspace",
        "backspace dabao",
        "delete last"
    ]:

        pyautogui.press(
            "backspace"
        )

        speak(
            "Backspace press kar diya hai."
        )

        return True


    # ========================================================
    # BATTERY / SYSTEM STATUS
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "battery",
            "battery kitni hai",
            "charging",
            "system status",
            "cpu",
            "cpu usage",
            "laptop status"
        ]
    ):

        system_status()

        return True


    # ========================================================
    # SCREENSHOT
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "screenshot",
            "screenshot lo",
            "screen shot",
            "screen shot lo",
            "screenshot lena"
        ]
    ):

        take_screenshot()

        return True


    # ========================================================
    # TIMER
    # ========================================================

    if (
        "timer" in text
        or (
            "second" in text
            and "lagao" in text
        )
        or (
            "minute" in text
            and "timer" in text
        )
    ):

        set_timer_from_text(text)

        return True


    # ========================================================
    # ALARM
    # ========================================================

    if "alarm" in text:

        set_alarm_from_text(text)

        return True


    # ========================================================
    # TIME
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "time kya hua",
            "time kya hai",
            "kitne baje",
            "what time",
            "what is the time",
            "current time",
            "samay kya hai"
        ]
    ):

        current_time = (
            datetime.datetime.now()
            .strftime("%I:%M %p")
        )

        speak(
            f"Abhi {current_time} hue hain."
        )

        return True


    # ========================================================
    # DATE
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "date kya hai",
            "aaj ki date",
            "aaj kya tarikh",
            "aaj ki tarikh",
            "what is the date",
            "today date",
            "today's date"
        ]
    ):

        current_date = (
            datetime.datetime.now()
            .strftime("%d %B %Y")
        )

        speak(
            f"Aaj {current_date} hai."
        )

        return True


    # ========================================================
    # AI PDF
    # ========================================================

    if (
        "pdf banao" in text
        or "pdf bana do" in text
        or "create pdf" in text
        or "make pdf" in text
        or "pdf tayyar karo" in text
    ):

        topic = text

        remove_words = [
            "jarvis",
            "mujhe",
            "pdf banao",
            "pdf bana do",
            "create pdf",
            "make pdf",
            "pdf tayyar karo",
            "par",
            "pe",
            "ka",
            "ki"
        ]

        for word in remove_words:

            topic = topic.replace(
                word,
                " "
            )

        topic = re.sub(
            r"\s+",
            " ",
            topic
        ).strip()

        if topic:

            if confirm_action(f"{topic} topic par PDF generate karunga"):
                create_pdf_file(topic)

        else:

            speak(
                "Kis topic par PDF banani hai?"
            )

        return True


    # ========================================================
    # AI IMAGE
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "image banao",
            "image bana do",
            "photo banao",
            "photo bana do",
            "tasveer banao",
            "generate image",
            "create image"
        ]
    ):

        topic = text

        remove_words = [
            "jarvis",
            "mujhe",
            "image banao",
            "image bana do",
            "photo banao",
            "photo bana do",
            "tasveer banao",
            "generate image",
            "create image"
        ]

        for word in remove_words:

            topic = topic.replace(
                word,
                " "
            )

        topic = re.sub(
            r"\s+",
            " ",
            topic
        ).strip()

        if topic:

            if confirm_action(f"{topic} ke liye AI image generate karke save karunga"):
                create_ai_image(topic)

        else:

            speak(
                "Kiski image banani hai?"
            )

        return True


    # ========================================================
    # AI NLU + CONTEXT-AWARE TASK PLANNING (V12 ADDITION)
    # Existing explicit command handlers above retain priority.
    # ========================================================

    plan = classify_and_plan_command(original_text)
    if plan:
        intent = plan.get("intent")
        if intent == "plan":
            steps = plan.get("steps", [])
            summary = "; phir ".join(
                f"{step['action'].replace('_', ' ')}: {step['query']}" for step in steps
            )
            speak("Maine ye steps plan kiye hain: " + summary + ". Har step se pehle confirmation loonga.")
            execute_ai_plan(plan)
            return True
        if intent == "clarify":
            speak(plan.get("reply") or "Thoda aur clearly batao ki kya karna hai.")
            return True
        # Ordinary conversation and questions use the existing conversational AI memory.

    # If the API key is unavailable, still respond supportively to clear mood-related messages.
    if not GROQ_API_KEY:
        mood_reply = local_mood_response(original_text)
        if mood_reply:
            speak(mood_reply)
            return True

    reply = ask_ai(original_text)
    speak(reply)
    return True


# ============================================================
# WAKE / SLEEP MODE
# ============================================================

WAKE_COMMANDS = [
    "hello jarvis",
    "hey jarvis",
    "hi jarvis",
    "good morning",
    "good morning jarvis",
    "good afternoon",
    "good afternoon jarvis",
    "good evening",
    "good evening jarvis",
    "uth jao",
    "jarvis uth jao",
    "wake up",
    "wake up jarvis"
]


def is_wake_command(text):
    cleaned = (text or "").lower().strip()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Google STT often hears "Jarvis" as "jar", "service", etc.
    direct = [
        "hello jarvis", "hello jar", "hey jarvis", "hey jar", "hi jarvis",
        "good morning", "good morning jarvis", "good afternoon",
        "good evening", "uth jao", "jarvis uth jao", "wake up", "wake up jarvis"
    ]
    if any(x in cleaned for x in direct):
        return True

    words = cleaned.split()
    if words and words[0] in ("hello", "hey", "hi"):
        return any(w.startswith("jar") for w in words[1:3])
    return False


def wake_reply():

    hour = datetime.datetime.now().hour

    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 22:
        greeting = "Good evening"
    else:
        greeting = "Hello"

    speak(
        f"{greeting}! Jarvis is awake. How can I help you?"
    )


def security_hotkey_monitor():
    """Local Ctrl+Alt+J monitor for unlocking a Jarvis session."""
    global SESSION_LOCKED, LAST_ACTIVITY_TIME
    was_down = False
    while True:
        try:
            down = ctrl_alt_j_pressed()
            if down and not was_down and SESSION_LOCKED and not PRIVACY_MODE:
                SESSION_LOCKED = False
                LAST_ACTIVITY_TIME = time.time()
                security_log("SESSION_UNLOCK", "Ctrl+Alt+J local hotkey")
                print("\n[SECURITY] Jarvis session locally UNLOCKED with Ctrl+Alt+J.")
                print_security_indicator("wake")
            was_down = down
            time.sleep(0.08)
        except Exception:
            time.sleep(0.2)


threading.Thread(target=security_hotkey_monitor, daemon=True).start()

# ============================================================
# STARTUP
# ============================================================

print("\n")
print("============================================")
print("             JARVIS STARTING")
print("============================================")
print("Jarvis running — wake listener active")
print("Jarvis sleep mode mein start hua hai.")
print_security_indicator("wake")
print("Wake command: Hello Jarvis / Good morning / Uth jao")
print("Safety mode: confirmation required before open/send/web/file actions")
calibrate_microphone_once()

# Start quietly in sleep mode.
# Program microphone se wake command sunta rahega.
jarvis_awake = False


# ============================================================
# MAIN CONTINUOUS LOOP
# ============================================================

def jarvis_voice_loop():
    global jarvis_awake, _last_console_mode
    while True:

        try:

            print("\n==========================================")

            # TRUE PRIVACY MODE: do not create/open sr.Microphone at all.
            if PRIVACY_MODE:
                jarvis_awake = False
                wait_in_true_privacy_mode()
                continue

            # Auto-sleep after inactivity while active.
            if jarvis_awake and (time.time() - LAST_ACTIVITY_TIME) >= AUTO_SLEEP_SECONDS:
                jarvis_awake = False
                gui_status("SLEEPING", "Say Hello Jarvis to wake me")
                security_log("AUTO_SLEEP", f"after {AUTO_SLEEP_SECONDS} seconds")
                print("Auto sleep: inactivity timeout.")
                print_security_indicator("wake")

            if jarvis_awake:
                if globals().get("_last_console_mode") != "active":
                    print("Jarvis AWAKE - Kuch bhi boliye:")
                    print_security_indicator("active")
                    _last_console_mode = "active"
            else:
                if globals().get("_last_console_mode") != "sleep":
                    print("Jarvis SLEEPING - 'Hello Jarvis' ya 'Uth jao' boliye:")
                    print_security_indicator("wake")
                    _last_console_mode = "sleep"

            gui_status("LISTENING", "Wake word sun raha hoon..." if not jarvis_awake else "Boliye, main sun raha hoon...")
            audio = capture_voice(
                timeout=3.5 if not jarvis_awake else 5,
                phrase_time_limit=5 if not jarvis_awake else 10
            )

            # ====================================================
            # SPEECH RECOGNITION
            # ====================================================

            text = recognize_voice(audio)

            print(
                "Aapne kaha:",
                text
            )
            gui_log("YOU", text)
            gui_status("THINKING", "Processing command...")

            update_activity()

            # ====================================================
            # SLEEP MODE - ONLY WAKE COMMANDS ARE ACCEPTED
            # ====================================================

            if not jarvis_awake:

                if is_wake_command(text):

                    jarvis_awake = True
                    _last_console_mode = None
                    gui_status("READY", "Awake • Ready when you are")
                    wake_reply()

                # Other speech is intentionally ignored while sleeping.
                continue

            # ====================================================
            # ALREADY AWAKE + WAKE COMMAND
            # ====================================================

            if is_wake_command(text):

                speak(
                    "Yes, Jarvis is already awake. Bataiye kya karna hai?"
                )

                continue

            # ====================================================
            # PROCESS NORMAL COMMAND
            # ====================================================

            command_result = process_command(
                text
            )

            # Privacy command received
            if command_result == "privacy":
                jarvis_awake = False
                continue

            # Sleep command received
            if command_result == "sleep":

                jarvis_awake = False
                _last_console_mode = None
                gui_status("SLEEPING", "Wake word only • Say Hello Jarvis")
                continue

            # Complete exit command received
            if command_result is False:
                break

        # ========================================================
        # NO SPEECH
        # ========================================================

        except sr.WaitTimeoutError:

            if jarvis_awake:
                print("Kuch sunai nahi diya...")
            else:
                pass

        # ========================================================
        # COULD NOT UNDERSTAND
        # ========================================================

        except sr.UnknownValueError:

            if jarvis_awake:
                print("Aawaz samajh nahi aayi...")
            else:
                pass

        # ========================================================
        # GOOGLE SPEECH RECOGNITION ERROR
        # ========================================================

        except sr.RequestError as error:

            print(
                "\nSPEECH RECOGNITION ERROR:",
                error
            )

            if jarvis_awake:
                speak(
                    "Speech recognition service se connect nahi ho raha."
                )

        # ========================================================
        # OTHER ERROR
        # ========================================================

        except KeyboardInterrupt:

            print(
                "\nJarvis manually stop kiya gaya."
            )

            break

        except Exception as error:

            print("\nPROGRAM ERROR:")
            print(type(error).__name__)
            print(error)

            gui_status("ERROR", f"{type(error).__name__}: retrying microphone")
            time.sleep(0.8)
            if jarvis_awake and not isinstance(error, AssertionError):
                speak("Ek technical problem aayi hai, lekin main abhi bhi running hoon.")
# ============================================================
# PROFESSIONAL DESKTOP GUI
# ============================================================

class JarvisGUI:
    def __init__(self):
        if not GUI_AVAILABLE:
            raise RuntimeError("customtkinter missing. Install: py -3.13 -m pip install customtkinter")

        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("JARVIS • Active AI Companion")
        self.root.geometry("1180x760")
        self.root.minsize(980, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.state = "SLEEPING"
        self.phase = 0.0
        self.messages_count = 0
        self.state_detail = "Say ‘Hello Jarvis’ when you need me"

        self.header = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.header.pack(fill="x", padx=30, pady=(22, 10))
        title_box = ctk.CTkFrame(self.header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="J A R V I S", font=("Segoe UI Semibold", 27)).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Direct Active Voice Assistant", font=("Segoe UI", 12), text_color="#8196a5").pack(anchor="w")
        self.clock = ctk.CTkLabel(self.header, text="", font=("Consolas", 14))
        self.clock.pack(side="right")
        self.online = ctk.CTkLabel(self.header, text="●  ONLINE", font=("Segoe UI Semibold", 12), text_color="#77e3bd")
        self.online.pack(side="right", padx=24)

        self.body = ctk.CTkFrame(self.root, corner_radius=22, border_width=1, border_color="#1d303a")
        self.body.pack(fill="both", expand=True, padx=30, pady=10)
        self.body.grid_columnconfigure(0, weight=3)
        self.body.grid_columnconfigure(1, weight=2)
        self.body.grid_rowconfigure(0, weight=1)

        self.visual = ctk.CTkFrame(self.body, fg_color="transparent")
        self.visual.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.canvas = tk.Canvas(self.visual, bg="#0b1116", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.chat_frame = ctk.CTkFrame(self.body, corner_radius=18, border_width=1, border_color="#20343e")
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=(0,18), pady=18)
        chat_head = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        chat_head.pack(fill="x", padx=18, pady=(16,8))
        ctk.CTkLabel(chat_head, text="CONVERSATION", anchor="w", font=("Segoe UI Semibold", 14)).pack(side="left")
        self.chat_hint = ctk.CTkLabel(chat_head, text="live", font=("Segoe UI", 11), text_color="#6f8b99")
        self.chat_hint.pack(side="right")
        self.chat = ctk.CTkTextbox(self.chat_frame, wrap="word", font=("Segoe UI", 14), corner_radius=12, border_width=0)
        self.chat.pack(fill="both", expand=True, padx=14, pady=(0,14))
        self.chat.configure(state="disabled")

        self.footer = ctk.CTkFrame(self.root, corner_radius=16, border_width=1, border_color="#1d303a")
        self.footer.pack(fill="x", padx=30, pady=(0,22))
        self.status = ctk.CTkLabel(self.footer, text="SLEEPING", font=("Segoe UI Semibold", 14))
        self.status.pack(side="left", padx=(18,10), pady=12)
        self.detail = ctk.CTkLabel(self.footer, text=self.state_detail, font=("Segoe UI", 13), text_color="#9eb2bd")
        self.detail.pack(side="left", padx=8)
        self.privacy = ctk.CTkLabel(self.footer, text="VOICE READY  •  LOCAL CONTROLS", font=("Segoe UI", 11), text_color="#6f8b99")
        self.privacy.pack(side="right", padx=18)

        self.root.after(80, self.animate)
        self.root.after(200, self.update_clock)

    def friendly_detail(self, state, detail=None):
        if detail:
            return str(detail)[:115]
        return {
            "SLEEPING": "Say ‘Hello Jarvis’ when you need me",
            "LISTENING": "I’m listening…",
            "THINKING": "One moment…",
            "SPEAKING": "Here’s what I found",
            "READY": "Ready when you are",
            "ERROR": "Something needs attention",
        }.get(state, "Ready when you are")

    def set_state(self, state, detail=None):
        def apply():
            self.state = str(state).upper()
            self.status.configure(text=self.state)
            self.state_detail = self.friendly_detail(self.state, detail)
            self.detail.configure(text=self.state_detail)
        self.root.after(0, apply)

    def add_message(self, role, text):
        def apply():
            self.messages_count += 1
            self.chat.configure(state="normal")
            stamp = datetime.datetime.now().strftime("%I:%M %p")
            label = "YOU" if str(role).upper() in ("USER", "YOU") else str(role).upper()
            self.chat.insert("end", f"{label}   {stamp}\n{text}\n\n")
            self.chat.see("end")
            self.chat.configure(state="disabled")
        self.root.after(0, apply)

    def update_clock(self):
        self.clock.configure(text=datetime.datetime.now().strftime("%d %b  •  %I:%M:%S %p"))
        self.root.after(1000, self.update_clock)

    def animate(self):
        self.phase += 0.055
        w = max(self.canvas.winfo_width(), 440)
        h = max(self.canvas.winfo_height(), 440)
        cx, cy = w/2, h/2 - 25
        self.canvas.delete("all")

        # ambient star/particle field - deterministic, smooth and subtle
        for i in range(34):
            a = i * 2.399 + self.phase * (0.05 if i % 2 else -0.035)
            rr = 120 + (i * 37) % 230
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.68
            size = 1 + (i % 3) * 0.45
            self.canvas.create_oval(x-size, y-size, x+size, y+size, fill="#173b4a", outline="")

        breath = (1 + math.sin(self.phase*1.45)) / 2
        activity = 3 + breath*5
        if self.state == "LISTENING": activity = 10 + 12*abs(math.sin(self.phase*2.3))
        elif self.state == "THINKING": activity = 8 + 7*breath
        elif self.state == "SPEAKING": activity = 11 + 15*abs(math.sin(self.phase*3.0))
        elif self.state == "SLEEPING": activity = 2 + breath*2

        # soft glow made from layered circles
        for i in range(8, 0, -1):
            r = 74 + i*8 + activity*.25
            shades = ["#0d1b22","#0d2029","#0e2530","#0e2a36","#10303d","#123744","#15404f","#18495a"]
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=shades[i-1], outline="")

        # orbital rings with broken arcs for a more premium HUD look
        for i in range(4):
            r = 92 + i*29 + activity*(.15+i*.06)
            start = (self.phase*(20 + i*8) * (-1 if i%2 else 1) * 57.3) % 360
            self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=start, extent=105+i*12,
                                   style="arc", outline=["#245268","#286b83","#2b86a0","#55c7df"][i], width=2)
            self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=start+180, extent=55+i*9,
                                   style="arc", outline=["#173d4e","#20586d","#24758d","#3aa7c0"][i], width=2)

        if self.state == "THINKING":
            for i in range(10):
                a = self.phase*2.2 + i*(math.pi/5)
                r = 150 + 5*math.sin(self.phase+i)
                x, y = cx + math.cos(a)*r, cy + math.sin(a)*r
                q = 2.5 + (i%3)
                self.canvas.create_oval(x-q,y-q,x+q,y+q,fill="#7ee7ff",outline="")

        core = 59 + activity*.18
        self.canvas.create_oval(cx-core, cy-core, cx+core, cy+core, fill="#081b24", outline="#5bd8f4", width=2)
        inner = 31 + 3.5*math.sin(self.phase*1.7)
        self.canvas.create_oval(cx-inner, cy-inner, cx+inner, cy+inner, fill="#68ddf5", outline="")
        eye = 12 + 2*breath
        self.canvas.create_oval(cx-eye, cy-eye, cx+eye, cy+eye, fill="#d7f9ff", outline="")

        state_line = {
            "SLEEPING":"Standing by",
            "LISTENING":"I’m listening",
            "THINKING":"Thinking",
            "SPEAKING":"Speaking",
            "READY":"Ready",
        }.get(self.state, self.state.title())
        self.canvas.create_text(cx, cy+190, text=state_line, fill="#d8f6fc", font=("Segoe UI Semibold", 18))
        self.canvas.create_text(cx, cy+218, text="JARVIS • PERSONAL AI", fill="#5f8493", font=("Segoe UI", 10))

        # living waveform, smoother than fixed bars
        if self.state in ("LISTENING", "SPEAKING"):
            points=[]
            width=245
            for j in range(61):
                x = cx-width/2 + j*(width/60)
                envelope = math.sin(math.pi*j/60)
                freq = 2.5 if self.state == "LISTENING" else 4.2
                y = cy+260 + math.sin(self.phase*freq + j*.55)*18*envelope + math.sin(self.phase*1.7+j*.19)*7*envelope
                points.extend([x,y])
            self.canvas.create_line(*points, fill="#69dff4", width=3, smooth=True)
        else:
            self.canvas.create_line(cx-95, cy+260, cx+95, cy+260, fill="#173d49", width=2)

        self.root.after(35, self.animate)

    def close(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()
        os._exit(0)

    def run(self):
        self.add_message("SYSTEM", "Ready. Say ‘Hello Jarvis’ to start.")
        threading.Thread(target=jarvis_voice_loop, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("AI note: GROQ_API_KEY environment variable set nahi hai; AI/NLU features require a key.")
    if not GUI_AVAILABLE:
        print("customtkinter installed nahi hai.")
        print("Run: py -3.13 -m pip install customtkinter")
    else:
        GUI_APP = JarvisGUI()
        GUI_APP.run()
