# Installation Guide

Follow the instructions below to install and run **Devaster - Device Master** based on your operating system.

## 🐧 Linux & 🍏 macOS (Unix-based)

You can install and launch the bot automatically using our quick-install script. Open your terminal and paste the following command:
```bash
curl -fsSL [https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main/install_unix.sh](https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main/install_unix.sh) | DEVASTER_INSTALL_BASE="[https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main](https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main)" bash
```

> **Note:** If you run into permission issues, you may need to run the command with `sudo`.

---

## 🪟 Windows

Since the automated script is built for Unix environments, Windows users can quickly set up the bot manually using Git and Python. 

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

> **Tip for Windows Users:** Alternatively, if you have [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/en-us/windows/wsl/install) installed, you can simply open your WSL terminal and use the Linux/macOS installation command above.
