import os
from selenium.common.exceptions import TimeoutException

import re
import subprocess
import sys
import difflib
import shutil
import webbrowser
import requests
import json
import platform
import glob          
import send2trash 
import threading
import time
import base64
import pickle
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psutil
import shlex # command parsing klie

PROFILE_PATH = "/home/venom/.config/BraveSoftware/AutomationProfile"
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
BRAVE_BINARY = "/usr/bin/brave"
# --- Browser Session State ---
browser_session = {
    "driver": None,
    "current_url": None,
    "last_search": None,
    "last_query": None,
}

from llm_agent import get_llm_response

def extract_llm_intent(user_message):
    system_prompt = """
You are an intelligent Linux desktop voice/text agent. 
Recognize user intent and output *only* JSON in this schema (no extra explanation):
Do NOT include <think> or any explanation. Output must be only a valid JSON object or array of them.
{"action":"...", ...}
Either a single JSON object:
{"action":"...", ...}

Or an array of multiple actions:
[
  {"action":"...", ...},
  {"action":"...", ...}
]
You are allowed to return a list of multiple actions as a JSON array.

Example:
User says: "In Music folder, create palindrome.c and write a program"
→ Respond with:
[
  {"action":"create_folder", "folder_path":"~/Music"},
  {"action":"create_file", "folder_path":"~/Music", "filename":"palindrome.c", "content":"..."}
]

If folder already exists, the create_folder action is still valid — it won't overwrite anything.

- Always resolve folder paths as if they are inside the user's home directory.
- Example: "in downloads" → "~/Downloads"
- Example: "in downloads/code/level1" → "~/Downloads/code/level1"
- Example: "in music/notes/old" → "~/Music/notes/old"
- Never use '/home/user' or '/path/to/...'
- Always return folder paths using tilde (~) syntax: ~/Downloads/... or ~/Music/...
- Do NOT assume ~/Documents unless user says "Documents"


Supported actions:
- chat: for info, answer, chitchat, or if no other action matches
- create_folder: {"action":"create_folder", "folder_path":"/absolute/or/~/relative/path"}
- create_project: {"action":"create_project", "project_name":"Calculator", "location":"~/Documents", "language":"cpp", "gui":true/false}
- create_file: {"action":"create_file", "folder_path":"~/path", "filename":"main.cpp", "content":"..."}
- file_exists: {"action":"file_exists", "filename":"..."}
- open_file: {"action":"open_file", "filename":"..."}
- play_music: {"action":"play_music", "song":"Song Name"}
- stop_music: {"action":"stop_music"}
- wifi_status: {"action":"wifi_status"}
- next_music: {"action":"next_music"}
- get_weather: {"action":"get_weather", "city":"Nagpur"}
- wifi_status: {"action":"wifi_status"}
- bluetooth_devices: {"action":"bluetooth_devices"}
- connected_devices: {"action":"connected_devices"}
- general_knowledge: {"action":"general_knowledge", "question":"Who is the CEO of Tesla?"}
- trash_files: {"action":"trash_files", "path_pattern":"<path>"} # Moves files/folders to the system trash. Can handle single files, directories, and wildcards (*).
  - Always use real file paths like '~/Music/filename.ext'.
  If user says:
  - "delete file X in folder Y"
  - "remove main.c from inside palindrome program"
  - "delete a file from Documents/subfolder"
→ Respond with:
{"action":"delete_file", "filepath":"~/Documents/subfolder/main.c"}

If a subfolder is mentioned (like 'inside palidrone program'), resolve the full path and use delete_file.

Never default to create_file or create_folder unless verbs like "create", "make", or "generate" are used.
  - Example (file): User says "trash the screenshot.png file from Downloads" -> {"action":"trash_files", "path_pattern":"~/Downloads/screenshot.png"}
  - Example (folder): User says "delete the 'java utility' folder from documents" -> {"action":"trash_files", "path_pattern":"~/Documents/java utility"}
This will trash the entire contents of the folder.

Do NOT use delete_file for folders.

  - Example: User says "trash the screenshot.png file from Downloads" -> {"action":"trash_files", "path_pattern":"~/Downloads/screenshot.png"}
- change_wallpaper: {"action":"change_wallpaper", "image_path":"/path/to/image.jpg"}
- system_usage: {"action":"system_usage"}
- network_info: {"action":"network_info"}
- system_usage: {"action":"system_usage"}
- network_info: {"action":"network_info"}
- delete_file:  If user says "delete a folder" or "delete a directory", or uses folder-related words,
→ Use: {"action":"trash_files", "path_pattern":"~/Documents/foldername/*"}
    This will trash the entire contents of the folder.
    Do NOT use delete_file for folders.
  {"action":"delete_file", "filepath":"/path/to/file.txt"}
- change_wallpaper: {"action":"change_wallpaper", "image_path":"/path/to/image.jpg"}
- previous_music: {"action":"previous_music"}
- open_browser: {"action":"open_browser"}
- navigate_to: {"action":"navigate_to", "url":"..."}
- search_website: {"action":"search_website", "query":"..."}
- save_note: {"action": "save_note", "filename": "xyz.txt", "content": "your content"}
- remind_me: {"action": "remind_me", "message": "your message", "after_minutes": 10}
- search_web: {"action": "search_web", "query": "Who won India vs England latest test series"}
- send_whatsapp: {"action":"send_whatsapp", "contact":"...", "message":"..."}
- tell_time: {"action":"tell_time"}
- rename_file: {"action":"rename_file", "filepath":"~/Downloads/pytorch.pdf", "newname":"pytorchai.pdf"}
- tell_date: {"action":"tell_date"}
- announce: {"action":"announce", "message":"..."}
- network_info: {"action":"network_info"} # For fetching IPv4 and IPv6 addresses
- system_info: {"action":"system_info"}
- battery_status: {"action":"battery_status"}
- change_brightness: {"action":"change_brightness", "amount": -50}
- extract_pdf_text: {"action":"extract_pdf_text", "query":"..."}
If the request does not match these, default to {"action":"chat", "message":"..."} with a concise answer.
Never output any explanation outside of JSON!
"""
    prompt = system_prompt + "\n\nUser message: " + user_message
    llm_out = get_llm_response(prompt, code_only=False).strip()
    llm_out = re.sub(r'<think>.*?</think>', '', llm_out, flags=re.DOTALL).strip()
    llm_out = get_llm_response(prompt, code_only=False).strip()
    match = re.search(r'(\[.*?\]|\{.*?\})', llm_out, re.DOTALL)

    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception as e:
            print("❌ JSON parse error:", e)

    # fallback if no valid JSON matched
    return [{"action": "chat", "message": llm_out}]

def do_create_folder(folder_path):
    try:
        # Fix hallucinated /home/user or root-level /music
        folder = folder_path.replace("/home/user", "~")
        if folder.startswith("/"):
            folder = "~" + folder  # convert /Music → ~/Music
        
        folder = os.path.expanduser(folder)
        Path(folder).mkdir(parents=True, exist_ok=True)
        return f"✅ Folder created at: {folder}"
    except Exception as e:
        return f"❌ Could not create folder: {e}"

def fuzzy_find_path(user_input):
    """
    Brute-force fuzzy searches entire home directory for any file or folder matching input.
    Returns the best-matched full path if found, else None.
    """
    user_input = os.path.basename(user_input.strip().lower())  # Extract just the filename or folder
    home_dir = str(Path.home())
    all_matches = []

    for root, dirs, files in os.walk(home_dir):
        for name in dirs + files:
            score = difflib.SequenceMatcher(None, user_input, name.lower()).ratio()
            if score >= 0.7:
                full_path = os.path.join(root, name)
                all_matches.append((score, full_path))

    if not all_matches:
        return None

    # Sort by highest match ratio
    all_matches.sort(reverse=True, key=lambda x: x[0])
    best_match = all_matches[0][1]
    return best_match


def do_search_web(query):
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        response = requests.post(url, headers=headers, data=data, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Get the first result block
        results = soup.select("a.result__a")
        if results:
            title = results[0].text.strip()
            return f"🌐 {title}"

        # Try fallback paragraph extraction
        snippets = soup.select("div.result__snippet")
        if snippets:
            return f"🌐 {snippets[0].text.strip()}"

        return f"❌ No meaningful answer found for: {query}"

    except Exception as e:
        return f"❌ Web search failed: {e}"


        return f"🌐 {snippet}" if snippet else "❌ No answer found."
    except Exception as e:
        return f"❌ DuckDuckGo search failed: {e}"


def do_get_weather(city_name=None):
    try:
        if not city_name:
            return "❌ Please specify a city to get weather info."

        url = f"https://wttr.in/{city_name}?format=3"
        resp = requests.get(url).text.strip()

        if "Unknown location" in resp:
            return f"❌ Weather info not available for '{city_name}'."

        return f"🌦️ {resp}"
    except Exception as e:
        return f"❌ Error fetching weather: {e}"
import psutil # Make sure this is at the top of your file

def do_trash_files(path_pattern):
    """
    Finds files/directories matching a pattern and moves them to the system Trash.
    Fuzzy matches files/folders even if the case or spelling is slightly off.
    """
    try:
        expanded_path = os.path.expanduser(path_pattern)
        items_to_trash = glob.glob(expanded_path)

        # If no exact glob match, try literal path or fuzzy
        if not items_to_trash:
            if os.path.exists(expanded_path):
                items_to_trash = [expanded_path]
            else:
                fuzzy_path = fuzzy_find_path(path_pattern)
                if fuzzy_path and os.path.exists(fuzzy_path):
                    items_to_trash = [fuzzy_path]
                else:
                    return f"🤷 No files or directories found matching: {path_pattern}"

        for item in items_to_trash:
            print(f"🚮 Moving to trash: {item}")
            send2trash.send2trash(item)

        count = len(items_to_trash)
        preview = ", ".join(os.path.basename(p) for p in items_to_trash[:3])
        if count > 3:
            preview += "..."
        item_type = "item" if count == 1 else "items"

        return f"✅ Moved {count} {item_type} to the Trash (e.g., {preview})."

    except Exception as e:
        return f"❌ Error while trying to move files to Trash: {e}"

def do_save_note(filename, content):
    try:
        notes_dir = os.path.expanduser("~/LuciferNotes")
        Path(notes_dir).mkdir(parents=True, exist_ok=True)

        filepath = os.path.join(notes_dir, filename if filename.endswith(".txt") else filename + ".txt")
        with open(filepath, "w") as f:
            f.write(content)

        subprocess.Popen(['kwrite', filepath])
        return f"📝 Note saved to: {filepath} (opened in KWrite)"
    except Exception as e:
        return f"❌ Could not save note: {e}"


def do_remind_me(message, after_minutes):
    def notify():
        time.sleep(after_minutes * 60)
        subprocess.run(['notify-send', 'Lucifer Reminder', message])
        subprocess.run(['espeak', f'Reminder: {message}'])

    threading.Thread(target=notify, daemon=True).start()
    return f"⏰ Reminder set for {after_minutes} minutes from now."


def do_get_network_info():
    """Fetches IPv4 and IPv6 addresses for all network interfaces."""
    addrs = psutil.net_if_addrs()
    info = "🌐 Network Information:\n"
    has_info = False
    for interface, addresses in addrs.items():
        # Skip the loopback interface
        if interface == 'lo':
            continue
            
        ipv4 = next((addr.address for addr in addresses if addr.family == psutil.AF_INET), "N/A")
        ipv6 = next((addr.address for addr in addresses if addr.family == psutil.AF_INET6), "N/A")
        
        # Only include interfaces that have a valid IP address
        if ipv4 != "N/A" or ipv6 != "N/A":
            info += f"- {interface}:\n  - IPv4: {ipv4}\n  - IPv6: {ipv6}\n"
            has_info = True

    if not has_info:
        return "❌ No active network interfaces with IP addresses were found."
        
    return info


def do_create_project(project_name, location, language, gui):
    try:
        # Fix LLM hallucination of /home/user
        location = location.replace("/home/user", "~")

        # Full project path
        base = os.path.expanduser(os.path.join(location, project_name))
        Path(base).mkdir(parents=True, exist_ok=True)

        skeleton_code = ""
        ext = ""
        language_lower = language.lower()
        gui = gui if isinstance(gui, bool) else False  # Fallback

        if language_lower in ["cpp", "c++"]:
            ext = "cpp"
            skeleton_code = '''#include <iostream>
using namespace std;
int main() {
    cout << "Calculator Program" << endl;
    // Add your calculator logic here
    return 0;
}'''
            if gui:
                skeleton_code += "\n// TODO: Add GUI code (Qt, GTK, etc.)"

        elif language_lower == "c":
            ext = "c"
            skeleton_code = '''#include <stdio.h>
int main() {
    printf("Calculator Program\\n");
    // Add your calculator logic here
    return 0;
}'''
            if gui:
                skeleton_code += "\n// TODO: Add GUI code (GTK+ or ncurses)"

        elif language_lower == "python":
            ext = "py"
            skeleton_code = 'print("Calculator Program")\n# Add your calculator logic here\n'
            if gui:
                skeleton_code += "# TODO: Add GUI (Tkinter, PyQt)"

        elif language_lower == "java":
            ext = "java"
            skeleton_code = f'''public class {project_name} {{
    public static void main(String[] args) {{
        System.out.println("Calculator Program");
        // Add your calculator logic here
    }}
}}'''
            if gui:
                skeleton_code += "\n// TODO: Add GUI (Swing, JavaFX)"

        else:
            return f"✅ Created folder '{project_name}' at {base} (language '{language}' not recognized)"

        filename = f"main.{ext}"
        filepath = os.path.join(base, filename)

        with open(filepath, 'w') as f:
            f.write(skeleton_code)

        return f"✅ Project '{project_name}' created with {language} skeleton at {base}"

    except Exception as e:
        return f"❌ Project creation error: {e}"


def do_create_file(folder_path, filename, content):
    try:
        folder = folder_path.replace("/home/user", "~")
        if folder.startswith("/"):
            folder = "~" + folder

        folder = os.path.expanduser(folder)
        Path(folder).mkdir(parents=True, exist_ok=True)

        filep = os.path.join(folder, filename)
        with open(filep, "w") as f:
            f.write(content)
        return f"✅ File '{filename}' created at: {filep}"
    except Exception as e:
        return f"❌ Could not create file: {e}"
    
    
def get_code_for_file(purpose, language="c"):
    prompt = f"Write a complete {language} program for this purpose:\n\n{purpose}"
    return get_llm_response(prompt, code_only=True)


def do_file_exists(filename):
    resolved_path = fuzzy_find_path(filename)
    if resolved_path and os.path.isfile(resolved_path):
        return f"✅ File found: {resolved_path}"
    return f"❌ File '{filename}' not found in your home directory."


def do_get_system_usage():
    """Fetches real-time CPU and RAM usage."""
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    return f"💻 CPU Usage: {cpu_usage}%\n🧠 RAM Usage: {ram_usage}% ({ram.used/1024**3:.2f}GB / {ram.total/1024**3:.2f}GB)"

def do_get_network_info():
    """Fetches IPv4 and IPv6 addresses for all network interfaces."""
    addrs = psutil.net_if_addrs()
    info = "🌐 Network Information:\n"
    for interface, addresses in addrs.items():
        ipv4 = next((addr.address for addr in addresses if addr.family == psutil.AF_INET), "N/A")
        ipv6 = next((addr.address for addr in addresses if addr.family == psutil.AF_INET6), "N/A")
        if ipv4 != "N/A" or ipv6 != "N/A":
            info += f"- {interface}:\n  - IPv4: {ipv4}\n  - IPv6: {ipv6}\n"
    return info

def do_change_wallpaper(image_path):
    """Changes the desktop wallpaper for KDE Plasma."""
    try:
        expanded_path = os.path.expanduser(image_path)
        if not os.path.exists(expanded_path):
            return f"❌ Image file not found at: {expanded_path}"

        # This script works for KDE Plasma to change the wallpaper on all screens
        jscript = f"""
        var allDesktops = desktops();
        for (i=0;i<allDesktops.length;i++) {{
            d = allDesktops[i];
            d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
            d.writeConfig("Image", "file://{expanded_path}");
        }}
        """
        cmd = ["qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", jscript]
        subprocess.run(cmd, check=True)
        return f"✅ Wallpaper changed to: {os.path.basename(image_path)}"
    except Exception as e:
        return f"❌ Failed to change wallpaper: {e}"

# Note for GNOME users: The command would be different, for example:
# gsettings set org.gnome.desktop.background picture-uri file:///path/to/image.jpg
def do_rename_file(filepath, newname):
    try:
        # Brute force search for actual file location
        resolved_path = fuzzy_find_path(filepath)
        if not resolved_path or not os.path.isfile(resolved_path):
            return f"❌ File not found: '{filepath}'"

        dirpath = os.path.dirname(resolved_path)
        newpath = os.path.join(dirpath, newname)

        os.rename(resolved_path, newpath)
        return f"✅ Renamed '{os.path.basename(resolved_path)}' to '{newname}' in {dirpath}"
    except Exception as e:
        return f"❌ Rename failed: {e}"

def do_wifi_status():
    try:
        ssid = subprocess.check_output("iwgetid -r", shell=True).decode().strip()
        return f"📶 Connected to WiFi: {ssid}" if ssid else "❌ Not connected to any WiFi."
    except:
        return "❌ Could not fetch WiFi details."


def do_open_file(filename):
    try:
        resolved_path = fuzzy_find_path(filename)
        if not resolved_path or not os.path.isfile(resolved_path):
            return f"❌ File '{filename}' not found."
        subprocess.Popen(['xdg-open', resolved_path])
        return f"✅ File opened: {resolved_path}"
    except Exception as e:
        return f"❌ Error opening file: {e}"


def do_play_music(song):
    import urllib.parse
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(song)}"
    try:
        html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
        ids = re.findall(r"watch\?v=(\w{11})", html)
        if not ids or not isinstance(ids[0], str):
            return f"❌ No YouTube video found for '{song}'."
        video_url = f"https://www.youtube.com/watch?v={ids[0]}"

        webbrowser.open(video_url)
        return f"✅ Playing '{song}' on YouTube."
    except Exception as e:
        return f"❌ Failed to play song: {e}"

def do_stop_music():
    os.system("pkill -f 'brave|firefox|chrome|chromium'")
    return "✅ Stopped browser music (browser killed)."

def do_control_media(cmd):
    try:
        subprocess.run(['playerctl', cmd])
        return f"Media {cmd} executed."
    except Exception as e:
        return f"❌ Failed: {e}"

def do_change_brightness(amount: int):
    try:
        current = int(subprocess.check_output(['brightnessctl', 'g']).decode().strip())
        max_val = int(subprocess.check_output(['brightnessctl', 'm']).decode().strip())
        new = max(1, min(max_val, current + int((amount/100)*max_val)))
        subprocess.run(['brightnessctl', 's', str(new)])
        return f"✅ Brightness adjusted by {amount}%."
    except Exception as e:
        return f"❌ Failed to change brightness: {e}"
def do_delete_file(filepath):
    try:
        resolved_path = fuzzy_find_path(filepath)
        if not resolved_path or not os.path.isfile(resolved_path):
            return f"❌ File not found: {filepath}"
        os.remove(resolved_path)
        return f"✅ Successfully deleted file: {resolved_path}"
    except Exception as e:
        return f"❌ Error deleting file: {e}"


        filepath = filepath.replace("/home/user", "~")
        if filepath.startswith("/"):
            filepath = "~" + filepath.lstrip("/")  # /Music → ~/Music

        expanded_path = os.path.expanduser(filepath)
        if not os.path.exists(expanded_path):
            return f"❌ File not found at: {expanded_path}"

        os.remove(expanded_path)
        return f"✅ Successfully deleted file: {expanded_path}"

    except Exception as e:
        return f"❌ Error deleting file: {e}"



def do_open_browser():
    webbrowser.open("https://google.com")
    return "✅ Browser opened."

def do_navigate_to(url):
    webbrowser.open(url)
    return f"✅ Navigating to {url}"

def do_search_website(query):
    url = f"https://www.google.com/search?q={query.replace(' ','+')}"
    webbrowser.open(url)
    return f"✅ Searching: {query}"

def send_whatsapp_message(driver, contact_name, message):
    wait = WebDriverWait(driver, 30)
    driver.get("https://web.whatsapp.com")

    try:
        # Wait for search bar to appear
        search_box = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"][@role="textbox"]')))
        time.sleep(2)

        # Search contact
        search_box.click()
        search_box.clear()
        search_box.send_keys(contact_name)
        time.sleep(2)

        # Brute-force all chat containers to find first visible contact
        chat_containers = driver.find_elements(By.XPATH, '//div[@data-testid="cell-frame-container"]')
        found = False

        for chat in chat_containers:
            try:
                title_elem = chat.find_element(By.XPATH, './/span[@dir="auto"]')
                if contact_name.lower() in title_elem.text.lower():
                    driver.execute_script("arguments[0].click();", chat)
                    found = True
                    break
            except:
                continue

        if not found:
            return f"❌ No chat found matching '{contact_name}'"

        # Send the message
        input_box = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//footer//div[@contenteditable="true"][@role="textbox"]')))
        input_box.click()
        input_box.send_keys(message)
        input_box.send_keys(Keys.ENTER)

        time.sleep(1)
        return f"✅ Message sent to {contact_name}: '{message}'"

    except Exception as e:
        try:
            with open("wa_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except:
            pass
        return f"❌ Error sending message to '{contact_name}': {str(e)}"
    
def send_email(recipient_email, subject, message_body):
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = None

    try:
        # Load credentials
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

        # Gmail service
        service = build("gmail", "v1", credentials=creds)

        # Compose email
        message = EmailMessage()
        message.set_content(message_body or "This is a fallback message. (No content was provided.)")
        message["To"] = recipient_email.strip()  # Strip spaces to avoid invalid header
        message["From"] = creds._client_id  # or hardcode your email here if needed
        message["Subject"] = subject

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_result = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

        return f"✅ Email sent to {recipient_email} with subject '{subject}' (ID: {send_result['id']})"

    except Exception as e:
        with open("gmail_debug.log", "w", encoding="utf-8") as f:
            f.write("Error:\n" + str(e))
        return f"❌ Failed to send email: {str(e)}\nDebug saved to gmail_debug.log"
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import shutil
import os

def start_driver():
    options = Options()
    options.binary_location = "/usr/bin/brave"

    
    options.add_argument("--user-data-dir=/home/venom/.config/BraveSoftware/Brave-Browser")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_argument("--remote-debugging-port=9222")  # helps with DevToolsActivePort
    
    # Remove automation flag
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    CHROMEDRIVER_PATH = shutil.which("chromedriver")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    # Remove navigator.webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
        """
    })

    return driver

def do_tell_time():
    return "⏰ " + datetime.now().strftime("%H:%M:%S")

def do_tell_date():
    return "📆 " + datetime.now().strftime("%A, %d %B %Y")

def do_announce(message):
    try:
        subprocess.run(['espeak', message])
    except:
        pass
    return f"[Speak]: {message}"

def do_system_info():
    uname = platform.uname()
    ram_gb = round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024.**3), 2)
    return f"{uname.system} {uname.release} on {uname.node}. CPU: {uname.processor}. RAM: {ram_gb} GB"

def do_battery_status():
    try:
        import psutil
        b = psutil.sensors_battery()
        return f"🔋 {b.percent}% {'charging' if b.power_plugged else 'discharging'}"
    except:
        return "🔋 Battery status not available."
def do_wifi_status():
    try:
        ssid = subprocess.check_output("iwgetid -r", shell=True).decode().strip()
        return f"📶 Connected to WiFi: {ssid}" if ssid else "❌ Not connected to any WiFi."
    except:
        return "❌ Could not fetch WiFi details."
def do_bluetooth_devices():
    try:
        output = subprocess.check_output("bluetoothctl paired-devices", shell=True).decode().strip()
        return f"🔵 Paired Bluetooth Devices:\n{output}" if output else "🔵 No Bluetooth devices paired."
    except:
        return "❌ Could not get Bluetooth devices."
def do_connected_devices():
    try:
        out = subprocess.check_output("lsusb", shell=True).decode()
        return f"🖱️ Connected USB Devices:\n{out}"
    except:
        return "❌ Failed to fetch USB devices."
def do_general_knowledge(question):
    prompt = f"Answer concisely:\n\n{question}"
    return get_llm_response(prompt)

def generate_code_content(filename, purpose="calculator"):
    ext = os.path.splitext(filename)[1].lower()
    lang = {
        ".c": "C",
        ".cpp": "C++",
        ".py": "Python",
        ".java": "Java"
    }.get(ext, "C")

    prompt = f"Write a complete {lang} program for a basic {purpose}."
    return get_llm_response(prompt, code_only=True)


def do_chat(resp):
    return resp

def do_extract_pdf_text(query):
    try:
        url = subprocess.check_output([
            "qdbus", "org.kde.okular", "/okular", "org.kde.okular.getDocumentUrl"
        ]).decode().strip()
        if not url.startswith("file://"):
            return "❌ No PDF open in Okular."
        filepath = url.replace("file://", "")
        pdf_text = subprocess.check_output(["pdftotext", filepath, "-"]).decode()
        if not query:
            return "📄 PDF content:\n" + pdf_text[:1500]
        else:
            prompt = f"The PDF loaded in Okular has this content:\n\n{pdf_text[:5000]}\n\nUser asks: {query}"
            summary = get_llm_response(prompt, code_only=False)
            return summary
    except Exception as e:
        return f"❌ PDF extraction error: {e}"

action_mapping = {
    "create_folder": lambda d: do_create_folder(d.get("folder_path")),
    "create_project": lambda d: do_create_project(d.get("project_name"), d.get("location"), d.get("language"), d.get("gui")),
    "create_file": lambda d: do_create_file(
    d.get("folder_path"),
    d.get("filename"),
    d.get("content") if d.get("content") and d.get("content") != "..." else generate_code_content(
        filename=d.get("filename", "program.c"),
        purpose="calculator"
    )
),

    "file_exists": lambda d: do_file_exists(d.get("filename")),
    "open_file": lambda d: do_open_file(d.get("filename")),
    "play_music": lambda d: do_play_music(d.get("song")),
    "stop_music": lambda d: do_stop_music(),
    "next_music": lambda d: do_control_media("next"),
    "previous_music": lambda d: do_control_media("previous"),
    "search_web": lambda d: do_search_web(d.get("query")),
    "open_browser": lambda d: do_open_browser(),
    "navigate_to": lambda d: do_navigate_to(d.get("url")),
    "search_website": lambda d: do_search_website(d.get("query")),
   "send_whatsapp": lambda d: send_whatsapp_message(start_driver(), d.get("contact"), d.get("message")),
    "system_usage": lambda d: do_get_system_usage(),
    "get_weather": lambda d: do_get_weather(d.get("city", "Nagpur")),
    "wifi_status": lambda d: do_wifi_status(),
    "bluetooth_devices": lambda d: do_bluetooth_devices(),
    "connected_devices": lambda d: do_connected_devices(),
    "general_knowledge": lambda d: do_search_web(d.get("question")),
    "save_note": lambda d: do_save_note(d.get("filename"), d.get("content")),
    "remind_me": lambda d: do_remind_me(d.get("message"), int(d.get("after_minutes", 5))),

    "trash_files": lambda d: do_trash_files(d.get("path_pattern")),
    "network_info": lambda d: do_get_network_info(),
    "delete_file": lambda d: do_delete_file(d.get("filepath")),
    "change_wallpaper": lambda d: do_change_wallpaper(d.get("image_path")),
    "tell_time": lambda d: do_tell_time(),
    "tell_date": lambda d: do_tell_date(),
    "announce": lambda d: do_announce(d.get("message")),
    "network_info": lambda d: do_get_network_info(),
    "system_info": lambda d: do_system_info(),
    "battery_status": lambda d: do_battery_status(),
    "change_brightness": lambda d: do_change_brightness(int(d.get("amount", 0))),
    "extract_pdf_text": lambda d: do_extract_pdf_text(d.get("query")),
    "rename_file": lambda d: do_rename_file(d.get("filepath"), d.get("newname")),
    "chat": lambda d: do_chat(d.get("message")),
    "none": lambda d: "❌ Sorry, I could not understand your command.",
    "wifi_status": lambda d: do_wifi_status(),
   "send_email": lambda d: send_email(
    d.get("recipient"),
    d.get("subject"),
    d.get("message")
),
}
def handle_intent(user_message):
    intents = extract_llm_intent(user_message)
    results = []
    for intent in intents:
        print(f"\n[DEBUG] Extracted intent: {intent}\n")
        action = intent.get("action", "none")
        handler = action_mapping.get(action, action_mapping["none"])
        result = handler(intent)
        results.append(result)
    return "\n".join(results)
def main():
    print("👿 Lucifer Agent Ready. Speak your command (type 'exit' or 'quit' to stop).")
    while True:
        try:
            q = input("👿 Command me: ").strip()
            if q.lower() in ("exit", "quit"):
                print("👿 Lucifer Agent terminated.")
                break
            if not q:
                continue
            if q.lower().startswith("pdf"):
                query = q[3:].strip()
                print(do_extract_pdf_text(query))
                continue
            result = handle_intent(q)
            print(result)
        except (KeyboardInterrupt, EOFError):
            print("\n👿 Agent interrupted.")
            break

if __name__ == "__main__":
    main()
