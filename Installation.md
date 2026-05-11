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

You have two options for installing the bot on Windows: using the standalone executable (easiest) or running it manually from the source code.

### Option 1: Quick Install (Executable)
The fastest way to get started on Windows is to use the pre-built `.exe` file.

1. Download the provided `.exe` file directly from this repository.
2. Double-click the downloaded file to run the application.

> **Note:** Windows SmartScreen or your antivirus might flag the file since it is an unrecognized download from GitHub. If this happens, click **"More info"** and then **"Run anyway"**.

### Option 2: Manual Setup (Git & Python)
If you prefer to run the application directly from the source code, open Command Prompt or PowerShell and execute these steps:
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

> **Tip for Windows Users:** If you have [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/en-us/windows/wsl/install) installed, you can simply open your WSL terminal and use the single-line Linux/macOS installation command instead!
