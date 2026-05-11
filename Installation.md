# Installation Guide

Follow the instructions below to install and run **Devaster - Device Master** based on your operating system.

## 🐧 Linux & 🍏 macOS (Unix-based)

You can install, pair, and launch the bot automatically using our quick-install script. Open your terminal and paste the following command:

```bash
curl -fsSL [https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main/install_unix.sh](https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main/install_unix.sh) | bash
```

> **Note:** During installation, you will be prompted to enter a 6-digit pairing code from Telegram and asked if you want the bot to run automatically in the background on startup.

---

## 🪟 Windows

Since the automated script is built for Unix environments, Windows users can set up the bot manually using Git and Python. 

Open Command Prompt or PowerShell and execute these steps:
```powershell
# 1. Clone the repository
git clone [https://github.com/Anmol-06/Devaster---Device-Master.git](https://github.com/Anmol-06/Devaster---Device-Master.git)

# 2. Navigate into the directory
cd Devaster---Device-Master

# 3. Install required Python dependencies
pip install -r requirements.txt

# 4. Start the application
python app.py
```

> **Tip for Windows Users:** If you have [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/en-us/windows/wsl/install) installed, you can simply open your WSL terminal and use the single-line Linux/macOS installation command above!
