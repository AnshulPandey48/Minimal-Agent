A multi-purpose intelligent agent for Linux desktops that can interact with your system like a sarcastic AI devil. It supports voice/text interaction and can perform tasks like file management, media control, weather, WhatsApp automation, reminders, PDF reading, Gmail automation, web scraping, and even code generation — all served with dark humor and LLM-powered responses.

Langchain implementation on the way!!!

User Input

   |
   
   v
   
LLM Agent (Intent Extractor)

   |
   
   v
   
Action Parser & Handler Dispatcher

   |
   
   v
   
───────────────┐

               v
               
[System Actions]  ←→ [Web APIs]

[Browser Control] ←→ [Selenium + Brave]

[Gmail Integration] ←→ [OAuth + Google API]

[WhatsApp Bot] ←→ [Selenium + WhatsApp Web]

[PDF Reader] ←→ [Okular + pdftotext]

[Media Control] ←→ [Playerctl]

[Weather/API] ←→ [wttr.in or DuckDuckGo]

[Code Generator] ←→ [LLM call (via Ollama/local LLM)]


| Feature                      | Description                                      |
| ---------------------------- | ------------------------------------------------ |
|  Web Search                | Uses DuckDuckGo to get results                   |
|  Music Commands            | Play/Stop music via browser or YouTube           |
|  PDF Reader                | Reads open Okular PDFs, summarizes via LLM       |
|  Sarcastic Devil Agent     | Replies with dark humor and Lucifer-like sarcasm |
|  LLM Intent Recognition    | Uses local model via Ollama or API               |
|  Code Generator            | Generate C/C++/Python/Java code from text        |
|  File/Folder Automation    | Create, delete, rename, move                     |
|  Wallpaper Control         | Change KDE wallpaper                             |
|  Trash Manager             | Trash files/folders with fuzzy match             |
|  Reminders & Notes          | Save text notes & voice reminders                |
|  Gmail Sender              | Sends mails via Gmail using Google API           |
|  WhatsApp Messenger        | Sends WhatsApp messages (Selenium+Brave)         |
|  Battery/System Info       | CPU, RAM, Network, Devices                       |
|  Secure Text Commands      | All parsed via JSON for secure, explainable flow |
|  Ollama Support (Optional) | Add LLM support via `get_llm_response()`         |



AgentMultipurpose/

│
├── main.py   # Main execution + Intent handling

├── llm_agent.py              # (You must add this) Wrapper to connect to LLM (Ollama etc.)

├── credentials.json          # Gmail OAuth credentials

├── token.pickle              # Saved Gmail token after first run

├── README.md                 # (This doc)

├── gmail_debug.log           # Logs email errors

├── wa_debug.html             # WhatsApp debugging output

├── LuciferNotes/             # Saved notes by the agent

├── agent_config/             # Optional: You can move all paths/config here

│
└── requirements.txt

Yes, the agent replies like a pissed-off demon sometimes.

1.sudo apt install python3 python3-pip
pip install -r requirements.txt

2. Gmail API Setup (for Email Feature)
Go to Google Cloud Console
Enable Gmail API
Create OAuth2 credentials (Desktop App)
Download credentials.json into your project root
Run any email command once to generate token.pickle

3.WhatsApp Setup (Selenium)
Install Brave Browser
Install chromedriver (sudo apt install chromium-chromedriver)
Make sure it's in /usr/local/bin/chromedriver
Your WhatsApp account must be logged in Brave with --user-data-dir pointing to your profile (default: ~/.config/BraveSoftware/Brave-Browser)

4.  Ollama Setup (LLM)
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull mistral
  then in llm_agent.py:
  import requests
def get_llm_response(prompt, code_only=False):
    res = requests.post("http://localhost:11434/api/generate", json={"model": "mistral", "prompt": prompt})
    return res.json()['response']

5.How to use

    python3 main.py
    
   Command me: play let it go
   
   Command me: in music create project devil in c
   
   Command me: what’s the weather in Nagpur?
   
   Command me: create file palindrome.c in Downloads and write a palindrome program
   
   Command me: send email to someone@gmail.com with subject 'dark rise' and message 'lucifer rises again'
   
   Command me: remind me to eat at 5
   

6.SecurityNotes
No AI calls are made unless LLM is integrated

Gmail OAuth is local

WhatsApp is local browser automation

All file operations use send2trash instead of hard delete

All path parsing is sandboxed inside ~/


7.Future Features (Contribute?)

GUI (Qt-based UI)

LLM fallback chaining

Audio Command parser (offline whisper support)

File encryption via GPG

Encrypted vault management

Scriptable automation chains


